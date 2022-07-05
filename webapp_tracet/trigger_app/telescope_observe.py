import os
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time

from tracet.triggerservice import trigger_mwa, trigger_atca
from .models import Observations, VOEvent

import logging
logger = logging.getLogger(__name__)

def trigger_observation(
        proposal_decision_model,
        trigger_message,
        reason="First Observation",
    ):
    """Perform any comon observation checks, send off observations with the telescope's function then record observations in the Observations model.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    trigger_message : `str`
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
        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            #equinox='J2000',
            unit=(u.deg, u.deg)
        )
        # Convert from RA/Dec to Alt/Az
        obs_source_altaz = obs_source.transform_to(AltAz(obstime=Time.now(), location=location))
        alt = obs_source_altaz.alt.deg
        logger.debug("Triggered observation at an elevation of {0}".format(alt))
        if alt < proposal_decision_model.proposal.mwa_horizon_limit:
            horizon_message = f"Not triggering due to horizon limit: alt {alt} < {proposal_decision_model.proposal.mwa_horizon_limit}. "
            logger.debug(horizon_message)
            return 'I', trigger_message + horizon_message

    # above the horizon so send off telescope specific set ups
    if proposal_decision_model.proposal.telescope.name.startswith("MWA"):
        # If telescope ends in VCS then this proposal is for observing in VCS mode
        vcsmode = proposal_decision_model.proposal.telescope.name.endswith("VCS")

        # Create an observation name
        # Collect event telescopes
        voevents = VOEvent.objects.filter(trigger_group_id=proposal_decision_model.trigger_group_id)
        telescopes = []
        for voevent in voevents:
            telescopes.append(voevent.telescope)
        # Make sure they are unique and seperate with a _
        telescopes = "_".join(list(set(telescopes)))
        obsname=f'{telescopes}_{proposal_decision_model.trigger_id}'

        # Check if you can observe and if so send off ATCA observation
        decision, trigger_message, obsids = trigger_mwa_observation(
            proposal_decision_model,
            trigger_message,
            obsname,
            vcsmode=vcsmode,
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
        obsname=f'{proposal_decision_model.trigger_id}'
        decision, trigger_message, obsids = trigger_atca_observation(
            proposal_decision_model,
            trigger_message,
            obsname,
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
    return decision, trigger_message

def trigger_mwa_observation(
        proposal_decision_model,
        trigger_message,
        obsname,
        vcsmode=False,
    ):
    """Check if the MWA can observe then send it off the observation.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.
    vcsmode : `boolean`, optional
        True to observe in VCS mode and False to observe in correlator/imaging mode. Default: False

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    trigger_message : `str`
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
        ra=proposal_decision_model.ra, dec=proposal_decision_model.dec,
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
        trigger_message += f"Web API error, possible server error.\n "
        return 'E', trigger_message, []
    if not result['success']:
        # Observation not succesful so record why
        for err_id in result['errors']:
            trigger_message += f"{result['errors'][err_id]}.\n "
        # Return an error as the trigger status
        return 'E', trigger_message, []

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

    return 'T', trigger_message, obsids


def trigger_atca_observation(
        proposal_decision_model,
        trigger_message,
        obsname,
    ):
    """Check if the ATCA telescope can observe, send it off the observation and return any errors.

    Parameters
    ----------
    proposal_decision_model : `django.db.models.Model`
        The Django ProposalDecision model object.
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    obsname : `str`
        The name of the observation.

    Returns
    -------
    result : `str`
        The results of the attempt to observer where 'T' means it was triggered, 'I' means it was ignored and 'E' means there was an error.
    trigger_message : `str`
        The updated trigger message to include an observation specific logs.
    observations : `list`
        A list of observations that were scheduled by ATCA (currently there is no functionality to record this so will be empty).
    """
    prop_settings = proposal_decision_model.proposal

    # TODO add any schedule checks or observation parsing here

    # Check if source is in dec ranges the ATCA can not observe
    if proposal_decision_model.dec > 15.:
        return 'I', trigger_message + "Source is above a declination of 15 degrees so ATCA can not observe it.\n ", []
    elif -5. < proposal_decision_model.dec < 5.:
        return 'I', trigger_message + "Source is within 5 degrees of the equator (which is riddled with satelite RFI) so ATCA will not observe.\n ", []

    # Not below horizon limit so observer
    logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")
    # trigger_atca(
    #     project_id=prop_settings.project_id,
    #     secure_key=os.environ.get('ATCA_SECURE_KEY_FILE', None),
    #     ra=proposal_decision_model.ra, dec=proposal_decision_model.dec,
    #     source=obsname,
    #     freqspecs=[prop_settings.atca_freq1, prop_settings.atca_freq2],
    #     nobs=prop_settings.atca_nobs,
    #     exptime=prop_settings.atca_exptime,
    #     calexptime=prop_settings.atca_calexptime,
    #     pretend=prop_settings.testing,
    # )
    # TODO Check if succesful

    # TODO Output the results

    return 'T', trigger_message, []