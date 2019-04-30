__version__ = "0.1"
__author__ = ["Dougal Dobie", "David Kaplan"]

import logging
import os
import astropy
from astropy.coordinates import Angle
from astropy.time import Time
import re
import voeventparse

import handlers
import triggerservice

import healpy as hp

import astropy.utils.data
import lxml.etree

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy.table import Table, Column
import astropy.units as u
import numpy as np

from mwa_pb import primary_beam

from timeit import default_timer as timer

log = logging.getLogger('voevent.handlers.LVC_GW')  # Inherit the logging setup from handlers.py

# Settings
DEC_LIMIT = 15.

HAS_NS_THRESH = 0.5

PROJECT_ID = 'D0011'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)

NOTIFY_LIST = ['ddob1600@uni.sydney.edu.au', 'kaplan@uwm.edu', 'tara@physics.usyd.edu.au']

EMAIL_TEMPLATE = """
The LIGO-GW handler triggered an
MWA observation at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

EMAIL_SUBJECT_TEMPLATE = "LIGO-GW handler trigger for %s"

# observatory location
MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)

# state storage
xml_cache = {}


################################################################################
class MWA_grid_points():
    grid_file = os.path.join('..',
                             'data', 'grid_points.fits')

    def __init__(self, frame, logger=log):
        try:
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

    def __init__(self, event=None):
        handlers.TriggerEvent.__init__(self, event=event)

    ##################################################
    def load_skymap(self, gwfile, nside=64, time=None):
        self.gwfile = gwfile
        try:
            self.gwmap, gwheader = hp.read_map(self.gwfile, h=True, nest=True, verbose=False)
            self.logger.debug('Read in GW map %s' % self.gwfile)
        except:
            self.logger.error('Unable to read GW sky probability map %s' % self.gwfile)
        self.header = {}
        for i in xrange(len(gwheader)):
            self.header[gwheader[i][0]] = gwheader[i][1]

        # compute the pointings for a specified time if provided
        if time:
            self.obstime = time
        # otherwise computer the pointings for the current time
        else:
            self.obstime = astropy.time.Time.now()

        self.frame = astropy.coordinates.AltAz(obstime=self.obstime, location=MWA)

        self.logger.debug('Current time is %s' % (self.obstime))

        self.nside = self.header['NSIDE']
        self.npix = hp.nside2npix(self.nside)
        self.logger.debug('Original NSIDE=%d, NPIX=%d' % (self.nside,
                                                          self.npix))

        self.MWA_grid = MWA_grid_points(self.frame, logger=self.logger)

        self.nside_down = nside
        self.npix_down = hp.nside2npix(self.nside_down)
        self.gwmap_down = hp.ud_grade(self.gwmap, self.nside_down, power=-2,
                                      order_in='NESTED',
                                      order_out='NESTED')
        self.logger.debug('Downsampled to NSIDE=%d' % self.nside_down)

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
        theta, phi = hp.pix2ang(self.nside_down, np.arange(self.npix_down), nest=True)

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
        return healpy.get_interp_val(self.gwmap_down, np.radians(90 - RADec.Dec.value), np.radians(RA.ra.value),
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
            self.logger.info('Insufficient power above horizon\n')
            return None, None

        # first go from altitude to zenith angle
        theta_horz = np.pi / 2 - self.AltAz_down.alt.radian
        phi_horz = self.AltAz_down.az.radian

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
        theta_horz = np.radians((90 - self.Alt_down))
        phi_horz = np.radians(self.Az_down)

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
        RADec=MWA_GW.get_mwapointing_grid(frequency=150e6, minprob=0.01, minelevation=45
        returndelays=False, returnpower=False)
        if returndelays=True, returns:
        RADec,delays
        
        if returnpower=True, returns:
        RADec,delays,power
        """

        if self.MWA_grid.data is None:
            self.logger.critical('Unable to find MWA grid points')
            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        # has it been downsampled already
        npix = self.npix_down
        nside = self.nside_down
        gwmap = self.gwmap_down
        RADec = self.RADec_down
        AltAz = self.AltAz_down

        gridRADec = self.MWA_grid.get_radec()

        self.logger.debug('Computing pointing for %s' % (self.obstime))

        # figure out what fraction is above horizon
        if (gwmap * (AltAz.alt > 0)).sum() < minprob:
            self.logger.info('Insufficient power above horizon\n')
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
        log.info("Best pointing found in %.1f s" % (end - start))
        log.info("Looped over %d grid points" % (len(self.MWA_grid.data)))

        if not (self.MWA_grid.data['elevation'][igrid] > minelevation):
            self.logger.info('Elevation %.1f deg too low\n' % self.MWA_grid.data['elevation'][igrid])
            # too close to horizon
            if not (returndelays or returnpower):
                return None
            else:
                if returnpower:
                    return None, None, None
                else:
                    return None, None

        self.logger.info('Best pointing at RA,Dec=%.1f,%.1f; Az,El=%.1f,%.1f: power=%.3f' %
                         (gridRADec[igrid].ra.value, gridRADec[igrid].dec.value,
                          self.MWA_grid.data['azimuth'][igrid],
                          self.MWA_grid.data['elevation'][igrid],
                          mapsum[igrid]))

        if mapsum[igrid] < minprob:
            self.logger.info('Pointing at Az,El=%.1f,%.1f has power=%.3f < min power\n' %
                             (self.MWA_grid.data['azimuth'][igrid],
                              self.MWA_grid.data['elevation'][igrid],
                              mapsum[igrid]))

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
        handle_gw(v, pretend=pretend)

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


