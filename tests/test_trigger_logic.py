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

def test_trigger_grb_event():
    xml_tests = [
                 # A short GRB we would want to trigger on
                 ('Fermi_GRB.yaml', [True, False, False, 'Fermi GRB probability greater than 50.\n Event duration between 0.256 and 1.023 s so triggering.\n ']),
                 # A SWIFT trigger that is too long to trigger on
                 ('SWIFT00.yaml', [False, True, False, 'SWIFT rate significance > 0.000 sigma.\n Event duration outside of all time ranges so not triggering.\n ']),
                 # A trigger type that we choose to ignore
                 ('SWIFT_Point_Dir_Change.yaml', [False, True, False, 'No probability metric given so assume it is a GRB.\n No event duration (None) so not triggering.\n ']),
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

        # Compare to expected
        assert_equal(trigger_bool, exp_trigger_bool)
        assert_equal(debug_bool, exp_debug_bool)
        assert_equal(pending_bool, exp_pending_bool)
        assert_equal(decision_reason_log, exp_decision_reason_log)

def test_trigger_nu_event():
    xml_tests = [
                 # An antares neutrino we would want to trigger on
                 ('Antares_1438351269.yaml', [True, False, False, 'The Antares ranking (1) is less than or equal to 2 so triggering.\n ']),
                 # An antares neutrino we would want to trigger on
                 ('IceCube_134191_017593623_0.yaml', [True, False, False, 'No thresholds for non Antares telescopes so triggering.\n ']),
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