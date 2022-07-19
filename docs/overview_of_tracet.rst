.. _overview:

Overview of TraceT
==================

The TraceT web app is composed of the following components:

- A service that connects to event brokers, parses the events, and passes them to the :ref:`Trigger Logic Module <trigger_logic>`
- A module which receives the parsed VOEvents and decides if they are worth triggering on. The rules for triggering are called :ref:`Proposals <proposals>` and include rules about the kind of VOEvents to listen for, the conditions under which an event is considered worth observing, and the telescope with which the observations will be made.
- :Ref:`Modules <triggerservice>` which send triggers to either the MWA or ATCA telescope.
- A service which will send sms/email alerts to users to request their input when a trigger decision requires expert input to proceed.
- A database which stores all the received events, the proposals, and a record of which events were triggered and the outcome of the trigger requests
