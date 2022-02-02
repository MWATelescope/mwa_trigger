import voeventparse
from . import handlers

import logging

logger = logging.getLogger(__name__)


def get_telescope(ivorn):
    # Check ivorn for the telescope name

    # Swift docs: https://gcn.gsfc.nasa.gov/swift.html
    if ivorn.startswith("ivo://nasa.gsfc.gcn/SWIFT#"):
        return "SWIFT"

    # Fermi docs: https://gcn.gsfc.nasa.gov/fermi.html
    if ivorn.startswith("ivo://nasa.gsfc.gcn/Fermi#"):
        return "Fermi"

    if ivorn.startswith("ivo://nasa.gsfc.gcn/Antares_Alert#"):
        return "Antares"

    # AMON docs: https://gcn.gsfc.nasa.gov/gcn/amon.html
    if ivorn.startswith("ivo://nasa.gsfc.gcn/AMON#"):
        return "AMON"

    # MAXI docs: http://gcn.gsfc.nasa.gov/maxi.html
    if ivorn.startswith("ivo://nasa.gsfc.gcn/MAXI#"):
        return "MAXI"

    if ivorn.startswith("ivo://gwnet/LVC#"):
        return "LVC"

    # Not found a know telescope so trying some simple logic
    return ivorn.split("//")[1].split("/")[1].split("#")[0]


def get_trigger_type(telescope, ivorn):
    trig_type_str = ivorn.split("#")[1]
    for i in range(len(trig_type_str)):
        # find first integer
        if trig_type_str[i].isdigit():
            break
    return trig_type_str[: i - 1]


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
        self.most_likely_index = None
        self.detect_prob = None
        self.rate_signif = None
        self.grb_ident = None
        self.telescope = None
        # TODO: Consider calling self.parse() at the end of this constructor

    def parse(self):
        # Read in xml
        if self.packet is None:
            with open(self.xml, "rb") as f:
                v = voeventparse.load(f)
        else:
            v = voeventparse.loads(self.packet.encode())

        # Work out which telescope the trigger is from
        self.telescope = get_telescope(v.attrib["ivorn"])
        logger.debug(self.telescope)
        self.this_trig_type = get_trigger_type(self.telescope, v.attrib["ivorn"])

        # Types of trigger we're looking for
        trig_pairs = [
            "SWIFT_BAT_GRB_Pos",
            "Fermi_GBM_Flt_Pos",
            "Fermi_GBM_Gnd_Pos",
            "Fermi_GBM_Fin_Pos",
        ]
        this_pair = f"{self.telescope}_{self.this_trig_type}"
        if this_pair in trig_pairs:
            self.ignore = False
        else:
            # Unknown telescope so ignoring
            self.ignore = True
            return

        # Parse trigger info (telescope dependent)
        if self.telescope == "Fermi":
            self.trig_time = float(
                v.find(".//Param[@name='Trig_Timescale']").attrib["value"]
            )
            # self.this_trig_type = v.attrib['ivorn'].split('_')[1]  # Flt, Gnd, or Fin
            self.sequence_num = int(
                v.find(".//Param[@name='Sequence_Num']").attrib["value"]
            )
            # Fermi triggers have likely hood statistics
            self.most_likely_index = int(
                v.find(".//Param[@name='Most_Likely_Index']").attrib["value"]
            )
            self.detect_prob = int(
                v.find(".//Param[@name='Most_Likely_Prob']").attrib["value"]
            )
        elif self.telescope == "SWIFT":
            # Check if SWIFT tracking fails
            startrack_lost_lock = v.find(
                ".//Param[@name='StarTrack_Lost_Lock']"
            ).attrib["value"]
            # convert 'true' to True, and everything else to false
            startrack_lost_lock = startrack_lost_lock.lower() == "true"
            logger.debug("StarLock OK? {0}".format(not startrack_lost_lock))
            if startrack_lost_lock:
                logger.warning(
                    "The SWIFT star tracker lost it's lock so ignoring event"
                )
                self.this_trig_type += " SWIFT lost star tracker"
                self.ignore = True
                return
            self.trig_time = float(
                v.find(".//Param[@name='Integ_Time']").attrib["value"]
            )
            # self.this_trig_type = "SWIFT"
            self.sequence_num = None
            self.rate_signif = float(
                v.find(".//Param[@name='Rate_Signif']").attrib["value"]
            )
            self.grb_ident = v.find(".//Param[@name='GRB_Identified']").attrib["value"]
            self.grb_ident = self.grb_ident == "true"

        elif self.telescope == "Antares":
            self.trig_time = None
            # self.this_trig_type = 'Antares'
            self.sequence_num = None

        # print(voeventparse.prettystr(v.What))
        self.trig_id = int(v.find(".//Param[@name='TrigID']").attrib["value"])
        logger.debug("Trig details:")
        logger.debug(f"Dur:  {self.trig_time} s")
        logger.debug(f"ID:   {self.trig_id}")
        logger.debug(f"Seq#: {self.sequence_num}")
        logger.debug(f"Type: {self.this_trig_type}")

        # Get current position
        self.ra, self.dec, self.err = handlers.get_position_info(v)
        logger.debug(f"Trig position: {self.ra} {self.dec} {self.err}")
