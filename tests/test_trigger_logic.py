"""Tests the parse_xml.py script
"""
import os
from yaml import load, dump, Loader
from numpy.testing import assert_equal

from tracet.parse_xml import parsed_VOEvent
from tracet.trigger_logic import worth_observing_grb, worth_observing_nu
import voeventparse

import logging
logger = logging.getLogger(__name__)

def strip_time(decision_reason_log):
    """Strip the first 28 characters of each line of the decision log to prevent the different times of the test causing errors.
    """
    decision_reason_log_lines = decision_reason_log.split("\n")
    stripped_lines = []
    for line in decision_reason_log_lines:
        stripped_lines.append(line[28:])
    decision_reason_log = "\n".join(stripped_lines)
    return decision_reason_log

def test_trigger_grb_event():
    xml_tests = [
                 # A short GRB we would want to trigger on
                #  ('Fermi_GRB.yaml', [True, False, False, '2022-09-08 01:30:34.201740: Event ID None: Fermi GRB probability greater than 50. \n2022-09-08 01:30:34.201740: Event ID None: Event duration between 0.256 and 1.023 s so triggering. \n']),
                #  # A SWIFT trigger that is too long to trigger on
                #  ('SWIFT00.yaml', [False, True, False, '2022-09-08 01:30:34.201740: Event ID None: SWIFT rate significance (13.74) >= swift_min_rate (0.000) sigma. \n2022-09-08 01:30:34.201740: Event ID None: Event duration outside of all time ranges so not triggering. \n']),
                #  # A trigger type that we choose to ignore
                #  ('SWIFT_Point_Dir_Change.yaml', [False, True, False, '2022-09-08 01:30:34.201740: Event ID None: No probability metric given so assume it is a GRB. \n2022-09-08 01:30:34.201740: Event ID None: No event duration (None) so not triggering. \n']),
                 # Trigger when swift significance rate is 0
                 ('SWIFT_Trigger.yaml', [True, False, False, '2022-09-08 01:30:34.201740: Event ID None: SWIFT rate significance (0) >= swift_min_rate (0.000) sigma. \n2022-09-08 01:30:34.201740: Event ID None: Event duration between 0.256 and 1.023 s so triggering. \n']),
                ]

    for yaml_file, exp_worth_obs in xml_tests:
        exp_trigger_bool, exp_debug_bool, exp_pending_bool, exp_decision_reason_log = exp_worth_obs
        # Open the preparsed file
        yaml_loc = os.path.join('tests/test_events', yaml_file)
        # Read in expected class and do the same
        with open(yaml_loc, 'r') as stream:
            trig = load(stream, Loader=Loader)

        # Send it through trigger logic
        trigger_bool, debug_bool, pending_bool, decision_reason_log = worth_observing_grb(
            event_duration=trig["event_duration"],
            fermi_most_likely_index=trig["fermi_most_likely_index"],
            fermi_detection_prob=trig["fermi_detection_prob"],
            swift_rate_signif=trig["swift_rate_signif"],
        )
        logger.debug(f"{yaml_file}")
        logger.debug(f"{trigger_bool}, {debug_bool}, {pending_bool}")
        logger.debug(f"{decision_reason_log}")

        # Strip time stamps from decision reason logs
        decision_reason_log = strip_time(decision_reason_log)
        exp_decision_reason_log = strip_time(exp_decision_reason_log)

        # Compare to expected
        assert_equal(trigger_bool, exp_trigger_bool)
        assert_equal(debug_bool, exp_debug_bool)
        assert_equal(pending_bool, exp_pending_bool)
        assert_equal(decision_reason_log, exp_decision_reason_log)

def test_trigger_nu_event():
    xml_tests = [
                 # An antares neutrino we would want to trigger on
                 ('Antares_1438351269.yaml', [True, False, False, '2022-09-08 01:30:34.201740: Event ID None: The Antares ranking (1) is less than or equal to 2 so triggering. \n']),
                 # An antares neutrino we would want to trigger on
                 ('IceCube_134191_017593623_0.yaml', [True, False, False, '2022-09-08 01:30:34.201740: Event ID None: No thresholds for non Antares telescopes so triggering. \n']),
                ]

    for yaml_file, exp_worth_obs in xml_tests:
        exp_trigger_bool, exp_debug_bool, exp_pending_bool, exp_decision_reason_log = exp_worth_obs
        # Open the preparsed file
        yaml_loc = os.path.join('tests/test_events', yaml_file)
        # Read in expected class and do the same
        with open(yaml_loc, 'r') as stream:
            trig = load(stream, Loader=Loader)

        # Send it through trigger logic
        trigger_bool, debug_bool, pending_bool, decision_reason_log = worth_observing_nu(
            antares_ranking=trig["antares_ranking"],
            telescope=trig["telescope"],
        )
        logger.debug(f"{trigger_bool}, {debug_bool}, {pending_bool}")
        logger.debug(f"{decision_reason_log}")

        # Strip time stamps from decision reason logs
        decision_reason_log = strip_time(decision_reason_log)
        exp_decision_reason_log = strip_time(exp_decision_reason_log)

        # Compare to expected
        assert_equal(trigger_bool, exp_trigger_bool)
        assert_equal(debug_bool, exp_debug_bool)
        assert_equal(pending_bool, exp_pending_bool)
        assert_equal(decision_reason_log, exp_decision_reason_log)


if __name__ == "__main__":
    """
    Tests the trigger software that doesn't require the database
    """

    # introspect and run all the functions starting with 'test'
    for f in dir():
        if f.startswith('test'):
            print(f)
            globals()[f]()