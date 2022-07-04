#! /usr/bin/env python
"""Tests the parse_xml.py script
"""
import os
from yaml import load, dump, Loader
from numpy.testing import assert_equal

from mwa_trigger.parse_xml import parsed_VOEvent
from mwa_trigger.trigger_logic import worth_observing_grb, worth_observing_nu
import voeventparse

import logging
logger = logging.getLogger(__name__)

def test_parse_grb_event():
    xml_tests = [
                 # A short GRB we would want to trigger on
                 ('Fermi_GRB.xml', None),
                 # Same as the above but a xml packet to test if it works
                 (None, '<VOEvent xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ivorn="ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos_2017-11-26T05:38:43.71_533367528_46-276" role="observation" version="2.0" xsi:schemaLocation="http://www.ivoa.net/xml/VOEvent/v2.0  http://www.ivoa.net/xml/VOEvent/VOEvent-v2.0.xsd">\n  <Who>\n    <AuthorIVORN>ivo://nasa.gsfc.tan/gcn</AuthorIVORN>\n    <Author>\n      <shortName>Fermi (via VO-GCN)</shortName>\n      <contactName>Julie McEnery</contactName>\n      <contactPhone>+1-301-286-1632</contactPhone>\n      <contactEmail>Julie.E.McEnery@nasa.gov</contactEmail>\n    </Author>\n    <Date>2017-11-26T05:39:07</Date>\n    <Description>This VOEvent message was created with GCN VOE version: 1.25 23jul17</Description>\n  </Who>\n  <What>\n    <Param name="Packet_Type" value="111"/>\n    <Param name="Pkt_Ser_Num" value="2"/>\n    <Param name="TrigID" value="533367528" ucd="meta.id"/>\n    <Param name="Sequence_Num" value="46" ucd="meta.id.part"/>\n    <Param name="Burst_TJD" value="18083" unit="days" ucd="time"/>\n    <Param name="Burst_SOD" value="20323.71" unit="sec" ucd="time"/>\n    <Param name="Burst_Inten" value="1349" unit="cts" ucd="phot.count"/>\n    <Param name="Trig_Timescale" value="0.512" unit="sec" ucd="time.interval"/>\n    <Param name="Data_Timescale" value="0.512" unit="sec" ucd="time.interval"/>\n    <Param name="Data_Signif" value="48.60" unit="sigma" ucd="stat.snr"/>\n    <Param name="Phi" value="33.00" unit="deg" ucd="pos.az.azi"/>\n    <Param name="Theta" value="50.00" unit="deg" ucd="pos.az.zd"/>\n    <Param name="SC_Long" value="193.50" unit="deg" ucd="pos.earth.lon"/>\n    <Param name="SC_Lat" value="0.00" unit="deg" ucd="pos.earth.lat"/>\n    <Param name="Algorithm" value="3" unit="dn"/>\n    <Param name="Most_Likely_Index" value="4" unit="dn"/>\n    <Param name="Most_Likely_Prob" value="94"/>\n    <Param name="Sec_Most_Likely_Index" value="7" unit="dn"/>\n    <Param name="Sec_Most_Likely_Prob" value="4"/>\n    <Param name="Hardness_Ratio" value="1.16" ucd="arith.ratio"/>\n    <Param name="Trigger_ID" value="0x0"/>\n    <Param name="Misc_flags" value="0x1000000"/>\n    <Group name="Trigger_ID">\n      <Param name="Def_NOT_a_GRB" value="false"/>\n      <Param name="Target_in_Blk_Catalog" value="false"/>\n      <Param name="Spatial_Prox_Match" value="false"/>\n      <Param name="Temporal_Prox_Match" value="false"/>\n      <Param name="Test_Submission" value="false"/>\n    </Group>\n    <Group name="Misc_Flags">\n      <Param name="Values_Out_of_Range" value="false"/>\n      <Param name="Delayed_Transmission" value="true"/>\n      <Param name="Flt_Generated" value="true"/>\n      <Param name="Gnd_Generated" value="false"/>\n    </Group>\n    <Param name="LightCurve_URL" value="http://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/2017/bn171126235/quicklook/glg_lc_medres34_bn171126235.gif" ucd="meta.ref.url"/>\n    <Param name="Coords_Type" value="1" unit="dn"/>\n    <Param name="Coords_String" value="source_object"/>\n    <Group name="Obs_Support_Info">\n      <Description>The Sun and Moon values are valid at the time the VOEvent XML message was created.</Description>\n      <Param name="Sun_RA" value="242.17" unit="deg" ucd="pos.eq.ra"/>\n      <Param name="Sun_Dec" value="-20.97" unit="deg" ucd="pos.eq.dec"/>\n      <Param name="Sun_Distance" value="69.34" unit="deg" ucd="pos.angDistance"/>\n      <Param name="Sun_Hr_Angle" value="0.03" unit="hr"/>\n      <Param name="Moon_RA" value="331.26" unit="deg" ucd="pos.eq.ra"/>\n      <Param name="Moon_Dec" value="-12.87" unit="deg" ucd="pos.eq.dec"/>\n      <Param name="MOON_Distance" value="99.27" unit="deg" ucd="pos.angDistance"/>\n      <Param name="Moon_Illum" value="45.41" unit="%" ucd="arith.ratio"/>\n      <Param name="Galactic_Long" value="75.98" unit="deg" ucd="pos.galactic.lon"/>\n      <Param name="Galactic_Lat" value="46.93" unit="deg" ucd="pos.galactic.lat"/>\n      <Param name="Ecliptic_Long" value="217.05" unit="deg" ucd="pos.ecliptic.lon"/>\n      <Param name="Ecliptic_Lat" value="66.71" unit="deg" ucd="pos.ecliptic.lat"/>\n    </Group>\n    <Description>The Fermi-GBM location of a transient.</Description>\n  </What>\n  <WhereWhen>\n    <ObsDataLocation>\n      <ObservatoryLocation id="GEOLUN"/>\n      <ObservationLocation>\n        <AstroCoordSystem id="UTC-FK5-GEO"/>\n        <AstroCoords coord_system_id="UTC-FK5-GEO">\n          <Time unit="s">\n            <TimeInstant>\n              <ISOTime>2017-11-26T05:38:43.71</ISOTime>\n            </TimeInstant>\n          </Time>\n          <Position2D unit="deg">\n            <Name1>RA</Name1>\n            <Name2>Dec</Name2>\n            <Value2>\n              <C1>241.6167</C1>\n              <C2>48.4167</C2>\n            </Value2>\n            <Error2Radius>4.7333</Error2Radius>\n          </Position2D>\n        </AstroCoords>\n      </ObservationLocation>\n    </ObsDataLocation>\n    <Description>The RA,Dec coordinates are of the type: source_object.</Description>\n  </WhereWhen>\n  <How>\n    <Description>Fermi Satellite, GBM Instrument</Description>\n    <Reference uri="http://gcn.gsfc.nasa.gov/fermi.html" type="url"/>\n  </How>\n  <Why importance="0.5">\n    <Inference probability="0.5">\n      <Concept>process.variation.burst;em.gamma</Concept>\n    </Inference>\n  </Why>\n  <Citations>\n    <EventIVORN cite="followup">ivo://nasa.gsfc.gcn/Fermi#GBM_Alert_2017-11-26T05:38:43.71_533367528_1-272</EventIVORN>\n    <Description>This is an updated position to the original trigger.</Description>\n  </Citations>\n  <Description>\n    </Description>\n  <original_prefix>voe</original_prefix>\n</VOEvent>\n'),
                 # A SWIFT trigger that is too long to trigger on
                 ('SWIFT00.xml', None),
                 # A trigger type that we choose to ignore
                 ('SWIFT_Point_Dir_Change.xml', None),
                ]

    for xml_file, xml_packet in xml_tests:
        # Parse the file
        if xml_file is None:
            xml_loc = None
            yaml_loc = os.path.join(os.path.dirname(__file__), 'test_events/Fermi_GRB.yaml')
        else:
            #xml_loc = os.path.join(os.path.dirname(__file__), 'test_events', xml_file)
            xml_loc = os.path.join('tests/test_events', xml_file)
            yaml_loc = xml_loc[:-4] + ".yaml"

        trig = parsed_VOEvent(xml_loc, packet=xml_packet)

        # read in yaml of expected parsed_VOEvent dict
        # dump file for future tests
        # if xml_file is not None:
        #    with open(yaml_loc, 'w') as stream:
        #        dump(dict(trig.__dict__), stream)

        # Convert 'event_observed' to string as it's easier to compare than datetime
        trig.__dict__['event_observed'] = str(trig.__dict__['event_observed'])
        # Set xml to None to prevent path errors when testing in different locations
        trig.__dict__['xml'] = None
        # Read in expected class and do the same
        with open(yaml_loc, 'r') as stream:
            expected_trig = load(stream, Loader=Loader)
            expected_trig['event_observed'] = str(expected_trig['event_observed'])
            expected_trig['xml'] = None
            # Put the packet through prettystr so they match
            expected_trig['packet'] = voeventparse.prettystr(voeventparse.loads(expected_trig['packet'].encode()))

        # Compare to expected
        assert_equal(trig.__dict__, expected_trig)

