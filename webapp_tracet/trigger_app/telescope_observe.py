import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from datetime import timedelta, datetime

import atca_rapid_response_api as arrApi

from tracet.triggerservice import trigger_mwa
from .models import Observations, Event

import logging
logger = logging.getLogger(__name__)

def trigger_observation(
        proposal_decision_model,
        decision_reason_log,
        reason="First Observation",
        event_id=None,
    ):
    """Perform any comon observation checks, send off observations with the telescope's function then record observations in the Observations model.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    """
    # Check if source is above the horizon
    if proposal_decision_model.proposal.telescope.name != "ATCA":
        # ATCA can schedule obs once the source has risen so does
        # not need to check if it is above the horizon

        # Create Earth location for the telescope
        telescope = proposal_decision_model.proposal.telescope
        location = EarthLocation(
            lon=telescope.lon*u.deg,
            lat=telescope.lat*u.deg,
            height=telescope.height*u.m
        )
        if proposal_decision_model.proposal.start_observation_at_high_sensitivity and not (proposal_decision_model.ra or proposal_decision_model.dec):
            #TODO: Replace with indian ocean high sensitivity area
            proposal_decision_model.alt = 20
            proposal_decision_model.az = 280
        else:
            obs_source = SkyCoord(
                proposal_decision_model.ra,
                proposal_decision_model.dec,
                #equinox='J2000',
                unit=(u.deg, u.deg)
            )
            # Convert from RA/Dec to Alt/Az
            obs_source_altaz_beg = obs_source.transform_to(AltAz(obstime=Time.now(), location=location))
            alt_beg = obs_source_altaz_beg.alt.deg
            # Calculate alt at end of obs
            end_time = Time.now() + timedelta(seconds=proposal_decision_model.proposal.mwa_exptime)
            obs_source_altaz_end = obs_source.transform_to(AltAz(obstime=end_time, location=location))
            alt_end = obs_source_altaz_end.alt.deg
            logger.debug(f"Triggered observation at an elevation of {alt_beg} to elevation of {alt_end}")
            if alt_beg < proposal_decision_model.proposal.mwa_horizon_limit and alt_end < proposal_decision_model.proposal.mwa_horizon_limit:
                horizon_message = f"{datetime.utcnow()}: Event ID {event_id}: Not triggering due to horizon limit: alt_beg {alt_beg:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f} and alt_end {alt_end:.4f} < {proposal_decision_model.proposal.mwa_horizon_limit:.4f}. "
                logger.debug(horizon_message)
                return 'I', decision_reason_log + horizon_message
            elif alt_beg < proposal_decision_model.proposal.mwa_horizon_limit:
                # Warn them in the log
                decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source is below the horizion limit at the start of the observation alt_beg {alt_beg:.4f}. \n"
            elif alt_end < proposal_decision_model.proposal.mwa_horizon_limit:
                # Warn them in the log
                decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Warning: The source will set below the horizion limit by the end of the observation alt_end {alt_end:.4f}. \n"

    # above the horizon so send off telescope specific set ups
    decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Above horizon so attempting to observer with {proposal_decision_model.proposal.telescope.name}. \n"
    if proposal_decision_model.proposal.telescope.name.startswith("MWA"):
        # If telescope ends in VCS then this proposal is for observing in VCS mode
        vcsmode = proposal_decision_model.proposal.telescope.name.endswith("VCS")

        # Create an observation name
        # Collect event telescopes
        voevents = Event.objects.filter(event_group_id=proposal_decision_model.event_group_id)
        telescopes = []
        for voevent in voevents:
            telescopes.append(voevent.telescope)
        # Make sure they are unique and seperate with a _
        telescopes = "_".join(list(set(telescopes)))
        obsname=f'{telescopes}_{proposal_decision_model.trig_id}'

        # Check if you can observe and if so send off MWA observation
        decision, decision_reason_log, obsids = trigger_mwa_observation(
            proposal_decision_model,
            decision_reason_log,
            obsname,
            vcsmode=vcsmode,
            event_id=event_id,
        )
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                obsid=obsid,
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=reason,
                website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )
    elif proposal_decision_model.proposal.telescope.name == "ATCA":
        # Check if you can observe and if so send off mwa observation
        obsname=f'{proposal_decision_model.trig_id}'
        decision, decision_reason_log, obsids = trigger_atca_observation(
            proposal_decision_model,
            decision_reason_log,
            obsname,
            event_id=event_id,
        )
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                obsid=obsid,
                telescope=proposal_decision_model.proposal.telescope,
                proposal_decision_id=proposal_decision_model,
                reason=reason,
                # TODO see if atca has a nice observation details webpage
                #website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )
    return decision, decision_reason_log

