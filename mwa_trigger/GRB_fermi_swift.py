#! python

"""
Library containing one or more functions to process incoming VOEvent XML strings. This library will
be imported by a long running process, so you can load large data files, etc, at import time, rather than
inside the processevent() function, to save time.

This library only handles Fermi and SWIFT VOEvents, other types of event would be handled in a separate library.
"""

__version__ = "0.4.1"
__author__ = ["Paul Hancock", "Andrew Williams", "Gemma Anderson"]

import logging
import sys

import astropy
from astropy.coordinates import Angle, SkyCoord
from astropy.time import Time
import astropy.units

import voeventparse

from . import handlers
from . import triggerservice

log = logging.getLogger('voevent.handlers.GRB_fermi_swift')   # Inherit the logging setup from handlers.py

# Settings
FERMI_POBABILITY_THRESHOLD = 50  # Trigger on Fermi events that have most-likely-prob > this number
LONG_SHORT_LIMIT = 2.05  # seconds
REPOINTING_LIMIT = 10  # degrees
SWIFT_SHORT_TRIGGERS_IN_VCSMODE = True  # Trigger swift triggers of short GRBs in vcsmode
SWIFT_LONG_TRIGGERS_IN_VCSMODE = True   # Trigger swift triggers of long GRBs in vcsmode
SWIFT_SHORT_VCS_TIME = 15   # How many minutes to request if this is a VCS trigger

PROJECT_ID = 'G0055'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)
PRETEND = False   # If True, override the 'pretend' flag passed, and never actually schedule observations

# Email these addresses when we trigger on an event
NOTIFY_LIST = ["Paul.Hancock@curtin.edu.au", "Gemma.Anderson@curtin.edu.au", "Andrew.Williams@curtin.edu.au", "jun.tian@postgrad.curtin.edu.au"]

# Email these addresses when we handle an event that is a GRB, but we don't trigger on it.
DEBUG_NOTIFY_LIST = ["Paul.Hancock@curtin.edu.au", "Gemma.Anderson@curtin.edu.au", "Andrew.Williams@curtin.edu.au", "jun.tian@postgrad.curtin.edu.au"]

EMAIL_TEMPLATE = """
The GRB Fermi+Swift handler triggered an MWA observation for a
Fermi/Swift GRB at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
Error Rad:  %(err)7.3f deg

"""

DEBUG_EMAIL_TEMPLATE = """
The GRB Fermi+Swift handler did NOT trigger an MWA observation for a
Fermi/Swift GRB. Log messages are:

%s

"""

EMAIL_SUBJECT_TEMPLATE = "GRB Fermi+Swift handler trigger for %s"

# state storage
xml_cache = {}


class GRB(handlers.TriggerEvent):
    """
    Subclass the TriggerEvent class to add a parameter 'short', relevant only for GRB type events.
    """
    def __init__(self, event=None):
        self.short = False  # True if short
        handlers.TriggerEvent.__init__(self, event=event)

    # Override or add GRB specific methods here if desired.


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
    isgrb = is_grb(v)
    log.debug("GRB? {0}".format(isgrb))
    if isgrb:
        handle_grb(v, pretend=(pretend or PRETEND))

    log.info("Finished.")
    return isgrb     # True if we're handling this event, False if we're rejecting it


def is_grb(v):
    """
    Tests to see if this XML packet is a Gamma Ray Burst event (SWIFT or Fermi alert).

    :param v: string in VOEvent XML format
    :return: Boolean, True if this event is a GRB.
    """
    ivorn = v.attrib['ivorn']

    trig_swift = ("ivo://nasa.gsfc.gcn/SWIFT#BAT_GRB_Pos",  # Swift positions
                  )

    # Ignore "ivo://nasa.gsfc.gcn/Fermi#GBM_Alert" as they always have ra/dec = 0/0
    trig_fermi = ("ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos",  # Fermi positions
                  "ivo://nasa.gsfc.gcn/Fermi#GBM_Gnd_Pos",
                  "ivo://nasa.gsfc.gcn/Fermi#GBM_Fin_Pos",
                  )

    swift = False
    fermi = False
    for t in trig_swift:
        if ivorn.find(t) == 0:
            swift = True
            break
    for t in trig_fermi:
        if ivorn.find(t) == 0:
            fermi = True
            break

    if not (swift or fermi):
        return False
    else:
        if swift:
            # check to see if a GRB was identified
            try:
                grbid = v.find(".//Param[@name='GRB_Identified']").attrib['value']
            except AttributeError:
                log.error("Param[@name='GRB_Identified'] not found in XML packet - discarding.")
                return False
            if grbid != 'true':
                return False
        elif fermi:
            return False   # Ignore all Fermi triggers

    return True


