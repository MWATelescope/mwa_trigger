Event Handling
================

The web application listens for events such as VOevents (`Notes on VOEvents <https://voevent.readthedocs.io/en/latest/>`_)
broadcast by the `4pisky network <https://4pisky.org/voevents/>`_ and a few other private networks.
These VOEvents are parsed using :py:meth:`tracet.parse_xml.parsed_VOEvent` to handle the telescope
dependent formatting and extracting the relevant data to the database.

The VOEvents are grouped into Event Groups if they have the same Trig ID which is an identifier the source telescope provides.
This grouping allows researchers to see VOEvents from the same source for a telescope and will repoint an
observation when required rather than creating a new one.

To decide if a event is worth observing, the web application has source dependent logic for each type of
source (:ref:`GRBs <grb-logic>`, Flare Stars, GWs and Neutrinos)

Each event is put through this logic for all current :ref:`proposals <proposals>` which have individual
thresholds and observing telescopes.