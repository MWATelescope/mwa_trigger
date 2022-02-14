"""Library to simplify calls to the 'trigger' web services running on mro.mwa128t.org, used to
   interrupt current MWA observations as a result of an incoming trigger.
"""

import base64
import json
import sys
import traceback
from time import gmtime, strftime
from astropy.coordinates import Angle
import astropy.units as u

import cabb_scheduler as cabb
import atca_rapid_response_api as arrApi

import logging

logging.basicConfig()

if sys.version_info.major == 3:  # Python3
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
else:  # Python2
    from urllib import urlencode
    from urllib2 import urlopen, HTTPError, URLError, Request


DEFAULTLOGGER = logging.getLogger()
DEFAULTLOGGER.level = logging.DEBUG

BASEURL = "http://mro.mwa128t.org/trigger/"


def web_api(
    url="",
    urldict=None,
    postdict=None,
    username=None,
    password=None,
    logger=DEFAULTLOGGER,
):
    """
    Given a url, an optional dictionary for URL arguments, and an optional dictionary
    containing data to POST, open the appropriate URL, POST data if supplied, and
    return the result of the call converted from JSON format to a Python dictionary.

    Parameters
    ----------
    url : `str`
        The full URL to open, minus any trailing ?name=value&name2=value2... arguments
    urldict : `dict`, optional
        Python dictionary to be URL-encoded and appended as ...?name=value&name2=value2&... data in the URL itself
    postdict : `dict`
        Python dictionary to be converted to JSON format and POSTed with the request.
    logger : `logging`
        If a logger object is passed, log activity to it, otherwise use the default logger which will suppress all output.
    username : `str`, optional
        BASIC auth username
    password : `str`, optional
        BASIC auth password

    Returns
    -------
    return : `tuple`
        A tuple of (result, header) where result is a Python dict (un-jsoned from the
        text), the text itself, or None, and 'header' is the HTTP header object (use
        .get_param() to extract values) or None.
    """
    if urldict is not None:
        urldata = "?" + urlencode(urldict)
    else:
        urldata = ""

    url += urldata

    if postdict is not None:
        postdata = urlencode(postdict)
        if sys.version_info.major > 2:
            postdata = postdata.encode()
    else:
        postdata = None

    if postdict:
        reqtype = "POST"
    else:
        reqtype = "GET"
    logger.debug("Request: %s %s." % (reqtype, url))
    if postdict:
        logger.debug("Data: %s" % postdict)

    # Set up request
    header = {"Content-Type": "application/json",
              "Accept": "application/json",
    }
    if (username is not None) and (password is not None):
        # Add authenticatin
        if sys.version_info.major > 2:
            base64string = base64.b64encode(
                ("%s:%s" % (username, password)).encode()
            )
            base64string = base64string.decode()
        else:
            base64string = base64.b64encode("%s:%s" % (username, password))
        header["Authorization"] = "Basic %s" % base64string
    try:
        req = Request(url, postdata, header)
        try:
            resobj = urlopen(req)
            data = resobj.read()
            logger.debug(data.decode())
            logger.debug(resobj.headers.get_content_charset())
            if sys.version_info.major > 2:
                if resobj.headers.get_content_charset() is None:
                    data = data.decode()
                else:
                    data = data.decode(resobj.headers.get_content_charset())
        except (ValueError, URLError):
            logger.error(
                "urlopen failed, or there was an error reading from the opened request object"
            )
            logger.error(traceback.format_exc())
            return None

        try:
            result = json.loads(data)
        except ValueError:
            result = data
        return result
    except HTTPError as error:
        logger.error(
            "HTTP error from server: code=%d, response:\n %s"
            % (error.code, error.read())
        )
        logger.error("Unable to retrieve %s" % (url))
        logger.error(traceback.format_exc())
        return None
    except URLError as error:
        logger.error("URL or network error: %s" % error.reason)
        logger.error("Unable to retrieve %s" % (url))
        logger.error(traceback.format_exc())
        return None