def handle_grb(v, pretend=False):
    """
    Handles the actual VOEvent parsing, generating observations if appropriate.

    :param v: string in VOEvent XML format
    :param pretend: Boolean, True if we don't want to actually schedule the observations.
    :return: None
    """
    log.debug("processing GRB {0}".format(v.attrib['ivorn']))

    # trigger = False

    if 'SWIFT' in v.attrib['ivorn']:
        # compute the trigger id
        trig_id = "SWIFT_" + v.attrib['ivorn'].split('_')[-1].split('-')[0]

        # #The following should never be hit because of the checks made in is_grb.
        # grbid = v.find(".//Param[@name='GRB_Identified']").attrib['value']
        # if grbid != 'true':
        #     log.debug("SWIFT alert but not a GRB")
        #     handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
        #                         to_addresses=DEBUG_NOTIFY_LIST,
        #                         subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
        #                         msg_text=DEBUG_EMAIL_TEMPLATE % "SWIFT alert but not a GRB",
        #                         attachments=[('voevent.xml', voeventparse.dumps(v))])
        #
        #     return

        log.debug("SWIFT GRB trigger detected")
        this_trig_type = "SWIFT"

        # If the star tracker looses it's lock then we can't trust any of the locations so we ignore this alert.
        startrack_lost_lock = v.find(".//Param[@name='StarTrack_Lost_Lock']").attrib['value']
        # convert 'true' to True, and everything else to false
        startrack_lost_lock = startrack_lost_lock.lower() == 'true'
        log.debug("StarLock OK? {0}".format(not startrack_lost_lock))
        if startrack_lost_lock:
            log.debug("The SWIFT star tracker lost it's lock")
            handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                to_addresses=DEBUG_NOTIFY_LIST,
                                subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                msg_text=DEBUG_EMAIL_TEMPLATE % "SWIFT alert for GRB, but with StarTrack_Lost_Lock",
                                attachments=[('voevent.xml', voeventparse.dumps(v))])
            return

        # cache the event using the trigger id
        if trig_id not in xml_cache:
            grb = GRB(event=v)
            grb.trigger_id = trig_id
            xml_cache[trig_id] = grb
        else:
            grb = xml_cache[trig_id]
            grb.add_event(v)

        trig_time = float(v.find(".//Param[@name='Integ_Time']").attrib['value'])
        if trig_time < LONG_SHORT_LIMIT:
            grb.debug("Probably a short GRB: t={0} < 2".format(trig_time))
            grb.short = True
            grb.vcsmode = SWIFT_SHORT_TRIGGERS_IN_VCSMODE
            trigger = True
        else:
            grb.debug("Probably a long GRB: t={0} > 2".format(trig_time))
            grb.short = False
            grb.vcsmode = SWIFT_LONG_TRIGGERS_IN_VCSMODE
            trigger = True

    elif "Fermi" in v.attrib['ivorn']:
        log.debug("Fermi GRB notice detected")

        # cache the event using the trigger id
        trig_id = "Fermi_" + v.attrib['ivorn'].split('_')[-2]
        this_trig_type = v.attrib['ivorn'].split('_')[1]  # Flt, Gnd, or Fin

        if trig_id not in xml_cache:
            grb = GRB(event=v)
            grb.trigger_id = trig_id
            xml_cache[trig_id] = grb
        else:
            grb = xml_cache[trig_id]
            grb.add_event(v)

        # Not all alerts have trigger times.
        # eg Fermi#GBM_Gnd_Pos
        if this_trig_type == 'Flt':
            trig_time = float(v.find(".//Param[@name='Trig_Timescale']").attrib['value'])
            if trig_time < LONG_SHORT_LIMIT:
                grb.short = True
                grb.debug("Possibly a short GRB: t={0}".format(trig_time))
            else:
                msg = "Probably not a short GRB: t={0}".format(trig_time)
                grb.debug(msg)
                grb.debug("Not Triggering")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return  # don't trigger

            most_likely = int(v.find(".//Param[@name='Most_Likely_Index']").attrib['value'])

            # ignore things that don't have GRB as best guess
            if most_likely == 4:
                grb.debug("MOST_LIKELY = GRB")
                prob = int(v.find(".//Param[@name='Most_Likely_Prob']").attrib['value'])

                # ignore things that don't reach our probability threshold
                if prob > FERMI_POBABILITY_THRESHOLD:
                    grb.debug("Prob(GRB): {0}% > {1}".format(prob, FERMI_POBABILITY_THRESHOLD))
                    trigger = True
                else:
                    msg = "Prob(GRB): {0}% <{1}".format(prob, FERMI_POBABILITY_THRESHOLD)
                    grb.debug(msg)
                    grb.debug("Not Triggering")
                    handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                        to_addresses=DEBUG_NOTIFY_LIST,
                                        subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                        msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                        attachments=[('voevent.xml', voeventparse.dumps(v))])
                    return
            else:
                msg = "MOST_LIKELY != GRB"
                grb.debug(msg)
                grb.debug("Not Triggering")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return
        else:
            # for Gnd/Fin we trigger if we already triggered on the Flt position
            grb.debug("Gnd/Flt message -> reverting to Flt trigger")
            trigger = grb.triggered
    else:
        msg = "Not a Fermi or SWIFT GRB."
        log.debug(msg)
        log.debug("Not Triggering")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject='GRB_fermi_swift debug notification',
                            msg_text=DEBUG_EMAIL_TEMPLATE % msg,
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

    if not trigger:
        grb.debug("Not Triggering")
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                            msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
        return

    # get current position
    ra, dec, err = handlers.get_position_info(v)
    # add it to the list of positions
    grb.add_pos((ra, dec, err))
    grb.debug("RA {0}, Dec {1}, err {2}".format(ra, dec, err))

    if not grb.vcsmode:
        req_time_min = 30
    else:
        grb.debug('Reducing request time to %d for VCS observation' % SWIFT_SHORT_VCS_TIME)
        req_time_min = SWIFT_SHORT_VCS_TIME

    # check repointing just for tests
    # last_pos = grb.get_pos(-2)
    # if None not in last_pos:
    #     grb.info("Old position: RA {0}, Dec {1}, err {2}".format(*last_pos))
    #
    #     pos_diff = SkyCoord(ra=last_pos[0], dec=last_pos[1], unit=astropy.units.degree, frame='icrs').separation(
    #                SkyCoord(ra=ra, dec=dec, unit=astropy.units.degree, frame='icrs')).degree
    #     if pos_diff < REPOINTING_LIMIT:
    #         grb.info("New position is {0} deg from previous (less than constraint of {1} deg)".format(pos_diff,
    #                                                                                                   REPOINTING_LIMIT))
    #         grb.info("Not triggering")
    #         handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
    #                             to_addresses=DEBUG_NOTIFY_LIST,
    #                             subject='GRB_fermi_swift debug notification',
    #                             msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
    #                             attachments=[('voevent.xml', voeventparse.dumps(v))])
    #         return
    #     else:
    #         grb.info("New position is {0} deg from previous (greater than constraint of {1} deg".format(pos_diff,
    #                                                                                                   REPOINTING_LIMIT))
    #         grb.info("Attempting trigger")
    # end tests

    # look at the schedule
    obslist = triggerservice.obslist(obstime=1800)
    if obslist is not None and len(obslist) > 0:
        grb.debug("Currently observing:")
        grb.debug(str(obslist))
        # are we currently observing *this* GRB?
        obs = str(obslist[0][1])  # in case the obslist is returning unicode strings
        obs_group_id = obslist[0][5]   # The group ID of the first observation in the list returned
        grb.debug("obs {0}, trig {1}".format(obs, trig_id))

        # Same GRB trigger from same telescope
        if trig_id in obs:
