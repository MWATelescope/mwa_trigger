#! /usr/bin/env python3
"""Tests the parse_xml.py script
"""
import os
from numpy.testing import assert_almost_equal

from mwa_trigger.parse_xml import Trigger_Event

import logging
logger = logging.getLogger(__name__)

def test_trigger_event():
    xml_tests = [
                 ('Fermi_GRB.xml', None),
                 ('SWIFT00.xml', None),
                 (None, """<?xml version='1.0' encoding='UTF-8'?>
<voe:VOEvent xmlns:voe="http://www.ivoa.net/xml/VOEvent/v2.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ivorn="ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos_2017-11-26T05:38:43.71_533367528_46-276" role="observation" version="2.0" xsi:schemaLocation="http://www.ivoa.net/xml/VOEvent/v2.0  http://www.ivoa.net/xml/VOEvent/VOEvent-v2.0.xsd"><Who><AuthorIVORN>ivo://nasa.gsfc.tan/gcn</AuthorIVORN><Author><shortName>Fermi (via VO-GCN)</shortName><contactName>Julie McEnery</contactName><contactPhone>+1-301-286-1632</contactPhone><contactEmail>Julie.E.McEnery@nasa.gov</contactEmail></Author><Date>2017-11-26T05:39:07</Date><Description>This VOEvent message was created with GCN VOE version: 1.25 23jul17</Description></Who><What><Param name="Packet_Type" value="111"/><Param name="Pkt_Ser_Num" value="2"/><Param name="TrigID" value="533367528" ucd="meta.id"/><Param name="Sequence_Num" value="46" ucd="meta.id.part"/><Param name="Burst_TJD" value="18083" unit="days" ucd="time"/><Param name="Burst_SOD" value="20323.71" unit="sec" ucd="time"/><Param name="Burst_Inten" value="1349" unit="cts" ucd="phot.count"/><Param name="Trig_Timescale" value="0.512" unit="sec" ucd="time.interval"/><Param name="Data_Timescale" value="0.512" unit="sec" ucd="time.interval"/><Param name="Data_Signif" value="48.60" unit="sigma" ucd="stat.snr"/><Param name="Phi" value="33.00" unit="deg" ucd="pos.az.azi"/><Param name="Theta" value="50.00" unit="deg" ucd="pos.az.zd"/><Param name="SC_Long" value="193.50" unit="deg" ucd="pos.earth.lon"/><Param name="SC_Lat" value="0.00" unit="deg" ucd="pos.earth.lat"/><Param name="Algorithm" value="3" unit="dn"/><Param name="Most_Likely_Index" value="4" unit="dn"/><Param name="Most_Likely_Prob" value="94"/><Param name="Sec_Most_Likely_Index" value="7" unit="dn"/><Param name="Sec_Most_Likely_Prob" value="4"/><Param name="Hardness_Ratio" value="1.16" ucd="arith.ratio"/><Param name="Trigger_ID" value="0x0"/><Param name="Misc_flags" value="0x1000000"/><Group name="Trigger_ID"><Param name="Def_NOT_a_GRB" value="false"/><Param name="Target_in_Blk_Catalog" value="false"/><Param name="Spatial_Prox_Match" value="false"/><Param name="Temporal_Prox_Match" value="false"/><Param name="Test_Submission" value="false"/></Group><Group name="Misc_Flags"><Param name="Values_Out_of_Range" value="false"/><Param name="Delayed_Transmission" value="true"/><Param name="Flt_Generated" value="true"/><Param name="Gnd_Generated" value="false"/></Group><Param name="LightCurve_URL" value="http://heasarc.gsfc.nasa.gov/FTP/fermi/data/gbm/triggers/2017/bn171126235/quicklook/glg_lc_medres34_bn171126235.gif" ucd="meta.ref.url"/><Param name="Coords_Type" value="1" unit="dn"/><Param name="Coords_String" value="source_object"/><Group name="Obs_Support_Info"><Description>The Sun and Moon values are valid at the time the VOEvent XML message was created.</Description><Param name="Sun_RA" value="242.17" unit="deg" ucd="pos.eq.ra"/><Param name="Sun_Dec" value="-20.97" unit="deg" ucd="pos.eq.dec"/><Param name="Sun_Distance" value="69.34" unit="deg" ucd="pos.angDistance"/><Param name="Sun_Hr_Angle" value="0.03" unit="hr"/><Param name="Moon_RA" value="331.26" unit="deg" ucd="pos.eq.ra"/><Param name="Moon_Dec" value="-12.87" unit="deg" ucd="pos.eq.dec"/><Param name="MOON_Distance" value="99.27" unit="deg" ucd="pos.angDistance"/><Param name="Moon_Illum" value="45.41" unit="%" ucd="arith.ratio"/><Param name="Galactic_Long" value="75.98" unit="deg" ucd="pos.galactic.lon"/><Param name="Galactic_Lat" value="46.93" unit="deg" ucd="pos.galactic.lat"/><Param name="Ecliptic_Long" value="217.05" unit="deg" ucd="pos.ecliptic.lon"/><Param name="Ecliptic_Lat" value="66.71" unit="deg" ucd="pos.ecliptic.lat"/></Group><Description>The Fermi-GBM location of a transient.</Description></What><WhereWhen><ObsDataLocation><ObservatoryLocation id="GEOLUN"/><ObservationLocation><AstroCoordSystem id="UTC-FK5-GEO"/><AstroCoords coord_system_id="UTC-FK5-GEO"><Time unit="s"><TimeInstant><ISOTime>2017-11-26T05:38:43.71</ISOTime></TimeInstant></Time><Position2D unit="deg"><Name1>RA</Name1><Name2>Dec</Name2><Value2><C1>241.6167</C1><C2>48.4167</C2></Value2><Error2Radius>4.7333</Error2Radius></Position2D></AstroCoords></ObservationLocation></ObsDataLocation><Description>The RA,Dec coordinates are of the type: source_object.</Description></WhereWhen><How><Description>Fermi Satellite, GBM Instrument</Description><Reference uri="http://gcn.gsfc.nasa.gov/fermi.html" type="url"/></How><Why importance="0.5"><Inference probability="0.5"><Concept>process.variation.burst;em.gamma</Concept></Inference></Why><Citations><EventIVORN cite="followup">ivo://nasa.gsfc.gcn/Fermi#GBM_Alert_2017-11-26T05:38:43.71_533367528_1-272</EventIVORN><Description>This is an updated position to the original trigger.</Description></Citations><Description>
  </Description></voe:VOEvent>"""),
                ]

    for xml_file, xml_packet in xml_tests:
        if xml_file is None:
            print(f'\n{xml_packet[:10]}')
            xml_loc = None
        else:
            print(f'\n{xml_file}')
            xml_loc = os.path.join(os.path.dirname(__file__), 'test_events', xml_file)
        trig = Trigger_Event(xml_loc, packet=xml_packet)
        trig.parse()
        print("Trig details:")
        print(f"Dur:  {trig.trig_time} s")
        print(f"ID:   {trig.trig_id}")
        print(f"Type: {trig.this_trig_type}")
        print(f"Trig position: {trig.ra} {trig.dec} {trig.err}")



if __name__ == "__main__":
    """
    Tests the relevant functions in sn_flux_est.py
    Uses psrcat version 1.59. Values may change for different versions
    """

    # introspect and run all the functions starting with 'test'
    for f in dir():
        if f.startswith('test'):
            print(f)
            globals()[f]()