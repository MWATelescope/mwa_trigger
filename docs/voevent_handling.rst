VOEvent Handling
================

The web application listens for VOevents (`Notes on VOEvents <https://voevent.readthedocs.io/en/latest/>`_)
broadcast by the `4pisky network <https://4pisky.org/voevents/>`_ and a few other private networks.
These VOEvents are parsed using :py:meth:`mwa_trigger.parse_xml.parsed_VOEvent` to handle the telescope
dependent formatting and extracting the relevant data to the database.

The VOEvents are grouped into TriggerEvents if they're likely the same source (within 100 seconds and a
separation less than the 95% confidence interval of the two events position errors). This grouping allows
researchers to see all VOEvents for the source (sometimes from multiple telescopes) and will repoint an
observation when required rather than creating a new one.

To decide if a VOEvent is worth observing, the web application has source dependent logic for each type of
source (:ref:`GRBs <grb-logic>`, Flare Stars, GWs and Neutrinos)

Each event is put through this logic for all current :ref:`proposals <proposals>` which have individual
thresholds and observing telescopes.