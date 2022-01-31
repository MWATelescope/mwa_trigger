__version__ = "0.1.1"
__author__ = ["Dougal Dobie", "David Kaplan", "Mieke Bouwhuis"]

import logging
import sys

import voeventparse

import astropy.utils.data
import lxml.etree

import astropy
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
import astropy.units as u

from timeit import default_timer as timer

from . import handlers
from . import triggerservice

log = logging.getLogger('voevent.handlers.neutrino')   # Inherit the logging setup from handlers.py

# Settings
MINIMUM_RANKING = 2     # selection criterion for Antares
REPOINTING_LIMIT = 10   # maximum allowed difference in neutrino direction for different alerts with common trigger ID, in degrees
PRETEND = False         # If True, force all to be in 'pretend' mode

PROJECT_ID = 'G0072'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)

# Email these addresses when we trigger on an event
NOTIFY_LIST = ['Andrew.Williams@curtin.edu.au', 'ddob1600@uni.sydney.edu.au', 'kaplan@uwm.edu', 'Mieke.Bouwhuis@csiro.au', 'clancy.james@curtin.edu.au']

# Email these addresses when we handle a neutrino event, but we don't trigger on it.
DEBUG_NOTIFY_LIST = ["Andrew.Williams@curtin.edu.au", 'Mieke.Bouwhuis@csiro.au', 'clancy.james@curtin.edu.au']

EMAIL_TEMPLATE = """
The Neutrino handler triggered an
MWA observation at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

DEBUG_EMAIL_TEMPLATE = """
The Neutrino handler DID NOT trigger an
MWA observation.

Reason is:
%s
"""

EMAIL_SUBJECT_TEMPLATE = "Neutrino handler trigger for %s"

# observatory location
MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8*u.m)

# state storage
xml_cache = {}


class Neutrino(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class for neutrino events.
    """
    def __init__(self, event=None):
        self.voe_source = None  # the source of the VOEvent message
        handlers.TriggerEvent.__init__(self, event=event)


################################################################################


def processevent(event='', pretend=True):
    """
    Called externally by the voevent_handler script when a new VOEvent is received. Return True if
    the event was parsed by this handler, False if it was another type of event that should be
    examined by a different handler.
    :param event: A string containing the XML string in VOEvent format
    :param pretend: Boolean, True if we don't want to actually schedule the observations.
    :return: Boolean, True if this handler processed this event, False to pass it to another handler function.
    """

    if sys.version_info.major == 2:
        # event arrives as a unicode string but loads requires a non-unicode string.
        v = voeventparse.loads(str(event))
    else:
        v = voeventparse.loads(event.encode())
    log.info("Working on: {}".format(v.attrib['ivorn']))
    isneutrino = is_neutrino(v)
    log.debug("Neutrino detection? {0}".format(isneutrino))
    if isneutrino:
        handle_neutrino(v, pretend=pretend)

    log.info("Finished.")
    return isneutrino     # True if we're handling this event, False if we're rejecting it


def is_neutrino(v):
    """
    Tests to see if this XML packet is a Neutrino event from Antares or IceCube.
    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a Neutrino.
    """
    ivorn = v.attrib['ivorn']
    log.debug("ivorn: {}".format(ivorn))

    neu_trigger = ["ivo://nasa.gsfc.gcn/AMON#ICECUBE_GOLD",
                   "ivo://nasa.gsfc.gcn/Antares"]

    neutrino = False
    for t in neu_trigger:
        if ivorn.find(t) == 0:
            neutrino = True
            break

    return neutrino


