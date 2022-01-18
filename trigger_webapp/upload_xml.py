#!/usr/bin/env python

import os
# Configure settings for project
# Need to run this before calling models from application!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trigger_webapp.settings')

import django
# Import settings
django.setup()

import sys
import voeventparse
import requests

from trigger_app.models import Trigger
from mwa_trigger.parse_xml import Trigger_Event

def write_and_upload(xml_string):
    # Parse
    trig = Trigger_Event(None, packet=xml_string)
    trig.parse()

    xml_file_name = f'{trig.trig_id}.xml'
    with open(xml_file_name, 'w') as f:
        f.write(xml_string)

    # Upload
    Trigger.objects.get_or_create(xml=xml_file_name,
                                  duration=trig.trig_time,
                                  trigger_id=trig.trig_id,
                                  trigger_type=trig.this_trig_type,
                                  ra=trig.ra,
                                  dec=trig.dec,
                                  pos_error=trig.err)

if __name__ == '__main__':
    xml_string = sys.stdin.read()
    print(xml_string)
    write_and_upload(xml_string)