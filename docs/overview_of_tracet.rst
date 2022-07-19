.. _overview:

Overview of TraceT
==================

The TraceT web app is composed of the following components:

- A service that connects to event brokers, parses the events, and passes them to the :ref:`Trigger Logic Module <trigger_logic>`
- A module which receives the parsed VOEvents and decides if they are worth triggering on. The rules for triggering are called :ref:`Proposals <proposals>` and include rules about the kind of VOEvents to listen for, the conditions under which an event is considered worth observing, and the telescope with which the observations will be made.
- :Ref:`Modules <triggerservice>` which send triggers to either the MWA or ATCA telescope.
- A service which will send sms/email alerts to users to request their input when a trigger decision requires expert input to proceed.
- A database which stores all the received events, the proposals, and a record of which events were triggered and the outcome of the trigger requests


Nomenclature
============

Event
    Typically refers to a **VOEvent** received from one of the brokers. Some of these events are interesting and require action. Some of the events are test events that are ignored. Some of the events are from instruments that are not of interest or report on types of events that are not monitored by any of the observing proposals.

Event Group
    When a transient such as a GRB occurs, and an instrument generates a VOEvent, there will typically be more than just a single event generated. For example, the Swift and Fermi telescopes generate a stream of events which give updated information over time, as new information is collected. These events are linked together using an identifier set by the observing instrument. The TraceT web-app collects all such events together and forms an Event Group. All the Events in a group are used to determine when a trigger should be issued, and are presented together for a user to view.

Trigger
    A request to observe is called a trigger. Triggers can be sent via a range of different methods, depending on the instrument which is receiving the trigger. The MWA and ATCA both provide a web api for receiving triggers, and require authentication via either password or secret key in order for a trigger to be considered. Sending a trigger to an instrument is not an *instruction* to observe but a *request* to observe, and as such this request may be denied.

Proposal
    For the TraceT web-app, a proposal is a set of rules which determine whether an event should generate a trigger. A proposal defines:
        - which alerts are interesting by choosing an instrument and object type combination
        - what conditions need to be satisfied before an alert will be responded to (duration of event, location on sky, etc)
        - which instrument will be triggered if an event meets the above conditions
        - what instrument settings will be used for the trigger (duration of observation, observing project name/credentials, etc)

    See :ref:`Creating a New Proposal <proposals>` for more information.

User
    Someone who has log-in access to the web-app. Other people may be able to view the web site, but only Users can make changes to Proposals and Alert settings, or receive Alerts.

Alert
    In some cases a Proposal will not be able to determine if an event should result in a trigger and expert user intervention is required. In such cases an Alert is sent to a user via email or sms, asking them to log into the web app, review the event, and then approve or reject the observing trigger.



For acronyms and further nomenclature see :ref:`the Glossary <glossary>`.

