#! python

"""
Library containing one or more functions to process incoming VOEvent XML strings. This library will
be imported by a long running process, so you can load large data files, etc, at import time, rather than
inside the processevent() function, to save time.
"""

__version__ = "0.3"
__author__ = ["Paul Hancock", "Andrew Williams", "Gemma Anderson"]

import os
import sys

if sys.version_info.major == 2:
    from ConfigParser import SafeConfigParser as conparser
else:
    from configparser import ConfigParser as conparser

import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
if sys.version_info.major == 2:
    from email.Encoders import encode_base64
else:
    from email.encoders import encode_base64

import logging

import astropy
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

from . import triggerservice

log = logging.getLogger('voevent.handlers')  # Inherit the logging setup from voevent_handler.py

# Settings
HORIZON_LIMIT = 30  # Don't observe if the source is below this elevation
FERMI_POBABILITY_THRESHOLD = 50  # Trigger on Fermi events that have most-likely-prob > this number


CPPATH = ['/usr/local/etc/trigger.conf', 'mwa_trigger/trigger.conf', './trigger.conf']   # Path list to look for configuration file
CP = conparser()
CP.read(CPPATH)

if CP.has_option(section='mail', option='mailhost'):
    MAILHOST = CP.get(section='mail', option='mailhost')
else:
    MAILHOST = 'cerberus'    # Using cerberus will only work for computers inside the MWA network, on-site.

# position of the observer
MWAPOS = EarthLocation.from_geodetic(lon="116:40:14.93",
                                     lat="-26:42:11.95",
                                     height=377.8)


EMAIL_FOOTER_TEMPLATE = """
Result: %(success)s

Errors: 
%(errors)s
"""


