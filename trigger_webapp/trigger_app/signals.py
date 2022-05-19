from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from .models import UserAlerts, AdminAlerts, VOEvent, PossibleEventAssociation, Status, ProposalSettings, ProposalDecision, Observations, TriggerID
from .telescope_observe import trigger_observation

from mwa_trigger.trigger_logic import worth_observing_grb

import os
from twilio.rest import Client
import datetime
from astropy import units as u
from astropy.coordinates import SkyCoord
import numpy as np
from scipy.stats import norm

import logging
logger = logging.getLogger(__name__)

account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', None)


@receiver(post_save, sender=VOEvent)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest VOEvent has already been observered or if it is new and update the models accordingly
    """
    # instance is the new VOEvent
    if instance.ignored:
        # VOEvent ignored so do nothing
        return

    event_coord = SkyCoord(ra=instance.ra*u.degree, dec=instance.dec*u.degree)

    # ------------------------------------------------------------------------------
    # Look for other events with the same Trigger ID
    # ------------------------------------------------------------------------------
    trigger_id_filter = TriggerID.objects.filter(trigger_id=instance.trigger_id)
    if trigger_id_filter.exists():
        trigger_id = TriggerID.objects.get(trigger_id=instance.trigger_id)
        # Trigger event already exists so link the VOEvent (have to update this way to prevent save() triggering this function again)
        VOEvent.objects.filter(id=instance.id).update(trigger_group_id=trigger_id)

        # Loop over all proposals settings and see if it's worth reobserving
        proposal_decisions = ProposalDecision.objects.filter(trigger_group_id=trigger_id)
        for prop_dec in proposal_decisions:
            if prop_dec.decision == "I":
                # Previous events were ignored, check if this new one is up to our standards
                # Update pos
                prop_dec.ra = instance.ra
                prop_dec.dec = instance.dec
                prop_dec.ra_hms = instance.ra_hms
                prop_dec.dec_dms = instance.dec_dms
                prop_dec.pos_error = instance.pos_error
                proposal_worth_observing(
                    prop_dec,
                    instance,
                    trigger_message=f"{prop_dec.decision_reason}Checking new VOEvent.\n ",
                )
            elif prop_dec.decision == "T":
                # Check new event position is further away than the repointing limit
                old_event_coord = SkyCoord(ra=prop_dec.ra*u.degree, dec=prop_dec.dec*u.degree)
                event_sep = event_coord.separation(old_event_coord ).deg
                if event_sep > prop_dec.proposal.repointing_limit:
                    # worth repointing
                    # Update pos
                    prop_dec.ra = instance.ra
                    prop_dec.dec = instance.dec
                    prop_dec.ra_hms = instance.ra_hms
                    prop_dec.dec_dms = instance.dec_dms
                    prop_dec.pos_error = instance.pos_error
                    repoint_message = f"Repointing because seperation ({event_sep} deg) is greater than the repointing limit ({prop_dec.proposal.repointing_limit} deg)."
                    proposal_worth_observing(
                        prop_dec,
                        instance,
                        observation_reason=repoint_message,
                        trigger_message=f"{prop_dec.decision_reason}{repoint_message}\n "
                    )

        # TODO update the PossibleEventAssociation ra and dec if the position is better.
        # Update latest_event_observed
        trigger_id.latest_event_observed = instance.event_observed
        trigger_id.save()

    else:
        # Make a new trigger group ID
        new_trig = TriggerID.objects.create(
            trigger_id=instance.trigger_id,
            ra=instance.ra,
            dec=instance.dec,
            ra_hms=instance.ra_hms,
            dec_dms=instance.dec_dms,
            pos_error=instance.pos_error,
            source_type=instance.source_type,
            earliest_event_observed=instance.event_observed,
            latest_event_observed=instance.event_observed,
        )
        # Link the VOEvent (have to update this way to prevent save() triggering this function again)
        VOEvent.objects.filter(id=instance.id).update(trigger_group_id=new_trig)

        # Loop over settings
        proposal_settings = ProposalSettings.objects.all()
        for prop_set in proposal_settings:
            # Create a ProposalDecision object to record what each proposal does
            prop_dec = ProposalDecision.objects.create(
                #decision=decision,
                #decision_reason=trigger_message,
                proposal=prop_set,
                trigger_group_id=new_trig,
                trigger_id=instance.trigger_id,
                duration=instance.duration,
                ra=instance.ra,
                dec=instance.dec,
                ra_hms=instance.ra_hms,
                dec_dms=instance.dec_dms,
                pos_error=instance.pos_error,
            )
            # Check if it's worth triggering an obs
            proposal_worth_observing(prop_dec, instance)

    # ------------------------------------------------------------------------------
    # Look for associated events (in time and space) which includes other telescopes
    # ------------------------------------------------------------------------------

    # Time range to considered the same event (in seconds)
    dt = 100
    early_dt = instance.event_observed - datetime.timedelta(seconds=dt)
    late_dt = instance.event_observed + datetime.timedelta(seconds=dt)

    # Check if the VOEvent was observed after the earliest event observed - 100s
    #                               and before the latest  event observed + 100s
    association_exists = False
    poss_events = PossibleEventAssociation.objects.filter(earliest_event_observed__lt=late_dt,
                                                      latest_event_observed__gt=early_dt)
    if poss_events.exists():
        for trig_event in poss_events:
            # Calculate 95% confidence interval seperation
            combined_err = np.sqrt(instance.pos_error**2 + trig_event.pos_error**2)
            c95_sep = norm.interval(0.95, scale=combined_err)[1]

            # Now make sure they're spacially similar
            trigger_coord = SkyCoord(ra=trig_event.ra*u.degree, dec=trig_event.dec*u.degree)
            if event_coord.separation(trigger_coord).deg < c95_sep:
                # Event is within the 95% confidence interval so consider them the same source/event
                association_exists = True
                prev_trig = trig_event

    if association_exists:
        # Trigger event already exists so link the VOEvent (have to update this way to prevent save() triggering this function again)
        VOEvent.objects.filter(id=instance.id).update(associated_event_id=prev_trig)

        # TODO update the PossibleEventAssociation ra and dec if the position is better.
        # Update latest_event_observed
        for trig_event in poss_events:
            trig_event.latest_event_observed = instance.event_observed
            trig_event.save()

    else:
        # Make a new trigger event
        new_trig = PossibleEventAssociation.objects.create(
            ra=instance.ra,
            dec=instance.dec,
            ra_hms=instance.ra_hms,
            dec_dms=instance.dec_dms,
            pos_error=instance.pos_error,
            source_type=instance.source_type,
            earliest_event_observed=instance.event_observed,
            latest_event_observed=instance.event_observed,
        )
        # Link the VOEvent (have to update this way to prevent save() triggering this function again)
        VOEvent.objects.filter(id=instance.id).update(associated_event_id=new_trig)


def proposal_worth_observing(
        prop_dec,
        voevent,
        trigger_message="",
        observation_reason="First observation."
    ):
    """For a proposal sees is this voevent is worth observing. If it is will trigger an observation and send off the relevant alerts.

    Parameters
    ----------
    prop_dec : `django.db.models.Model`
        The Django ProposalDecision model object.
    voevent : `django.db.models.Model`
        The Django VOEvent model object.
    trigger_message : `str`, optional
        A log of all the decisions made so far so a user can understand why the source was(n't) observed. Default: "".
    observation_reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".
    """

    # Defaults if not worth observing
    trigger_bool = debug_bool = pending_bool = False

    if prop_dec.proposal.event_telescope is None or str(prop_dec.proposal.event_telescope).strip() == voevent.telescope.strip():
        # This project observes events from this telescope

        # Check if this proposal thinks this event is worth observing
        proj_source_bool = False
        if prop_dec.proposal.source_type == "GRB" and voevent.source_type == "GRB":
            # This proposal wants to observe GRBs so check if it is worth observing
            trigger_bool, debug_bool, pending_bool, trigger_message = worth_observing_grb(
                # event values
                trig_duration=voevent.duration,
                fermi_most_likely_index=voevent.fermi_most_likely_index,
                fermi_detection_prob=voevent.fermi_detection_prob,
                swift_rate_signif=voevent.swift_rate_signif,
                # Thresholds
                trig_min_duration=prop_dec.proposal.trig_min_duration,
                trig_max_duration=prop_dec.proposal.trig_max_duration,
                pending_min_duration_1=prop_dec.proposal.pending_min_duration_1,
                pending_max_duration_1=prop_dec.proposal.pending_max_duration_1,
                pending_min_duration_2=prop_dec.proposal.pending_min_duration_2,
                pending_max_duration_2=prop_dec.proposal.pending_max_duration_2,
                fermi_min_detection_prob=prop_dec.proposal.fermi_prob,
                swift_min_rate_signif=prop_dec.proposal.swift_rate_signf,
                # Other
                trigger_message=trigger_message,
            )
            proj_source_bool = True
        # TODO set up other source types here

        if not proj_source_bool:
            # Proposal does not observe this type of source so update message
            trigger_message += f"This proposal does not observe {voevent.get_source_type_display()}s.\n "
    else:
        # Proposal does not observe event from this telescope so update message
        trigger_message += f"This proposal does not trigger on events from {voevent.telescope}.\n "

    if trigger_bool:
        # Check if you can observe and if so send off the observation
        decision, trigger_message = trigger_observation(
            prop_dec,
            trigger_message,
            reason=observation_reason,
        )
        if decision == 'E':
            # Error observing so send off debug
            debug_bool = True
    elif pending_bool:
        # Send off a pending decision
        decision = 'P'
    else:
        decision = 'I'

    # Update proposal decision and log
    prop_dec.decision = decision
    prop_dec.decision_reason = trigger_message
    prop_dec.save()

    # TODO do something smart with these results to decide which telescope to observe with
    # but hopefully the proposal settings will describe if you want to observe or not.

    # send off alert messages to users and admins
    send_all_alerts(trigger_bool, debug_bool, pending_bool, prop_dec)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, proposal_decision_model):
    """
    """
    # Work out all the telescopes that observed the event
    voevents = VOEvent.objects.filter(trigger_group_id=proposal_decision_model.trigger_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ", ".join(list(set(telescopes)))

    # Get all admin alert permissions for this project
    admin_alerts = AdminAlerts.objects.filter(proposal=proposal_decision_model.proposal)
    for aa in admin_alerts:
        # Grab user
        user = aa.user
        user_alerts = UserAlerts.objects.filter(user=user, proposal=proposal_decision_model.proposal)

        # Send off the alerts of types user defined
        for ua in user_alerts:
            # Check if user can recieve each type of alert
            # Trigger alert
            if aa.alert and ua.alert and trigger_bool:
                subject = f"Trigger Web App Observation {proposal_decision_model.id}"
                message_type_text = f"The trigger web service scheduled the following {proposal_decision_model.proposal.telescope} observations:\n"
                # Send links for each observation
                obs = Observations.objects.filter(proposal_decision_id=proposal_decision_model)
                for ob in obs:
                    message_type_text += f"{ob.website_link}\n"
                send_alert_type(ua.type, ua.address, subject, message_type_text, proposal_decision_model, telescopes)

            # Debug Alert
            if aa.debug and ua.debug and debug_bool:
                subject = f"Trigger Web App Debug {proposal_decision_model.id}"
                message_type_text = f"This is a debug notification from the trigger web service."
                send_alert_type(ua.type, ua.address, subject, message_type_text, proposal_decision_model, telescopes)

            # Pending Alert
            if aa.approval and ua.approval and pending_bool:
                subject = f"PENDING Trigger Web App {proposal_decision_model.id}"
                message_type_text = f"HUMAN INTERVENTION REQUIRED! The trigger web service is unsure about the following event."
                send_alert_type(ua.type, ua.address, subject, message_type_text, proposal_decision_model, telescopes)

def send_alert_type(alert_type, address, subject, message_type_text, proposal_decision_model, telescopes):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    # Set up message text
    message_text = f"""{message_type_text}

Event Details are:
Duration:    {proposal_decision_model.duration}
RA:          {proposal_decision_model.ra_hms} hours
Dec:         {proposal_decision_model.dec_dms} deg
Error Rad:   {proposal_decision_model.pos_error} deg
Detected by: {telescopes}

Decision log:
{proposal_decision_model.decision_reason}

Proposal decision can be seen here:
http://127.0.0.1:8000/proposal_decision_details/{proposal_decision_model.id}/
"""

    if alert_type == 0:
        # Send an email
        send_mail(
            subject,
            message_text,
            settings.EMAIL_HOST_USER,
            [address],
            #fail_silently=False,
        )
    elif alert_type == 1:
        # Send an SMS
        message = client.messages.create(
                    to=address,
                    from_='+17755216557',
                    body=message_text,
        )
    elif alert_type == 2:
        # Make a call
        call = client.calls.create(
                    url='http://demo.twilio.com/docs/voice.xml',
                    to=address,
                    from_='+17755216557',
        )


@receiver(post_save, sender=User)
def create_admin_alerts_proposal(sender, instance, **kwargs):
    if kwargs.get('created'):
        # Create an admin alert for each proposal
        proposal_settings = ProposalSettings.objects.all()
        for prop_set in proposal_settings:
            s = AdminAlerts(user=instance, proposal=prop_set)
            s.save()


@receiver(post_save, sender=ProposalSettings)
def create_admin_alerts_user(sender, instance, **kwargs):
    if kwargs.get('created'):
        # Create an admin alert for each user
        users = User.objects.all()
        for user in users:
            s = AdminAlerts(user=user, proposal=instance)
            s.save()


def on_startup(sender, **kwargs):
    # Create a twistd comet status object and set it to stopped until the twistd_comet_wrapper.py is called
    if Status.objects.filter(name='twistd_comet').exists():
        Status.objects.filter(name='twistd_comet').update(status=2)
    else:
        Status.objects.create(name='twistd_comet', status=2)


# Getting a signal from views.py which indicates that the server has started
startup_signal = Signal()
# Run twistd startup function
startup_signal.connect(on_startup, dispatch_uid='models-startup')