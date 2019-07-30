__version__ = "0.1"
__author__ = ["Dougal Dobie", "David Kaplan"]

import logging
import os
import random
import time
from timeit import default_timer as timer

import astropy
from astropy.coordinates import Angle, SkyCoord, EarthLocation
from astropy.time import Time
from astropy.table import Table
import astropy.utils.data
import astropy.units as u

import healpy

import numpy as np

from mwa_pb import primary_beam

import voeventparse

import handlers
import triggerservice


log = logging.getLogger('voevent.handlers.LVC_GW')  # Inherit the logging setup from handlers.py

GW_PRETEND = False    # Override incoming 'pretend' parameter

# Settings
"""
Define triggering settings - use these global constants defined below:

HAS_NS_THRESH: a float. The minimum probability that one of the merger objects is a neutron star
MAX_RESPONSE_TIME: a float. The maximum allowable delay between the merger and triggering observations in seconds
OBS_LENGTH: an int. The length of the triggered observation in seconds
MIN_PROB: a float. The minimum probability required above the horizon for an observation to be triggered
PROJECT_ID: a string. The MWA project ID
TEST_PROB: a float. The probability that an incoming test event (one per hour) will trigger a 'pretend' observation.

"""

HAS_NS_THRESH = 0.5
MAX_RESPONSE_TIME = 600
OBS_LENGTH = 1800     # length of the observation in seconds
MIN_PROB = 0.1
PROJECT_ID = 'D0011'
TEST_PROB = 0.01      # Roughly one test event every four days will generate a 'pretend' trigger


SECURE_KEY = handlers.get_secure_key(PROJECT_ID)


# Email these addresses when we trigger on an event
NOTIFY_LIST = ['ddob1600@uni.sydney.edu.au', 'kaplan@uwm.edu', 'tara@physics.usyd.edu.au', "Andrew.Williams@curtin.edu.au"]

# Email these addresses when we handle an event that is a GRB, but we don't trigger on it.
DEBUG_NOTIFY_LIST = ["Andrew.Williams@curtin.edu.au"]

EMAIL_TEMPLATE = """
The LIGO-GW handler triggered an
MWA observation at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

DEBUG_EMAIL_TEMPLATE = """
The LIGO-GW handler did NOT trigger an MWA observation for a
LIGO-GW event. Log messages are:

%s

"""

EMAIL_SUBJECT_TEMPLATE = "LIGO-GW handler trigger for %s"

DEBUG_EMAIL_SUBJECT_TEMPLATE = "GW_LIGO (%s) debug notification"

GCN_TEMPLATE = """
D. Kaplan (UWM), D. Dobie (Sydney/CSIRO), A. Williams (Curtin),
T. Murphy (Sydney), I. Brown (UWM), E. Lenc (CSIRO), C. Lynch (Curtin),
G. Anderson (Curtin), P. Hancock (Curtin),B. Gaensler (Toronto),
K. Bannister (CSIRO) on behalf of the MWA Collaboration

We have automatically triggered an observation of LIGO/Virgo %s
with the Murchison Widefield Array (MWA). A 30 minute observation at a
central frequency of 185 MHz with 30 MHz bandwidth started at %s
(%.0f minutes post-merger) and lasted 30 minutes.

The 20 x 20 deg field-of-view is centered on RA %.3f deg, Dec %.3f deg
and contains %.3f of the localisation probability.

Analysis of this data is underway, and subsequent epochs are planned.

We thank the MWA Operations team for supporting these observations

