import logging

logger = logging.getLogger(__name__)


def worth_observing(voevent, max_duration=2.05, fermi_prob=50):
    """Decide if a VOEvent is worth observing.

    Parameters
    ----------

    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    short_bool = False
    trigger_message = ""

    # Check the duration of the event
    if voevent.trig_time is not None:
        if voevent.trig_time < max_duration:
            short_bool = True
            trigger_message += f"Trigger time less than {max_duration} s. "
        else:
            debug_bool = True
            trigger_message += f"Trigger time greater than {max_duration} s. "

    if voevent.most_likely_index is not None:
        # Fermi triggers have their own probability
        if voevent.most_likely_index == 4:
            logger.debug("MOST_LIKELY = GRB")
            # ignore things that don't reach our probability threshold
            if voevent.detect_prob > fermi_prob:
                trigger_bool = True
                trigger_message += f"Fermi GRB probability greater than {fermi_prob}. "
            else:
                debug_bool = True
                trigger_message += f"Fermi GRB probability less than {fermi_prob}. "
        else:
            logger.debug("MOST LIKELY != GRB")
            debug_bool = False
            trigger_message += f"Fermi GRB likely index not 4. "
    elif short_bool:
        trigger_bool = True

    return trigger_bool, debug_bool, short_bool, trigger_message


def worth_observing_atca_short_grb(voevent):
    """
    Decide if an event is worth observing as part of the ATCA sGRB project

    Parameters
    ----------
    voevent : :obj:`mwa_trigger.parse_xml.parsed_VOEvent`
      The VOEvent to consider.

    Return
    ------
    trig, hold, msg : (bool, bool, string)
       The trigger status, True = worth observing.
       If the trigger should be held for manual intervation, True = on hold.
       A message detailing the decision logic.
    """
    # Setup up defaults
    trigger = False
    hold = False
    trigger_message = ""

    # TODO: Move these to a table in the database
    MAGNETAR_LIMIT = 0.033
    SHORT_LIMIT = 0.257
    MID_LIMIT = 1.025
    RATE_SIGNIF = 0.0

    if not voevent.telescope == "SWIFT":
        return False, False, "Not a SWIFT event."
    else:
        trigger_message += "A SWIFT event. "

    if not voevent.grb_ident:
        trigger_message += "Not a GRB. "
        return False, False, trigger_message
    else:
        trigger_message += "Id-ed as GRB."

    # Check the duration of the event
    if voevent.trig_time is not None:
        if voevent.trig_time < MAGNETAR_LIMIT:
            trigger = False
            trigger_message += f"Likely magnetar (trig_time < {MAGNETAR_LIMIT:.3f} s). "
        elif voevent.rate_signif <= RATE_SIGNIF:
            trigger = False
            trigger_message += f"Rate_signif < {RATE_SIGNIF:.3f} sigma. "
        elif voevent.trig_time < SHORT_LIMIT:
            trigger = True
            trigger_message += (
                f"Probably short duration (trig_time < {SHORT_LIMIT:.3f} s). "
            )
        elif voevent.trig_time < MID_LIMIT:
            trigger = True
            hold = True
            trigger_message += f"Maybe short duration (trig_time < {MID_LIMIT:.3f} s). "
        else:
            trigger = False
            trigger_message += (
                f"Probably long duration (trig_time > {MID_LIMIT:.3f} s. "
            )
    else:
        trigger_message += "Trigger has no trig_time"
        return False, False, trigger_message

    return trigger, hold, trigger_message