def busy(project_id=None, obstime=None, logger=DEFAULTLOGGER):
    """
    Call with a project_id and a desired observing time. This function will return False if the given project_id
    is allowed to override current observations from now for the given length of time, or True if not.

    Note that a False result doesn't guarantee a later call to trigger_mwa() will succeed, as new observations may have been
    added to the schedule in the meantime.

    Parameters
    ----------
    project_id : `str`
        The MWA project ID, eg 'C001'.
    obstime : `int`
        Length of time to check in seconds. eg 1800.
    logger : `logging`, optional
        logging.logger object.

    Returns
    -------
    return : `boolean`
        True if the telescope can't be overridden.
    """
    urldict = {}
    if project_id is not None:
        urldict["project_id"] = project_id
    else:
        logger.error("triggering.trigger_mwa() must be passed a valid project_id")
        return None

    if obstime is not None:
        urldict["obstime"] = obstime

    result = web_api(url=BASEURL + "busy", urldict=urldict, logger=logger)
    return result


def vcsfree(logger=DEFAULTLOGGER):
    """
    This function will return the maximum number of seconds that a VCS trigger will be allowed to request,
    given the current free space, and upcoming VCS observations in the schedule.

    Note that this doesn't guarantee a later call to trigger_mwa() will succeed, as new VCS observations may have been
    added to the schedule in the meantime.

    Parameters
    ----------
    logger : `logging`, optional
        logging.logger object.

    Returns
    -------
    return : `int`
        Number of seconds the vcs is free.
    """
    urldict = {}

    result = web_api(url=BASEURL + "vcsfree", urldict=urldict, logger=logger)
    return result


def obslist(obstime=None, logger=DEFAULTLOGGER):
    """
    Call with a desired observing time. This function will return a list of tuples containing
    (starttime, obsname, creator, projectid, mode) for each observation between 'now' and the
    given number of seconds in the future.

    Parameters
    ----------
    obstime : `int`
        Length of time to check in seconds. eg 1800.
    logger : `logging`, optional
        logging.logger object.

    Returns
    -------
    return : `list`
        List of (starttime, obsname, creator, projectid, mode) tuples.
    """
    urldict = {}
    if obstime is not None:
        urldict["obstime"] = obstime

    result = web_api(url=BASEURL + "obslist", urldict=urldict, logger=logger)
    return result


