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
        # Other
        trigger_message="",
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
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".

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


def worth_observing_nu(
        # event values
        antares_ranking=None,
        telescope=None,
        # Thresholds
        antares_min_ranking=2,
        # Other
        trigger_message="",
    ):
    """Decide if a Neutrino VOEvent is worth observing.

    Parameters
    ----------
    antares_ranking : `int`, optional
        The rank of antaras event. Default: None.
    telescope : `int`, optional
        The rank of telescope of the event. Default: None.
    antares_min_ranking : `int`, optional
        The minimum (inclusive) rank of antaras events. Default: 2.
    trigger_message : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".

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

    if telescope == "Antares":
        # Check the Antares ranking
        if antares_ranking <= antares_min_ranking:
            trigger_bool = True
            trigger_message += f"The Antares ranking ({antares_ranking}) is less than or equal to {antares_min_ranking} so triggering.\n "
        else:
            debug_bool = True
            trigger_message += f"The Antares ranking ({antares_ranking}) is greater than {antares_min_ranking} so not triggering.\n "
    else:
        trigger_bool = True
        trigger_message += f"No thresholds for non Antares telescopes so triggering.\n "

    return trigger_bool, debug_bool, pending_bool, trigger_message