"""
# observatory location
MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)

# state storage
xml_cache = {}


################################################################################
class MWA_grid_points(object):
    libpath = os.path.join(os.path.split(__file__)[:-1])[0]
    grid_file = os.path.join(libpath, '..', 'data', 'grid_points.fits')

    def __init__(self, frame, logger=None):
        try:
            if logger is None:
                self.logger = log
            else:
                self.logger = logger
            self.frame = frame
            self.data = Table.read(MWA_grid_points.grid_file)
            self.logger.debug('Grid points loaded')

            self.gridAltAz = SkyCoord(self.data['azimuth'] * u.deg, self.data['elevation'] * u.deg, frame=self.frame)
            self.logger.debug('Grid points converted to SkyCoord')

        except:
            self.logger.critical('Cannot open MWA grid points file %s' % MWA_grid_points.grid_file)
            self.data = None

    ##################################################
    def get_radec(self, frame=None):
        """
        Calculate the celestial coordinates of MWA grid points in the MWA frame
        :param frame: An astropy coordinate frame. By default: MWA frame at current time
        
        :return: An astropy SkyCoord with the celestial coordinates
        """

        if not frame:
            frame = self.frame

        altaz = SkyCoord(self.data['azimuth'] * u.deg, self.data['elevation'] * u.deg, frame=frame)
        radec = altaz.transform_to('icrs')

        return radec

    ##################################################
    def find_closest_grid_pointing(self, RADec):
        """
        Returns the grid pointing that is closest to the requested position (Ra,Dec) in degrees
        along with the distance to that point in degrees
        
        :param RADec: An astropy SkyCoord with the celestial coordinates of the requested position
        
        :return closest: An astropy Row with the closest gridpoint to RADec
        :return closest_distance: An astropy Angle with the distance from the closest gridpoint to the requested position
        
        """

        if RADec is None:
            return None, None

        if self.data is None:
            self.logger.critical('Unable to find MWA grid points')
            return None, None

        distances = self.gridAltAz.separation(RADec)

        closest_arg = np.argmin(distances)
        closest = self.data[closest_arg]
        closest_distance = distances[closest_arg]

        return closest, closest_distance


################################################################################


class GW(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class for GW events.
    """

    def __init__(self, event=None, logger=log):
        self.gwfile = ''
        self.gwmap = ''
        self.header = {}
        self.obstime = 0
        self.frame = None
        self.nside = 0
        self.npix = 0
        self.MWA_grid = None
        self.nside_down = 0
        self.npix_down = 0
        self.gwmap_down = None
        self.RADec_down = None
        self.AltAz_down = None
        handlers.TriggerEvent.__init__(self, event=event, logger=logger)

    ##################################################
    def load_skymap(self, gwfile, nside=64, calc_time=None):
        self.gwfile = gwfile
        try:
            self.gwmap, gwheader = healpy.read_map(self.gwfile, h=True, nest=True, verbose=False)
            self.debug('Read in GW map %s' % self.gwfile)
        except:
            self.error('Unable to read GW sky probability map %s' % self.gwfile)
            return

        self.header = {}
        for i in xrange(len(gwheader)):
            self.header[gwheader[i][0]] = gwheader[i][1]

        # compute the pointings for a specified time if provided
        if calc_time:
            self.obstime = calc_time
        # otherwise computer the pointings for the current time
        else:
            self.obstime = astropy.time.Time.now()

        self.frame = astropy.coordinates.AltAz(obstime=self.obstime, location=MWA)

        self.debug('Current time is %s' % (self.obstime))

        self.nside = self.header['NSIDE']
        self.npix = healpy.nside2npix(self.nside)
        self.debug('Original NSIDE=%d, NPIX=%d' % (self.nside, self.npix))

        # Pass in 'self' as the logger, to catch any log messages in the self.loglist attribute
        self.MWA_grid = MWA_grid_points(self.frame, logger=self)

        self.nside_down = nside
        self.npix_down = healpy.nside2npix(self.nside_down)
        self.gwmap_down = healpy.ud_grade(self.gwmap,
                                          self.nside_down, power=-2,
                                          order_in='NESTED',
                                          order_out='NESTED')
        self.debug('Downsampled to NSIDE=%d' % self.nside_down)

        self.compute_coords()

    ##################################################
    def compute_coords(self):
        """
        Convert the coordinates of the downsampled skymap to RA,Dec.
        Then convert RA,Dec to Alt,Az in the current observatory frame.
        
        """
        # theta is co-latitude
        # phi is longitude
        # both in radians
        theta, phi = healpy.pix2ang(self.nside_down, np.arange(self.npix_down), nest=True)

        # now in degrees
        Dec_down = 90 - np.degrees(theta)
        RA_down = np.degrees(phi)

        self.RADec_down = SkyCoord(RA_down * u.deg, Dec_down * u.deg, frame='icrs')

        self.AltAz_down = self.RADec_down.transform_to(self.frame)

    ##################################################
    def interp(self, RADec):
        """
        Compute the bilinear interpolation value of a sky position
        using the 4 nearest points on the skymap
        
        :param RADec: An astropy SkyCoord with the requested sky position
        :return: The interpolated value as a float
        
        """
        return healpy.get_interp_val(self.gwmap_down, np.radians(90 - RADec.Dec.value), np.radians(RADec.ra.value),
                                     nest=True)

    ##################################################
    def get_mwapointing(self, frequency=150e6, minprob=0.01, ZAweight=False):
        """
        RADec=MWA_GW.get_mwapointing(frequency=150e6, minprob=0.01, ZAweight=False)
        return the astropy SkyCoord of brightest GW pixel
        constrained to be above horizon.
        Will additionally weight by cos(ZA) if desired
        """

        pointingmap = self.gwmap_down * (self.AltAz_down.alt > 0)

        # figure out what fraction is above horizon
        if (pointingmap).sum() < minprob:
            self.info('Insufficient power (%.3f) above horizon (>%.3f required)\n' % (pointingmap.sum(), minprob))
            return None, None

        # first go from altitude to zenith angle
        theta_horz = np.pi / 2 - self.AltAz_down.alt.radian
        # phi_horz = self.AltAz_down.az.radian

        if ZAweight:
            # weight the map by cos(ZA) if desired
            # will account for projection of MWA tile beam
            pointingmap *= np.cos(theta_horz)

        select_pointing = pointingmap == pointingmap.max()
        RADec_point = self.RADec_down[select_pointing]

        return RADec_point

    ##################################################
    def get_mwabeam(self, delays, frequency=150e6):
        """
        beam=MWA_GW.get_mwa_gwmap(delays, frequency=150e6)
        """

        # first go from altitude to zenith angle
        theta_horz = np.pi / 2 - self.AltAz_down.alt.radian
        phi_horz = self.AltAz_down.az.radian

        beamX, beamY = primary_beam.MWA_Tile_analytic(theta_horz, phi_horz,
                                                      freq=frequency,
                                                      delays=delays,
                                                      zenithnorm=True,
                                                      power=True)
        return ((beamX + beamY) * 0.5)

    ##################################################
    def get_mwa_gwpower(self, delays, frequency=150e6):
        """
        power=MWA_GW.get_mwapower(delays, frequency=150e6)
        """

        beam = self.get_mwabeam(delays, frequency=frequency)
        return (beam * self.gwmap_down).sum()

    ##################################################
    def interp_mwa(self, delays, RA, Dec, frequency=150e6):
        """
        beam=MWA_GW.interp_mwa(delays, RA, Dec, frequency=150e6)
        """
        beam = self.get_mwabeam(delays, frequency=frequency)
        return healpy.get_interp_val(beam,
                                     np.radians(90 - Dec),
                                     np.radians(RA),
                                     nest=True)

    ##################################################
    def get_mwapointing_grid(self, frequency=150e6, minprob=0.01, minelevation=45,
                             returndelays=False, returnpower=False):
        """

        :rtype: SkyCoord
        :param frequency: Frequency in Hz
        :param minprob: Minimum probability value
        :param minelevation: Minimum elevation angle, in degrees
        :param returndelays: If True, return delay values as well as MWA grid points
        :param returnpower: If True, return delay values AND primary beam power in that direction as well as MWA grid points
        :return: astropy.coordinates.SkyCoord object containing MWA coordinate grid
        """
        """
        RADec=MWA_GW.get_mwapointing_grid(frequency=150e6, minprob=0.01, minelevation=45
        returndelays=False, returnpower=False)
        if returndelays=True, returns:
        RADec,delays
        
        if returnpower=True, returns:
        RADec,delays,power
        """

        if (self.MWA_grid is None) or (self.MWA_grid.data is None):
            self.critical('Unable to find MWA grid points')
            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        # has it been downsampled already
        gwmap = self.gwmap_down
        AltAz = self.AltAz_down

        gridRADec = self.MWA_grid.get_radec()

        self.debug('Computing pointing for %s' % (self.obstime))

        # figure out what fraction is above horizon
        pointingmap = (gwmap * (AltAz.alt > 0)).sum()
        if pointingmap < minprob:
            self.info('Insufficient power (%.3f) above horizon (>%.3f required)\n' % (pointingmap, minprob))
            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        # first go from altitude to zenith angle
        theta_horz = np.pi / 2 - AltAz.alt.radian
        phi_horz = AltAz.az.radian

        mapsum = np.zeros((len(self.MWA_grid.data)))
        start = timer()
        for igrid in xrange(len(self.MWA_grid.data)):
            beamX, beamY = primary_beam.MWA_Tile_analytic(theta_horz, phi_horz,
                                                          freq=frequency,
                                                          delays=self.MWA_grid.data[igrid]['delays'],
                                                          zenithnorm=True,
                                                          power=True)

            mapsum[igrid] = ((beamX + beamY) * 0.5 * gwmap).sum()
        # this is the best grid point
        # such that it is over our minimum elevation
        igrid = np.where(mapsum == mapsum[self.MWA_grid.data['elevation'] > minelevation].max())[0][0]
        end = timer()
        self.info("Best pointing found in %.1f s" % (end - start))
        self.info("Looped over %d grid points" % (len(self.MWA_grid.data)))

        if not (self.MWA_grid.data['elevation'][igrid] > minelevation):
            self.info('Elevation %.1f deg too low\n' % self.MWA_grid.data['elevation'][igrid])
            # too close to horizon
            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        msg = 'Best pointing at RA,Dec=%.1f,%.1f; Az,El=%.1f,%.1f: power=%.3f'
        self.info(msg % (gridRADec[igrid].ra.value, gridRADec[igrid].dec.value,
                         self.MWA_grid.data['azimuth'][igrid],
                         self.MWA_grid.data['elevation'][igrid],
                         mapsum[igrid]))

        if mapsum[igrid] < minprob:
            msg = 'Pointing at Az,El=%.1f,%.1f has power=%.3f < min power (%.3f)\n'
            self.info(msg % (self.MWA_grid.data['azimuth'][igrid],
                             self.MWA_grid.data['elevation'][igrid],
                             mapsum[igrid], minprob))

            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        if not (returndelays or returnpower):
            return gridRADec[igrid]
        else:
            if not returnpower:
                return gridRADec[igrid], self.MWA_grid.data[igrid]['delays']
            else:
                return gridRADec[igrid], self.MWA_grid.data[igrid]['delays'], mapsum[igrid]

