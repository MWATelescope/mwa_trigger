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
import astropy.units as u

import mwa_gw

log = logging.getLogger('voevent.handlers.FlareStar_swift_maxi')   # Inherit the logging setup from handlers.py

# Settings
DEC_LIMIT = 15.

HAS_NS_THRESH = 0.5

PROJECT_ID = 'D0011'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)

NOTIFY_LIST = ['ddob1600@uni.sydney.edu.au', 'kaplan@uwm.edu', 'tara@physics.usyd.edu.au']

EMAIL_TEMPLATE = """
The LIGO-GW handled triggered an MWA observation for 
%(name)s at %(trigtime)s UTC.
Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
"""

EMAIL_SUBJECT_TEMPLATE = "LIGO-GW handler trigger for %s"

# state storage
xml_cache = {}
# list of star names
flare_stars = []

class GW(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class for GW events.
    """
    def __init__(self, event=None):
        handlers.TriggerEvent.__init__(self, event=event)

    # Override or add GW specific methods here if desired.
    
    
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
    return isgw     # True if we're handling this event, False if we're rejecting it


def is_gw(v):
    """
    Tests to see if this XML packet is a Gravitational Wave event (LIGO OpenLVEM alert).
    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a GW.
    """
    ivorn = v.attrib['ivorn']

    trig_ligo = "ivo://nasa.gsfc.gcn/LVC#"
    
    ligo = False
    
    if ivorn.find(trig_ligo) == 0:
      ligo = True
      
    return ligo


def handle_gw(v, pretend=False):
    """
    Handles the parsing of the VOEvent and generates observations.
    
    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to schedule observations (automatically switches to True for test events)
    :return: None
    """
    
    if v.attrib['role'] == 'test':
        pretend = True
        
    params = {elem.attrib['name']: elem.attrib['value'] for elem in v.iterfind('.//Param')}
    
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
        log.debug("Event below NS threshold (%.1f). Not triggering."%(HAS_NS_THRESH))
        return
        
    if 'skymap_fits' in params:
        log.debug("No skymap in VOEvent. Not triggering.")
        return
    
    response = mwa_gw.MWA_GW_fast(params['skymap_fits'], logger=log)
    
    event = GW(event=v)
    
    ra, dec = get_mwapointing_grid(minprob=0.01, minelevation=45)
    
    gw.add_pos(ra, dec, 0.0)
    
    trig_id = params['GraceID']
    event.trigger_id = trig_id
    
    req_time_s = 1800
    
    obslist = triggerservice.obslist(obstime=req_time_s)
    
    if obslist is not None and len(obslist) > 0:
        gw.debug("Currently observing:")
        gw.debug(str(obslist))
        
    emaildict = {'triggerid': gw.trigger_id,
                 'trigtime': Time.now().iso,
                 'ra': ra,
                 'dec': dec}
    
    email_text = EMAIL_TEMPLATE % emaildict
    email_subject = EMAIL_SUBJECT_TEMPLATE % gw.trigger_id
    # Do the trigger
    grb.trigger_observation(ttype="LVC",
                            obsname=trig_id,
                            time_min=req_time_s/60,
                            pretend=pretend,
                            project_id=PROJECT_ID,
                            secure_key=SECURE_KEY,
                            email_tolist=NOTIFY_LIST,
                            email_text=email_text,
                            email_subject=email_subject)
    
    






