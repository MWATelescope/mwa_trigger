#!/usr/bin/env python

"""Takes the XML for a VO event on standard input, and passes it on to the running
   voevent_handler process, where it will be queued and processed.

   This command will be called by the COMET event broker as each incoming XML packet
   is received, and may be called two or more times in parallel if packets arrive at
   nearly the same time.

   It can also be called manually for testing, eg:

   cat test.xml | ./push_voevent.py
"""

import ConfigParser
import datetime
import logging
import os
import pwd
import sys
import traceback
import warnings


############### set up the logging before importing Pyro4
class MWALogFormatter(object):
    """
    Add a time string to the start of any log messages sent to the log file.
    """
    def format(self, record):
        return "%s: %s" % (datetime.datetime.utcnow().isoformat(), record.getMessage())


LOGLEVEL_LOGFILE = logging.DEBUG      # Logging level for logfile

# Make the log file name include the username, to avoid permission errors
LOGFILE = "/var/log/mwa/push_voevent-%s.log" % pwd.getpwuid(os.getuid()).pw_name

formatter = MWALogFormatter()

filehandler = logging.FileHandler(LOGFILE)
filehandler.setLevel(LOGLEVEL_LOGFILE)
filehandler.setFormatter(formatter)

DEFAULTLOGGER = logging.getLogger('push_voevent')
DEFAULTLOGGER.setLevel(logging.DEBUG)
DEFAULTLOGGER.addHandler(filehandler)

import Pyro4

CPPATH = ['/usr/local/etc/trigger.conf', './trigger.conf']   # Path list to look for configuration file


############## Point to a running Pyro nameserver #####################
# If not on site, start one before running this code, using pyro_nameserver.py
CP = ConfigParser.SafeConfigParser()
CP.read(CPPATH)

if CP.has_option(section='pyro', option='ns_host'):
    Pyro4.config.NS_HOST = CP.get(section='pyro', option='ns_host')
else:
    Pyro4.config.NS_HOST = 'localhost'

if CP.has_option(section='pyro', option='ns_port'):
    Pyro4.config.NS_PORT = int(CP.get(section='pyro', option='ns_port'))
else:
    Pyro4.config.NS_PORT = 9090

if Pyro4.config.NS_HOST in ['helios', 'mwa-db']:
    Pyro4.config.SERIALIZER = 'pickle'   # We must be on site, where we have an ancient Pyro4 install and nameserver running

Pyro4.config.COMMTIMEOUT = 10.0

sys.excepthook = Pyro4.util.excepthook

warnings.simplefilter('ignore', UserWarning)


def initPyro(logger=DEFAULTLOGGER):
    """
    Create a proxy object for the VOEventHandler, to call methods on remotely.

    :param logger: An optional logging.Logger object to use to log messages from the Pyro4 proxy
    """
    logger.debug("Locating Pyro nameserver")
    ns = Pyro4.locateNS(host='helios', broadcast=False)
    logger.debug("Found Pyro nameserver")
    uri = ns.lookup('VOEventHandler')
    logger.debug("Looked up VOEventHandler uri")
    client = Pyro4.Proxy(uri)
    logger.debug("Created Pyro client")
    with client:
        client.ping()   # Make sure the remote server is alive
        logger.debug('Pyro ping() succeeded!')
    return client


def PyroTransmit(event='', logger=DEFAULTLOGGER):
    """
    Send an XML string to the remote VOEventHandler for processing.

    :param event: string containing VOEvent XML
    :param logger: An optional logging.Logger object to use to log messages from the Pyro4 proxy
    """
    try:
        client = initPyro()   # Create a client proxy object
    except Pyro4.errors.PyroError:
        logger.exception('Exception in initPyro()')
        return False

    try:
        with client:
            logger.debug('Transmitting event to the handler via Pyro')
            client.putEvent(event=event)   # Send the XML
    except (Pyro4.errors.ConnectionClosedError, Pyro4.errors.TimeoutError, Pyro4.errors.ProtocolError):
        logger.error('Communication exception in PyroTransmit')
        return False
    except Pyro4.errors.PyroError:
        logger.error('Other exception in PyroTransmitLoop: %s', traceback.format_exc())
        return False

    return True


if __name__ == '__main__':
    event = sys.stdin.read()
    success = PyroTransmit(event)
    if success:
        sys.exit(0)
    else:
        sys.exit(-1)
