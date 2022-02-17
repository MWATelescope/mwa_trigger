import logging

logger = logging.getLogger(__name__)


def worth_observing_grb(
        # event values
        trig_duration=None,
        fermi_most_likely_index=None,
        fermi_detection_prob=None,
        swift_rate_signif=None,
        # Thresholds
        trig_min_duration=0.256,
        trig_max_duration=1.023,
        pending_min_duration_1=0.124,
        pending_max_duration_1=0.255,
        pending_min_duration_2=1.024,
        pending_max_duration_2=2.048,
        fermi_min_detection_prob=50,
        swift_min_rate_signif=0.,
    ):
    """Decide if a GRB VOEvent is worth observing.

    Parameters
    ----------
    trig_duration : `float`, optional
        The duration of the VOevent in seconds.
    fermi_most_likely_index : `int`, optional
        An index that Fermi uses to describe what sort of source the VOEvent. GRBs are 4 so this is what we check for.
    fermi_detection_prob : `int`, optional
        A GRB detection probabilty that Fermi produces as a percentage.
    swift_rate_signif : `float`, optional
        A rate signigicance that SWIFT produces in sigma.
    trig_min_duration, trig_max_duration : `float`, optional
        The a trigger duration between trig_min_duration and trig_max_duration will trigger an observation. Default 0.256, 1.023.
    pending_min_duration_1, pending_max_duration_1 : `float`, optional
        The a trigger duration between pending_min_duration_1 and pending_max_duration_1 will create a pending observation. Default 0.124, 0.255.
    pending_min_duration_2, pending_max_duration_2 : `float`, optional
        The a trigger duration between pending_min_duration_2 and pending_max_duration_2 will create a pending observation. Default 1.024, 2.048.
    fermi_min_detection_prob : `float`, optional
        The minimum fermi_detection_prob to trigger or create a pending observation. Default: 50.
    swift_min_rate_signif : `float`, optional
        The minimum swift_rate_signif to trigger or create a pending observation. Default: 0.0.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False
    trigger_message = ""

    # Check the events likelyhood data
    likely_bool = False
    if fermi_most_likely_index is not None:
        # Fermi triggers have their own probability
        if fermi_most_likely_index == 4:
            logger.debug("MOST_LIKELY = GRB")
            # ignore things that don't reach our probability threshold
            if fermi_detection_prob > fermi_min_detection_prob:
                likely_bool = True
                trigger_message += f"Fermi GRB probability greater than {fermi_min_detection_prob}.\n "
            else:
                debug_bool = True
                trigger_message += f"Fermi GRB probability less than {fermi_min_detection_prob} so not triggering.\n "
        else:
            logger.debug("MOST LIKELY != GRB")
            debug_bool = False
            trigger_message += f"Fermi GRB likely index not 4.\n "
    elif swift_rate_signif is not None:
        # Swift has a rate signif in sigmas
        if swift_rate_signif > swift_min_rate_signif:
            likely_bool = True
            trigger_message += f"SWIFT rate significance > {swift_min_rate_signif:.3f} sigma.\n "
        else:
            debug_bool = True
            trigger_message += f"SWIFT rate significance <= {swift_min_rate_signif:.3f} sigma so not triggering.\n "
    else:
        likely_bool = True
        trigger_message += f"No probability metric given so assume it is a GRB.\n "

    # Check the duration of the event
    if trig_duration is not None and likely_bool:
        if trig_min_duration <= trig_duration <= trig_max_duration:
            trigger_bool = True
            trigger_message += f"Trigger duration between {trig_min_duration} and {trig_max_duration} s so triggering.\n "
        elif pending_min_duration_1 <= trig_duration <= pending_max_duration_1:
            pending_bool = True
            trigger_message += f"Trigger duration between {pending_min_duration_1} and {pending_max_duration_1} s so waiting for a human's decision.\n "
        elif pending_min_duration_2 <= trig_duration <= pending_max_duration_2:
            pending_bool = True
            trigger_message += f"Trigger duration between {pending_min_duration_2} and {pending_max_duration_2} s so waiting for a human's decision.\n "
        else:
            debug_bool = True
            trigger_message += f"Trigger duration outside of all time ranges so not triggering.\n "

    return trigger_bool, debug_bool, pending_bool, trigger_message


def worth_observing_atca_short_grb(
    voevent, magnetar_limit=0.033, short_limit=0.257, mid_limit=1.025, rate_signif=0.0
):
    """
    Decide if an event is worth observing as part of the ATCA sGRB project.

    An event needs to be a SWIFT event, with GRB_identified=True.

    magnetars and long GRBs don't cause a trigger.

    Short GRBs do cause a trigger.

    "mid" GRBs cause a trigger but are put on hold for user intervention.

    Parameters
    ----------
    voevent : :obj:`mwa_trigger.parse_xml.parsed_VOEvent`
      The VOEvent to consider.

    magnetar_limit : float, default 0.033
      Break point for the magnetar -> short grb transition

    short_limit : float, default 0.257
      Break point for the short -> mid grb transition

    mid_limit : float, default 1.025
      Break point for the mid -> long grb transition

    rate_signif : float, default 0.0
      Lower limit on the rate significance (sigmas) for trigger events to be accepted


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
    if voevent.trig_duration is not None:
        if voevent.trig_duration < magnetar_limit:
            trigger = False
            trigger_message += f"Likely magnetar (trig_duration < {magnetar_limit:.3f} s). "
        elif voevent.rate_signif <= rate_signif:
            trigger = False
            trigger_message += f"Rate_signif < {rate_signif:.3f} sigma. "
        elif voevent.trig_duration < short_limit:
            trigger = True
            trigger_message += (
                f"Probably short duration (trig_duration < {short_limit:.3f} s). "
            )
        elif voevent.trig_duration < mid_limit:
            trigger = True
            hold = True
            trigger_message += f"Maybe short duration (trig_duration < {mid_limit:.3f} s). "
        else:
            trigger = False
            trigger_message += (
                f"Probably long duration (trig_duration > {mid_limit:.3f} s. "
            )
    else:
        trigger_message += "Trigger has no trig_duration"
        return False, False, trigger_message

    return trigger, hold, trigger_message
