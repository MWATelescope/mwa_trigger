#! python

"""
Library containing one or more functions to process incoming VOEvent XML strings. This library will
be imported by a long running process, so you can load large data files, etc, at import time, rather than
inside the processevent() function, to save time.
"""

__version__ = "0.2"
__author__ = ["Paul Hancock", "Andrew Williams", "Gemma Anderson"]

import logging

import astropy
from astropy.coordinates import Angle
from astropy.time import Time

import voeventparse

import handlers
import triggerservice

log = logging.getLogger('voevent.handlers.fermi_swift')   # Inherit the logging setup from handlers.py

# Settings
HORIZON_LIMIT = 30  # Don't observe if the source is below this elevation
FERMI_POBABILITY_THRESHOLD = 50  # Trigger on Fermi events that have most-likely-prob > this number

PROJECT_ID = 'D0009'
SECURE_KEY = handlers.get_secure_key(PROJECT_ID)
NOTIFY_LIST = ['too@mwa128t.org', 'Paul.Hancock@curtin.edu.au', 'Gemma.Anderson@curtin.edu.au', 'Andrew.Williams@curtin.edu.au']

EMAIL_TEMPLATE = """

The Fermi/Swift handler triggered an MWA observation for a 
Fermi/Swift GRB at %(trigtime)s UTC.

Details are:
Trigger ID: %(triggerid)s
RA:         %(ra)s hours
Dec:        %(dec)s deg
Error Rad:  %(err)7.3f deg

Result: %(result)s

Errors: 
%(errors)s

"""

EMAIL_SUBJECT_TEMPLATE = "Fermi-Swift handler trigger for %s"

# state storage
xml_cache = {}


class GRB(handlers.TriggerEvent):
    def __init__(self, event=None):
        self.short = False  # True if short
        handlers.TriggerEvent.__init__(self, event=event)

    # Override or add GRB specific methods here if desired.


def processevent(event=''):
    """

    :param event: A string containg the XML string in VOEvent format
    :return: TBD - do we want multiple handlers? Do we try a new event in each handler until
    one returns True, indicating that it understands it, or simply call all handlers
    for every events?
    """

    # event arrives as a unicode string but loads requires a non-unicode string.
    v = voeventparse.loads(str(event))
    log.info("Working on: %s" % v.attrib['ivorn'])
    isgrb = is_grb(v)
    log.debug("GRB? {0}".format(isgrb))
    if isgrb:
        handle_grb(v)

    log.info("Finished.")
    return isgrb     # True if we're handling this event, False if we're rejecting it


def is_grb(v):
    ivorn = v.attrib['ivorn']

    trig_list = ("ivo://nasa.gsfc.gcn/SWIFT#BAT_GRB_Pos",  # Swift positions
                 # "ivo://nasa.gsfc.gcn/Fermi#GBM_Alert",  # Ignore these as they always have ra/dec = 0/0
                 "ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos",  # Fermi positions
                 "ivo://nasa.gsfc.gcn/Fermi#GBM_Gnd_Pos",
                 "ivo://nasa.gsfc.gcn/Fermi#GBM_Fin_Pos"
                 )
    for t in trig_list:
        if ivorn.find(t) == 0:
            return True
    return False