#        if obs == trig_id:
            #  update the schedule!
            grb.info("Already observing this GRB")
            last_pos = grb.get_pos(-2)
            grb.info("Old position: RA {0}, Dec {1}, err {2}".format(*last_pos))
            pos_diff = SkyCoord(ra=last_pos[0], dec=last_pos[1], unit=astropy.units.degree, frame='icrs').separation(
                       SkyCoord(ra=ra, dec=dec, unit=astropy.units.degree, frame='icrs')).degree
            grb.info("New position is {0} deg from previous".format(pos_diff))
            if pos_diff < REPOINTING_LIMIT:
                grb.info("(less than constraint of {0} deg)".format(REPOINTING_LIMIT))
                grb.info("Not triggering")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject='GRB_fermi_swift debug notification',
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return
            grb.info("(greater than constraint of {0}deg)".format(REPOINTING_LIMIT))

            if "SWIFT" in trig_id:
                grb.info("Updating SWIFT observation with new coords")
                pass

            elif "Fermi" in trig_id:
                prev_type = grb.last_trig_type
                if this_trig_type == 'Flt' and (prev_type in ['Gnd','Fin']):
                    msg = "{0} positions have precedence over {1}".format(prev_type, this_trig_type)
                    grb.info(msg)
                    grb.info("Not triggering")
                    handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                        to_addresses=DEBUG_NOTIFY_LIST,
                                        subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                        msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                        attachments=[('voevent.xml', voeventparse.dumps(v))])
                    return
                elif this_trig_type == 'Gnd' and prev_type == 'Fin':
                    msg = "{0} positions have precedence over {1}".format(prev_type, this_trig_type)
                    grb.info(msg)
                    grb.info("Not triggering")
                    handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                        to_addresses=DEBUG_NOTIFY_LIST,
                                        subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                        msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                        attachments=[('voevent.xml', voeventparse.dumps(v))])
                    return
                else:
                    grb.info("Triggering {0} to replace {1}".format(this_trig_type, prev_type))

            # shorten the observing time requested so we are ~30mins total (for non VCS).
            # If this is a VCS mode observation, don't shorten the time - if the previous trigger was
            # in VCS mode, we won't be able to interrupt it, and if it wasn't, we still want the normal
            # length of a VCS trigger.
            if (grb.first_trig_time is not None) and not grb.vcsmode:
                req_time_min = 30 - (Time.now() - grb.first_trig_time).sec // 60
                grb.debug('Set requested time to %d' % req_time_min)

        # if we are observing a SWIFT trigger but not the trigger we just received
        elif 'SWIFT' in obs:
            if "SWIFT" in trig_id:
                if obs in xml_cache:
                    prev_short = xml_cache[obs].short
                else:
                    prev_short = False  # best bet if we don't know

                grb.info("Curently observing a SWIFT trigger")
                if grb.short and not prev_short:
                    grb.info("Interrupting with a short SWIFT GRB")
                else:
                    grb.info("Not interrupting previous observation")
                    handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                        to_addresses=DEBUG_NOTIFY_LIST,
                                        subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                        msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                        attachments=[('voevent.xml', voeventparse.dumps(v))])
                    return
            else:
                grb.info("Not interrupting previous obs")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return

        # if we are observing a FERMI trigger but not the trigger we just received
        elif 'Fermi' in obs:
            # SWIFT > Fermi
            if "SWIFT" in trig_id:
                grb.info("Replacing a Fermi trigger with a SWIFT trigger")
            else:
                grb.info("Currently observing a different Fermi trigger, not interrupting")
                handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                                    to_addresses=DEBUG_NOTIFY_LIST,
                                    subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                                    msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                                    attachments=[('voevent.xml', voeventparse.dumps(v))])
                return

        else:
            grb.info("Not currently observing any GRBs")
    else:
        grb.debug("Current schedule empty")

    emaildict = {'triggerid': grb.trigger_id,
                 'trigtime': Time.now().iso,
                 'ra': Angle(grb.ra[-1], unit=astropy.units.deg).to_string(unit=astropy.units.hour, sep=':'),
                 'dec': Angle(grb.dec[-1], unit=astropy.units.deg).to_string(unit=astropy.units.deg, sep=':'),
                 'err': grb.err[-1]}
    email_text = EMAIL_TEMPLATE % emaildict
    email_subject = EMAIL_SUBJECT_TEMPLATE % grb.trigger_id

    # Do the trigger
    result = grb.trigger_observation(ttype=this_trig_type,
                                     obsname=trig_id,
                                     time_min=req_time_min,
                                     pretend=(pretend or PRETEND),
                                     project_id=PROJECT_ID,
                                     secure_key=SECURE_KEY,
                                     email_tolist=NOTIFY_LIST,
                                     email_text=email_text,
                                     email_subject=email_subject,
                                     creator='VOEvent_Auto_Trigger: GRB_Fermi_swift=%s' % __version__,
                                     voevent=voeventparse.dumps(v))
    if result is None:
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=DEBUG_NOTIFY_LIST,
                            subject='GRB_fermi_swift debug notification for trigger: %s' % trig_id,
                            msg_text=DEBUG_EMAIL_TEMPLATE % '\n'.join([str(x) for x in grb.loglist]),
                            attachments=[('voevent.xml', voeventparse.dumps(v))])
