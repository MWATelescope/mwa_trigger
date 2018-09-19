#! python

"""
Library containing one or more functions to process incoming VOEvent XML strings. This library will
be imported by a long running process, so you can load large data files, etc, at import time, rather than
inside the processevent() function, to save time.

This module only handles MAXI and SWIFT VOEvents for Flare Stars.
"""

__version__ = "0.1"
__author__ = ["Paul Hancock", "Andrew Williams", "Gemma Anderson"]

import logging

import astropy
from astropy.coordinates import Angle
from astropy.time import Time
import re
import voeventparse

import handlers
import triggerservice

log = logging.getLogger('voevent.handlers.FlareStar_swift_maxi')   # Inherit the logging setup from handlers.py

# Settings
DEC_LIMIT = 32.

PROJECT_ID = 'D0009'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)

NOTIFY_LIST = ["Paul.Hancock@curtin.edu.au", "Gemma.Anderson@curtin.edu.au"]

EMAIL_TEMPLATE = """
The Flare Star MAXI+Swift handler triggered an MWA observation for
%(name)s at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

EMAIL_SUBJECT_TEMPLATE = "Flare Star MAXI+Swift handler trigger for %s"

# state storage
xml_cache = {}
# list of star names
flare_stars = []


def make_flare_star_names():
    """
    Read a list of flare star names from a data file

    :return:
    None
    """
    global flare_stars
    flare_stars = [a.strip().lower() for a in open('mwa_trigger/FlareStarNames.txt', 'r').readlines() if not a.startswith("#")]
    # reformat ' ' into either '' or '_' in the list above
    flare_stars.extend([re.sub(' ', '_', f) for f in flare_stars if ' ' in f])
    flare_stars.extend([re.sub(' ', '', f) for f in flare_stars if ' ' in f])
    return

make_flare_star_names()


class FlareStar(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class to add a parameter 'short', relevant only for GRB type events.
    """
    def __init__(self, event=None):
        handlers.TriggerEvent.__init__(self, event=event)

    # Override or add source specific methods here if desired.


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

    # only respond to SWIFT and MAXI evetnts
    ivorn = v.attrib['ivorn']
    if not(('SWIFT' in ivorn) or ('MAXI' in ivorn)):
        return False

    log.info("Working on: %s" % ivorn)
    isflarestar = is_flarestar(v)
    log.debug("Flare Star ? {0}".format(isflarestar))
    if isflarestar:
        handle_flarestar(v, pretend=pretend)

    log.info("Finished.")
    return isflarestar     # True if we're handling this event, False if we're rejecting it


def is_flarestar(v):
    """
    Tests to see if this XML packet is a Flare Star from MAXI or SWIFT.

    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a Flare Star.
    """
    # SWIFT encodes a Why.Inference.Name
    if hasattr(v.Why.Inference, 'Name'):
        name = v.Why.Inference.Name
        log.debug("Found {0} in SWIFT format".format(name))
    else:
        # MAXI uses a Soruce_Name parameter
        src = v.find(".//Param[@name='Source_Name']")
        if src is None:
            return False
        # MAXI sometimes puts spaces at the start of the string!
        name = src.attrib['value'].strip()

        # move the name into some standard place so we can easily reference it later
        v.Why.Inference.Name = name
        log.debug("Found {0} in MAXI format".format(name))

    if str(name).lower() in flare_stars:
        return True
    return False


def handle_flarestar(v, pretend=False):
    """
    Handles the actual VOEvent parsing, generating observations if appropriate.

    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to actually schedule the observations.
    :return: None
    """
    ivorn = v.attrib['ivorn']
    log.debug("processing Flare Star {0}".format(ivorn))

    name = v.Why.Inference.Name
    trig_id = v.find(".//Param[@name='TrigID']").attrib['value']
    c = voeventparse.get_event_position(v)
    if c.dec > DEC_LIMIT:
        log.debug("Flare Star {0} above declination cutoff of +10 degrees".format(name))
        log.debug("Not triggering")
        return

    if trig_id not in xml_cache:
        fs = FlareStar(event=v)
        fs.trigger_id = trig_id
        xml_cache[trig_id] = fs
    else:
        fs = xml_cache[trig_id]
        fs.add_event(v)

    ra = c.ra
    dec = c.dec
    fs.add_pos((ra, dec, 0.))
    fs.debug("Flare Star {0} is detected at RA={1}, Dec={2}".format(name, ra, dec))

    req_time_min = 30

    # look at the schedule
    obslist = triggerservice.obslist(obstime=1800)
    if obslist is not None and len(obslist) > 0:
        fs.debug("Currently observing:")
        fs.debug(str(obslist))
        # are we currently observing *this* GRB?
        obs = str(obslist[0][1])  # in case the obslist is returning unicode strings
        fs.debug("obs {0}, trig {1}".format(obs, trig_id))

        # Same GRB trigger from same telescope
        if obs == trig_id:
            fs.info("already observing this star")
            fs.info("not triggering again")
            return
    else:
        fs.debug("Current schedule empty")

    fs.debug("Triggering")
    # label as SWIFT or MAXI for the trigger type
    ttype = v.attrib['ivorn'].split('/')[-1].split('#')[0]

    emaildict = {'triggerid': fs.trigger_id,
                 'trigtime': Time.now().iso,
                 'ra': Angle(fs.ra[-1], unit=astropy.units.deg).to_string(unit=astropy.units.hour, sep=':'),
                 'dec': Angle(fs.dec[-1], unit=astropy.units.deg).to_string(unit=astropy.units.deg, sep=':'),
                 'name': name}
    email_text = EMAIL_TEMPLATE % emaildict
    email_subject = EMAIL_SUBJECT_TEMPLATE % fs.trigger_id
    # Do the trigger
    fs.trigger_observation(ttype=ttype,
                           obsname=trig_id,
                           time_min=req_time_min,
                           pretend=pretend,
                           project_id=PROJECT_ID,
                           secure_key=SECURE_KEY,
                           email_tolist=NOTIFY_LIST,
                           email_text=email_text,
                           email_subject=email_subject)