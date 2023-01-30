"""Tests the upload_xml.py script
"""
import unittest
from unittest.mock import patch
from requests import Session
from webapp_tracet.upload_xml import write_and_upload

import logging
logger = logging.getLogger(__name__)

class TestStringMethods(unittest.TestCase):
    @patch.object(Session, 'post')    
    def test_upload_xml(self, mock_post):

        TEST_XML_STRING = "<xml>test xml</xml>"
        write_and_upload(TEST_XML_STRING)

        self.assertIn('xml_packet', mock_post.call_args.kwargs['data'])

