#!/usr/bin/env python

import os
import sys
import requests

from tracet.parse_xml import parsed_VOEvent
import logging
logger = logging.getLogger(__name__)


def write_and_upload(xml_string):

    # Upload
    session = requests.session()
    session.auth = (os.environ['UPLOAD_USER'], os.environ['UPLOAD_PASSWORD'])
    SYSTEM_ENV = os.environ.get('SYSTEM_ENV', None)
    if SYSTEM_ENV == 'PRODUCTION' or SYSTEM_ENV == 'STAGING':
        url = 'https://tracet.duckdns.org/event_create/'
    else:
        url = 'http://127.0.0.1:8000/event_create/'

    # Parse
    data = parsed_VOEvent(None, packet=xml_string)
    data.xml_packet = xml_string
    session.post(url, data=data)

if __name__ == '__main__':
    xml_string = sys.stdin.read()
    write_and_upload(xml_string)
