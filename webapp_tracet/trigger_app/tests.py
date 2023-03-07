from django.test import TestCase
from unittest.mock import patch

from .models import EventGroup, Event, PossibleEventAssociation, ProposalDecision, Observations
from yaml import load, Loader, safe_load

from tracet.parse_xml import parsed_VOEvent
import astropy.units as u
from astropy.coordinates import Angle, SkyCoord, EarthLocation
from astropy.time import Time


def create_voevent_wrapper(trig, ra_dec, dec_alter=True):
    if dec_alter:
        dec = ra_dec.dec.deg
        dec_dms = ra_dec.dec.to_string(unit=u.deg, sep=':')
    else:
        dec = trig.dec
        dec_dms = trig.dec_dms
    # Checks for no event observed
    if trig.event_observed is None:
        event_observed = None
    else:
        event_observed = trig.event_observed
    Event.objects.create(
        telescope=trig.telescope,
        xml_packet=trig.packet,
        duration=trig.event_duration,
        trig_id=trig.trig_id,
        self_generated_trig_id=trig.self_generated_trig_id,
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
        event_observed=event_observed,
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

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):

        xml_paths = [
            "../tests/test_events/group_01_01_Fermi.xml",
            "../tests/test_events/group_01_02_Fermi.xml",
            "../tests/test_events/group_01_03_SWIFT.xml"
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_possible_event_association(self):
        # Check there are three Events that were grouped as one PossibleEventAssociation
        self.assertEqual(len(Event.objects.all()), 3)
        self.assertEqual(len(PossibleEventAssociation.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_01 MWA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.all().filter(
            proposal__telescope__name='MWA_VCS').first().decision, 'T')

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_01 ATCA proposal decison:\n{ProposalDecision.objects.all().filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.all().filter(
            proposal__telescope__name='ATCA').first().decision, 'T')


class test_grb_group_02(TestCase):
    """Tests that events with the same Trigger ID will be grouped and trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
    ]

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/group_02_SWIFT_01_BAT_GRB_Pos.xml",
            "../tests/test_events/group_02_SWIFT_02_XRT_Pos.xml",
            "../tests/test_events/group_02_SWIFT_03_UVOT_Pos.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 3)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_grb_group_02 MWA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__telescope__name='MWA_VCS').first().decision, 'T')

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_02 ATCA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__telescope__name='ATCA').first().decision, 'T')


class test_grb_group_03(TestCase):
    """Tests ignored observations during an event
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/atca_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        "trigger_app/test_yamls/mwa_short_grb_proposal_settings.yaml",
    ]

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/SWIFT_BAT_Lightcurve.xml",
            "../tests/test_events/SWIFT_BAT_POS.xml"
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 2)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_grb_group_03 MWA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__telescope__name='MWA_VCS').first().decision, 'T')

    def test_mwa_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_grb_group_03 MWA proposal short GRB decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='MWA_VCS').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__telescope__name='MWA_VCS').first().decision, 'I')

    def test_atca_proposal_decision(self):
        print(
            f"\n\ntest_grb_group_02 ATCA proposal decison:\n{ProposalDecision.objects.filter(proposal__telescope__name='ATCA').first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__telescope__name='ATCA').first().decision, 'T')


class test_nu(TestCase):
    """Tests that a neutrino Event will trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_nu_proposal_settings.yaml",
    ]

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/Antares_1438351269.xml",
            "../tests/test_events/IceCube_134191_017593623_0.xml",
            "../tests/test_events/IceCube_134191_017593623_1.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 3)
        self.assertEqual(len(EventGroup.objects.all()), 2)

    def test_proposal_decision(self):
        # Two proposals decisions made
        print(
            f"\n\ntest_nu proposal decison:\n{ProposalDecision.objects.all().first().decision_reason}\n\n")
        self.assertEqual(len(ProposalDecision.objects.all()), 2)
        # Both triggered
        for prop_dec in ProposalDecision.objects.all():
            self.assertEqual(prop_dec.decision, 'T')


class test_fs(TestCase):
    """Tests that a flare star Event will trigger an observation
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        "trigger_app/test_yamls/mwa_fs_proposal_settings.yaml",
    ]

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/HD_8537_FLARE_STAR_TEST.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check there are three Events that were grouped as one by the trigger ID
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_proposal_decision(self):
        print(ProposalDecision.objects.all())
        print(
            f"\n\ntest_fs proposal decison:\n{ProposalDecision.objects.all().first().decision_reason}\n\n")
        self.assertEqual(ProposalDecision.objects.all().first().decision, 'T')


class test_hess_any_dur(TestCase):
    """Tests that a HESS Event will trigger an observation but only if we use a proposal with the any duration flag
    """
    # Load default fixtures
    fixtures = [
        "default_data.yaml",
        # Standard proposal that shouldn't trigger
        "trigger_app/test_yamls/mwa_grb_proposal_settings.yaml",
        # Hess proposal with the any duration flag that should trigger
        "trigger_app/test_yamls/mwa_hess_proposal_settings.yaml",
    ]

    with open('trigger_app/test_yamls/trigger_mwa_test.yaml', 'r') as file:
        trigger_mwa_test = safe_load(file)

    with open('trigger_app/test_yamls/atca_test_api_response.yaml', 'r') as file:
        atca_test_api_response = safe_load(file)

    @patch('trigger_app.telescope_observe.trigger_mwa', return_value=trigger_mwa_test)
    @patch('atca_rapid_response_api.api.send', return_value=atca_test_api_response)
    def setUp(self, fake_atca_api, fake_mwa_api):
        xml_paths = [
            "../tests/test_events/HESS_test_event.xml",
        ]

        # Setup current RA and Dec at zenith for the MWA
        MWA = EarthLocation(lat='-26:42:11.95',
                            lon='116:40:14.93', height=377.8 * u.m)
        mwa_coord = coord = SkyCoord(az=0., alt=90., unit=(
            u.deg, u.deg), frame='altaz', obstime=Time.now(), location=MWA)
        ra_dec = mwa_coord.icrs

        # Parse and upload the xml file group
        for xml in xml_paths:
            trig = parsed_VOEvent(xml)
            create_voevent_wrapper(trig, ra_dec)

    def test_trigger_groups(self):
        # Check event was made
        self.assertEqual(len(Event.objects.all()), 1)
        self.assertEqual(len(EventGroup.objects.all()), 1)

    def test_proposal_decision(self):
        # Test only one proposal triggered
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__event_any_duration=True).first().decision, 'T')
        self.assertEqual(ProposalDecision.objects.filter(
            proposal__event_any_duration=False).first().decision, 'I')