class TriggerEvent(object):
    """
    Class to encapsulate a single trigger event. It can include multiple VOEvent structures,
    stored in the .events attribute, so long as those VOEvents all refer to the same underlying
    physical event (eg, updates with better positions).
    """
    def __init__(self, event=None, logger=log):
        """
        Create a new trigger event and initialise attributes.

        :param event: string containing XML format VOEvent.
        :param logger: optional logger object to use for log messages associated with this event.
        """
        # ra,dec and err are lists of all the position values, with the most recent (and presumably best) last.
        self.ra = []   # list of RAs in J2000 degrees, most recent last.
        self.dec = []  # List of DECs in J2000 degrees, most recent last.
        self.err = []  # List of position error radii, in J2000 degrees, most recent last.
        self.triggered = False  # True if this event has ever been triggered (generated MWA observations)
        self.trigger_id = ''  # the id for this event as it appears in the observing schedule
        self.events = []  # a list of all the voevent XML strings, most recent last.
        self.first_trig_time = None  # when was the TriggerEvent first triggered
        self.last_trig_type = None  # Arbitrary string storing the reason for the last trigger.
        self.loglist = []   # List of log messages associated with this trigger event.
        self.logger = logger  # Logger object to use for log messages associated with this event.

        # default observing parameters to be passed to triggerservice.trigger
        self.freqspecs = '145,24'
        self.avoidsun = True
        self.inttime = 0.5  # seconds 0.5, 1, 2 are the only valid values currently
        self.freqres = 10  # khz
        self.exptime = 120  # seconds
        self.calibrator = True
        self.calexptime = 120  # seconds
        self.vcsmode = False
        self.buffered = False

        self.info('Event created')
        self.add_event(event)

    def add_event(self, event):
        """
        Add an XML event string to the .events list for this event.

        :param event: string containing XML format VOEvent.
        """
        if event is not None:
            self.info('New VOEvent added')
            self.events.append(event)

    def add_pos(self, pos):
        """
        Add a position to the list of positions for this event. Newer (and presumably more accurate) positions
        are appended to the end of the coordinate lists.

        :param pos: A tuple of (ra, dec, err) where ra and dec are the J2000 coords in degrees, and err is the error radius in deg
        :return:
        """
        ra, dec, err = pos
        self.ra.append(ra)
        self.dec.append(dec)
        self.err.append(err)
        self.info('Position added')

    def get_pos(self, index=-1):
        """
        Return one position tuple (ra, dec, err) for this event. By default, the most recent position is returned, but
        any position can be returned by passing the relevant index value (eg, for the first position, use index=0).

        :param index: The list index to return, satisying normal Python list indexing rules. Default of -1
        :return: A tuple of (ra, dec, err) where ra and dec are the J2000 coords in degrees, and err is the error radius in deg
        """
        if len(self.ra) < abs(index):
            return None, None, None
        return self.ra[index], self.dec[index], self.err[index]

    def trigger_observation(self,
                            ttype=None,
                            obsname='Trigger_test',
                            time_min=30,
                            pretend=False,
                            project_id="",
                            secure_key="",
                            email_tolist=None,
                            email_text="",
                            email_subject="",
                            creator=None,
                            voevent=""):
        """
        Tell the MWA to observe the target of interest - override this method in your handler as desired if you
        want some other observation parameters.

        :param ttype: Arbitrary string giving the reason for this trigger (eg 'Flt').
        :param obsname: Arbitrary string for the name of the observation in the schedule.
        :param time_min: Total length of observation time, in minutes.
        :param pretend: Boolean, True if we don't want to actually schedule the observations.
        :param project_id: The project ID requesting the triggered observation.
        :param secure_key: The password specific to that project ID.
        :param email_tolist: list of email addresses to send the notification email to.
        :param email_text: Base email message - success string, errors, and other data will be appended and attached.
        :param email_subject: string containing email subject line.
        :param creator: string containing text to put in creator field for new observation
        :param voevent: string containing the full XML text of the VOEvent.
        :return: The full results dictionary returned by the triggerservice API (see triggerservice.trigger).
        """

        self.triggered = True
        # This is the *first* trigger time so only update it once
        if self.first_trig_time is None:
            self.info('First trigger sent')
            self.first_trig_time = Time.now()
        else:
            self.info('Subsequent trigger sent')
        self.last_trig_type = ttype

        if time_min < 2:
            self.debug("Requested time is <2 min. Not triggering")
            return

        # set up the target, observer, and time
        ra, dec, err = self.get_pos()   # Find the most recent coordinates added to this event.
        obs_source = SkyCoord(ra=ra,
                              dec=dec,
                              equinox='J2000',
                              unit=(astropy.units.deg, astropy.units.deg))
        obs_source.location = MWAPOS
        t = Time.now()
        obs_source.obstime = t

        # figure out the altitude of the target
        obs_source_altaz = obs_source.transform_to('altaz')
        alt = obs_source_altaz.alt.deg
        self.debug("Triggered observation at an elevation of {0}".format(alt))

        # Determine the number and duration of observations
        if self.vcsmode:
            # VCS mode uses a single observation only
            nobs = 1
            exptime = time_min * 60
        else:
            # normal observations split this time into 2 min chunks
            nobs = int(time_min * 60 / self.exptime)
            exptime = self.exptime

        if creator is None:
            crstring = 'VOEvent_Auto_Trigger: handlers=%s' % __version__
        else:
            crstring = creator + ' handlers=%s' % __version__
        # trigger if we are above the horizon limit
        if alt > HORIZON_LIMIT:
            self.info("Triggering at gps time %d ..." % (t.gps,))
            result = triggerservice.trigger(project_id=project_id, secure_key=secure_key,
                                            pretend=pretend,
                                            ra=ra, dec=dec,
                                            creator=crstring,
                                            obsname=obsname, nobs=nobs,
                                            freqspecs=self.freqspecs,
                                            avoidsun=self.avoidsun,
                                            inttime=self.inttime, freqres=self.freqres,
                                            exptime=exptime,
                                            calibrator=self.calibrator, calexptime=self.calexptime,
                                            vcsmode=self.vcsmode,
                                            buffered=self.buffered,
                                            logger=self)
            # self.debug("Response: {0}".format(result))
            if result is None:
                self.error("Trigger Service Error: triggerservice.trigger() returned None")
                return
            if email_tolist:
                if result['success']:
                    success_string = "SUCCESS - observation inserted into MWA schedule"
                else:
                    success_string = "FAILURE - observation NOT inserted into MWA schedule"
                errorkeys = list(result['errors'].keys())
                errorkeys.sort()
                errors_string = '\n'.join(['[%s]: %s' % (num, result['errors'][num]) for num in errorkeys])
                email_footer = EMAIL_FOOTER_TEMPLATE % {'success': success_string, 'errors': errors_string}

                attachments = []
                if result['schedule']:
                    sched_data = "Commands:\n%s \n\n STDOUT:\n%s \n\n STDERR:\n%s" % (result['schedule']['commands'],
                                                                                      result['schedule']['stdout'],
                                                                                      result['schedule']['stderr'])
                    attachments.append(('schedule_%s.txt' % self.trigger_id, sched_data, 'text/plain'))
                if result['clear']:
                    clear_data = "Commands:\n%s \n\n STDOUT:\n%s \n\n STDERR:\n%s" % (result['clear']['command'],
                                                                                      result['clear']['stdout'],
                                                                                      result['clear']['stderr'])
                    attachments.append(('clear_%s.txt' % self.trigger_id, clear_data, 'text/plain'))
                log_data = '\n'.join([str(x) for x in self.loglist])
                attachments.append(('log_%s.txt' % self.trigger_id, log_data, 'text/plain'))
                attachments.append(('voevent.xml', voevent, 'text/xml'))

                send_email(from_address='mwa@telemetry.mwa128t.org',
                           to_addresses=email_tolist,
                           subject=email_subject,
                           msg_text=email_text + email_footer,
                           attachments=attachments)

            return result
        else:
            self.debug("not triggering due to horizon limit: alt {0} < {1}".format(alt, HORIZON_LIMIT))
            return

    def log(self, level=logging.DEBUG, msg=''):
        """
        Wrapper function, so log messages passed to this object by calling the debug, info, warning, error and critical
        methods can be caught and saved in a 'loglist' attribute, then passed on to the logger object for handling.

        :param level: One of logging.DEBUG, logging.INFO, etc.
        :param msg: string containing the full log message.
        :return: None
        """
        self.logger.log(level=level, msg=msg)
        now = Time.now()
        self.loglist.append("%s=(%d): %s" % (now.iso, int(now.gps), msg))

    def debug(self, msg=''):
        self.log(level=logging.DEBUG, msg=msg)

    def info(self, msg=''):
        self.log(level=logging.INFO, msg=msg)

    def warning(self, msg=''):
        self.log(level=logging.WARNING, msg=msg)

    def error(self, msg=''):
        self.log(level=logging.ERROR, msg=msg)

    def critical(self, msg=''):
        self.log(level=logging.CRITICAL, msg=msg)


