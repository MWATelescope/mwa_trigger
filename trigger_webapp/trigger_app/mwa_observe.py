import os
from astropy.units import deg
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

from mwa_trigger.triggerservice import trigger

import logging
logger = logging.getLogger(__name__)


def trigger_mwa_observation(voevent, trigger_message,
                            horizion_limit=30,
                            pretend=True):
    """Check if the mwa can observe then send it off the observation.
    """
    # set up the target, observer, and time
    obs_source = SkyCoord(ra=voevent.ra,
                          dec=voevent.dec,
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
        horizon_message = f" Not triggering due to horizon limit: alt {alt} < {horizion_limit}"
        logger.debug(horizon_message)
        return 'I', trigger_message + horizon_message, []

    # Not below horizon limit so observer
    logger.info(f"Triggering at gps time {t.gps} ...")
    result = trigger(project_id='C002',
                        secure_key=os.environ['MWA_SECURE_KEY'],
                        group_id=voevent.trigger_id,
                        pretend=pretend,
                        ra=voevent.ra, dec=voevent.dec,
                        creator='VOEvent_Auto_Trigger', #TODO grab version
                        obsname=f'{voevent.telescope}_{voevent.trigger_id}',
                        nobs=1, # Changes if not in VCS
                        freqspecs='145,24',
                        avoidsun=True,
                        inttime=0.5,
                        freqres=10,
                        exptime=15, # Default VCS time
                        calibrator=True,
                        calexptime=120,
                        vcsmode=True, #TODO for now this is always true but should make a setting to change it
                        buffered=False,
                    )
    # Check if succesful
    if not result['success']:
        # Observation not succesful so record why
        for err_id in result['error']:
            trigger_message += f" {result['error'][err_id]}"
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