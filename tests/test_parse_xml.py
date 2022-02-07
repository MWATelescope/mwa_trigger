#! /usr/bin/env python
"""Tests the parse_xml.py script
"""
import os
from numpy.testing import assert_almost_equal, assert_string_equal, assert_equal

from mwa_trigger.parse_xml import parsed_VOEvent
from mwa_trigger.trigger_logic import worth_observing
import voeventparse

import logging
logger = logging.getLogger(__name__)

def test_trigger_event():
    xml_tests = [
                 # A short GRB we would want to trigger on
                 ('Fermi_GRB.xml', None, [True, False, True, "Trigger time less than 2.05 s. Fermi GRB probabilty greater than 50. "], {'trig_time': 0.512, 'this_trig_type': 'GBM_Flt_Pos', 'sequence_num': 46, 'trig_id': 533367528, 'ra': 241.6167, 'dec': 48.4167, 'err': 4.7333, 'most_likely_index': 4, 'detect_prob': 94, 'telescope': 'Fermi', 'ignore': False}),
                 # Same as the above but a xml packet to test if it works
                 (None, """<?xml version='1.0' encoding='UTF-8'?>
<voe:VOEvent xmlns:voe="http://www.ivoa.net/xml/VOEvent/v2.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ivorn="ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos_2017-11-26T05:38:43.71_533367528_46-276" role="observation" version="2.0" xsi:schemaLocation="http://www.ivoa.net/xml/VOEvent/v2.0  http://www.ivoa.net/xml/VOEvent/VOEvent-v2.0.xsd"><Who><AuthorIVORN>ivo://nasa.gsfc.tan/gcn</AuthorIVORN><Author><shortName>Fermi (via VO-GCN)</shortName><contactName>Julie McEnery</contactName><contactPhone>+1-301-286-1632</contactPhone><contactEmail>Julie.E.McEnery@nasa.gov</contactEmail></Author><Date>2017-11-26T05:39:07</Date><Description>This VOEvent message was created with GCN VOE version: 1.25 23jul17</Description></Who><What><Param name="Packet_Type" value="111"/><Param name="Pkt_Ser_Num" value="2"/><Param name="TrigID" value="533367528" ucd="meta.id"/><Param name="Sequence_Num" value="46" ucd="meta.id.part"/><Param name="Burst_TJD" value="18083" unit="days" ucd="time"/><Param name="Burst_SOD" value="20323.71" unit="sec" ucd="time"/><Param name="Burst_Inten" value="1349" unit="cts" ucd="phot.count"/><Param name="Trig_Timescale" value="0.512" unit="sec" ucd="time.interval"/><Param name="Data_Timescale" value="0.512" unit="sec" ucd="time.interval"/><Param name="Data_Signif" value="48.60" unit="sigma" ucd="stat.snr"/><Param name="Phi" value="33.00" unit="deg" ucd="pos.az.azi"/><Param name="Theta" value="50.00" unit="deg" ucd="pos.az.zd"/><Param name="SC_Long" value="193.50" unit="deg" ucd="pos.earth.lon"/><Param name="SC_Lat" value="0.00" unit="deg" ucd="pos.earth.lat"/><Param name="Algorithm" value="3" unit="dn"/><Param name="Most_Likely_Index" value="4" unit="dn"/><Param name="Most_Likely_Prob" value="94"/><Param name="Sec_Most_Likely_Index" value="7" unit="dn"/><Param name="Sec_Most_Likely_Prob" value="4"/><Param name="Hardness_Ratio" value="1.16" ucd="arith.ratio"/><Param name="Trigger_ID" value="0x0"/><Param name="Misc_flags" value="0x1000000"/><Group name="Trigger_ID"><Param name="Def_NOT_a_GRB" value="false"/><Param name="Target_in_Blk_Catalog" value="false"/><Param name="Spatial_Prox_Match" value="false"/><Param name="Temporal_Prox_Match" value="false"/><Param name="Test_Submission" value="false"/></Group><Group name="Misc_Flags"><Param name="Values_Out_of_Range" value="false"/><Param name="Delayed_Transmission" value="true"/><Param name="Flt_Generated" value="true"/><Param name="Gnd_Generated" value="false"/></Group><Param name="LightCurve_URL" value="http://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/2017/bn171126235/quicklook/glg_lc_medres34_bn171126235.gif" ucd="meta.ref.url"/><Param name="Coords_Type" value="1" unit="dn"/><Param name="Coords_String" value="source_object"/><Group name="Obs_Support_Info"><Description>The Sun and Moon values are valid at the time the VOEvent XML message was created.</Description><Param name="Sun_RA" value="242.17" unit="deg" ucd="pos.eq.ra"/><Param name="Sun_Dec" value="-20.97" unit="deg" ucd="pos.eq.dec"/><Param name="Sun_Distance" value="69.34" unit="deg" ucd="pos.angDistance"/><Param name="Sun_Hr_Angle" value="0.03" unit="hr"/><Param name="Moon_RA" value="331.26" unit="deg" ucd="pos.eq.ra"/><Param name="Moon_Dec" value="-12.87" unit="deg" ucd="pos.eq.dec"/><Param name="MOON_Distance" value="99.27" unit="deg" ucd="pos.angDistance"/><Param name="Moon_Illum" value="45.41" unit="%" ucd="arith.ratio"/><Param name="Galactic_Long" value="75.98" unit="deg" ucd="pos.galactic.lon"/><Param name="Galactic_Lat" value="46.93" unit="deg" ucd="pos.galactic.lat"/><Param name="Ecliptic_Long" value="217.05" unit="deg" ucd="pos.ecliptic.lon"/><Param name="Ecliptic_Lat" value="66.71" unit="deg" ucd="pos.ecliptic.lat"/></Group><Description>The Fermi-GBM location of a transient.</Description></What><WhereWhen><ObsDataLocation><ObservatoryLocation id="GEOLUN"/><ObservationLocation><AstroCoordSystem id="UTC-FK5-GEO"/><AstroCoords coord_system_id="UTC-FK5-GEO"><Time unit="s"><TimeInstant><ISOTime>2017-11-26T05:38:43.71</ISOTime></TimeInstant></Time><Position2D unit="deg"><Name1>RA</Name1><Name2>Dec</Name2><Value2><C1>241.6167</C1><C2>48.4167</C2></Value2><Error2Radius>4.7333</Error2Radius></Position2D></AstroCoords></ObservationLocation></ObsDataLocation><Description>The RA,Dec coordinates are of the type: source_object.</Description></WhereWhen><How><Description>Fermi Satellite, GBM Instrument</Description><Reference uri="http://gcn.gsfc.nasa.gov/fermi.html" type="url"/></How><Why importance="0.5"><Inference probability="0.5"><Concept>process.variation.burst;em.gamma</Concept></Inference></Why><Citations><EventIVORN cite="followup">ivo://nasa.gsfc.gcn/Fermi#GBM_Alert_2017-11-26T05:38:43.71_533367528_1-272</EventIVORN><Description>This is an updated position to the original trigger.</Description></Citations><Description>
  </Description></voe:VOEvent>""", [True, False, True, "Trigger time less than 2.05 s. Fermi GRB probabilty greater than 50. "], {'trig_time': 0.512, 'this_trig_type': 'GBM_Flt_Pos', 'sequence_num': 46, 'trig_id': 533367528, 'ra': 241.6167, 'dec': 48.4167, 'err': 4.7333, 'most_likely_index': 4, 'detect_prob': 94, 'telescope': 'Fermi', 'ignore': False}),
                 # A SWIFT trigger that is too long to trigger on
                 ('SWIFT00.xml', None, [False, True, False, "Trigger time greater than 2.05 s. "], {'trig_time': 4.096, 'this_trig_type': 'BAT_GRB_Pos', 'sequence_num': None, 'trig_id': 772006, 'ra': 45.0, 'dec': -80.0, 'err': 0.05, 'most_likely_index': None, 'detect_prob': None, 'telescope': 'SWIFT', 'ignore': False}),
                 # A trigger type that we choose to ignore
                 ('Antares_1438351269.xml', None, [False, False, False, ""], {'trig_time': None, 'this_trig_type': '143835126', 'sequence_num': None, 'trig_id': None, 'ra': None, 'dec': None, 'err': None, 'most_likely_index': None, 'detect_prob': None, 'telescope': 'Antares', 'ignore': True}),
                ]

    for xml_file, xml_packet, exp_worth_obs, exp_parse in xml_tests:
        # Parse the file
        if xml_file is None:
            print(f'\n{xml_packet[:10]}')
            xml_loc = None
        else:
            print(f'\n{xml_file}')
            xml_loc = os.path.join(os.path.dirname(__file__), 'test_events', xml_file)
        trig = parsed_VOEvent(xml_loc, packet=xml_packet)
        print("Trig details:")
        print(trig.__dict__)
        # print(f"Dur:  {trig.trig_time} s")
        # print(f"ID:   {trig.trig_id}")
        # print(f"Type: {trig.this_trig_type}")
        # print(f"Trig position: {trig.ra} {trig.dec} {trig.err}")

        # Compare to expected
        assert_equal(trig.trig_time, exp_parse['trig_time'])
        assert_equal(trig.this_trig_type, exp_parse['this_trig_type'])
        assert_equal(trig.sequence_num, exp_parse['sequence_num'])
        assert_equal(trig.trig_id, exp_parse['trig_id'])
        assert_equal(trig.ra, exp_parse['ra'])
        assert_equal(trig.dec, exp_parse['dec'])
        assert_equal(trig.err, exp_parse['err'])
        assert_equal(trig.most_likely_index, exp_parse['most_likely_index'])
        assert_equal(trig.detect_prob, exp_parse['detect_prob'])
        assert_equal(trig.telescope, exp_parse['telescope'])
        assert_equal(trig.ignore, exp_parse['ignore'])


        # Send it through trigger logic
        trigger_bool, debug_bool, short_bool, trigger_message = worth_observing(trig)
        print(f"{trigger_bool}, {debug_bool}, {short_bool}")
        print(f"{trigger_message}")

        # Compare to expected
        assert_equal(trigger_bool, exp_worth_obs[0])
        assert_equal(debug_bool, exp_worth_obs[1])
        assert_equal(short_bool, exp_worth_obs[2])
        assert_equal(trigger_message, exp_worth_obs[3])

if __name__ == "__main__":
    """
    Tests the trigger software that doesn't require the database
    """

    # introspect and run all the functions starting with 'test'
    for f in dir():
        if f.startswith('test'):
            print(f)
            globals()[f]()