def handle_neutrino(v, pretend=False):
    """
    Handles the parsing of the VOEvent and generates observations.

    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to schedule observations (automatically switches to True for test events)
    :return: None
    """

    if v.attrib['role'] != "observation":
        log.info("Attribute role != 'observation'. Setting pretend=True")
        pretend = True

    if PRETEND:
        log.info("Global PRETEND is True, setting pretend=True")
        pretend = True

    # Fetch params from the What section
    params = voeventparse.convenience.get_toplevel_params(v)

    try:
        is_real = params.get("isRealAlert")["value"]
    except:
        is_real = True

    if not is_real:
        log.info("Parameter isRealAlert is not True, setting pretend=True")
        pretend = True

    if 'Antares' in v.attrib['ivorn']:
        trig_id = params.get("TrigID")["value"]
        # Determine if the event satisfies trigger criteria
        # Note: this should ultimately be made more complex than selecting simply on ranking
        ranking = int(params.get("ranking")["value"])
        if ranking < MINIMUM_RANKING:
            log.info("Event ranking %s below trigger threshold %s. Not triggering." % (ranking, MINIMUM_RANKING))
            handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                to_addresses=DEBUG_NOTIFY_LIST,
                                subject='DEBUG Neutrino alert for: %s - below minimum ranking to trigger' % trig_id,
                                msg_text=DEBUG_EMAIL_TEMPLATE % ("Event ranking %s below trigger threshold %s. Not triggering." % (ranking, MINIMUM_RANKING)),
                                attachments=[('voevent.xml', voeventparse.dumps(v))])
            return

        if trig_id not in xml_cache:
            neutrino = Neutrino(event=v)
            neutrino.voe_source = "ANTARES"
            neutrino.trigger_id = trig_id
            log.info("Trigger id: {}".format(trig_id))

            if pretend:
                neutrino.info("****This is a test event****")

            xml_cache[trig_id] = neutrino
        else:
            neutrino = xml_cache[trig_id]

    elif 'ICECUBE' in v.attrib['ivorn']:
        trig_id = params.get("AMON_ID")["value"]

        if trig_id not in xml_cache:
            neutrino = Neutrino(event=v)
            neutrino.voe_source = "ICECUBE"
            neutrino.trigger_id = trig_id
            log.info("Trigger id: {}".format(trig_id))

            if pretend:
                neutrino.info("****This is a test event****")

            xml_cache[trig_id] = neutrino
        else:
            neutrino = xml_cache[trig_id]

    else:
        log.debug("Not an ICECUBE or ANTARES neutrino.")
        log.debug("Not Triggering")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject='DEBUG Neutrino alert - Not an ICECUBE or ANTARES event, not triggering',
                            msg_text=DEBUG_EMAIL_TEMPLATE % ("Unknown event type, not triggering"),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

    position = voeventparse.convenience.get_event_position(v)

    log.info("Neutrino detected at: RA={:.2f}, Dec={:.2f} ({:.2f} deg error circle)".format(position.ra, position.dec, position.err))

    neutrino.add_pos((position.ra, position.dec, position.err))

    req_time_min = 30

    # Check for scheduled observations
    obslist = triggerservice.obslist(obstime=req_time_min * 60)

    if obslist is not None and len(obslist) > 0:
        neutrino.debug("Currently observing:")
        neutrino.debug(str(obslist))
        # Check if we are currently observing *this* neutrino
        obs = str(obslist[0][1])  # in case the obslist is returning unicode strings
        neutrino.debug("Current observation: {0}, current trigger: {1}".format(obs, trig_id))

        if trig_id in obs:
            neutrino.info("Already observing this Neutrino")
            # Check the difference in position
            last_pos = neutrino.get_pos(-2)
            neutrino.info("Old position: RA {0}, Dec {1}, err {2}".format(*last_pos))
            pos_diff = SkyCoord(ra=last_pos[0], dec=last_pos[1], unit=astropy.units.degree, frame='icrs').separation(
                       SkyCoord(ra=position.ra, dec=position.dec, unit=astropy.units.degree, frame='icrs')).degree
            neutrino.info("New position is {0} deg from previous".format(pos_diff))
            # Continue the current observation when the position difference is less than REPOINTING_DIR
            if pos_diff < REPOINTING_LIMIT:
                neutrino.info("(less than constraint of {0} deg)".format(REPOINTING_LIMIT))
                neutrino.info("Not triggering")
                return

            neutrino.info("(greater than constraint of {0}deg)".format(REPOINTING_LIMIT))
            neutrino.info("Update current observation.")
        else:
            neutrino.info("Not currently observing this Neutrino")
    else:
        neutrino.debug("Current schedule empty")

    emaildict = {'triggerid': neutrino.trigger_id,
                 'trigtime': Time.now().iso,
                 'ra': position.ra,
                 'dec': position.dec}

    email_text = EMAIL_TEMPLATE % emaildict
    email_subject = EMAIL_SUBJECT_TEMPLATE % neutrino.trigger_id
    # Do the trigger
    result = neutrino.trigger_observation(ttype=neutrino.voe_source,
                                          obsname=trig_id,
                                          time_min=req_time_min,
                                          pretend=pretend,
                                          project_id=PROJECT_ID,
                                          secure_key=SECURE_KEY,
                                          email_tolist=NOTIFY_LIST,
                                          email_text=email_text,
                                          email_subject=email_subject,
                                          creator='VOEvent_Auto_Trigger: Neutrino=%s' % __version__,
                                          voevent=voeventparse.dumps(v))
    if result is None:    # Trigger failed:
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject='DEBUG Neutrino alert - Trigger failed',
                            msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in neutrino.loglist]),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])


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
