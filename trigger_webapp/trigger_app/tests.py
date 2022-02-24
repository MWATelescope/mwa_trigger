from django.test import TestCase

from .models import VOEvent, TriggerEvent, ProposalSettings

from mwa_trigger.parse_xml import parsed_VOEvent
from astropy.coordinates import Angle
import astropy.units as u
import datetime

class test_group_01(TestCase):
    # Load default fixtures
    fixtures = ["default_data.yaml", "trigger_app/test_yamls/mwa_proposal_settings.yaml"]
    def setUp(self):
        xml_paths = [
            "../tests/test_events/group_01_01_Fermi.xml",
            "../tests/test_events/group_01_02_Fermi.xml",
            "../tests/test_events/group_01_03_SWIFT.xml"
        ]
        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)

            VOEvent.objects.create(
                telescope=trig.telescope,
                xml_packet=trig.packet,
                duration=trig.trig_duration,
                trigger_id=trig.trig_id,
                sequence_num=trig.sequence_num,
                event_type=trig.event_type,
                ra=trig.ra,
                dec=trig.dec,
                ra_hms=Angle(trig.ra, unit=u.deg).to_string(unit=u.hour, sep=':'),
                dec_dms=Angle(trig.dec, unit=u.deg).to_string(unit=u.deg, sep=':'),
                pos_error=trig.err,
                ignored=trig.ignore,
                source_name=trig.source_name,
                source_type=trig.source_type,
                event_observed=datetime.datetime.strptime(str(trig.event_observed), "%Y-%m-%dT%H:%M:%S.%f"),
                fermi_most_likely_index=trig.fermi_most_likely_index,
                fermi_detection_prob=trig.fermi_detection_prob,
                swift_rate_signif=trig.swift_rate_signif,
            )

    def test_trigger_groups(self):
        # Check there are three VOEvents that were grouped as one TriggerEvent
        self.assertEqual(len(VOEvent.objects.all()), 3)
        self.assertEqual(len(TriggerEvent.objects.all()), 1)