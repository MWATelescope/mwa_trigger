Creating a New User
===================

Create a User
-------------
Use `this page <http://tracet.duckdns.org/admin/auth/user/add/>`_ to make a new user.
You can give them a generic password that they can change later. If you would like
to make them an admin you can edit the user and under permissions, click the staff
status checkbox.


Update Alert Permissions
------------------------
By default, all users will have permission to receive trigger alerts and
will not have permission to receive pending and debug alerts for all
proposals. As an admin, you can give the user permission to receive debug
and pending alerts if you trust them to decide if a VOEvent should be
triggered or not. Use the
`Alert Permissions <http://tracet.duckdns.org/admin/trigger_app/alertpermission/>`_
page to edit these permissions.

Notify the User to Add Alerts
-----------------------------
All users have proposal specific alert settings, so to receive an alert for
your proposal, all users must update their alerts on the
`User Alert Control  <http://tracet.duckdns.org/user_alert_status/>`_ page.
Users can set multiple alert types per proposal (e.g. email and SMS) and
per alert type (trigger, pending and debug).
It is recommended that users set a phone call alert type for pending alerts
to assure the pending decision is promptly investigated.

Verifying Your Phone Number on Twilio
-------------------------------------
Since we use the free version of Twilio, we need to verify a number on Twilio before it can send an SMS or call.
You will need to contact the admin that has access to the Twilio account so they can do this for you.
`Here <https://support.twilio.com/hc/en-us/articles/223180048-Adding-a-Verified-Phone-Number-or-Caller-ID-with-Twilio>`_ is a guide on how to verify a phone number on Twilio.