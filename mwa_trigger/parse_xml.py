import voeventparse
from . import handlers

import logging
logger = logging.getLogger(__name__)


def get_telescope(ivorn):
    # Check for SWIFT triggers
    trig_swift = ("ivo://nasa.gsfc.gcn/SWIFT#BAT_GRB_Pos",
                 )
    for t in trig_swift:
        if ivorn.startswith(t):
            return 'SWIFT'

    # Check for Fermi triggers
    # Ignore "ivo://nasa.gsfc.gcn/Fermi#GBM_Alert" as they always have ra/dec = 0/0
    trig_fermi = ("ivo://nasa.gsfc.gcn/Fermi#GBM_Flt_Pos",
                  "ivo://nasa.gsfc.gcn/Fermi#GBM_Gnd_Pos",
                  "ivo://nasa.gsfc.gcn/Fermi#GBM_Fin_Pos",
                 )
    for t in trig_fermi:
        if ivorn.startswith(t):
            return 'Fermi'

    # Check for Antares triggers
    trig_ant = ("ivo://nasa.gsfc.gcn/Antares_Alert#",
               )
    for t in trig_ant:
        if ivorn.startswith(t):
            return 'Antares'

    # Not found so return None
    return None


class parsed_VOEvent:
    def __init__(self, xml, packet=None):
        self.xml = xml
        self.packet = packet
        # Make default Nones if unknown telescope found
        self.trig_time = None
        self.this_trig_type = None
        self.sequence_num = None
        self.trig_id = None
        self.ra = None
        self.dec = None
        self.err = None

    def parse(self):
        # Read in xml
        if self.packet is None:
            with open(self.xml, 'rb') as f:
                v = voeventparse.load(f)
        else:
            v = voeventparse.loads(self.packet.encode())

        # Work out which telescope the trigger is from
        self.telescope = get_telescope(v.attrib['ivorn'])
        logger.debug(self.telescope)
        if self.telescope is None:
            # Unknown telescope so ignoring
            self.ignore = True
            return
        else:
            self.ignore = False

        # Parse trigger info (telescope dependent)
        if self.telescope == 'Fermi':
            self.trig_time = float(v.find(".//Param[@name='Trig_Timescale']").attrib['value'])
            self.this_trig_type = v.attrib['ivorn'].split('_')[1]  # Flt, Gnd, or Fin
            self.sequence_num = int(v.find(".//Param[@name='Sequence_Num']").attrib['value'])
        elif self.telescope == 'SWIFT':
            # Check if SWIFT tracking fails
            startrack_lost_lock = v.find(".//Param[@name='StarTrack_Lost_Lock']").attrib['value']
            # convert 'true' to True, and everything else to false
            startrack_lost_lock = startrack_lost_lock.lower() == 'true'
            logger.debug("StarLock OK? {0}".format(not startrack_lost_lock))
            if startrack_lost_lock:
                logger.warning("The SWIFT star tracker lost it's lock so ignoringe event")
                self.this_trig_type = "SWIFT lost star tracker"
                self.ignore = True
                return
            self.trig_time = float(v.find(".//Param[@name='Integ_Time']").attrib['value'])
            self.this_trig_type = "SWIFT"
            self.sequence_num = None
        elif self.telescope == 'Antares':
            self.trig_time = None
            self.this_trig_type = 'Antares'
            self.sequence_num = None


        #print(voeventparse.prettystr(v.What))
        self.trig_id = int(v.find(".//Param[@name='TrigID']").attrib['value'])
        logger.debug("Trig details:")
        logger.debug(f"Dur:  {self.trig_time} s")
        logger.debug(f"ID:   {self.trig_id}")
        logger.debug(f"Seq#: {self.sequence_num}")
        logger.debug(f"Type: {self.this_trig_type}")

        # Get current position
        self.ra, self.dec, self.err = handlers.get_position_info(v)
        logger.debug(f"Trig position: {self.ra} {self.dec} {self.err}")