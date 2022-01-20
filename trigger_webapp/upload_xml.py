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


def write_and_upload(xml_string):
    # Parse
    trig = parsed_VOEvent(None, packet=xml_string)
    trig.parse()

    # Upload
    session = requests.session()
    session.auth = ("nick", "test123")
    url = 'http://127.0.0.1:8000/voevent_create/'
    data = {'telescope' : trig.telescope,
            'xml_packet' : xml_string,
            'duration' : trig.trig_time,
            'trigger_id' : trig.trig_id,
            'sequence_num' : trig.sequence_num,
            'trigger_type' : trig.this_trig_type,
            'ra' : trig.ra,
            'dec' : trig.dec,
            'pos_error' : trig.err,
            'ignored' : trig.ignore}
    r = session.post(url, data=data)

    # Upload
    # VOEvent.objects.get_or_create(telescope=trig.telescope,
    #                               xml_packet=xml_string,
    #                               duration=trig.trig_time,
    #                               trigger_id=trig.trig_id,
    #                               sequence_num=trig.sequence_num,
    #                               trigger_type=trig.this_trig_type,
    #                               ra=trig.ra,
    #                               dec=trig.dec,
    #                               pos_error=trig.err,
    #                               ignored=trig.ignore)
    # v = voeventparse.loads(xml_string.encode())
    # print(voeventparse.prettystr(v))

if __name__ == '__main__':
    xml_string = sys.stdin.read()
    write_and_upload(xml_string)