import voeventparse
from . import data_load
import pandas as pd
from astropy.coordinates import Angle
import astropy.units as u
from astropy.table import Table
import astropy_healpix as ah
import numpy as np
import urllib.request
import os
import uuid

import logging

logger = logging.getLogger(__name__)

# A dictionary of the telescopes each source type can be detected by
SOURCE_TELESCOPES = {
    "GRB":[
        "SWIFT",
        "Fermi",
        "HESS",
    ],
    "FS":[
        "SWIFT",
        "MAXI",
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
    """Check ivorn for the telescope name

    Parameters
    ----------
    ivorn : `str`
        Descriptor string of the event.

    Returns
    -------
    telescope : `str`
        The telescope name.
    """

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
    """Get the type of event from the ivorn

    Parameters
    ----------
    ivorn : `str`
        Descriptor string of the event.

    Returns
    -------
    event_type : `str`
        The type of the event
    """
    trig_type_str = ivorn.split("#")[1]
    if "LVC" in ivorn:
        # Do LVS specific parsing
        return trig_type_str.split("-")[-1]
    elif "Antares" in ivorn:
        # Do Antares specific parsing
        return ivorn.split("Antares_")[-1].split("#")[0]
    elif "HESS" in ivorn:
        # Currently one event type for Hess
        return "GRB_To"
    else:
        # Do default parsing
        for i in range(len(trig_type_str)):
            # find first integer
            if trig_type_str[i].isdigit():
                break
        if trig_type_str[i-1] == "_":
            # skip the _
            return str(trig_type_str[: i - 1])
        else:
            return str(trig_type_str[:i])


def load_swift_source_database():
    """Load the SWIFT source database file within the repo into a pandas dataframe.
    """
    df = pd.read_table(data_load.SWIFT_FLARE_STAR_NAMES, sep='|', header=0, comment="+", skiprows=41, usecols=list(range(1,15)), skipinitialspace=True)
    df = df[df['ROW'] != 'ROW']
    return df


def get_source_types(telescope, event_type, source_name, v):
    """Predict what the source type of the event.

    Parameters
    ----------
    telescope : `str`
        The name of the telescope that observed this event.
    event_type : `str`
        The type of the event that is extracted from the ivorn (e.g. BAT_GRB_Pos).
    source_name : `str`
        The name of the source from the telescope.
    v : `object`
        The xml loaded into the voeventparse class.

    Returns
    -------
    source_type : `str`
        Source typre of the event (GRB, FS, NU or GW).
    """
    #Check for Gravitational Waves
    if telescope in SOURCE_TELESCOPES["GW"]:
        return "GW"

    # Check for neutrinos
    if telescope == "Antares" or ( telescope == "AMON" and "ICECUBE" in event_type ):
        return "NU"

    # Check for Flare Stars
    maxi_data_file = data_load.MAXI_FLARE_STAR_NAMES
    maxi_flare_stars = [a.strip().lower() for a in open(maxi_data_file, 'r').readlines() if not a.startswith("#")]
    swift_df = load_swift_source_database()
    swift_flare_stars = list(swift_df[swift_df['SRC_TYPE'] == '11']["NAME"])
    flare_stars = maxi_flare_stars + swift_flare_stars
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
        grb = v.find(".//Param[@name='GRB_Identified']")
        if grb is None:
            grb = False
        else:
            grb = grb.attrib['value']
            # Convert string to bool
            if 'true' in grb.lower().strip():
                grb = True
            elif 'false' in grb.lower().strip():
                grb = False
            else:
                logger.error(f"Unrecognised value of Param[@name='GRB_Identified']: {grb}")
                grb = False
    elif telescope == "Fermi":
        #grb = False   # Ignore all Fermi triggers
        grb = True
        # I could put the most likely index here but it's easier to log in the trigger logic
    elif telescope == "HESS":
        # Assume all HESS triggers are GRBs
        grb = True
    if not grb:
        # Perform second check using the declared source name
        if source_name is not None:
            if "GRB" in source_name:
                grb = True
    if grb:
        return "GRB"

    # No type found so return None
    return None


def get_position_info(v):
    """Get the ra,dec,err from a given voevent.

    Parameters
    ----------
    v : `object`
        The xml loaded into the voeventparse class.

    Returns
    -------
    ra, dec, err : `tuple`
        A tuple of (ra, dec, err) where ra,dec are the coordinates in J2000 and err is the error radius in deg.
    """
    try:
        ra  = float(v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Position2D.Value2.C1)
        dec = float(v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Position2D.Value2.C2)
        err = float(v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Position2D.Error2Radius)
    except:
        # Try old method if new one doesn't work
        try:
            ra = float(v.find(".//C1"))
            dec = float(v.find(".//C2"))
            err = float(v.find('.//Error2Radius'))
        except:
            ra = None
            dec = None
            err = None
    return ra, dec, err


class parsed_VOEvent:
    """Parses a VOEvent XML file or packet and extracts the useful information from most telescope formats.

    Parameters
    ----------
    xml : `str`
        The location of an XML file you wish to parse
    packet : `str`, optional
        The contents of an XML file you wish to parse (instead of the file).
    trig_pairs : `list`, optional
        A list of strings in the format "{telescope}_{event_type}" that you consider interesting.

    Attributes
    ----------
    xml : `str`
        The location of an XML file you wish to parse.
    packet : `str`
        The contents of an XML file you wish to parse (instead of the file).
    trig_pairs : `list`
        A list of strings in the format "{telescope}_{event_type}" that you consider interesting.
    event_duration : `float`
        The duration of the event in seconds.
    event_observed : DateTime
        The date and time that event was observed.
    telescope : `str`
        The name of the telescope that observed this event.
    event_type : `str`
        The type of the event that is extracted from the ivorn (e.g. BAT_GRB_Pos).
    ra : `float`
        The right ascension in degrees.
    ra_hms : `str`
        The right ascension in the format "HH:MM:SS.SS".
    dec : `float`
        The declination in degrees.
    dec_dms : `str`
        The declination in the format "DD:MM:SS.SS".
    err : `float`
        The uncertainty in the event position in degrees.
    ignore : `bool`
        If the event should be ignored (e.g. test or unknown events).
    source_type : `str`
        The predicted source type (GRB, FS, NU or GW).
    trig_id : `str`
        The ID the telescope has given the event.
    sequence_num : `int`
        What number/sequence this event is for the trig_id group.
    source_name : `str`
        The name of the source from the telescope.
    grb_ident : `bool`
        If the telescope has identified it as a GRB.
    role : `str`
        The role of the observation (eg. test or observation).
    ntares_ranking : 1
        The rating (1 is best) for Antares sources.
    fermi_detection_prob : `float`
        The probability the source is real the Fermi provides (it appears to be a percentage).
    fermi_most_likely_index : `int`
        An index that Fermi uses to describe what sort of source the Event is. GRBs are four, so this is what we check for.
    swift_rate_signif :  `float`
        The "RATE_SIGNIF" (appears to be a signal-to-noise ratio) to observe for SWIFT sources (in sigma).
    false_alarm_rate_hz : `str`
        False alarm rate, a statistic that is used to describe the significance of a gravitational-wave event.
    lvc_classification_BNS : `float`
        Likelyhood of the event being a BNS (0-1 range)
    lvc_classification_NSBH : `float`
        Likelyhood of the event being a NSBH (0-1 range)
    lvc_classification_BBH : `float`
        Likelyhood of the event being a BBH (0-1 range)
    lvc_classification_Terrestrial : `float`
        Likelyhood of the event being terrestrial (noise) (0-1 range)
    retraction_message : `string`
        Message for why observation has been retracted
    skymap_fits : `string`
        The contents of a sky map (shows GW probability) in a multi-order FITS format as a Base64-encoded string.
    """
    def __init__(self, xml, packet=None, trig_pairs=None):
        self.xml = xml
        self.packet = packet
        self.trig_pairs = trig_pairs
        # Make default Nones if unknown telescope found
        self.event_duration = None
        self.event_type = None
        self.sequence_num = None
        self.trig_id = None
        self.self_generated_trig_id = False
        self.ra = None
        self.dec = None
        self.err = None
        self.fermi_most_likely_index = None
        self.fermi_detection_prob = None
        self.swift_rate_signif = None
        self.antares_ranking = None
        self.grb_ident = None
        self.telescope = None
        self.source_name = None
        self.source_type = None
        self.event_observed = None
        self.lvc_classification_BNS = None
        self.lvc_classification_NSBH = None
        self.lvc_classification_BBH = None
        self.lvc_classification_Terrestrial = None
        self.retraction_message = None
        self.skymap_fits = None
        self.prob_density_tile = None
        self.right_ascension_degrees = None
        self.decension_degrees = None

        if self.trig_pairs is None:
            # use defaults
            self.trig_pairs = [
                "SWIFT_BAT_GRB_Pos",
                "SWIFT_XRT_Pos",
                "SWIFT_UVOT_Pos",
                # Ignoring the below as they don't give additional information
                # "SWIFT_BAT_QuickLook_Pos",
                # "SWIFT_SC_Slew",
                # "SWIFT_FOM_Obs",
                "Fermi_GBM_Flt_Pos",
                "Fermi_GBM_Gnd_Pos",
                "Fermi_GBM_Fin_Pos",
                "HESS_GRB_To",
                "LVC_EarlyWarning",
                "LVC_Preliminary",
                "LVC_Initial",
                "LVC_Update",
                "LVC_Retraction",
                "AMON_ICECUBE_BRONZE_Event",
                "AMON_ICECUBE_GOLD_Event",
                "Antares_Alert",
            ]
        # Make default Nones if unknown telescope found
        self.parse()

    def __iter__(self):
        return self.__dict__.iteritems()

    def parse(self):
        """Parses the XML into the class attributes. This is run when the class is initiated.
        """
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
        if self.telescope == "SWIFT":
            try:
                self.source_name = str(v.Why.Inference.Name)
            except AttributeError:
                self.source_name = None
        elif self.telescope == "MAXI":
            # MAXI uses a Source_Name parameter
            src = v.find(".//Param[@name='Source_Name']")
            if src is not None:
                # MAXI sometimes puts spaces at the start of the string!
                self.source_name = str(src.attrib['value']).strip()

        # Work out what type of source it is
        self.source_type = get_source_types(self.telescope, self.event_type, self.source_name, v)
        logger.debug(f"source types: {self.source_type}")

        # Attempt to get a Trigger ID (for Fermi, SWIFT, Antares and LVC)
        if v.find(".//Param[@name='TrigID']") is not None:
            self.trig_id = str(v.find(".//Param[@name='TrigID']").attrib["value"])
        elif v.find(".//Param[@name='AMON_ID']") is not None:
            # ICECUBE's ID
            self.trig_id = str(v.find(".//Param[@name='AMON_ID']").attrib["value"])
        elif v.find(".//Param[@name='GraceID']") is not None:
            # The gracedb ID for GW
            self.trig_id = str(v.find(".//Param[@name='GraceID']").attrib["value"])
        else:
            # Hess has no Trigger ID so make a random one
            self.trig_id = str(uuid.uuid4().int)[:12]
            self.self_generated_trig_id = True

        # Get current position
        self.ra, self.dec, self.err = get_position_info(v)
        if self.ra is None or self.dec is None:
            self.ra_hms = None
            self.dec_dms = None
        else:
            self.ra_hms  = str(Angle(self.ra,  unit=u.deg).to_string(unit=u.hour, sep=':'))
            self.dec_dms = str(Angle(self.dec, unit=u.deg).to_string(unit=u.deg,  sep=':'))
        logger.debug(f"Trig position: {self.ra} {self.dec} {self.err}")

        self.event_observed = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Time.TimeInstant.ISOTime
        
        # Check the voevent role (normally observation or test)
        self.role = v.attrib["role"]
        if self.role == "test":
            # Just a test observation so ignore it
            self.ignore = True
            print('Just a test observation so ignore it')
            return

        # Antares has a flag for real alerts that is worth checking
        elif v.find(".//Param[@name='isRealAlert']") is not None:
            if not v.find(".//Param[@name='isRealAlert']").attrib["value"]:
                # Not a real alert so ignore
                self.ignore = True
                print('Not a real alert so ignore')
                return

        # Check if this is the type of trigger we're looking for
        this_pair = f"{self.telescope}_{self.event_type}"
        if this_pair in self.trig_pairs:
            self.ignore = False
        else:
            # Unknown telescope so ignoring
            print('Unknown telescope so ignoring')
            self.ignore = True
            return
        # Parse trigger info (telescope dependent)
        if self.telescope == "Fermi":
            self.event_duration = float(
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
            # Check if SWIFT tracking fails
            startrack_lost_lock = v.find(".//Param[@name='StarTrack_Lost_Lock']")
            if startrack_lost_lock is None:
                # No 'StarTrack_Lost_Lock' in xml so assume false
                startrack_lost_lock = False
            else:
                startrack_lost_lock = startrack_lost_lock.attrib["value"]
                # convert 'true' to True, and everything else to false
                startrack_lost_lock = (startrack_lost_lock.lower() == "true")
            logger.debug("StarLock OK? {0}".format(not startrack_lost_lock))
            if startrack_lost_lock:
                logger.warning("The SWIFT star tracker lost it's lock so ignoring event")
                self.event_type += " SWIFT lost star tracker"
                self.ignore = True
                return

            # Get time and significance
            event_duration = v.find(".//Param[@name='Integ_Time']")
            if event_duration is not None:
                self.event_duration = float(event_duration.attrib["value"])
            self.sequence_num = None
            swift_rate_signif = v.find(".//Param[@name='Rate_Signif']")
            if swift_rate_signif is not None:
                self.swift_rate_signif = float(swift_rate_signif.attrib["value"])
            grb_ident = v.find(".//Param[@name='GRB_Identified']")
            if grb_ident is not None:
                self.grb_ident = grb_ident.attrib["value"]

        elif self.telescope == "Antares":
            self.event_duration = None
            self.sequence_num = None
            self.antares_ranking = int(v.find(".//Param[@name='ranking']").attrib["value"])

        elif self.telescope == "LVC":
            self.event_duration = None
            self.sequence_num = None

            if self.event_type == 'EarlyWarning' or self.event_type == 'Preliminary' or self.event_type == 'Initial' or self.event_type == 'Update':
                # Capture Probabilities of observations for proposals and analysis
                self.false_alarm_rate_hz = str(v.find(".//Param[@name='FAR']").attrib["value"])
                self.lvc_classification_BNS = float(v.find(".//Param[@name='BNS']").attrib["value"])
                self.lvc_classification_NSBH = float(v.find(".//Param[@name='NSBH']").attrib["value"])
                self.lvc_classification_BBH = float(v.find(".//Param[@name='BBH']").attrib["value"])
                self.lvc_classification_Terrestrial = float(v.find(".//Param[@name='Terrestrial']").attrib["value"])

            if self.event_type == 'Initial' or self.event_type == 'Update':
                # Initial and Update alerts should contain skymap data as URL
                self.skymap_fits = str(v.find(".//Param[@name='skymap_fits']").attrib["value"])

                url =  self.skymap_fits
                urllib.request.urlretrieve(url, "skymap.fits")

                skymap = Table.read("skymap.fits")
                i = np.argmax(skymap['PROBDENSITY'])
                self.prob_density_tile = float(skymap[i]['PROBDENSITY'] * (np.pi / 180)**2)
                
                uniq = skymap[i]['UNIQ']
                level, ipix = ah.uniq_to_level_ipix(uniq)
                nside = ah.level_to_nside(level)
                ra, dec = ah.healpix_to_lonlat(ipix, nside, order='nested')
                self.right_ascension_degrees = float(ra.deg)
                self.decension_degrees = float(dec.deg)
                os.remove("skymap.fits")

            if self.event_type == 'Retraction':
                # Capture message that comes with retraction
                self.retraction_message = str(v.Citations.Description)
                    
        logger.debug("Trig details:")
        logger.debug(f"Dur:  {self.event_duration} s")
        logger.debug(f"ID:   {self.trig_id}")
        logger.debug(f"Seq#: {self.sequence_num}")
        logger.debug(f"Type: {self.event_type}")