def handle_grb(v):
    log.debug("processing GRB {0}".format(v.attrib['ivorn']))

    # trigger = False

    if 'SWIFT' in v.attrib['ivorn']:
        log.debug("SWIFT GRB trigger detected")
        this_trig_type = "SWIFT"

        # cache the event using the trigger id
        trig_id = "SWIFT_" + v.attrib['ivorn'].split('_')[-1].split('-')[0]
        if trig_id not in xml_cache:
            grb = GRB(event=v)
            grb.trigger_id = trig_id
            xml_cache[trig_id] = grb
        else:
            grb = xml_cache[trig_id]
            grb.add_event(v)

        trig_time = float(v.find(".//Param[@name='Integ_Time']").attrib['value'])
        if trig_time < 2:
            grb.debug("Probably a short GRB: t={0} < 2".format(trig_time))
            grb.short = True
            trigger = True

        else:
            grb.debug("Probably a long GRB: t={0} > 2".format(trig_time))
            grb.short = False
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
            if trig_time < 2:
                grb.short = True
                grb.debug("Possibly a short GRB: t={0}".format(trig_time))
            else:
                grb.debug("Probably not a short GRB: t={0}".format(trig_time))
                grb.debug("Not Triggering")
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
                    grb.debug("Prob(GRB): {0}% <{1}".format(prob, FERMI_POBABILITY_THRESHOLD))
                    grb.debug("Not Triggering")
                    return
            else:
                grb.debug("MOST_LIKELY != GRB")
                grb.debug("Not Triggering")
                return
        else:
            # for Gnd/Fin we trigger if we already triggered on the Flt position
            grb.debug("Gnd/Flt message -> reverting to Flt trigger")
            trigger = grb.triggered
    else:
        log.debug("Not a Fermi or SWIFT GRB.")
        log.debug("Not Triggering")
        return

    if not trigger:
        grb.debug("Not Triggering")
        return

    # get current position
    ra, dec, err = handlers.get_position_info(v)
    # add it to the list of positions
    grb.add_pos((ra, dec, err))
    grb.debug("RA {0}, Dec {1}, err {2}".format(ra, dec, err))

    req_time_min = 30

    # look at the schedule
    obslist = triggerservice.obslist(obstime=1800)
    if obslist is not None and len(obslist) > 0:
        grb.debug("Currently observing:")
        grb.debug(obslist)
        # are we currently observing *this* GRB?
        obs = str(obslist[0][1])  # in case the obslist is returning unicode strings
        grb.debug("obs {0}, trig {1}".format(obs, trig_id))

        # Same GRB trigger from same telescope
        if obs == trig_id:
            #  update the schedule!
            grb.info("Already observing this GRB")
            last_pos = grb.get_pos(-2)
            grb.info("Old position: RA {0}, Dec {1}, err {2}".format(*last_pos))

            if "SWIFT" in trig_id:
                grb.info("Updating SWIFT observation with new coords")
                pass

            elif "Fermi" in trig_id:
                prev_type = grb.last_trig_type
                if this_trig_type == 'Flt' and (prev_type in ['Gnd','Fin']):
                    grb.info("{0} positions have precedence over {1}".format(prev_type, this_trig_type))
                    grb.info("Not triggering")
                    return
                elif this_trig_type == 'Gnd' and prev_type == 'Fin':
                    grb.info("{0} positions have precedence over {1}".format(prev_type, this_trig_type))
                    grb.info("Not triggering")
                    return
                else:
                    grb.info("Triggering {0} to replace {1}".format(this_trig_type, prev_type))

            # shorten the observing time requested so we are ~30mins total.
            if grb.first_trig_time is not None:
                req_time_min = 30 - (Time.now() - grb.first_trig_time).sec // 60
            else:
                req_time_min = 30

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
                    grb.info("Not interrupting previous obs")
                    return
            else:
                grb.info("Not interrupting previous obs")
                return

        # if we are observing a FERMI trigger but not the trigger we just received
        elif 'Fermi' in obs:
            # SWIFT > Fermi
            if "SWIFT" in trig_id:
                grb.info("Replacing a Fermi trigger with a SWIFT trigger")
            else:
                grb.info("Currently observing a different Fermi trigger, not interrupting")
                return

        else:
            grb.info("Not currently observing any GRBs")
    else:
        grb.debug("Current schedule empty")

    # Do the trigger
    grb.trigger(time=Time.now(), ttype=this_trig_type)
    result = grb.trigger_observation(obsname=trig_id, time_min=req_time_min, project_id=PROJECT_ID, secure_key=SECURE_KEY)
    if result is not None:
        if result['success']:
            success_string = "SUCCESS - observation inserted into MWA schedule"
        else:
            success_string = "FAILURE - observation NOT inserted into MWA schedule"
        errors_string = '\n'.join(result['errors'])
        emaildict = {'triggerid':grb.trig_id,
                     'trigtime':Time.now().iso,
                     'ra':Angle(grb.ra[-1], unit=astropy.units.deg).to_string(unit=astropy.units.hour, sep=':'),
                     'dec':Angle(grb.dec[-1], unit=astropy.units.deg).to_string(unit=astropy.units.dec, sep=':'),
                     'err':grb[err][-1],
                     'success':success_string,
                     'errors':errors_string}
        handlers.send_email(from_address='mwa@telemetry.mwa128t.org',
                            to_addresses=NOTIFY_LIST,
                            subject=EMAIL_SUBJECT_TEMPLATE % grb.trig_id,
                            msg_text=EMAIL_TEMPLATE % emaildict,
                            attachments=[('schedule_%s.txt' % grb.trig_id, '\n'.join(result['schedule']), 'text/plain'),
                                         ('clear_%s.txt' % grb.trig_id, '\n'.join(result['clear']), 'text/plain')])
    return
