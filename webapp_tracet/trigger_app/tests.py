from django.test import TestCase

from .models import TriggerID, VOEvent, PossibleEventAssociation, ProposalDecision, Observations

from tracet.parse_xml import parsed_VOEvent
import astropy.units as u
from astropy.coordinates import Angle, SkyCoord, EarthLocation
from astropy.time import Time
import datetime


def create_voevent_wrapper(trig, ra_dec, dec_alter=True):
    if dec_alter:
        dec=ra_dec.dec.deg
        dec_dms=ra_dec.dec.to_string(unit=u.deg, sep=':')
    else:
        dec=trig.dec
        dec_dms=trig.dec_dms
    VOEvent.objects.create(
        telescope=trig.telescope,
        xml_packet=trig.packet,
        duration=trig.trig_duration,
        trigger_id=trig.trig_id,
        sequence_num=trig.sequence_num,
        event_type=trig.event_type,
        antares_ranking=trig.antares_ranking,
        # Sent event up so it's always pointing at zenith
        ra=ra_dec.ra.deg,
        dec=dec,
        ra_hms=ra_dec.ra.to_string(unit=u.hour, sep=':'),
        dec_dms=dec_dms,
        pos_error=trig.err,
        ignored=trig.ignore,
        source_name=trig.source_name,
        source_type=trig.source_type,
        event_observed=datetime.datetime.strptime(str(trig.event_observed), "%Y-%m-%dT%H:%M:%S.%f"),
        fermi_most_likely_index=trig.fermi_most_likely_index,
        fermi_detection_prob=trig.fermi_detection_prob,
        swift_rate_signif=trig.swift_rate_signif,
    )


class test_grb_group_01(TestCase):
    """Tests that events in a similar position and time will be grouped as possible event associations and trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]
    def setUp(self):
        xml_paths = [
            "../tests/test_events/group_01_01_Fermi.xml",
            "../tests/test_events/group_01_02_Fermi.xml",
            "../tests/test_events/group_01_03_SWIFT.xml"
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)


    def test_possible_event_association(self):
        # Check there are three VOEvents that were grouped as one PossibleEventAssociation
        self.assertEqual(len(VOEvent.objects.all()), 3)
        self.assertEqual(len(PossibleEventAssociation.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(f"\n\n!!!!!!!!!!!!!!\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n!!!!!!!!!!!!!!!\n\n")
        self.assertEqual(ProposalDecision.objects.all().filter(proposal__telescope__name='MWA_VCS').first().decision, 'T')

    def test_atca_proposal_decision(self):
        print(f"\n\n!!!!!!!!!!!!!!\n{ProposalDecision.objects.all().filter(proposal__telescope__name='ATCA').first().decision_reason}\n!!!!!!!!!!!!!!!\n\n")
        self.assertEqual(ProposalDecision.objects.all().filter(proposal__telescope__name='ATCA').first().decision, 'T')


class test_grb_group_02(TestCase):
    """Tests that events with the same Trigger ID will be grouped and trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]
    def setUp(self):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
            "../tests/test_events/group_02_SWIFT_02_XRT_Pos.xml",
            "../tests/test_events/group_02_SWIFT_03_UVOT_Pos.xml"
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)


    def test_trigger_groups(self):
        # Check there are three VOEvents that were grouped as one by the trigger ID
        self.assertEqual(len(VOEvent.objects.all()), 3)
        self.assertEqual(len(TriggerID.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(f"\n\n!!!!!!!!!!!!!!\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n!!!!!!!!!!!!!!!\n\n")
        self.assertEqual(ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision, 'T')

    def test_atca_proposal_decision(self):
        print(f"\n\n!!!!!!!!!!!!!!\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n!!!!!!!!!!!!!!!\n\n")
        self.assertEqual(ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision, 'T')

class test_grb_group_03(TestCase):
    """Tests that a strange combination of SWIFT event types
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]
    def setUp(self):
        xml_paths = [
            # A poisition but not confirmed what it is
            "../tests/test_events/group_03_SWIFT_BAT_QuickLook_Pos.xml",
            # Confirmed the previous alert is a GRB
            "../tests/test_events/group_03_SWIFT_FOM_Obs.xml",
            # Improved position that should trigger a new observation
            "../tests/test_events/group_03_SWIFT_XRT_Pos.xml"
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec, dec_alter=False)


    def test_trigger_groups(self):
        # Check there are three VOEvents that were grouped as one by the trigger ID
        self.assertEqual(len(VOEvent.objects.all()), 3)
        self.assertEqual(len(TriggerID.objects.all()), 1)

    def test_atca_proposal_decision(self):
        # Final proposal dicision was triggered
        print(f"SWIFT ATCA TEST:{ProposalDecision.objects.all().first().decision_reason}")
        self.assertEqual(ProposalDecision.objects.all().first().decision, 'T')

    def test_atca_observations_triggered(self):
        # First observation ignored but two other observations were triggered
        self.assertEqual(len(Observations.objects.all()), 2)


class test_nu(TestCase):
    """Tests that a neutrino VOEvent will trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_nu_proposal_settings.yaml",
    ]
    def setUp(self):
        xml_paths = [
            "../tests/test_events/Antares_1438351269.xml",
            "../tests/test_events/IceCube_134191_017593623_0.xml",
            "../tests/test_events/IceCube_134191_017593623_1.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)


    def test_trigger_groups(self):
        # Check there are three VOEvents that were grouped as one by the trigger ID
        self.assertEqual(len(VOEvent.objects.all()), 3)
        self.assertEqual(len(TriggerID.objects.all()), 2)

    def test_proposal_decision(self):
        # Two proposals decisions made
        self.assertEqual(len(ProposalDecision.objects.all()), 2)
        # Both triggered
        for prop_dec in ProposalDecision.objects.all():
            self.assertEqual(prop_dec.decision, 'T')


class test_fs(TestCase):
    """Tests that a flare star VOEvent will trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_fs_proposal_settings.yaml",
    ]
    def setUp(self):
        xml_paths = [
            "../tests/test_events/HD_8537_FLARE_STAR_TEST.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95', lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)


    def test_trigger_groups(self):
        # Check there are three VOEvents that were grouped as one by the trigger ID
        self.assertEqual(len(VOEvent.objects.all()), 1)
        self.assertEqual(len(TriggerID.objects.all()), 1)

    def test_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(f"\n\n!!!!!!!!!!!!!!\n{ProposalDecision.objects.all().first().decision_reason}\n!!!!!!!!!!!!!!!\n\n")
        self.assertEqual(ProposalDecision.objects.all().first().decision, 'T')