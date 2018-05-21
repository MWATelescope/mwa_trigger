#!/usr/bin/env python

"""Takes the XML for a VO event on standard input, and passes it on to the running
   voevent_handler process, where it will be queued and processed.

   This command will be called by the COMET event broker as each incoming XML packet
   is received, and may be called two or more times in parallel if packets arrive at
   nearly the same time.
"""

import logging
import sys
import traceback
import warnings

import Pyro4

logging.basicConfig()
DEFAULTLOGGER = logging.getLogger()

Pyro4.config.NS_HOST = 'localhost'
Pyro4.config.NS_PORT = 9090
# Pyro4.config.SERIALIZER = 'pickle'   # TODO - uncomment this on site, where we have an ancient Pyro4 install
Pyro4.config.COMMTIMEOUT = 10.0

sys.excepthook = Pyro4.util.excepthook

warnings.simplefilter('ignore', UserWarning)


def initPyro(logger=DEFAULTLOGGER):
  """Create a proxy object for the VOEventHandler, to call methods on remotely.
  """
  logger.debug("Creating client object to connect to voevent_handler")
  ns = Pyro4.locateNS()
  uri = ns.lookup('VOEventHandler')
  client = Pyro4.Proxy(uri)
  with client:
    client.ping()   # Make sure the remote server is alive
    logger.debug('Pyro ping() succeeded!')
  return client


def PyroTransmit(event='', logger=DEFAULTLOGGER):
  """Send an XML string to the remote VOEventHandler for processing.
  """
  try:
    client = initPyro()   # Create a client proxy object
  except:
    logger.exception('Exception in initPyro()')
    return False

  try:
    with client:
      logger.debug('Transmitting event to the handler via Pyro')
      client.putEvent(event=event)   # Send the XML
  except (Pyro4.errors.ConnectionClosedError, Pyro4.errors.TimeoutError, Pyro4.errors.ProtocolError):
    logger.error('Communication exception in PyroTransmit')
    return False
  except:
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
