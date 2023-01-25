import datetime
import logging

logger = logging.getLogger(__name__)


def worth_observing_grb(
        # event values
        event_duration=None,
        fermi_most_likely_index=None,
        fermi_detection_prob=None,
        swift_rate_signif=None,
        # Thresholds
        event_any_duration=False,
        event_min_duration=0.256,
        event_max_duration=1.023,
        pending_min_duration_1=0.124,
        pending_max_duration_1=0.255,
        pending_min_duration_2=1.024,
        pending_max_duration_2=2.048,
        fermi_min_detection_prob=50,
        swift_min_rate_signif=0.,
        # Other
        decision_reason_log="",
        event_id=None,
    ):
    """Decide if a GRB Event is worth observing.

    Parameters
    ----------
    event_duration : `float`, optional
        The duration of the VOevent in seconds.
    fermi_most_likely_index : `int`, optional
        An index that Fermi uses to describe what sort of source the Event. GRBs are 4 so this is what we check for.
    fermi_detection_prob : `int`, optional
        A GRB detection probabilty that Fermi produces as a percentage.
    swift_rate_signif : `float`, optional
        A rate signigicance that SWIFT produces in sigma.
    event_any_duration: `Bool`, optional
        If True will trigger on an event with any duration including None. Default False.
    event_min_duration, event_max_duration : `float`, optional
        A event duration between event_min_duration and event_max_duration will trigger an observation. Default 0.256, 1.023.
    pending_min_duration_1, pending_max_duration_1 : `float`, optional
        A event duration between pending_min_duration_1 and pending_max_duration_1 will create a pending observation. Default 0.124, 0.255.
    pending_min_duration_2, pending_max_duration_2 : `float`, optional
        A event duration between pending_min_duration_2 and pending_max_duration_2 will create a pending observation. Default 1.024, 2.048.
    fermi_min_detection_prob : `float`, optional
        The minimum fermi_detection_prob to trigger or create a pending observation. Default: 50.
    swift_min_rate_signif : `float`, optional
        The minimum swift_rate_signif to trigger or create a pending observation. Default: 0.0.
    decision_reason_log : `str`, optional
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
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
                decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB probability greater than {fermi_min_detection_prob}. \n"
            else:
                debug_bool = True
                decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB probability less than {fermi_min_detection_prob} so not triggering. \n"
        else:
            logger.debug("MOST LIKELY != GRB")
            debug_bool = False
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Fermi GRB likely index not 4. \n"
    elif swift_rate_signif is not None:
        # Swift has a rate signif in sigmas
        if swift_rate_signif > swift_min_rate_signif:
            likely_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: SWIFT rate significance > {swift_min_rate_signif:.3f} sigma. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: SWIFT rate significance <= {swift_min_rate_signif:.3f} sigma so not triggering. \n"
    else:
        likely_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No probability metric given so assume it is a GRB. \n"

    # Check the duration of the event
    if event_any_duration and likely_bool:
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Accepting any event duration so triggering. \n"
    elif not event_any_duration and event_duration is None:
        debug_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No event duration (None) so not triggering. \n"
    elif event_duration is not None and likely_bool:
        if event_min_duration <= event_duration <= event_max_duration:
            trigger_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {event_min_duration} and {event_max_duration} s so triggering. \n"
        elif pending_min_duration_1 <= event_duration <= pending_max_duration_1:
            pending_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {pending_min_duration_1} and {pending_max_duration_1} s so waiting for a human's decision. \n"
        elif pending_min_duration_2 <= event_duration <= pending_max_duration_2:
            pending_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration between {pending_min_duration_2} and {pending_max_duration_2} s so waiting for a human's decision. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Event duration outside of all time ranges so not triggering. \n"

    return trigger_bool, debug_bool, pending_bool, decision_reason_log

def worth_observing_nu(
        # event values
        antares_ranking=None,
        telescope=None,
        # Thresholds
        antares_min_ranking=2,
        # Other
        decision_reason_log="",
        event_id=None,
    ):
    """Decide if a Neutrino Event is worth observing.

    Parameters
    ----------
    antares_ranking : `int`, optional
        The rank of antaras event. Default: None.
    telescope : `int`, optional
        The rank of telescope of the event. Default: None.
    antares_min_ranking : `int`, optional
        The minimum (inclusive) rank of antaras events. Default: 2.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
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
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The Antares ranking ({antares_ranking}) is less than or equal to {antares_min_ranking} so triggering. \n"
        else:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The Antares ranking ({antares_ranking}) is greater than {antares_min_ranking} so not triggering. \n"
    else:
        trigger_bool = True
        decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: No thresholds for non Antares telescopes so triggering. \n"

    return trigger_bool, debug_bool, pending_bool, decision_reason_log