def trigger_mwa(
    project_id=None,
    secure_key=None,
    group_id=None,
    ra=None,
    dec=None,
    alt=None,
    az=None,
    source=None,
    freqspecs=None,
    creator=None,
    obsname=None,
    nobs=None,
    exptime=None,
    calexptime=None,
    calibrator=None,
    freqres=None,
    inttime=None,
    avoidsun=None,
    vcsmode=None,
    buffered=None,
    pretend=None,
    logger=DEFAULTLOGGER,
):
    """
    Call with the parameters that describe the observation/s to schedule, and those observations will
    be added to the schedule immediately, starting 'now'.

    You can pass more than one position, in any combination of:
      -one or more RA/Dec pairs
      -one or more alt/az pairs
      -one of more source names

    Observations will be generated for each position given, in turn (all RA/Dec first, then all Alt/Az, then all sourcenames).

    You can also pass, for example, one Alt value and a list of Az values, in which case the one Alt value will be
    propagated to the other Az's. For example, alt=70.0, az=[0,90,180] will give [(70,0), (70,90), (70,180)]. The same
    is true for RA/Dec.

    You can also pass more than one frequency specifier, in which case observations will be generated for each choice
    of frequency, AT each position.

    If the 'avoidsum' parameter is True, then the coordinates of the target and calibrator are shifted slightly to
    put the Sun in a beam null. For this to work, the target coordinates must be RA/Dec values, not Alt/Az.

    Parameters
    ----------
    project_id : `str`
        Project ID for the triggered observations, eg 'C001'.
    secure_key : `str`
        Password associated with that project_id.
    group_id : `int`, optional
        The start time of a previously triggered observation of the same event.
    ra : `float` or `list`
        Either one RA (float, in hours), or a list of RA floats. Eg 12.234, or [11.0, 12.0].
    dec : `float` or `list`
        Either one Dec (float, in degrees), or a list of Dec floats. Eg -12.234, or [-26.0, -36.0].
    alt : `float` or `list`
        Either one Alt (float, in degrees), or a list of Alt floats. Eg 80.0, or [70.0, 90.0].
    az : `float` or `list`
        Either one Az (float, in degrees), or a list of Az floats. Eg 250.3, or [90.0, 270.0].
    source : `str` or `list`
        Either one source name string, or a list of source name strings. Eg 'Sun', or ['Sun', 'Moon'].
    freqspecs : `float` or `list`
        Either one frequency specifier string, or a list of frequency specifier strings. Eg '145,24', or ['121,24', '145,24'].
    creator : `str`
        Creator string, eg 'Andrew'.
    obsname : `str`
        Observation name string, eg 'Fermi Trigger 20180211.1234'.
    nobs : `int`
        Number of observations to schedule for each position/frequency combination.
    exptime : `int`
        Exposure time of each observation scheduled, in seconds (must be modulo-8 seconds).
    calexptime : `int`
        Exposure time of the trailing calibrator observation, if applicable, in seconds.
    calibrator : `boolean` or `str`
        None or False for no calibrator observation, a source name to specify one, or True to have one chosen for you.
    freqres : `float`
        Correlator frequency resolution for observations. None to use whatever the current mode is, for lower latency. Eg 40.
    inttime : `float`
        Correlator integration time for observations. None to use whatever the current mode is, for lower latency. Eg 0.5.
    avoidsun : `boolean` or `int`
        If True, the coordinates of the target and calibrator are shifted slightly to put the Sun in a null.
    vcsmode : `boolean`
        If True, the observations are made in 'Voltage Capture' mode instead of normal (HW_LFILES) mode.
    buffered : `boolean`
        If True and vcsmode, trigger a Voltage capture using the ring buffer.
    pretend : `boolean` or `int`
        If True, the clear_schedule.py and single_observation.py commands will be generated but NOT run.
    logger : `logging`, optional
        logging.logger object.

    Returns
    -------
        The structure returned is a dictionary with the following keys:

        ``"success"``
            True if the observations were scheduled successfully, False if there was an error (`boolean`).
        ``"errors"``
            A dictionary, containing integer keys from 0-N, where each value is an error message. Normally empty.
        ``"params"``
            A dictionary containing all parameters passed to the web service, after parsing, and some extra
            parameters calculated by the web service (the name of the automatically chosen calibrator, etc).
        ``"clear"``
            the commands used to clear the schedule. It contains the keys/values:

            ``"command"``
                The full clear_schedule.py command line.
            ``"retcode"``
                The integer return code from that command.
            ``"stderr"``
                The output to STDERR from that command.
            ``"stdout"``
                The output to STDOUT from that command.
        ``"schedule"``
            The commands used to schedule the triggered observations. It contains the keys/values:

            ``"command"``
                A string containing all of the single_observation.py command lines.
            ``"retcode"``
                The integer return code from the shell spawned to run those commands.
            ``"stderr"``
                The output to STDERR from those commands.
            ``"stdout"``
                The output to STDOUT from those commands.
    """

    if vcsmode and buffered:
        return triggerbuffer(
            project_id=project_id,
            secure_key=secure_key,
            pretend=pretend,
            obstime=nobs * exptime,
            logger=logger,
        )

    urldict = {}
    postdict = {}
    if project_id is not None:
        urldict["project_id"] = project_id
    else:
        logger.error("triggering.trigger_mwa() must be passed a valid project_id")
        return None

    if secure_key is not None:
        postdict["secure_key"] = secure_key
    else:
        logger.error("triggering.trigger_mwa() must be passed a valid secure_key")
        return None

    if group_id is not None:
        postdict["group_id"] = group_id
    if ra is not None:
        postdict["ra"] = ra
    if dec is not None:
        postdict["dec"] = dec
    if alt is not None:
        postdict["alt"] = alt
    if az is not None:
        postdict["az"] = az
    if source is not None:
        postdict["source"] = source
    if freqspecs is not None:
        if type(freqspecs) == list:
            postdict["freqspecs"] = json.dumps(freqspecs)
        else:
            postdict["freqspecs"] = freqspecs

    if creator is not None:
        postdict["creator"] = creator
    if obsname is not None:
        urldict["obsname"] = obsname
    if nobs is not None:
        postdict["nobs"] = nobs
    if exptime is not None:
        postdict["exptime"] = exptime
    if calexptime is not None:
        postdict["calexptime"] = calexptime
    if (freqres is not None) and (inttime is not None):
        postdict["freqres"] = freqres
        postdict["inttime"] = inttime
    else:
        if (freqres is None) != (inttime is None):
            logger.error(
                "triggering.trigger_mwa() must be passed BOTH inttime AND freqres, or neither of them."
            )
            return None
    if calibrator is not None:
        postdict["calibrator"] = calibrator
    if avoidsun is not None:
        postdict["avoidsun"] = avoidsun
    if pretend is not None:
        postdict["pretend"] = pretend
    if vcsmode is not None:
        postdict["vcsmode"] = vcsmode

    logger.debug("urldict=%s" % urldict)
    logger.debug("postdict=%s" % postdict)

    if vcsmode:
        result = web_api(
            url=BASEURL + "triggervcs",
            urldict=urldict,
            postdict=postdict,
            logger=logger,
        )
    else:
        result = web_api(
            url=BASEURL + "triggerobs",
            urldict=urldict,
            postdict=postdict,
            logger=logger,
        )
    return result