def test_parse_nu_event():
    xml_tests = [
                 # An antares neutrino we would want to trigger on
                 ('Antares_1438351269.xml', None),
                 # An antares neutrino we would want to trigger on
                 ('IceCube_134191_017593623_0.xml', None),
                ]

    for xml_file, xml_packet in xml_tests:
        # Parse the file
        xml_loc = os.path.join('tests/test_events', xml_file)
        yaml_loc = xml_loc[:-4] + ".yaml"

        trig = parsed_VOEvent(xml_loc, packet=xml_packet)

        # read in yaml of expected parsed_VOEvent dict
        # dump file for future tests
        # if xml_file is not None:
        #    with open(yaml_loc, 'w') as stream:
        #        dump(dict(trig.__dict__), stream)

        # Convert 'event_observed' to string as it's easier to compare than datetime
        trig.__dict__['event_observed'] = str(trig.__dict__['event_observed'])
        # Set xml to None to prevent path errors when testing in different locations
        trig.__dict__['xml'] = None
        # Read in expected class and do the same
        with open(yaml_loc, 'r') as stream:
            expected_trig = load(stream, Loader=Loader)
            expected_trig['event_observed'] = str(expected_trig['event_observed'])
            expected_trig['xml'] = None
            # Put the packet through prettystr so they match
            expected_trig['packet'] = voeventparse.prettystr(voeventparse.loads(expected_trig['packet'].encode()))

        # Compare to expected
        assert_equal(trig.__dict__, expected_trig)

