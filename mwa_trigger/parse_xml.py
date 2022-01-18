import voeventparse
from . import handlers

import logging
logger = logging.getLogger(__name__)


def get_telescope(ivorn):
    trig_swift = ("ivo://nasa.gsfc.gcn/SWIFT#BAT_GRB_Pos",  # Swift positions
                    )

    # Ignore "ivo://nasa.gsfc.gcn/Fermi#GBM_Alert" as they always have ra/dec = 0/0
    trig_fermi = ("ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos",  # Fermi positions
                    "ivo://nasa.gsfc.gcn/Fermi#GBM_Gnd_Pos",
                    "ivo://nasa.gsfc.gcn/Fermi#GBM_Fin_Pos",
                    )

    for t in trig_swift:
        if ivorn.startswith(t):
            return 'SWIFT'
    for t in trig_fermi:
        if ivorn.startswith(t):
            return 'Fermi'
    # Not found so return None
    return None


class Trigger_Event:
    def __init__(self, xml):
        self.xml = xml

    def parse(self):
        # Read in xml
        with open(self.xml, 'rb') as f:
            v = voeventparse.load(f)

        # Work out which telescope the trigger is from
        telescope = get_telescope(v.attrib['ivorn'])
        logger.debug(telescope)

        # Parse trigger info (telescope dependent)
        if telescope == 'Fermi':
            self.trig_time = float(v.find(".//Param[@name='Trig_Timescale']").attrib['value'])
            self.trig_id = "Fermi_" + v.attrib['ivorn'].split('_')[-2]
            self.this_trig_type = v.attrib['ivorn'].split('_')[1]  # Flt, Gnd, or Fin
        elif telescope == 'SWIFT':
            self.trig_time = float(v.find(".//Param[@name='Integ_Time']").attrib['value'])
            self.trig_id = "SWIFT_" + v.attrib['ivorn'].split('_')[-1].split('-')[0]
            self.this_trig_type = "SWIFT"
        logger.debug("Trig details:")
        logger.debug(f"Dur:  {self.trig_time} s")
        logger.debug(f"ID:   {self.trig_id}")
        logger.debug(f"Type: {self.this_trig_type}")

        # Get current position
        self.ra, self.dec, self.err = handlers.get_position_info(v)
        logger.debug(f"Trig position: {self.ra} {self.dec} {self.err}")