def triggerbuffer(
    project_id=None, secure_key=None, pretend=None, obstime=None, logger=DEFAULTLOGGER
):
    """
    If the correlator is in VOLTAGE_BUFFER mode, trigger an immediate dump of the memory buffers to
    disk, and start capturing voltage data for obstime seconds (after which a 16 second VOLTAGE_STOP observation is
    inserted into the schedule), or until the next scheduled VOLTAGE_STOP observation, whichever comes
    first.

    Parameters
    ----------
    project_id : `str`
        Project ID for the triggered observations, eg 'C001'.
    secure_key : `str`
        Password associated with that project_id.
    pretend : `boolean` or `int`
        If True, the clear_schedule.py and single_observation.py commands will be generated but NOT run.
    logger : `logging`, optional
        logging.logger object.
    obstime : `int`
        Duration of data capture, in seconds.

    Returns
    -------
        The structure returned is a dictionary with the following keys:

        ``"success"``
            True if the observations were scheduled successfully, False if there was an error (`boolean`).
        ``"errors"``
            A dictionary, containing integer keys from 0-N, where each value is an error message. Normally empty.
        ``"params"``
            A dictionary containing all parameters passed to the web service, after parsing, and some extra
            parameters calculated by the web service (the name of the automatically chosen calibrator, etc).
        ``"clear"``
            the commands used to clear the schedule. It contains the keys/values:

            ``"command"``
                The full clear_schedule.py command line.
            ``"retcode"``
                The integer return code from that command.
            ``"stderr"``
                The output to STDERR from that command.
            ``"stdout"``
                The output to STDOUT from that command.
        ``"schedule"``
            The commands used to schedule the triggered observations. It contains the keys/values:

            ``"command"``
                A string containing all of the single_observation.py command lines.
            ``"retcode"``
                The integer return code from the shell spawned to run those commands.
            ``"stderr"``
                The output to STDERR from those commands.
            ``"stdout"``
                The output to STDOUT from those commands.
    """
    urldict = {}
    postdict = {}
    if project_id is not None:
        urldict["project_id"] = project_id
    else:
        logger.error("triggering.trigger_mwa() must be passed a valid project_id")
        return None

    if secure_key is not None:
        postdict["secure_key"] = secure_key
    else:
        logger.error("triggering.trigger_mwa() must be passed a valid secure_key")
        return None

    if pretend is not None:
        postdict["pretend"] = pretend

    if obstime is not None:
        postdict["obstime"] = obstime

    result = web_api(
        url=BASEURL + "triggerbuffer", urldict=urldict, postdict=postdict, logger=logger
    )
    return result


