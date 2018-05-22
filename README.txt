
VOEvent trigger framework for MWA observations. This repository is made up of:

/README.txt - this file
/setup.py - package file
/trigger.conf.example - sample configuration file
/python_requirements.txt - requirements file to set up a virtual python environment

/mwa_trigger/
    __init__.py - package file
    triggerservice.py - library containing wrapper code to generate a triggered MWA observation.
    handlers.py - library containing classes and functions useful for parsing VOEvents and generating
                  triggers.
    fermi_swift.py - library containing the handler function to parse and trigger on Fermi/Swift VOEvents.

/scripts/
    push_voevent.py - script that takes a VOEvent on standard input and passes it on via RPC call
                      to the voevent_handler.py daemon. The push_voevent.py script is usually called
                      by the 'comet' VOEvent broker when a VOEvent is received, but it can also be
                      called from the command line, for testing.
    voevent_handler.py - This daemon runs continuously once it's started, and accepts VOEvents via RPC call
                         from the push_voevent.py script. These events are queued, and one by one, queued
                         events are passed to a predefined 'handler function' for processing. If a handler
                         function returned False, the next handler function is tried. If a handler
                         returns True, no more handlers are tried for that VOEvent.

To get a trigger handler running, you will need to:

- Copy template.conf.example to mwa_trigger/template.conf (or /usr/local/etc/trigger.conf) and edit
  appropriately. At a minimum, you will need to add a line to the 'auth' section, with the project ID
  code your handler will run as, and the valid secure_key (password) for that project ID. Contact
  Andrew.Williams@curtin.edu.au for a password.


- If the trigger handler will not be running on-site, then in one terminal window, run:

      pyro_nameserver.py

  This will start a Pyro 'Name service' daemon, allowing push_voevent.py to find the network details
  it needs to contact the voevent_handler.py daemon. If the handler is running on site, this step isn't
  necessary because there is already a name service daemon running on the host mwa-db, but you will need to
  change the ns_host line in the [pyro] section of trigger.conf.


- In another terminal window, run:

      python voevent_handler.py

  This will start the daemon that waits for VOEvent messages to be sent to it using Pyro RPC calls, and
  queues them, to pass to a handler function.

  (You may want to use python voevent_handler.py within a virtual environment)


- In a third terminal window, run:

      twistd comet --remote=voevent.4pisky.org -r -v --cmd=./push_voevent.py
                   --local-ivo=ivo://mwa-paul/comet-broker

  That will exit, but leave comet running in the background. The comet broker will call the push_voevent.py
  script when a VOEvent is received. You can run multiple instances of the comet broker at the same time,
  pointing at different higher-level brokers, and all will use push_voevent.py to pass events on to a
  single instance of voevent_handler.py. You may want to use a different IVO or broker.


- You can send a test trigger by doing something like:

      cat trigger.xml | ./push_voevent.py

  That will send an XML structure directly to voevent_handler.py, as if it had been received by the
  comet broker.


Note that the fermi_swift.py library in this code will be running as-is on site, on helios2. If you are
writing your own handler, modify voevent_handler.py to import your library instead of fermi_swift.py,
and change the EVENTHANDLERS global to call processevent() in your library instead.