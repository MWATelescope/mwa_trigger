
VOEvent trigger front end for scheduling MWA observations. This repository is made up of:

/README.txt - this file
/setup.py - package file
/trigger.conf.example - sample configuration file
/python_requirements.txt - requirements file to set up a virtual python environment

/mwa_trigger/
    __init__.py - package file
    triggerservice.py - library containing wrapper code to generate a triggered MWA observation.
    handlers.py - library containing classes and functions useful for parsing VOEvents and generating
                  triggers.
    GRB_fermi_swift.py - library containing the handler function to parse and trigger on Fermi/Swift VOEvents.

/scripts/
    pyro_nameserver.py - simple script to start a Pyro4 Remote Procedure Call (RPC) nameserver running,
                         to allow push_voevent.py to communicate with voevent_handler.py.
    push_voevent.py - script that takes a VOEvent on standard input and passes it on via RPC call
                      to the voevent_handler.py daemon. The push_voevent.py script is usually called
                      by the 'comet' VOEvent broker when a VOEvent is received, but it can also be
                      called from the command line, for testing.
    voevent_handler.py - This daemon runs continuously once it's started, and accepts VOEvents via RPC call
                         from the push_voevent.py script. These events are queued, and one by one, queued
                         events are passed to a predefined 'handler function' for processing. If a handler
                         function returned False, the next handler function is tried. If a handler
                         returns True, no more handlers are tried for that VOEvent.

Software overview:

The triggering system is divided into two parts. The back-end is a web service, on an on-site server, and
part of the telescope Monitor and Control system. It accepts stateless requests from clients, anywhere on
the internet. An entirely separate front end (contained in this repository) parses incoming VOEvents,
makes decisions about when to trigger a new observation (or repoint an existing triggered observation with
a better position), and calls the web service to actually schedule the observations.

Multiple front ends can use the web service - another VOEvent parser running in parallel, real-time code
running on site analysing the data stream in some way, etc.

Separating the science (what VOEvents to trigger on, and why) from the scheduling function lets the
operations team handle the code that directly controls the telescope schedule, while allowing scientists
in the transient science project teams to write their own code to decide which events to follow, and how.

Back-end web service (in the mwa-MandC-Core repository, running on site):

The back-end web service has these functions, called by generating an HTTP request to a particular URL
with a set of parameters:

  - busy() - when given a science project ID code and a desired override time, in seconds from the present,
  return 'True' if that science project is authorised to remove all of the observations already in the
  schedule over that time period.

  - obslist() - when given a desired override time, return a summary of all observations already in the
  schedule over that time period.

  - triggerobs() - The caller supplies a science project ID code, the password associated with that
  project, and a set of observation parameters (described later). If that science project is authorised
  to override all the observations already in the schedule over the requested time period, that period
  in the schedule is cleared, and the requested observation/s are added to the schedule, starting at
  that instant.

  - triggervcs() - like triggerobs, only schedules observations in Voltage Capture mode, if there is
  enough free disk space on the voltage capture servers.

  - triggerbuffer() - If there is a currently scheduled observation in the 'Voltage Buffer' mode, this
  service, when called, sends a signal to the capture processes on each of the VCS computers, causing
  them to immediately dump their memory buffers to disk (150 seconds of data in the current
  configuration), and continue dumping data to disk for the time specified. Note that it can take a
  long time (tens of minutes) for the capture processes to finish dumping their memory buffers and
  'catch up' to real time. After the observing time specified, a VOLTAGE_STOP observation is inserted
  into the schedule, unless the requested observing time extends past an existing VOLTAGE_STOP
  observation.

The back end of the triggering system ONLY cares about the science project code asking for an override,
the science project codes of the observations in the schedule, and the supplied password. Which transient
projects are authorised to override which observing projects is decided by the MWA board and the MWA
director, and encoded in a configuration file maintained by the operations team. There is only one
additional constraint - ongoing voltage capture observations can not be interrupted at the moment, but
this will change in the future.

The triggerbuffer() service uses the existing VOLTAGE_BUFFER observations in the schedule, so does not
take any other observation parameters. For triggerobs() and triggervcs(), there are many observation
parameters that can be passed, to satisfy different science requirements. These include:

  - One or more pointing directions, each specified as an RA/Dec, an Azimuth/Elevation, or a source
  name (from a limited local list of typical targets).

  - Whether to modify the given pointing direction/s to keep the desired target near the primary beam
  centre, but to minimise the power from the Sun by putting it in a primary beam null. This option has
  no affect if the Sun is below the horizon.

  - One or more frequency specifiers, defining the (arbitrary) set of 24 coarse channels to save, out
  of the 256 coarse channels (1.28 MHz wide) defining the 0 - 327.68 MHz total bandwidth. Pointing
  directions and frequency specifiers are multiplied - for example, if two pointing directions are given,
  and three frequency specifiers, then each target direction will be observed at each of the three
  chosen frequency sets.

  - The number of observations to schedule, and the length of each observation. Typically 15 observations
  of 120 seconds each are scheduled. This is because the MWA analogue beamformers do not track sidereal
  motion during a single observation.

  - The correlator averaging parameters to use - frequency resolution (currently 10, 20, or 40 kHz) and
  time resolution (currently 0.5, 1.0 or 2.0 seconds)

  - Whether to schedule calibrator observation/s after the triggered source, and if so, what source to
  calibrate on, and how long the calibrator observation/s should be. The user can also let the system
  choose a calibrator source automatically. If more than one one frequency specifier was given, then
  the calibrator will also be observed at each of the given frequencies.

Latency:

The MWA observing schedule is stored in a set of database tables on a PostgreSQL server on-site, with
start and stop times stored as the number of seconds since the GPS epoch ('GPS seconds'). All
observations must start and stop on an integer multiple of eight GPS seconds, so while an observation
in progress can be truncated by changing it's stop time, the modulo 8 seconds constraint gives a natural
latency of up to 8 seconds. In practice, the Monitor and Control system gives the various components of
the telescope time to prepare, by sending their new configuration a few seconds ahead of the start of
each observation. This means that a running observation cannot have its stop time changed to a value less
than four seconds in the future, and a new observation can't be scheduled to start less than 4 seconds
in the future. Including other processing delays, this gives a latency period of 8-16 seconds between
the trigger time and the start
of a triggered observation.



To get a trigger handler running, you will need to:

- Copy trigger.conf.example to mwa_trigger/trigger.conf (or /usr/local/etc/trigger.conf) and edit
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


- If you want to respond to actual broadcast VOEvents (as opposed to manually pushing VOEvent XML
  files for testing), then, in a third terminal window, run:

      twistd comet --remote=voevent.4pisky.org -r -v --cmd=./push_voevent.py
                   --local-ivo=ivo://mwa-paul/comet-broker

  That will exit, but leave comet running in the background. The comet broker will call the push_voevent.py
  script when a VOEvent is received. You can run multiple instances of the comet broker at the same time,
  pointing at different higher-level brokers, and all will use push_voevent.py to pass events on to a
  single instance of voevent_handler.py. You may want to use a different IVO or broker.

  If you are only pushing static XML files for testing, you won't need the Twisted or Comet packages
  installed.


- You can send a test trigger by doing something like:

      cat trigger.xml | ./push_voevent.py

  That will send an XML structure directly to voevent_handler.py, as if it had been received by the
  comet broker.


Note that the GRB_fermi_swift.py library in this code will be running as-is on site, on helios2. If you are
writing your own handler, modify voevent_handler.py to import your library instead of fermi_swift.py,
and change the EVENTHANDLERS global to call processevent() in your library instead.