def trigger_mwa_observation(
        proposal_decision_model,
        decision_reason_log,
        obsname,
        vcsmode=False,
        event_id=None,
    ):
    """Check if the MWA can observe then send it off the observation.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.
    vcsmode : `boolean`, optional
        True to observe in VCS mode and False to observe in correlator/imaging mode. Default: False
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    observations : `list`
        A list of observations that were scheduled by MWA.
    """
    prop_settings = proposal_decision_model.proposal

    # Not below horizon limit so observer
    logger.info(f"Triggering MWA at UTC time {Time.now()} ...")
    result = trigger_mwa(
        project_id=prop_settings.project_id.id,
        secure_key=prop_settings.project_id.password,
        pretend=prop_settings.testing,
        ra=proposal_decision_model.ra, 
        dec=proposal_decision_model.dec,
        alt=proposal_decision_model.alt,
        az=proposal_decision_model.az,
        creator='VOEvent_Auto_Trigger', #TODO grab version
        obsname=obsname,
        nobs=prop_settings.mwa_nobs,
        freqspecs=prop_settings.mwa_freqspecs, #Assume always using 24 contiguous coarse frequency channels
        avoidsun=True,
        inttime=prop_settings.mwa_inttime,
        freqres=prop_settings.mwa_freqres,
        exptime=prop_settings.mwa_exptime,
        calibrator=True,
        calexptime=prop_settings.mwa_calexptime,
        vcsmode=vcsmode,
    )
    logger.debug(f"result: {result}")
    # Check if succesful
    if result is None:
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: Web API error, possible server error.\n "
        return 'E', decision_reason_log, []
    if not result['success']:
        # Observation not succesful so record why
        for err_id in result['errors']:
            decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: {result['errors'][err_id]}.\n "
        # Return an error as the trigger status
        return 'E', decision_reason_log, []

    # Output the results
    logger.info(f"Trigger sent: {result['success']}")
    logger.info(f"Trigger params: {result['success']}")
    if 'stdout' in result['schedule'].keys():
        if result['schedule']['stdout']:
            logger.info(f"schedule' stdout: {result['schedule']['stdout']}")
    if 'stderr' in result['schedule'].keys():
        if result['schedule']['stderr']:
            logger.info(f"schedule' stderr: {result['schedule']['stderr']}")

    # Grab the obsids (sometimes we will send of several observations)
    obsids = []
    for r in result['schedule']['stderr'].split("\n"):
        if r.startswith("INFO:Schedule metadata for"):
            obsids.append(r.split(" for ")[1][:-1])

    return 'T', decision_reason_log, obsids


def trigger_atca_observation(
        proposal_decision_model,
        decision_reason_log,
        obsname,
        event_id=None,
    ):
    """Check if the ATCA telescope can observe, send it off the observation and return any errors.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    decision_reason_log : `str`
        The updated trigger message to include an observation specific logs.
    observations : `list`
        A list of observations that were scheduled by ATCA (currently there is no functionality to record this so will be empty).
    """
    prop_obj = proposal_decision_model.proposal

    # TODO add any schedule checks or observation parsing here

    # Check if source is in dec ranges the ATCA can not observe
    if proposal_decision_model.dec > 15.:
        return 'I', f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Source is above a declination of 15 degrees so ATCA can not observe it.\n ", []
    elif -5. < proposal_decision_model.dec < 5.:
        return 'I', f"{decision_reason_log}{datetime.utcnow()}: Event ID {event_id}: Source is within 5 degrees of the equator (which is riddled with satelite RFI) so ATCA will not observe.\n ", []

    # Not below horizon limit so observer
    logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")

    rq = {
        "source": prop_obj.source_type,
        "rightAscension": proposal_decision_model.ra_hms,
        "declination": proposal_decision_model.dec_dms,
        "project": prop_obj.project_id.id,
        "maxExposureLength": str(timedelta(minutes=prop_obj.atca_max_exptime)),
        "minExposureLength": str(timedelta(minutes=prop_obj.atca_min_exptime)),
        "scanType": "Dwell",
        "3mm": {
            "use": prop_obj.atca_band_3mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_3mm_exptime)),
            "freq1": prop_obj.atca_band_3mm_freq1,
            "freq2": prop_obj.atca_band_3mm_freq2,
        },
        "7mm": {
            "use": prop_obj.atca_band_7mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_7mm_exptime)),
            "freq1": prop_obj.atca_band_7mm_freq1,
            "freq2": prop_obj.atca_band_7mm_freq2,
        },
        "15mm": {
            "use": prop_obj.atca_band_15mm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_15mm_exptime)),
            "freq1": prop_obj.atca_band_15mm_freq1,
            "freq2": prop_obj.atca_band_15mm_freq2,
        },
        "4cm": {
            "use": prop_obj.atca_band_4cm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_4cm_exptime)),
            "freq1": prop_obj.atca_band_4cm_freq1,
            "freq2": prop_obj.atca_band_4cm_freq2,
        },
        "16cm": {
            "use": prop_obj.atca_band_16cm,
            "exposureLength": str(timedelta(minutes=prop_obj.atca_band_16cm_exptime)),
            # Only frequency available due to limited bandwidth
            "freq1": 2100,
            "freq2": 2100,
        },
    }

    # We have our request now, so we need to craft the service request to submit it to
    # the rapid response service.
    rapidObj = { 'requestDict': rq }
    rapidObj["authenticationToken"] = prop_obj.project_id.password
    rapidObj["email"] = prop_obj.project_id.atca_email

    if prop_obj.testing:
        rapidObj["test"] = True
        rapidObj["noTimeLimit"] = True
        rapidObj["noScoreLimit"] = True

    request = arrApi.api(rapidObj)
    try:
        response = request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
        decision_reason_log += f"{datetime.utcnow()}: Event ID {event_id}: ATCA return message: {r}\n "
        return 'E', decision_reason_log, []

    # # Check for errors
    # if  (not response["authenticationToken"]["received"]) or (not response["authenticationToken"]["verified"]) or \
    #     (not response["schedule"]["received"]) or (not response["schedule"]["verified"]):
    #     decision_reason_log += f"ATCA return message: {r}\n "
    #     return 'E', decision_reason_log, []

    return 'T', decision_reason_log, [response["id"]]