def get_position_info(v):
    """
    Return the ra,dec,err from a given voevent
    These are typically in degrees, in the J2000 equinox.

    :param v: A VOEvent string, in XML format
    :return: A tuple of (ra, dec, err) where ra,dec are the coordinates in J2000 and err is the error radius in deg.
    """
    ra = float(v.find(".//C1"))
    dec = float(v.find(".//C2"))
    err = float(v.find('.//Error2Radius'))
    return ra, dec, err


def get_secure_key(project_id):
    """
    Look up the supplied project ID in the configuration file, to find the matching password

    :param project_id: Project ID string, eg C001
    :return: password associated with that project ID
    """
    if CP.has_option(section='auth', option=project_id):
        return CP.get(section='auth', option=project_id)
    else:
        return ''


def send_email(from_address='', to_addresses=None, msg_text='', subject='', attachments=None, logger=log):
    """
    Sends an email to the given address list, with the supplied message text. An optional list of attachments
    can be provided as well, to keep the main email concise.

    :param from_address: string containing the email address that the message is sent from.
    :param to_addresses: list of strings containing destination email addresses, or a string containing one address
    :param msg_text: A string containing the full text of the message to send.
    :param subject: A string containing the subject line of the email.
    :param attachments: A list of (filename, payload, mimetype) tuples, where:
                            -filename is the name the attachment will be saved as on the client, not a local file name.
                            -payload is the entire content of the attachment (a PNG image, zip file, etc)
                            -mimetype is the type string, and defaults to 'text/plain' if omitted from the tuple
    :param logger: An optional logger object to use for logging messages, instead of the default logger.
    :return:
    """
    if attachments is None:
        attachments = []

    if not to_addresses:
        logger.error('Must specify a list of email addresses to send the email to.')
        return False

    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = ', '.join(to_addresses)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    msg.attach(MIMEText(msg_text))

    for attachspec in attachments:
        if type(attachspec) != tuple:
            logger.error('attachments must be a tuple of (filename, payload, mimetype), where payload is the file contents.')
            return False

        try:
            if len(attachspec) == 2:
                filename, payload = attachspec
                if filename.endswith('.xml'):
                    mimetype = 'text/xml'
                else:
                    mimetype = 'text/plain'
            else:
                filename, payload, mimetype = attachspec

            if mimetype:
                mimemain, mimesub = mimetype.split('/')
            else:
                mimemain = 'text'
                mimesub = 'plain'
        except ValueError:
            logger.error('attachments must be a tuple of (filename, payload, mimetype), where payload is the file contents.')
            return False

        part = MIMEBase(mimemain, mimesub)
        part.set_payload(payload)
        encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filename))
        msg.attach(part)

    smtp = None
    try:
        smtp = smtplib.SMTP(MAILHOST)
        errordict = smtp.sendmail(from_address, to_addresses, msg.as_string())
        for destaddress, sending_error in errordict.items():
            logger.error('Error sending email to %s: %s' % (destaddress, sending_error))
    except smtplib.SMTPException:
        logger.error('Email could not be sent:')
    finally:
        if smtp is not None:
            smtp.close()
