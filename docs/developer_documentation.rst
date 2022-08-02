Web Application Software Layout
===============================

The TraceT repository consists of a Django web application and a python module named tracet.

The :ref:`tracet python module <parse_xml>` is kept separate from the web application to make them easy to install for other applications.
For example, the :ref:`parsed_VOEvent class <parsed_VOEvent>` can be used to parse VOEvent XML files and packets.

The web application is Django based with a single app called trigger_app and uses Postgres for the database.


How Events are input
====================

TraceT currently uses a single event broker, but more can easily be added.
The twistd_comet_wrapper.py should always be :ref:`running <start_server>`, and its status can be seen on the homepage.
The twistd comet broker listens for VOEvents, and each time it receives one, it uses upload_xml.py to :ref:`parsed the event <parsed_VOEvent>` and upload it to the Event model.


How Events are Handled
======================

Every time an event is added to the database (see above), this signals the group_trigger function in webapp_tracet/trigger_app/signals.py.
This will group events by their trig_id and then loop over the ProposalSettings model objects to see if any proposals want to observe this type of object.
If a proposal is interesting in the event, it is put through the :ref:`trigger_logic` and will use
webapp_tracet/trigger_app/telescope_observe.py to trigger observations and send alerts based on the UserAlerts models.