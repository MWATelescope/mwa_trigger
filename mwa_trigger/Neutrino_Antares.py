__version__ = "0.1"
__author__ = ["Dougal Dobie", "David Kaplan"]

import logging
import sys

import voeventparse

import astropy.utils.data
import lxml.etree

import astropy
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u

from timeit import default_timer as timer

import handlers
import triggerservice


# Inherit the logging setup from handlers.py
log = logging.getLogger('voevent.handlers.antares')

# Settings
DEC_LIMIT = 15.
MINIMUM_RANKING = 2
REPOINTING_LIMIT = 10  # degrees

PROJECT_ID = 'XXXXXX'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)

NOTIFY_LIST = ['ddob1600@uni.sydney.edu.au', 'kaplan@uwm.edu']

EMAIL_TEMPLATE = """
The Antares neutrino handler triggered an
MWA observation at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

EMAIL_SUBJECT_TEMPLATE = "Antares handler trigger for %s"

DEBUG_EMAIL_TEMPLATE = """
The Antares neutrino handler did NOT trigger an MWA observation for an
Antares event. Log messages are:

%s

"""

DEBUG_EMAIL_SUBJECT_TEMPLATE = "Antares (%s) debug notification"

# observatory location
MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8*u.m)

# state storage
xml_cache = {}


class Neutrino(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class for neutrino events.
    """

    def __init__(self, event=None):
        handlers.TriggerEvent.__init__(self, event=event)


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

    if sys.version_info.major == 2:
        # event arrives as a unicode string but loads requires a non-unicode string.
        v = voeventparse.loads(str(event))
    else:
        v = voeventparse.loads(event.encode('latin-1'))
    log.info("Working on: %s" % v.attrib['ivorn'])
    isneutrino = is_neutrino(v)
    log.debug("Neutrino detection? {0}".format(isneutrino))
    if isneutrino:
        handle_neutrino(v, pretend=pretend)

    log.info("Finished.")
    return isneutrino     # True if we're handling this event, False if we're rejecting it


def is_neutrino(v):
    """
    Tests to see if this XML packet is a Gravitational Wave event (LIGO OpenLVEM alert).
    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a GW.
    """
    ivorn = v.attrib['ivorn']
    log.debug("ivorn: %s" % (ivorn))

    trig_antares = "ivo://nasa.gsfc.gcn/Antares"

    neutrino = False

    if ivorn.find(trig_antares) == 0:
        neutrino = True

    return neutrino


def get_position_info(v):
    """
    Return the ra,dec,err from a given voevent.
    These are in degrees, in the J2000 equinox.

    :param v: A VOEvent string, in XML format
    :return: A tuple of (ra, dec, err) where ra,dec are the coordinates in J2000 and err is the error radius in deg.
    """
    ra = float(v.findtext("WhereWhen//Position2D//C1"))
    dec = float(v.findtext("WhereWhen//Position2D//C2"))
    err = float(v.findtext("WhereWhen//Position2D//Error2Radius"))

    return ra, dec, err


def handle_neutrino(v, pretend=False):
    """
    Handles the parsing of the VOEvent and generates observations.

    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to schedule observations (automatically switches to True for test events)
    :return: None
    """

    if v.attrib['role'] != "observation":
        log.info("This is a test event. Setting pretend=True")
        pretend = True
        is_test = True
    else:
        is_test = False

    # Determine if the event satisfies trigger criteria
    # Note: this should ultimately be made more complex than selecting simply on ranking
    ranking = v.find(".//Param[@name='ranking']").attrib['value']
    if ranking < MINIMUM_RANKING:
        log.info(
            "Event ranking (%d) below trigger threshold. Not triggering." % (ranking))
        return

    trig_id = v.find(".//Param[@name='TrigID']").attrib['value']
    
    debug_email_subject = DEBUG_EMAIL_SUBJECT_TEMPLATE % trig_id

    if trig_id not in xml_cache:
        neutrino = Neutrino(event=v)
        neutrino.trigger_id = trig_id
        log.info("Trigger id: %s" % (trig_id))
        
        if is_test:
            neutrino.info("****This is a test event****")
        
        xml_cache[trig_id] = neutrino
    else:
        neutrino = xml_cache[trig_id]
        neutrino.add_event(v)  


    ra, dec, err = get_position_info(v)

    log.info("Neutrino detected at: RA=%.2f, Dec=%.2f (%.2f deg error circle)" % (
        ra, dec, err))

    neutrino.add_pos((ra, dec, err))

    req_time_s = 1800

    obslist = triggerservice.obslist(obstime=req_time_s)

    if obslist is not None and len(obslist) > 0:
        neutrino.debug("Currently observing:")
        neutrino.debug(str(obslist))
        
        if trig_id in obs:
            neutrino.info("Already observing this GRB")
            last_pos = neutrino.get_pos(-2)
            neutrino.info("Old position: RA {0}, Dec {1}, err {2}".format(*last_pos))
            pos_diff = SkyCoord(ra=last_pos[0], dec=last_pos[1], unit=astropy.units.degree, frame='icrs').separation(
                       SkyCoord(ra=ra, dec=dec, unit=astropy.units.degree, frame='icrs')).degree
            grb.info("New position is {0} deg from previous".format(pos_diff))
            if pos_diff < REPOINTING_LIMIT:
                neutrino.info("(less than constraint of {0} deg)".format(REPOINTING_LIMIT))
                neutrino.info("Not triggering")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject=debug_email_subject,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in neutrino.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return
            neutrino.info("(greater than constraint of {0}deg)".format(REPOINTING_LIMIT))
            
    

    emaildict = {'triggerid': neutrino.trigger_id,
                 'trigtime': Time.now().iso,
                 'ra': ra,
                 'dec': dec}

    email_text = EMAIL_TEMPLATE % emaildict
    email_subject = EMAIL_SUBJECT_TEMPLATE % neutrino.trigger_id
    # Do the trigger
    neutrino.trigger_observation(ttype="Antares",
                                 obsname=trig_id,
                                 time_min=req_time_s / 60,
                                 pretend=pretend,
                                 project_id=PROJECT_ID,
                                 secure_key=SECURE_KEY,
                                 email_tolist=NOTIFY_LIST,
                                 email_text=email_text,
                                 email_subject=email_subject)


def test_event(filepath='../test_events/Antares_observation.xml'):

    pretend = True

    log.info('Running test event from %s' % (filepath))

    payload = astropy.utils.data.get_file_contents(filepath)
    v = lxml.etree.fromstring(payload)

    start = timer()

    isneutrino = is_neutrino(v)
    log.debug("Neutrino detection? {0}".format(isneutrino))

    if isneutrino:
        handle_neutrino(v, pretend=pretend)

    end = timer()

    log.info("Finished. Response time: %.1f s" % (end-start))


if __name__ == '__main__':
    test_event()
