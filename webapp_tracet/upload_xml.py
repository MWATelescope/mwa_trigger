#!/usr/bin/env python

import os
import sys
import requests
from astropy.coordinates import Angle
import astropy.units as u

from tracet.parse_xml import parsed_VOEvent


def write_and_upload(xml_string):
    # Parse
    trig = parsed_VOEvent(None, packet=xml_string)

    # Upload
    session = requests.session()
    session.auth = (os.environ['UPLOAD_USER'], os.environ['UPLOAD_PASSWORD'])
    SYSTEM_ENV = os.environ.get('SYSTEM_ENV', None)
    if SYSTEM_ENV == 'PRODUCTION' or SYSTEM_ENV == 'STAGING':
        url = 'https://mwa-trigger.duckdns.org/event_create/'
    else:
        url = 'http://127.0.0.1:8000/event_create/'
    data = {
        'telescope' : trig.telescope,
        'xml_packet' : xml_string,
        'duration' : trig.event_duration,
        'trig_id' : trig.trig_id,
        'sequence_num' : trig.sequence_num,
        'event_type' : trig.event_type,
        'role' : trig.role,
        'ra' : trig.ra,
        'dec' : trig.dec,
        'ra_hms' : trig.ra_hms,
        'dec_dms' : trig.dec_dms,
        'pos_error' : trig.err,
        'ignored' : trig.ignore,
        'source_name' : trig.source_name,
        'source_type' : trig.source_type,
        'event_observed' : trig.event_observed,
        'fermi_most_likely_index' : trig.fermi_most_likely_index,
        'fermi_detection_prob' : trig.fermi_detection_prob,
        'swift_rate_signif' : trig.swift_rate_signif,
        'antares_ranking' : trig.antares_ranking,
    }
    r = session.post(url, data=data)

if __name__ == '__main__':
    xml_string = sys.stdin.read()
    write_and_upload(xml_string)