.. _proposals:

Creating a New Proposal
=======================

This web application is designed to handle several science
cases using several telescopes at once through "proposals". Your project
may have several proposals. For example, if you want to observe GRBs from
SWIFT with the MWA and ATCA, you will need to make two proposals. One
observes GRBs from SWIFT with the MWA, and another observes GRBs with ATCA.


Step 1: Creating the Proposal
-----------------------------

Admin users can create and edit proposals in the
`Edit Proposal Settings <https://mwa-trigger.duckdns.org/proposal_create/>`_
page. Each item has a description which should be sufficient to set up your proposal.


Step 2: Check the Flowchart
---------------------------

Once you've created a proposal, you should check the flowchart to confirm
that the trigger logic is what you require for your science case and telescope
allocation. To view your proposal's flowchart, click the "View Flow Diagram"
button for your proposal in the "Current Proposal Settings (Summarised)" table
on the home page. You can always edit your settings and thresholds if this is
not what you require.

Step 3: Update Alert Permissions
--------------------------------
By default, all users will have permission to receive trigger alerts and
will not have permission to receive pending and debug alerts for all
proposals. As an admin, you can give users you trust permission to receive debug
and pending alerts and decide if a VOEvent should be triggered on or not. Use the
`Alert Pemission <https://mwa-trigger.duckdns.org/admin/trigger_app/alertpermission/>`_
page to edit these permissions.

Step 4: Notify Users to Update their Alerts
-------------------------------------------
All users have proposal specific alert settings, so to receive an alert for
your proposal, all users must update their alerts on the
`User Alert Control  <https://mwa-trigger.duckdns.org/user_alert_status/>`_ page.
Users can set multiple alert types per proposal (e.g. email and SMS) and
per alert type (trigger, pending and debug).
It is recommended that users set a phone call alert type for pending alerts
to assure the pending decision is promptly investigated.



