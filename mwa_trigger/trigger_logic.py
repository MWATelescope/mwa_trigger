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
            if voevent.detect_prob  > fermi_prob:
                trigger_bool = True
                trigger_message += f"Fermi GRB probabilty greater than {fermi_prob}. "
            else:
                debug_bool = True
                trigger_message += f"Fermi GRB probabilty less than {fermi_prob}. "
        else:
            logger.debug("MOST LIKELY != GRB")
            debug_bool = False
            trigger_message += f"Fermi GRB likey index not 4. "
    elif short_bool:
        trigger_bool = True

    return trigger_bool, debug_bool, short_bool, trigger_message