def test_parse_fs_event():
    xml_tests = [
                 # An SWIFT flare star we would want to trigger on
                 ('HD_8537_FLARE_STAR_TEST.xml', None, ),
                ]

    for xml_file, xml_packet in xml_tests:
        # Parse the file
        xml_loc = os.path.join('tests/test_events', xml_file)
        yaml_loc = xml_loc[:-4] + ".yaml"

        trig = parsed_VOEvent(xml_loc, packet=xml_packet)

        # read in yaml of expected parsed_VOEvent dict
        # dump file for future tests
        # if xml_file is not None:
        #    with open(yaml_loc, 'w') as stream:
        #        dump(dict(trig.__dict__), stream)

        # Convert 'event_observed' to string as it's easier to compare than datetime
        trig.__dict__['event_observed'] = str(trig.__dict__['event_observed'])
        # Set xml to None to prevent path errors when testing in different locations
        trig.__dict__['xml'] = None
        # Read in expected class and do the same
        with open(yaml_loc, 'r') as stream:
            expected_trig = load(stream, Loader=Loader)
            expected_trig['event_observed'] = str(expected_trig['event_observed'])
            expected_trig['xml'] = None
            # Put the packet through prettystr so they match
            expected_trig['packet'] = voeventparse.prettystr(voeventparse.loads(expected_trig['packet'].encode()))

        # Compare to expected
        assert_equal(trig.__dict__, expected_trig)

        # Always trigger so no trigger logic to test

if __name__ == "__main__":
    """
    Tests the trigger software that doesn't require the database
    """

    # introspect and run all the functions starting with 'test'
    for f in dir():
        if f.startswith('test'):
            print(f)
            globals()[f]()