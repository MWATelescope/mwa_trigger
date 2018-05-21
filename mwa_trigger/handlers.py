#! python

"""
Library containing one or more functions to process incoming VOEvent XML strings. This library will
be imported by a long running process, so you can load large data files, etc, at import time, rather than
inside the processevent() function, to save time.
"""

__version__ = "0.3"
__author__ = ["Paul Hancock", "Andrew Williams", "Gemma Anderson"]

import ConfigParser
import os
import traceback

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import Encoders
import logging

import astropy
from astropy.coordinates import SkyCoord, EarthLocation
from astropy.time import Time

import triggerservice

log = logging.getLogger('voevent.handlers')  # Inherit the logging setup from voevent_handler.py

# Settings
HORIZON_LIMIT = 30  # Don't observe if the source is below this elevation
FERMI_POBABILITY_THRESHOLD = 50  # Trigger on Fermi events that have most-likely-prob > this number


CPPATH = ['/usr/local/etc/trigger.conf', './trigger.conf']   # Path list to look for configuration file
CP = ConfigParser.SafeConfigParser()
CP.read(CPPATH)

if CP.has_option(section='mail', option='mailhost'):
    MAILHOST = CP.get(section='mail', option='mailhost')
else:
    MAILHOST = 'cerberus'    # Using cerberus will only work for computers inside the MWA network, on-site.

# position of the observer
MWAPOS = EarthLocation.from_geodetic(lon="116:40:14.93",
                                     lat="-26:42:11.95",
                                     height=377.8)


class TriggerEvent(object):
    def __init__(self, event=None, logger=log):
        self.ra = []  # a list of all the position ra/dec/errs
        self.dec = []
        self.err = []
        self.triggered = False  # True if this event has ever been triggered
        self.trigger_id = ''  # the id for this event as it appears in the observing schedule
        self.events = []  # a list of all the voevents
        self.first_trig_time = None  # when was the TriggerEvent first triggered
        self.last_trig_type = None
        self.loglist = []
        self.logger = logger

        self.info('Event created')
        self.add_event(event)

    def add_event(self, event):
        """For storing a list of all VOEvents associated with this TriggerEvent"""
        if event is not None:
            self.info('New VOEvent added')
            self.events.append(event)

    def trigger(self, time, ttype):
        self.triggered = True
        # This is the *first* trigger time so only update it once
        if self.first_trig_time is None:
            self.info('First trigger sent')
            self.first_trig_time = time
        else:
            self.info('Subsequent trigger sent')
        self.last_trig_type = ttype

    def add_pos(self, pos):
        ra, dec, err = pos
        self.ra.append(ra)
        self.dec.append(dec)
        self.err.append(err)
        self.info('Position added')

    def get_pos(self, index=-1):
        if len(self.ra) < abs(index):
            return None, None, None
        return self.ra[index], self.dec[index], self.err[index]

    def trigger_observation(self, obsname='Trigger_test', time_min=30, project_id="", secure_key=""):
        """
        Tell the MWA to observe the target of interest - override this method in your handler as desired if you
        want some other observation parameters.

        :param obsname: Arbitrary string for the name of the observation in the schedule.
        :param time_min: Total length of observation time, in minutes.
        :param project_id: The project ID requesting the triggered observation
        :param secure_key: The password specific to that project ID
        :return: The full results dictionary returned by the triggerservice API (see triggerservice.trigger)
        """
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

        # how many observations are required
        nobs = int(time_min // 2)
        # trigger if we are above the horizon limit
        if alt > HORIZON_LIMIT:
            self.info("Triggering at gps time %d ..." % (t.gps,))
            result = triggerservice.trigger(project_id=project_id, secure_key=secure_key, ra=ra, dec=dec,
                                            creator='VOEvent_Auto_Trigger_{0}'.format(__version__), obsname=obsname,
                                            pretend=False,
                                            freqspecs='145,24', nobs=nobs, avoidsun=True, inttime=0.5, freqres=10,
                                            exptime=120, calibrator=True, calexptime=120)
            self.debug("Response: {0}".format(result))
            return result
        else:
            self.debug("not triggering due to horizon limit: alt {0} < {1}".format(alt, HORIZON_LIMIT))
            return

    def log(self, level=logging.DEBUG, msg=''):
        self.logger.log(level=level, msg=msg)
        self.loglist.append(msg)

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
                            -mimetype is the type string, eg 'file/text'
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
            filename, payload, mimetype = attachspec
            if mimetype:
                mimemain, mimesub = mimetype.split('/')
            else:
                mimemain = 'application'
                mimesub = 'octet-stream'
        except ValueError:
            logger.error('attachments must be a tuple of (filename, payload, mimetype), where payload is the file contents.')
            return False

        part = MIMEBase(mimemain, mimesub)
        part.set_payload(payload)
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(filename))
        msg.attach(part)

    smtp = None
    try:
        smtp = smtplib.SMTP(MAILHOST)
        errordict = smtp.sendmail(from_address, to_addresses, msg.as_string())
        for destaddress, sending_error in errordict.items():
            logger.error('Error sending email to %s: %s' % (destaddress, sending_error))
    except smtplib.SMTPException:
        logger.error('Email could not be sent: %s' % traceback.format_exc())
    finally:
        if smtp is not None:
            smtp.close()
