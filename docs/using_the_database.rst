Using the database
==================


Uploading a VOEvent
------------------------
You can use the `testing <https://mwa-trigger.duckdns.org/test_upload_xml/>`_ page of TraceT to upload a VOEvent XML file.
This can be used to test the web app (see if tracet behaves the way you expect)
or to trigger an observation (often due to something going wrong and your want to manually trigger an observation).

The uploaded XML file will be treated as a real event so if you do NOT want to trigger observations, ensure that all proposals are in testing mode .

You can copy and paste the contents of an XML file into the text box and edit its RA and Dec to ensure it's above the horizon.
You should also change the group event ID (normally labelled as TrigID), so TraceT knows to treat it as a new event group.