# VOEvent trigger front end for scheduling MWA observations.

## Credit
This repository was developed for use on the MWA telescope by Andrew Williams with contributions from Paul Hancock.
The triggering logic for individual handlers were developed by various project groups - see the `__author__` fields in the scripts in the `tracet/` directory.

If you use this code to generate observations for your research please cite the description paper [Hancock et al, 2019](https://ui.adsabs.harvard.edu/abs/2019PASA...36...46H/abstract), and [Anderson et al, 2021](https://ui.adsabs.harvard.edu/abs/2021PASA...38...26A/abstract)

## Contents

This repository is made up of the `tracet` python moudle and the `webapp_tracet`.

### tracet
This module contains useful functions such as:

```
parse_xml.py - parses a variety of xml files and puts all the relivent data into a standard class.

trigger_logic.py - decided if the parsed xml is worth observing with several methods.

triggerservice.py - calls the web service to schedule observations with the MWA and ATCA telescopes.
```
The full documentation can be found [here](https://tracet.readthedocs.io/en/latest/)

### Trigger webapp
A web application that can automatically monitor for VOEvents and trigger observations based on the parameters the user has set. How to install and use the web app is explained in webapp_tracet/README.md.

## Latency

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
