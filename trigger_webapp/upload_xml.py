#!/usr/bin/env python

import os
# Configure settings for project
# Need to run this before calling models from application!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trigger_webapp.settings')

import django
# Import settings
django.setup()

from trigger_app.models import VOEvent

import sys
import voeventparse
import requests

#from django.test import Client
from mwa_trigger.parse_xml import parsed_VOEvent
from astropy.coordinates import Angle
import astropy.units as u


def write_and_upload(xml_string):
    # Parse
    trig = parsed_VOEvent(None, packet=xml_string)

    # Upload
    session = requests.session()
    session.auth = ("nick", "test123")
    url = 'http://127.0.0.1:8000/voevent_create/'
    data = {
        'telescope' : trig.telescope,
        'xml_packet' : xml_string,
        'duration' : trig.trig_duration,
        'trigger_id' : trig.trig_id,
        'sequence_num' : trig.sequence_num,
        'event_type' : trig.event_type,
        'ra' : trig.ra,
        'dec' : trig.dec,
        'raj' : Angle(trig.ra, unit=u.deg).to_string(unit=u.hour, sep=':'),
        'decj': Angle(trig.dec, unit=u.deg).to_string(unit=u.deg, sep=':'),
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