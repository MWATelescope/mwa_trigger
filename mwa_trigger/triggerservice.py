
"""Library to simplify calls to the 'trigger' web services running on mro.mwa128t.org, used to
   interrupt current MWA observations as a result of an incoming trigger.
"""

import base64
import json
import sys
import traceback

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


def web_api(url='', urldict=None, postdict=None, username=None, password=None, logger=DEFAULTLOGGER):
    """
    Given a url, an optional dictionary for URL arguments, and an optional dictionary
    containing data to POST, open the appropriate URL, POST data if supplied, and
    return the result of the call converted from JSON format to a Python dictionary.

    :param url:   The full URL to open, minus any trailing ?name=value&name2=value2... arguments
    :param urldict: Optional Python dictionary to be URL-encoded and appended as
             ...?name=value&name2=value2&... data in the URL itself
    :param postdict: Python dictionary to be converted to JSON format and POSTed
              with the request.
    :param logger: If a logger object is passed, log activity to it, otherwise use
              the default logger which will suppress all output.

    :param username: Optional BASIC auth username

    :param password: Optional BASIC auth password

    :return: A tuple of (result, header) where result is a Python dict (un-jsoned from the
             text), the text itself, or None, and 'header' is the HTTP header object (use
             .get_param() to extract values) or None.
    """
    if urldict is not None:
        urldata = '?' + urlencode(urldict)
    else:
        urldata = ''

    url += urldata

    if postdict is not None:
        postdata = urlencode(postdict)
    else:
        postdata = None

    if postdict:
        reqtype = 'POST'
    else:
        reqtype = 'GET'
    logger.debug("Request: %s %s." % (reqtype, url))
    if postdict:
        logger.debug('Data: %s' % postdict)
    try:
        if (username is not None) and (password is not None):
            if sys.version_info.major > 2:
                base64string = base64.b64encode(('%s:%s' % (username, password)).encode('latin-1'))
                base64string = base64string.decode('latin-1')
                postdata = postdata.encode('latin-1')
            else:
                base64string = base64.b64encode('%s:%s' % (username, password))
            req = Request(url, postdata, {'Content-Type':'application/json',
                                          'Accept':'application/json',
                                          'Authorization':'Basic %s' % base64string})
        else:
            req = Request(url, postdata, {'Content-Type': 'application/json',
                                          'Accept': 'application/json'})
        try:
            resobj = urlopen(req)
            data = resobj.read()
            if sys.version_info.major > 2:
                data = data.decode(resobj.headers.get_content_charset())
        except (ValueError, URLError):
            logger.error('urlopen failed, or there was an error reading from the opened request object')
            logger.error(traceback.format_exc())
            return None

        try:
            result = json.loads(data)
        except ValueError:
            result = data
        return result
    except HTTPError as error:
        logger.error("HTTP error from server: code=%d, response:\n %s" % (error.code, error.read()))
        logger.error('Unable to retrieve %s' % (url))
        logger.error(traceback.format_exc())
        return None
    except URLError as error:
        logger.error("URL or network error: %s" % error.reason)
        logger.error('Unable to retrieve %s' % (url))
        logger.error(traceback.format_exc())
        return None


def busy(project_id=None, obstime=None, logger=DEFAULTLOGGER):
    """
    Call with a project_id and a desired observing time. This function will return False if the given project_id
    is allowed to override current observations from now for the given length of time, or True if not.

    Note that a False result doesn't guarantee a later call to trigger() will succeed, as new observations may have been
    added to the schedule in the meantime.

    :param project_id: eg 'C001'
    :param obstime: eg 1800
    :param logger: optional logging.logger object
    :return: boolean
    """
    urldict = {}
    if project_id is not None:
        urldict['project_id'] = project_id
    else:
        logger.error('triggering.trigger() must be passed a valid project_id')
        return None

    if obstime is not None:
        urldict['obstime'] = obstime

    result = web_api(url=BASEURL + 'busy', urldict=urldict, logger=logger)
    return result


def vcsfree(logger=DEFAULTLOGGER):
    """
    This function will return the maximum number of seconds that a VCS trigger will be allowed to request,
    given the current free space, and upcoming VCS observations in the schedule.

    Note that this doesn't guarantee a later call to trigger() will succeed, as new VCS observations may have been
    added to the schedule in the meantime.

    :param logger: optional logging.logger object
    :return: int
    """
    urldict = {}

    result = web_api(url=BASEURL + 'vcsfree', urldict=urldict, logger=logger)
    return result


