#!/usr/bin/env python

"""
This scripts starts a Pyro4 RPC nameserver daemon, which other processes can use to register a network
RPC service, or for a client to find a registered network service.
"""

import ConfigParser

import Pyro4
from Pyro4 import naming

CPPATH = ['/usr/local/etc/trigger.conf', './trigger.conf']   # Path list to look for configuration file


if __name__ == '__main__':
    CP = ConfigParser.SafeConfigParser()
    CP.read(CPPATH)

    if CP.has_option(section='pyro', option='ns_host'):
        ns_host = CP.get(section='default', option='ns_host')
    else:
        ns_host = 'localhost'

    if CP.has_option(section='pyro', option='ns_port'):
        ns_port = int(CP.get(section='default', option='ns_port'))
    else:
        ns_port = 9090

    print "Pyro4 nameserver started."
    Pyro4.naming.startNSloop(host=ns_host, port=ns_port, enableBroadcast=False)
