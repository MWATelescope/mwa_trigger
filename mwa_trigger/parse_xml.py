import voeventparse
from . import handlers
from . import data_load

import logging

logger = logging.getLogger(__name__)

# A dictionary of the telescopes each source type can be detected by
SOURCE_TELESCOPES = {
    "GRB":[
        "SWIFT",
        "Fermi",
    ],
    "FS":[
        "SWIFT",
    ],
    "GW":[
        "LVC",
    ],
    "NU":[
        "Antares",
        "AMON",
    ],
}

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

    if ivorn.startswith("ivo://HESS/GRB#"):
        return "HESS"

    # Not found a know telescope so trying some simple logic
    return str(ivorn.split("//")[1].split("/")[1].split("#")[0])


def get_event_type(ivorn):
    trig_type_str = ivorn.split("#")[1]
    for i in range(len(trig_type_str)):
        # find first integer
        if trig_type_str[i].isdigit():
            break
    return str(trig_type_str[: i - 1])


def get_source_types(telescope, event_type, source_name, v):
    """
    """
    #Check for Gravitational Waves
    if telescope in SOURCE_TELESCOPES["GW"]:
        return "GW"

    # Check for neutrinos
    if telescope == "Antares" or ( telescope == "AMON" and event_type == "ICECUBE_GOLD" ):
        return "NU"

    # Check for Flare Stars
    data_file = data_load.FLARE_STAR_NAMES
    flare_stars = [a.strip().lower() for a in open(data_file, 'r').readlines() if not a.startswith("#")]
    # Check if this is a sub_sub_threshold event and ignore if it is
    if telescope == "SWIFT" and 'sub-sub-threshold' in str(v.What.Description):
        flare_star = False
    else:
        flare_star = False
        for f in flare_stars:
            # Check if the name is within the "name" string since MAXI does stupid things sometimes
            if f in str(source_name).lower():
                flare_star =True
    if flare_star:
        return "FS"

    # Check for GRB
    grb = False
    if telescope == "SWIFT":
        # check to see if a GRB was identified
        try:
            grb = v.find(".//Param[@name='GRB_Identified']").attrib['value']
        except AttributeError:
            logger.error("Param[@name='GRB_Identified'] not found in XML packet - discarding.")
            grb = False
        grb = bool(grb) # Make sure it's not a string
    elif telescope == "Fermi":
        #grb = False   # Ignore all Fermi triggers
        grb = True
        # I could put the most likely index here but it's easier to log in the trigger logic
    if grb:
        return "GRB"

    # No type found so return None
    return None


class parsed_VOEvent:
    def __init__(self, xml, packet=None, trig_pairs=None):
        self.xml = xml
        self.packet = packet
        self.trig_pairs = trig_pairs
        # Make default Nones if unknown telescope found
        self.trig_duration = None
        self.event_type = None
        self.sequence_num = None
        self.trig_id = None
        self.ra = None
        self.dec = None
        self.err = None
        self.fermi_most_likely_index = None
        self.fermi_detection_prob = None
        self.swift_rate_signif = None
        self.grb_ident = None
        self.telescope = None
        self.source_name = None
        self.source_type = None
        self.event_observed = None
        if self.trig_pairs is None:
            # use defaults
            self.trig_pairs = [
                "SWIFT_BAT_GRB_Pos",
                "SWIFT_XRT_Pos",
                "SWIFT_UVOT_Pos",
                "Fermi_GBM_Flt_Pos",
                "Fermi_GBM_Gnd_Pos",
                "Fermi_GBM_Fin_Pos",
                "HESS_GRB_To",
            ]
        self.parse()

    def __iter__(self):
        return self.__dict__.iteritems()

    def parse(self):
        # Read in xml
        if self.packet is None:
            with open(self.xml, "rb") as f:
                v = voeventparse.load(f)
            self.packet = voeventparse.prettystr(v)
        else:
            v = voeventparse.loads(self.packet.encode())

        # Work out which telescope the trigger is from
        self.telescope = get_telescope(v.attrib["ivorn"])
        logger.debug(self.telescope)
        self.event_type = get_event_type(v.attrib["ivorn"])

        # See if the trigger has a source name
        if self.telescope == "SWIFT" and self.event_type == "BAT_GRB_Pos":
            self.source_name = str(v.Why.Inference.Name)
        elif self.telescope == "MAXI":
            # MAXI uses a Source_Name parameter
            src = v.find(".//Param[@name='Source_Name']")
            if src is not None:
                # MAXI sometimes puts spaces at the start of the string!
                self.source_name = str(src.attrib['value']).strip()

        # Work out what type of source it is
        self.source_type = get_source_types(self.telescope, self.event_type, self.source_name, v)
        logger.debug(f"source types: {self.source_type}")

        # Attempt to get a Trigger ID (for Fermi and SWIFT)
        if v.find(".//Param[@name='TrigID']") is not None:
            self.trig_id = int(v.find(".//Param[@name='TrigID']").attrib["value"])

        # Check if this is the type of trigger we're looking for
        this_pair = f"{self.telescope}_{self.event_type}"
        if this_pair in self.trig_pairs:
            self.ignore = False
        else:
            # Unknown telescope so ignoring
            self.ignore = True
            return

        # Parse trigger info (telescope dependent)
        if self.telescope == "Fermi":
            self.trig_duration = float(
                v.find(".//Param[@name='Trig_Timescale']").attrib["value"]
            )
            self.sequence_num = int(
                v.find(".//Param[@name='Sequence_Num']").attrib["value"]
            )
            # Fermi triggers have likely hood statistics
            self.fermi_most_likely_index = int(
                v.find(".//Param[@name='Most_Likely_Index']").attrib["value"]
            )
            self.fermi_detection_prob = int(
                v.find(".//Param[@name='Most_Likely_Prob']").attrib["value"]
            )
        elif self.telescope == "SWIFT":
            if "BAT" in self.event_type:
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
                    self.event_type += " SWIFT lost star tracker"
                    self.ignore = True
                    return

                # Get time and significance
                self.trig_duration = float(
                    v.find(".//Param[@name='Integ_Time']").attrib["value"]
                )
                self.sequence_num = None
                self.swift_rate_signif = float(
                    v.find(".//Param[@name='Rate_Signif']").attrib["value"]
                )
                self.grb_ident = v.find(".//Param[@name='GRB_Identified']").attrib["value"]

        elif self.telescope == "Antares":
            self.trig_duration = None
            self.sequence_num = None

        self.event_observed = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Time.TimeInstant.ISOTime
        logger.debug("Trig details:")
        logger.debug(f"Dur:  {self.trig_duration} s")
        logger.debug(f"ID:   {self.trig_id}")
        logger.debug(f"Seq#: {self.sequence_num}")
        logger.debug(f"Type: {self.event_type}")

        # Get current position
        self.ra, self.dec, self.err = handlers.get_position_info(v)
        logger.debug(f"Trig position: {self.ra} {self.dec} {self.err}")