def handle_gw(v, pretend=False, time=None):
    """
    Handles the parsing of the VOEvent and generates observations.
    
    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to schedule observations (automatically switches to True for test events)
    :return: None
    """

    if v.attrib['role'] == 'test':
        pretend = True

    params = {elem.attrib['name']:elem.attrib['value'] for elem in v.iterfind('.//Param')}

    if params['Group'] != 'CBC':
        log.debug("Event not CBC")
        return

    if params['Packet_Type'] == "164":
        log.debug("Alert is an event retraction. Not triggering.")
        return

    alert_type = params['AlertType']

    if alert_type != 'Preliminary':
        log.debug("Alert type is not Preliminary. Not triggering.")
        return

    if float(params['HasNS']) < HAS_NS_THRESH:
        log.debug("Event below NS threshold (%.1f). Not triggering." % (HAS_NS_THRESH))
        return

    if 'skymap_fits' not in params:
        log.debug("No skymap in VOEvent. Not triggering.")
        return

    gw = GW(event=v)
    gw.load_skymap(params['skymap_fits'], time=time)

    trig_id = params['GraceID']
    gw.trigger_id = trig_id

    RADecgrid = gw.get_mwapointing_grid()
    if RADecgrid is None:
        log.info("Not triggering")
        return

    ra, dec = RADecgrid.ra, RADecgrid.dec
    log.debug("Coordinate: %s, %s" % (ra, dec))
    gw.add_pos((ra, dec, 0.0))

    req_time_s = 1800

    obslist = triggerservice.obslist(obstime=req_time_s)

    if obslist is not None and len(obslist) > 0:
        gw.debug("Currently observing:")
        gw.debug(str(obslist))

    emaildict = {'triggerid':gw.trigger_id,
                 'trigtime':Time.now().iso,
                 'ra':ra.to_string(unit=astropy.units.hour, sep=':'),
                 'dec':dec.to_string(unit=astropy.units.deg, sep=':')}

    email_text = EMAIL_TEMPLATE % emaildict
    log.info(email_text)

    email_subject = EMAIL_SUBJECT_TEMPLATE % gw.trigger_id
    # Do the trigger
    gw.trigger_observation(ttype="LVC",
                           obsname=trig_id,
                           time_min=req_time_s / 60,
                           pretend=pretend,
                           project_id=PROJECT_ID,
                           secure_key=SECURE_KEY,
                           email_tolist=NOTIFY_LIST,
                           email_text=email_text,
                           email_subject=email_subject)


def test_event(filepath='../test_events/MS190410a-1-Preliminary.xml', test_time=Time('2018-4-03 12:00:00')):
    pretend = True

    log.info('Running test event from %s' % (filepath))
    log.info('Mock time: %s' % (test_time))

    payload = astropy.utils.data.get_file_contents(filepath)
    v = voeventparse.loads(str(event))

    start = timer()
    isgw = is_gw(v)
    log.debug("GW? {0}".format(isgw))
    if isgw:
        handle_gw(v, pretend=pretend, time=test_time)

    end = timer()

    log.info("Finished. Response time: %.1f s" % (end - start))


def test_skymap():
    test_time = Time('2018-4-03 19:00:00')
    event = GW()
    event.load_skymap('../test_events/bayestar.fits.gz', time=test_time)

    event.get_mwapointing_grid()


if __name__ == '__main__':
    test_event()
#  test_event(filepath='../test_events/LVC_example_preliminary.xml')