################################################################################


def processevent(event='', pretend=True):
    """
    Called externally by the voevent_handler script when a new VOEvent is received. Return True if
    the event was parsed by this handler, False if it was another type of event that should be
    examined by a different handler.
    
    :param event: A string containg the XML string in VOEvent format
    :param pretend: Boolean, True if we don't want to actually schedule the observations.
    :return: Boolean, True if this handler processed this event, False to pass it to another handler function.
    
    """

    # event arrives as a unicode string but loads requires a non-unicode string.
    v = voeventparse.loads(str(event))
    log.info("Working on: %s" % v.attrib['ivorn'])
    isgw = is_gw(v)
    log.debug("GW? {0}".format(isgw))
    if isgw:
        handle_gw(v, pretend=(pretend or GW_PRETEND))

    log.info("Finished.")
    return isgw  # True if we're handling this event, False if we're rejecting it


def is_gw(v):
    """
    Tests to see if this XML packet is a Gravitational Wave event (LIGO OpenLVEM alert).
    
    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a GW.
    
    """
    ivorn = v.attrib['ivorn']
    log.debug("ivorn: %s" % (ivorn))

    trig_ligo = "ivo://gwnet/LVC#"

    ligo = False

    if ivorn.find(trig_ligo) == 0:
        ligo = True

    return ligo