def trigger_atca(
    project_id=None,
    secure_key=None,
    ra=None,
    dec=None,
    source=None,
    freqspecs=[5500, 9000],
    nobs=32,
    exptime=20,
    calexptime=2,
    pretend=False,
    logger=DEFAULTLOGGER,
):
    """
    Create a schedule for the ATCA and try to trigger an observation.

    parameters
    ----------
    project_id : str
        Project id
    secure_key : str
        filename for authentication token to use
    ra, dec : float, float
        RA/DEC pointing in degrees.
    source : str
        Name of the source to be observed (<= 10 chars)
    freqspecs : [int, int] Default=[5500,9000]
        The [f1,f2] frequencies to observe in MHz.
    nobs : int Default=32
        Number of observations to schedule
    exptime : int Default=20
        Exposure time per observation in minutes
    calexptime : int Default=2
        Exposure time per (phase) calibration in minutes
    pretend : bool Default=False
        If true, don't actually do any obs.
    logger : logging.logger
        The logger to use.
    """

    ra_str = Angle(ra * u.deg).to_string(unit=u.hour, sep=":")
    dec_str = Angle(dec * u.deg).to_string(unit=u.deg, sep=":")

    schedule = cabb.schedule()
    # currentFreqs = cabb.monica_information.getFrequencies()
    scan1 = schedule.addScan(
        {
            "source": source,
            "rightAscension": ra_str,
            "declination": dec_str,
            "freq1": freqspecs[0],
            "freq2": freqspecs[1],
            "project": project_id,
            "scanLength": "00:20:00",  # TODO: convert exptime to hh:mm:ss
            "scanType": "Dwell",
        }
    )
    schedule.disablePriorCalibration()
    calList = scan1.findCalibrator()
    currentArray = cabb.monica_information.getArray()
    bestCal = calList.getBestCalibrator(currentArray)
    logger.info(
        f"Calibrator chosen: {bestCal['calibrator'].getName():s}, {bestCal['distance']:.1f} degrees away"
    )
    calScan = schedule.addCalibrator(
        bestCal["calibrator"],
        scan1,
        {"scanLength": "00:02:00"},  # TODO: convert calexptime to hh:mm:ss
    )

    for _ in range(nobs - 1):
        schedule.copyScans([scan1.getId()])

    schedule.setLooping(False)

    if pretend:
        fname = strftime("%Y-%m-%d_%H%M", gmtime())
        fname = f"{project_id}_{fname}.sch"
        schedule.write(name=fname)

    schedString = schedule.toString()

    # We have our schedule now, so we need to craft the service request to submit it to
    # the rapid response service.
    rapidObj = {"schedule": schedString}
    rapidObj["authenticationTokenFile"] = secure_key
    # The name of the main target needs to be specified.
    rapidObj["nameTarget"] = source
    rapidObj["nameCalibrator"] = bestCal["calibrator"].getName()
    rapidObj["email"] = "test@example.com"
    rapidObj["usePreviousFrequencies"] = False

    if pretend:
        rapidObj["test"] = True
        rapidObj["noTimeLimit"] = True
        rapidObj["noScoreLimit"] = True
        rapidObj["minimumTime"] = 2.0

    request = arrApi.api(rapidObj)
    try:
        response = request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
    return
