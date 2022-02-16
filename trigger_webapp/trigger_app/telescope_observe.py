import os
import astropy.units as u
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time

from mwa_trigger.triggerservice import trigger_mwa, trigger_atca
from .models import Observations, VOEvent

import logging
logger = logging.getLogger(__name__)

def trigger_observation(project_decision_model,
                        trigger_message,
                        reason="First Observation"):
    """Wrap the differente observation functions
    """
    # Check if source is above the horizon
    # Create Earth location for the telescope
    telescope = project_decision_model.project.telescope
    location = EarthLocation(
        lon=telescope.lon*u.deg,
        lat=telescope.lat*u.deg,
        height=telescope.height*u.m
    )
    obs_source = SkyCoord(
        project_decision_model.ra,
        project_decision_model.dec,
        #equinox='J2000',
        unit=(u.deg, u.deg)
    )
    # Convert from RA/Dec to Alt/Az
    obs_source_altaz = obs_source.transform_to(AltAz(obstime=Time.now(), location=location))
    alt = obs_source_altaz.alt.deg
    logger.debug("Triggered observation at an elevation of {0}".format(alt))
    if alt < project_decision_model.project.horizon_limit:
        horizon_message = f"Not triggering due to horizon limit: alt {alt} < {project_decision_model.project.horizon_limit}. "
        logger.debug(horizon_message)
        return 'I', trigger_message + horizon_message

    # above the horizon so send off telescope specific set ups
    if project_decision_model.project.telescope.name.startswith("MWA"):
        # If telescope ends in VCS then this project is for observing in VCS mode
        vcsmode = project_decision_model.project.telescope.name.endswith("VCS")

        # Create an observation name
        # Collect event telescopes
        voevents = VOEvent.objects.filter(trigger_group_id=project_decision_model.trigger_group_id)
        telescopes = []
        for voevent in voevents:
            telescopes.append(voevent.telescope)
        # Make sure they are unique and seperate with a _
        telescopes = "_".join(list(set(telescopes)))
        obsname=f'{telescopes}_{project_decision_model.trigger_group_id.trigger_id}'

        # Check if you can observe and if so send off ATCA observation
        decision, trigger_message, obsids = trigger_mwa_observation(
            project_decision_model,
            trigger_message,
            obsname,
            vcsmode=vcsmode,
        )
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                obsid=obsid,
                telescope=project_decision_model.project.telescope,
                project_decision_id=project_decision_model,
                reason=reason,
                website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )
    elif project_decision_model.project.telescope.name == "ATCA":
        # Check if you can observe and if so send off mwa observation
        obsname=f'{project_decision_model.trigger_group_id.trigger_id}'
        decision, trigger_message, obsids = trigger_atca_observation(
            project_decision_model,
            trigger_message,
            obsname,
        )
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                obsid=obsid,
                telescope=project_decision_model.project.telescope,
                project_decision_id=project_decision_model,
                reason=reason,
                # TODO see if atca has a nice observation details webpage
                #website_link=f"http://ws.mwatelescope.org/observation/obs/?obsid={obsid}",
            )
    return decision, trigger_message

def trigger_mwa_observation(project_decision_model,
                            trigger_message,
                            obsname,
                            vcsmode=False):
    """Check if the mwa can observe then send it off the observation.
    """
    proj_settings = project_decision_model.project

    # Calculate number of obs and their duration
    if vcsmode:
        # VCS mode uses a single observation only
        nobs = 1
        exptime = proj_settings.mwa_exptime
    else:
        # normal observations split this time into 2 min chunks
        nobs = int(proj_settings.mwa_exptime / 120)
        exptime = 120

    # Not below horizon limit so observer
    logger.info(f"Triggering MWA at UTC time {Time.now()} ...")
    result = trigger_mwa(project_id=proj_settings.project_id,
        secure_key=os.environ['MWA_SECURE_KEY'],
        #group_id=project_decision_model.trigger_group_id.trigger_id, # only need this for follow up obs
        pretend=proj_settings.testing,
        ra=project_decision_model.ra, dec=project_decision_model.dec,
        creator='VOEvent_Auto_Trigger', #TODO grab version
        obsname=obsname,
        nobs=nobs,
        freqspecs=f"{proj_settings.mwa_centrefreq},24", #Assume always using 24 contiguous coarse frequency channels
        avoidsun=proj_settings.mwa_avoidsun,
        inttime=proj_settings.mwa_inttime,
        freqres=proj_settings.mwa_freqres,
        exptime=exptime,
        calibrator=proj_settings.mwa_calibrator,
        calexptime=proj_settings.mwa_calexptime,
        vcsmode=vcsmode,
        buffered=proj_settings.mwa_buffered,
    )
    # Check if succesful
    if result is None:
        trigger_message += f"Web API error, possible server error.\n "
        return 'E', trigger_message, []
    if not result['success']:
        # Observation not succesful so record why
        for err_id in result['error']:
            trigger_message += f"{result['error'][err_id]}.\n "
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


def trigger_atca_observation(project_decision_model,
                            trigger_message,
                            obsname,
                            vcsmode=False):
    """Check if the atca can observe then send it off the observation.
    """
    proj_settings = project_decision_model.project

    # TODO add any schedule checks or observation parsing here

    # Not below horizon limit so observer
    logger.info(f"Triggering  ATCA at UTC time {Time.now()} ...")
    trigger_atca(
        project_id=proj_settings.project_id,
        secure_key=os.environ['ATCA_SECURE_KEY_FILE'],
        ra=project_decision_model.ra, dec=project_decision_model.dec,
        source=obsname,
        freqspecs=[proj_settings.atca_freq1, proj_settings.atca_freq2],
        nobs=proj_settings.atca_nobs,
        exptime=proj_settings.atca_exptime,
        calexptime=proj_settings.atca_calexptime,
        pretend=proj_settings.testing,
    )
    # TODO Check if succesful

    # TODO Output the results

    return 'T', trigger_message, []