def handle_gw(v, pretend=False, calc_time=None):
    """
    Handles the parsing of the VOEvent and generates observations.
    
    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to schedule observations (automatically switches to True for test events)
    :param calc_time: astropy.time.Time object for calculations
    :return: None
    
    """

    if v.attrib['role'] == 'test':  # There's a 'test' event every hour, and half of these are followed by a retraction.
        if random.random() < TEST_PROB:   # Some events, at random, generate a 'pretend' trigger.
            log.info('Test event, pretending to trigger.')
            pretend = True
        else:
            log.info('Test event, not triggering.')
            return

    params = {elem.attrib['name']:elem.attrib['value'] for elem in v.iterfind('.//Param')}
    
    trig_id = params['GraceID']
    debug_email_subject = DEBUG_EMAIL_SUBJECT_TEMPLATE % trig_id
    
    if trig_id not in xml_cache:
        gw = GW(event=v)
        gw.trigger_id = trig_id
        xml_cache[trig_id] = gw 
    else:
        gw = xml_cache[trig_id]
        gw.add_event(v)  

    if params['Packet_Type'] == "164":
        gw.info("Alert is an event retraction. Not triggering.")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject=debug_email_subject,
                            msg_text=DEBUG_EMAIL_TEMPLATE % "Alert is an event retraction. Not triggering.",
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

