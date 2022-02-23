import logging

logger = logging.getLogger(__name__)


def worth_observing_grb(voevent,
                        trig_min_duration=0.256, trig_max_duration=1.023,
                        pending_min_duration=1.024, pending_max_duration=2.048,
                        fermi_prob=50, rate_signif=0.0):
    """Decide if a GRB VOEvent is worth observing.

    Parameters
    ----------

    """
    # Setup up defaults
    trigger_bool = False
    debug_bool = False
    pending_bool = False
    trigger_message = ""

    # Check the events likelyhood data
    likely_bool = False
    if voevent.most_likely_index is not None:
        # Fermi triggers have their own probability
        if voevent.most_likely_index == 4:
            logger.debug("MOST_LIKELY = GRB")
            # ignore things that don't reach our probability threshold
            if voevent.detect_prob > fermi_prob:
                likely_bool = True
                trigger_message += f"Fermi GRB probability greater than {fermi_prob}.\n "
            else:
                debug_bool = True
                trigger_message += f"Fermi GRB probability less than {fermi_prob} so not triggering.\n "
        else:
            logger.debug("MOST LIKELY != GRB")
            debug_bool = False
            trigger_message += f"Fermi GRB likely index not 4.\n "
    if voevent.rate_signif is not None:
        # Swift has a rate signif in sigmas
        if voevent.rate_signif > rate_signif:
            likely_bool = True
            trigger_message += f"SWIFT Rate_signif > {rate_signif:.3f} sigma.\n "
        else:
            debug_bool = True
            trigger_message += f"SWIFT Rate_signif <= {rate_signif:.3f} sigma so not triggering.\n "

    # Check the duration of the event
    if voevent.trig_duration is not None and likely_bool:
        if trig_min_duration <= voevent.trig_duration <= trig_max_duration:
            trigger_bool = True
            trigger_message += f"Trigger duration between {trig_min_duration} and {trig_max_duration} s so triggering.\n "
        elif pending_min_duration <= voevent.trig_duration <= pending_max_duration:
            pending_bool = True
            trigger_message += f"Trigger duration between {pending_min_duration} and {pending_max_duration} s so waiting for a human's decision.\n "
        else:
            debug_bool = True
            trigger_message += f"Trigger duration outside of all time ranges so not triggering.\n "

    return trigger_bool, debug_bool, pending_bool, trigger_message