def worth_observing_gw(
        # event values
        event_type=None,
        telescope=None,
        lvc_false_alarm_rate=None,
        lvc_binary_neutron_star_probability=None,
        lvc_neutron_star_black_hole_probability=None,
        lvc_binary_black_hole_probability=None,
        lvc_terrestial_probability=None,
        lvc_includes_neutron_star_probability=None,
        # Thresholds
        minimum_neutron_star_probability=None,
        maximum_neutron_star_probability=None,
        minimum_binary_neutron_star_probability=None,
        maximum_binary_neutron_star_probability=None,
        minimum_neutron_star_black_hole_probability=None,
        maximum_neutron_star_black_hole_probability=None,
        minimum_binary_black_hole_probability=None,
        maximum_binary_black_hole_probability=None,
        minimum_terrestial_probability=None,
        maximum_terrestial_probability=None,
        start_observation_at_high_sensitivity=None,

        # Other
        decision_reason_log="",
        event_id=None, 
    ):
    """Decide if a Gravity Wave Event is worth observing.

    Parameters
    ----------
    lvc_binary_neutron_star_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_neutron_star_black_hole_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_binary_black_hole_probability : `float`, optional
        The terrestial probability of gw event. Default: None.
    lvc_terrestial_probability : `float`, optional
        The terrestial probability of gw event. Default: None
    lvc_includes_neutron_star_probability : `float`, optional
        The terrestial probability of gw event. Default: None
    
    event_type : `str`, optional
        Lvc alert type for gw event. Default: None.
    minimum_terrestial_probability : `float`, optional
        The minimum terrestial probability. Default: 0.95.
    maximum_terrestial_probability : `float`, optional
        The maximum terrestial probability. Default: 0.95.
    minimum_neutron_star_probability : `float`, optional
        The minimum neutron star probability. Default: 0.01.
    minimum_mass_gap_probability : `float`, optional
        The minimum mass gap probability. Default: 0.01.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    event_id : `int`, optional
        An Event ID that will be recorded in the decision_reason_log. Default: None.

    Returns
    -------
    trigger_bool : `boolean`
        If True an observations should be triggered.
    debug_bool : `boolean`
        If True a debug alert should be sent out.
    pending_bool : `boolean`
        If True will create a pending observation and wait for human intervention.
    decision_reason_log : `str`
        A log of all the decisions made so far so a user can understand why the source was(n't) observed.
    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False

    if telescope == "LVC":
        # PROB_NS
        if lvc_includes_neutron_star_probability > maximum_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NS probability ({lvc_includes_neutron_star_probability}) is greater than {maximum_neutron_star_probability} so not triggering. \n"
        elif lvc_includes_neutron_star_probability < minimum_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NS probability ({lvc_includes_neutron_star_probability}) is less than {minimum_neutron_star_probability} so not triggering. \n"
        elif lvc_binary_neutron_star_probability > maximum_binary_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BNS probability ({lvc_binary_neutron_star_probability}) is greater than {maximum_neutron_star_probability} so not triggering. \n"
        elif lvc_binary_neutron_star_probability < minimum_binary_neutron_star_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BNS probability ({lvc_binary_neutron_star_probability}) is less than {minimum_neutron_star_probability} so not triggering. \n"
        elif lvc_neutron_star_black_hole_probability > maximum_neutron_star_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NSBH probability ({lvc_neutron_star_black_hole_probability}) is greater than {maximum_neutron_star_black_hole_probability} so not triggering. \n"
        elif lvc_neutron_star_black_hole_probability < minimum_neutron_star_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_NSBH probability ({lvc_neutron_star_black_hole_probability}) is less than {maximum_neutron_star_black_hole_probability} so not triggering. \n"
        elif lvc_binary_black_hole_probability > maximum_binary_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BBH probability ({lvc_binary_black_hole_probability}) is greater than {maximum_binary_black_hole_probability} so not triggering. \n"
        elif lvc_binary_black_hole_probability < minimum_binary_black_hole_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_BBH probability ({lvc_binary_black_hole_probability}) is less than {minimum_binary_black_hole_probability} so not triggering. \n"
        elif lvc_terrestial_probability > maximum_terrestial_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_Terre probability ({lvc_terrestial_probability}) is greater than {maximum_terrestial_probability} so not triggering. \n"
        elif lvc_terrestial_probability < minimum_terrestial_probability:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The PROB_Terre probability ({lvc_terrestial_probability}) is less than {minimum_terrestial_probability} so not triggering. \n"
        
        
        elif (event_type == 'EarlyWarning' or event_type == 'Preliminary') and not start_observation_at_high_sensitivity:
            debug_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: Observing early and preliminary events is ({start_observation_at_high_sensitivity}) so not triggering. \n"
        else:
            trigger_bool = True
            decision_reason_log += f"{datetime.datetime.utcnow()}: Event ID {event_id}: The probability looks good so triggering. \n"


    return trigger_bool, debug_bool, pending_bool, decision_reason_log