#    alert_type = params['AlertType']
#    if alert_type != 'Preliminary':
#        log.debug("Alert type is not Preliminary. Not triggering.")
#        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
#                            to_addresses=DEBUG_NOTIFY_LIST,
#                            subject='GW_LIGO debug notification',
#                            msg_text=DEBUG_EMAIL_TEMPLATE % "Alert type is not Preliminary. Not triggering.",
#                            attachments=[('voevent.xml', voeventparse.dumps(v))])
#        return

#    if params['Group'] != 'CBC':
#        log.debug("Event not CBC")
#        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
#                            to_addresses=DEBUG_NOTIFY_LIST,
#                            subject='GW_LIGO debug notification',
#                            msg_text=DEBUG_EMAIL_TEMPLATE % "Event not CBC",
#                            attachments=[('voevent.xml', voeventparse.dumps(v))])
#        return

    if float(params['HasNS']) < HAS_NS_THRESH:
        msg = "P_HasNS (%.2f) below threshold (%.2f). Not triggering." % (float(params['HasNS']), HAS_NS_THRESH)
        gw.debug(msg)
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject=debug_email_subject,
                            msg_text=DEBUG_EMAIL_TEMPLATE % msg,
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

    if 'skymap_fits' not in params:
        gw.debug("No skymap in VOEvent. Not triggering.")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject=debug_email_subject,
                            msg_text=DEBUG_EMAIL_TEMPLATE % "No skymap in VOEvent. Not triggering.",
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return
        
    try:
        gw.load_skymap(params['skymap_fits'], calc_time=calc_time)
    except:
        gw.debug("Failed to load skymap. Retrying in 10 seconds")
        time.sleep(10)    
        
        gw.load_skymap(params['skymap_fits'], calc_time=calc_time)

    RADecgrid, delays, power = gw.get_mwapointing_grid(returndelays=True, returnpower=True, minprob=MIN_PROB)
    if RADecgrid is None:
        gw.info("No pointing from skymap, not triggering")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject=debug_email_subject,
                            msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in gw.loglist]),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

    ra, dec = RADecgrid.ra, RADecgrid.dec
    gw.info("Pointing at %s, %s" % (ra, dec))
    gw.info("Pointing contains %.3f of the localisation" % (power))
    gw.add_pos((ra.deg, dec.deg, 0.0))

    req_time_s = OBS_LENGTH

    obslist = triggerservice.obslist(obstime=req_time_s)

    currently_observing = False
    if obslist is not None and len(obslist) > 0:
        gw.debug("Currently observing:")
        gw.debug(str(obslist))
        
        obs = str(obslist[0][1])
        gw.debug("obs {0}, trig {1}".format(obs, trig_id))
        
        if obs == trig_id:
            currently_observing = True
            gw.info("Already observing this GW event")
            
            last_pos = gw.get_pos(-2)
            last_ra = last_pos[0]
            last_dec = last_pos[1]
            gw.info("Old position: RA {0}, Dec {1}".format(last_ra,last_dec))
          
            if (abs(ra.deg - last_ra) < 5.0) and (abs(dec.deg - last_dec) < 5.0):
                gw.info("New pointing ver close to old pointing. Not triggering.")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject=debug_email_subject,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % "New pointing same as old pointing. Not triggering.",
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return
            
            else:
              gw.info("Updating pointing.")

    time_string = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Time.TimeInstant.ISOTime.text
    merger_time = Time(time_string)
    delta_T = Time.now() - merger_time
    delta_T_sec = delta_T.sec

    if not currently_observing:
        #  If this event is not currently being observed, check whether time since merger exceeds max response time

        if delta_T_sec > MAX_RESPONSE_TIME:
            log_message = "Time since merger (%d s) greater than max response time (%d s). Not triggering" % (delta_T_sec, MAX_RESPONSE_TIME)
            gw.info(log_message)
            handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                to_addresses=DEBUG_NOTIFY_LIST,
                                subject=debug_email_subject,
                                msg_text=DEBUG_EMAIL_TEMPLATE % log_message,
                                attachments=[('voevent.xml', voeventparse.dumps(v))])
                                
            return
        
    #  Check if this event has been triggered on before
    if gw.first_trig_time is not None:
        #  If it has been triggered, update the required time for the updated observation
        req_time_s -= (Time.now()-gw.first_trig_time).sec
        gw.info("Required observing time: %.0f s" % (req_time_s))

    emaildict = {'triggerid':gw.trigger_id,
                 'trigtime':Time.now().iso,
                 'ra':ra.to_string(unit=astropy.units.hour, sep=':'),
                 'dec':dec.to_string(unit=astropy.units.deg, sep=':')}

    email_text = EMAIL_TEMPLATE % emaildict
    gw.info(email_text)

    gw.info("Template GCN text:")
    gcn_text = GCN_TEMPLATE % (trig_id, Time.now().iso, delta_T_sec, ra.deg, dec.deg, power)
    gw.info(gcn_text)

    email_subject = EMAIL_SUBJECT_TEMPLATE % gw.trigger_id
    # Do the trigger
    result = gw.trigger_observation(ttype="LVC",
                                    obsname=trig_id,
                                    time_min=req_time_s / 60,
                                    pretend=(pretend or GW_PRETEND),
                                    project_id=PROJECT_ID,
                                    secure_key=SECURE_KEY,
                                    email_tolist=NOTIFY_LIST,
                                    email_text=email_text,
                                    email_subject=email_subject)
    if result is None:
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject=debug_email_subject,
                            msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in gw.loglist]),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])


def test_event(filepath='../test_events/MS190410a-1-Preliminary.xml', test_time=Time('2018-4-03 12:00:00')):
    pretend = True

    log.info('Running test event from %s' % (filepath))
    log.info('Mock time: %s' % (test_time))

    payload = astropy.utils.data.get_file_contents(filepath)
    v = voeventparse.loads(str(payload))
    
    params = {elem.attrib['name']:elem.attrib['value'] for elem in v.iterfind('.//Param')}

    return

#    start = timer()
#    isgw = is_gw(v)
#    log.debug("GW? {0}".format(isgw))
#    if isgw:
#        handle_gw(v, pretend=(pretend or GW_PRETEND), calc_time=test_time)
#    end = timer()
#    log.info("Finished. Response time: %.1f s" % (end - start))


def test_skymap():
    test_time = Time('2018-4-03 19:00:00')
    event = GW()
    event.load_skymap('../test_events/bayestar.fits.gz', calc_time=test_time)

    event.get_mwapointing_grid()


if __name__ == '__main__':
    test_event()
#  test_event(filepath='../test_events/LVC_example_preliminary.xml')
