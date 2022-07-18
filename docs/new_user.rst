Creating a New User
===================

Create a User
-------------
Use `this page <http://mwa-trigger.duckdns.org/admin/auth/user/add/>`_ to make a new user.
You can give them a generic password that they can change later. If you would like
to make them an admin you can edit the user and under permissions, click the staff
status checkbox.


Update Admin Alerts
-------------------
By default, all users will have permission to receive trigger alerts and
will not have permission to receive pending and debug alerts for all
proposals. As an admin, you can give the user permission to receive debug
and pending alerts if you trust them to decide if a VOEvent should be
triggered or not. Use the
`Admin Alert Control <http://mwa-trigger.duckdns.org/admin/trigger_app/adminalerts/>`_
page to edit these permissions.

Notify the User to Add Alerts
-----------------------------
All users have proposal specific alert settings, so to receive an alert for
your proposal, all users must update their alerts on the
`User Alert Control  <http://mwa-trigger.duckdns.org/user_alert_status/>`_ page.
Users can set multiple alert types per proposal (e.g. email and SMS) and
per alert type (trigger, pending and debug).
It is recommended that users set a phone call alert type for pending alerts
to assure the pending decision is promptly investigated.