def obslist(obstime=None, logger=DEFAULTLOGGER):
    """
    Call with a desired observing time. This function will return a list of tuples containing
    (starttime, obsname, creator, projectid, mode) for each observation between 'now' and the
    given number of seconds in the future.

    :param obstime: eg 1800
    :param logger:  optional logging.logger object
    :return: list of (starttime, obsname, creator, projectid, mode) tuples
    """
    urldict = {}
    if obstime is not None:
        urldict['obstime'] = obstime

    result = web_api(url=BASEURL + 'obslist', urldict=urldict, logger=logger)
    return result


def trigger(project_id=None, secure_key=None,
            ra=None, dec=None, alt=None, az=None, source=None, freqspecs=None,
            creator=None, obsname=None, nobs=None, exptime=None,
            calexptime=None, calibrator=None,
            freqres=None, inttime=None,
            avoidsun=None,
            vcsmode=None,
            buffered=None,
            pretend=None,
            logger=DEFAULTLOGGER):
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

    The structure returned is a dictionary, containing the following:
      result['success'] - a boolean, True if the observations were scheduled successfully, False if there was an error.
      result['errors'] - a dictionary, containing integer keys from 0-N, where each value is an error message. Normally empty.
      result['params'] - a dictionary containing all parameters passed to the web service, after parsing, and some extra
                         parameters calculated by the web service (the name of the automatically chosen calibrator, etc).
      result['clear'] - the commands used to clear the schedule. It contains the keys/values:
                           'command': The full clear_schedule.py command line
                           'retcode': The integer return code from that command
                           'stderr': The output to STDERR from that command
                           'stdout': The output to STDOUT from that command
      result['schedule'] - the commands used to schedule the triggered observations. It contains the keys/values:
                           'command': A string containing all of the single_observation.py command lines
                           'retcode':The integer return code from the shell spawned to run those commands
                           'stderr': The output to STDERR from those commands
                           'stdout': The output to STDOUT from those commands

    :param project_id: eg 'C001' - project ID for the triggered observations
    :param secure_key: password associated with that project_id
    :param ra: Either one RA (float, in hours), or a list of RA floats. Eg 12.234, or [11.0, 12.0]
    :param dec: Either one Dec (float, in degrees), or a list of Dec floats. Eg -12.234, or [-26.0, -36.0]
    :param alt: Either one Alt (float, in degrees), or a list of Alt floats. Eg 80.0, or [70.0, 90.0]
    :param az: Either one Az (float, in degrees), or a list of Az floats. Eg 250.3, or [90.0, 270.0]
    :param source: Either one source name string, or a list of source name strings. Eg 'Sun', or ['Sun', 'Moon']
    :param freqspecs: Either one frequency specifier string, or a list of frequency specifier strings. Eg '145,24', or ['121,24', '145,24']
    :param creator: Creator string, eg 'Andrew'
    :param obsname: Observation name string, eg 'Fermi Trigger 20180211.1234'
    :param nobs: Number of observations to schedule for each position/frequency combination
    :param exptime: Exposure time of each observation scheduled, in seconds (must be modulo-8 seconds)
    :param calexptime: Exposure time of the trailing calibrator observation, if applicable, in seconds
    :param calibrator: None or False for no calibrator observation, a source name to specify one, or True to have one chosen for you.
    :param freqres: Correlator frequency resolution for observations. None to use whatever the current mode is, for lower latency. Eg 40
    :param inttime: Correlator integration time for observations. None to use whatever the current mode is, for lower latency. Eg 0.5
    :param avoidsun: boolean or integer. If True, the coordinates of the target and calibrator are shifted slightly to put the Sun in a null.
    :param vcsmode: boolean. If True, the observations are made in 'Voltage Capture' mode instead of normal (HW_LFILES) mode.
    :param buffered: boolean. If True and vcsmode, trigger a Voltage capture using the ring buffer.
    :param pretend: boolean or integer. If True, the clear_schedule.py and single_observation.py commands will be generated but NOT run.
    :param logger: optional logging.logger object
    :return: dictionary structure describing the processing (see above for more information).
    """

    if vcsmode and buffered:
        return triggerbuffer(project_id=project_id,
                             secure_key=secure_key,
                             pretend=pretend,
                             obstime=nobs*exptime,
                             logger=logger)

    urldict = {}
    postdict = {}
    if project_id is not None:
        urldict['project_id'] = project_id
    else:
        logger.error('triggering.trigger() must be passed a valid project_id')
        return None

    if secure_key is not None:
        postdict['secure_key'] = secure_key
    else:
        logger.error('triggering.trigger() must be passed a valid secure_key')
        return None

    if ra is not None:
        postdict['ra'] = ra
    if dec is not None:
        postdict['dec'] = dec
    if alt is not None:
        postdict['alt'] = alt
    if az is not None:
        postdict['az'] = az
    if source is not None:
        postdict['source'] = source
    if freqspecs is not None:
        if type(freqspecs) == list:
            postdict['freqspecs'] = json.dumps(freqspecs)
        else:
            postdict['freqspecs'] = freqspecs

    if creator is not None:
        postdict['creator'] = creator
    if obsname is not None:
        urldict['obsname'] = obsname
    if nobs is not None:
        postdict['nobs'] = nobs
    if exptime is not None:
        postdict['exptime'] = exptime
    if calexptime is not None:
        postdict['calexptime'] = calexptime
    if (freqres is not None) and (inttime is not None):
        postdict['freqres'] = freqres
        postdict['inttime'] = inttime
    else:
        if (freqres is None) != (inttime is None):
            logger.error('triggering.trigger() must be passed BOTH inttime AND freqres, or neither of them.')
            return None
    if calibrator is not None:
        postdict['calibrator'] = calibrator
    if avoidsun is not None:
        postdict['avoidsun'] = avoidsun
    if pretend is not None:
        postdict['pretend'] = pretend
    if vcsmode is not None:
        postdict['vcsmode'] = vcsmode

    logger.debug('urldict=%s' % urldict)
    logger.debug('postdict=%s' % postdict)

    if vcsmode:
        result = web_api(url=BASEURL + 'triggervcs', urldict=urldict, postdict=postdict, logger=logger)
    else:
        result = web_api(url=BASEURL + 'triggerobs', urldict=urldict, postdict=postdict, logger=logger)
    return result


def triggerbuffer(project_id=None,
                  secure_key=None,
                  pretend=None,
                  obstime=None,
                  logger=DEFAULTLOGGER):
    """
    If the correlator is in VOLTAGE_BUFFER mode, trigger an immediate dump of the memory buffers to
    disk, and start capturing voltage data for obstime seconds (after which a 16 second VOLTAGE_STOP observation is
    inserted into the schedule), or until the next scheduled VOLTAGE_STOP observation, whichever comes
    first.

    The structure returned is a dictionary, containing the following:
      result['success'] - a boolean, True if the observations were scheduled successfully, False if there was an error.
      result['errors'] - a dictionary, containing integer keys from 0-N, where each value is an error message. Normally empty.
      result['params'] - a dictionary containing all parameters passed to the web service, after parsing, and some extra
                         parameters calculated by the web service (the name of the automatically chosen calibrator, etc).
      result['clear'] - the commands used to clear the schedule. It contains the keys/values:
                           'command': The full clear_schedule.py command line
                           'retcode': The integer return code from that command
                           'stderr': The output to STDERR from that command
                           'stdout': The output to STDOUT from that command
      result['schedule'] - the commands used to trigger the buffer dump and add a VOLTAGE_STOP observation.
                           It contains the keys/values:
                               'command': A string containing all of the single_observation.py command lines
                               'retcode':The integer return code from the shell spawned to run those commands
                               'stderr': The output to STDERR from those commands
                               'stdout': The output to STDOUT from those commands

    :param project_id: eg 'C001' - project ID for the triggered observations
    :param secure_key: password associated with that project_id
    :param pretend: boolean or integer. If True, the triggervcs command will NOT be run.
    :param logger: optional logging.logger object
    :param obstime: Duration of data capture, in seconds.
    :return: dictionary structure describing the processing (see above for more information).
    """
    urldict = {}
    postdict = {}
    if project_id is not None:
        urldict['project_id'] = project_id
    else:
        logger.error('triggering.trigger() must be passed a valid project_id')
        return None

    if secure_key is not None:
        postdict['secure_key'] = secure_key
    else:
        logger.error('triggering.trigger() must be passed a valid secure_key')
        return None

    if pretend is not None:
        postdict['pretend'] = pretend

    if obstime is not None:
        postdict['obstime'] = obstime

    result = web_api(url=BASEURL + 'triggerbuffer', urldict=urldict, postdict=postdict, logger=logger)
    return result
