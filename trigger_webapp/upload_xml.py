#!/usr/bin/env python

import os
import sys
import requests
from astropy.coordinates import Angle
import astropy.units as u

from mwa_trigger.parse_xml import parsed_VOEvent


def write_and_upload(xml_string):
    # Parse
    trig = parsed_VOEvent(None, packet=xml_string)
    if trig.ra is None or trig.dec is None:
        ra_hms = None
        dec_dms = None
    else:
        ra_hms = Angle(trig.ra, unit=u.deg).to_string(unit=u.hour, sep=':')
        dec_dms = Angle(trig.dec, unit=u.deg).to_string(unit=u.deg, sep=':')

    # Upload
    session = requests.session()
    session.auth = (os.environ['UPLOAD_USER'], os.environ['UPLOAD_PASSWORD'])
    url = 'https://mwa-trigger.duckdns.org/voevent_create/'
    data = {
        'telescope' : trig.telescope,
        'xml_packet' : xml_string,
        'duration' : trig.trig_duration,
        'trigger_id' : trig.trig_id,
        'sequence_num' : trig.sequence_num,
        'event_type' : trig.event_type,
        'ra' : trig.ra,
        'dec' : trig.dec,
        'ra_hms' : ra_hms,
        'dec_dms': dec_dms,
        'pos_error' : trig.err,
        'ignored' : trig.ignore,
        'source_name' : trig.source_name,
        'source_type' : trig.source_type,
        'event_observed' : trig.event_observed,
        'fermi_most_likely_index' : trig.fermi_most_likely_index,
        'fermi_detection_prob' : trig.fermi_detection_prob,
        'swift_rate_signf' : trig.swift_rate_signif,
    }
    r = session.post(url, data=data)

    # Upload
    # VOEvent.objects.get_or_create(telescope=trig.telescope,
    #                               xml_packet=xml_string,
    #                               duration=trig.trig_duration,
    #                               trigger_id=trig.trig_id,
    #                               sequence_num=trig.sequence_num,
    #                               event_type=trig.this_trig_type,
    #                               ra=trig.ra,
    #                               dec=trig.dec,
    #                               pos_error=trig.err,
    #                               ignored=trig.ignore)
    # v = voeventparse.loads(xml_string.encode())
    # print(voeventparse.prettystr(v))

if __name__ == '__main__':
    xml_string = sys.stdin.read()
    write_and_upload(xml_string)