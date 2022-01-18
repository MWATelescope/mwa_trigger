#! /usr/bin/env python3
"""Tests the parse_xml.py script
"""
import os
from numpy.testing import assert_almost_equal

from mwa_trigger.parse_xml import Trigger_Event

import logging
logger = logging.getLogger(__name__)

def test_trigger_event():
    xml_tests = [
                 ('Fermi_GRB.xml'),
                 ('SWIFT00.xml')
                ]

    for xml in xml_tests:
        print(f'\n{xml}')
        xml_loc = os.path.join(os.path.dirname(__file__), 'test_events', xml)
        trig = Trigger_Event(xml_loc)
        trig.parse()
        print("Trig details:")
        print(f"Dur:  {trig.trig_time} s")
        print(f"ID:   {trig.trig_id}")
        print(f"Type: {trig.this_trig_type}")
        print(f"Trig position: {trig.ra} {trig.dec} {trig.err}")



if __name__ == "__main__":
    """
    Tests the relevant functions in sn_flux_est.py
    Uses psrcat version 1.59. Values may change for different versions
    """

    # introspect and run all the functions starting with 'test'
    for f in dir():
        if f.startswith('test'):
            print(f)
            globals()[f]()