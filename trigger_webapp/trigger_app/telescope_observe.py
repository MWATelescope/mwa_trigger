import os
from astropy.units import deg
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

from mwa_trigger.triggerservice import trigger
from .models import Observations, VOEvent

import logging
logger = logging.getLogger(__name__)

def trigger_observation(project_decision_model,
                        trigger_message,
                        horizion_limit=30,
                        pretend=True,
                        reason="First Observation"):
    """Wrap the differente observation functions
    """
    if project_decision_model.project.telescope.startswith("MWA"):
        # If telescope ends in VCS then this project is for observing in VCS mode
        vcsmode = project_decision_model.project.telescope.endswith("VCS")

        # Check if you can observe and if so send off mwa observation
        decision, trigger_message, obsids = trigger_mwa_observation(
            project_decision_model,
            trigger_message,
            horizion_limit=horizion_limit,
            pretend=pretend,
            vcsmode=vcsmode,
        )
        if decision == 'E':
            # Error observing so send off debug
            debug_bool = True
        for obsid in obsids:
            # Create new obsid model
            Observations.objects.create(
                obsid=obsid,
                project_decision_id=project_decision_model,
                reason=reason
            )
    return decision, trigger_message

def trigger_mwa_observation(project_decision_model,
                            trigger_message,
                            horizion_limit=30,
                            pretend=True,
                            vcsmode=False):
    """Check if the mwa can observe then send it off the observation.
    """
    # set up the target, observer, and time
    obs_source = SkyCoord(ra=project_decision_model.ra,
                          dec=project_decision_model.dec,
                          equinox='J2000',
                          unit=(deg, deg))
    obs_source.location = EarthLocation.from_geodetic(lon="116:40:14.93",
                                                      lat="-26:42:11.95",
                                                      height=377.8)
    t = Time.now()
    obs_source.obstime = t

    # figure out the altitude of the target
    obs_source_altaz = obs_source.transform_to('altaz')
    alt = obs_source_altaz.alt.deg
    logger.debug("Triggered observation at an elevation of {0}".format(alt))

    if alt < horizion_limit:
        horizon_message = f"Not triggering due to horizon limit: alt {alt} < {horizion_limit}. "
        logger.debug(horizon_message)
        return 'I', trigger_message + horizon_message, []

    # Collect event telescopes
    voevents = VOEvent.objects.filter(trigger_group_id=project_decision_model.trigger_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and seperate with a _
    telescopes = "_".join(list(set(telescopes)))

    # Not below horizon limit so observer
    logger.info(f"Triggering at gps time {t.gps} ...")
    result = trigger(project_id='C002',
                        secure_key=os.environ['MWA_SECURE_KEY'],
                        group_id=project_decision_model.trigger_group_id.trigger_id,
                        pretend=pretend,
                        ra=project_decision_model.ra, dec=project_decision_model.dec,
                        creator='VOEvent_Auto_Trigger', #TODO grab version
                        obsname=f'{telescopes}_{project_decision_model.trigger_group_id.trigger_id}',
                        nobs=1, # Changes if not in VCS
                        freqspecs='145,24',
                        avoidsun=True,
                        inttime=0.5,
                        freqres=10,
                        exptime=15, # TODO (Default VCS time) change this for non vcs observing
                        calibrator=True,
                        calexptime=120,
                        vcsmode=vcsmode,
                        buffered=False,
                    )
    # Check if succesful
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