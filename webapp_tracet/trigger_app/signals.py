from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from pyparsing import MutableMapping

from .models import UserAlerts, AlertPermission, Event, Status, ProposalSettings, ProposalDecision, Observations, EventGroup
from .telescope_observe import trigger_observation
from operator import itemgetter
from tracet.trigger_logic import worth_observing_grb, worth_observing_nu, worth_observing_gw

import os
from twilio.rest import Client
import datetime
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import numpy as np
from scipy.stats import norm

import logging
logger = logging.getLogger(__name__)

account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', None)
my_number = os.environ.get('TWILIO_PHONE_NUMBER', None)


@receiver(post_save, sender=Event)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest Event has already been observered or if it is new and update the models accordingly
    """
    # instance is the new Event
    logger.info('Trying to group with similar events')
    # ------------------------------------------------------------------------------
    # Look for other events with the same Trig ID
    # ------------------------------------------------------------------------------
    instanceData = {
        "ra": instance.ra,
        "dec": instance.dec,
        "ra_hms": instance.ra_hms,
        "dec_dms": instance.dec_dms,
        "pos_error": instance.pos_error,
        "earliest_event_observed": instance.event_observed,
        "latest_event_observed": instance.event_observed,
    }

    if(instance.source_name and instance.source_type):
        instanceData = {
            "ra": instance.ra,
            "dec": instance.dec,
            "ra_hms": instance.ra_hms,
            "dec_dms": instance.dec_dms,
            "pos_error": instance.pos_error,
            "source_type": instance.source_type,
            "source_name": instance.source_name,
            "earliest_event_observed": instance.event_observed,
            "latest_event_observed": instance.event_observed,
        }

    # cleanInstanceData = dict(filter(itemgetter(1), instanceData))
    event_group = EventGroup.objects.update_or_create(
        trig_id=instance.trig_id,
        defaults=instanceData,
    )[0]
    # Link the Event (have to update this way to prevent save() triggering this function again)
    logger.info(f'Linking event ({instance.id}) to group {event_group}')
    Event.objects.filter(id=instance.id).update(event_group_id=event_group)

    if instance.ignored:
        # Event ignored so do nothing
        logger.info('Event ignored so do nothing')
        return
    if (instance.ra and instance.dec):
        logger.info(f'Getting sky coordinates {instance.ra} {instance.dec}')
        event_coord = SkyCoord(ra=instance.ra * u.degree,
                               dec=instance.dec * u.degree)

    logger.info('Getting proposal decisions')
    proposal_decisions = ProposalDecision.objects.filter(
        event_group_id=event_group).order_by("proposal__priority")

    if proposal_decisions.exists():
        # Loop over all proposals settings and see if it's worth reobserving
        logger.info(
            'Loop over all proposals settings and see if it\'s worth reobserving')

        for prop_dec in proposal_decisions:
            logger.info(
                f'Proposal decision (prop_dec.id, prop_dec.decision): {prop_dec.id, prop_dec.decision}')
            if prop_dec.decision == "C":
                # Previous observation canceled so assume no new observations should be triggered
                prop_dec.decision_reason += f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Previous observation canceled so not observing . \n"
                logger.info(
                    'Save proposal decision (prop_dec.decision == "C")')
                prop_dec.save()
            elif prop_dec.decision == "I" or prop_dec.decision == "E":
                # Previous events were ignored, check if this new one is up to our standards
                # Update pos
                prop_dec.ra = instance.ra
                prop_dec.dec = instance.dec
                prop_dec.ra_hms = instance.ra_hms
                prop_dec.dec_dms = instance.dec_dms
                if instance.pos_error != 0.:
                    # Don't update pos_error if zero, assume it's a null
                    prop_dec.pos_error = instance.pos_error
                    prop_dec.decision_reason = f"{prop_dec.decision_reason}{datetime.datetime.utcnow()}: Event ID {instance.id}: Checking new Event. \n"

                proposal_worth_observing(
                    prop_dec,
                    instance,
                )
            elif prop_dec.decision == "T":
                # Check new event position is further away than the repointing limit

                if (prop_dec.ra and prop_dec.dec):
                    old_event_coord = SkyCoord(
                        ra=prop_dec.ra * u.degree, dec=prop_dec.dec * u.degree)
                    event_sep = event_coord.separation(old_event_coord).deg
                    if event_sep > prop_dec.proposal.repointing_limit:
                        # worth repointing
                        # Update pos
                        prop_dec.ra = instance.ra
                        prop_dec.dec = instance.dec
                        prop_dec.ra_hms = instance.ra_hms
                        prop_dec.dec_dms = instance.dec_dms
                        if instance.pos_error != 0.:
                            # Don't update pos_error if zero, assume it's a null
                            prop_dec.pos_error = instance.pos_error
                        repoint_message = f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Repointing because seperation ({event_sep:.4f} deg) is greater than the repointing limit ({prop_dec.proposal.repointing_limit:.4f} deg)."
                        # Trigger observation
                        logger.info(
                            f'Trigger observation ({prop_dec.decision} == "T")')
                        decision, decision_reason_log = trigger_observation(
                            prop_dec,
                            f"{prop_dec.decision_reason}{repoint_message} \n",
                            reason=repoint_message,
                            event_id=instance.id,
                        )
                        if decision == 'E':
                            # Error observing so send off debug
                            debug_bool = True
                        else:
                            debug_bool = False
                        # Update proposal decision and log
                        prop_dec.decision = decision
                        prop_dec.decision_reason = decision_reason_log
                        logger.info('Update proposal decision and log')
                        prop_dec.save()

                        # send off alert messages to users and admins
                        send_all_alerts(True, debug_bool, False, prop_dec)

        if instance.pos_error and instance.pos_error < event_group.pos_error and instance.pos_error != 0.:
            # Updated event group's best position
            event_group.ra = instance.ra
            event_group.dec = instance.dec
            event_group.ra_hms = instance.ra_hms
            event_group.dec_dms = instance.dec_dms
            event_group.pos_error = instance.pos_error

        # Update latest_event_observed
        event_group.latest_event_observed = instance.event_observed
        logger.info('saving event group')
        event_group.save()

    else:
        # First unignored event so create proposal decisions objects
        logger.info(
            'First unignored event so create proposal decisions objects')
        # Loop over settings
        proposal_settings = ProposalSettings.objects.all().order_by("priority")

        for prop_set in proposal_settings:
            # Create a ProposalDecision object to record what each proposal does
            prop_dec = ProposalDecision.objects.create(
                decision_reason=f"{datetime.datetime.utcnow()}: Event ID {instance.id}: Beginning event analysis. \n",
                proposal=prop_set,
                event_group_id=event_group,
                trig_id=instance.trig_id,
                duration=instance.duration,
                ra=instance.ra,
                dec=instance.dec,
                ra_hms=instance.ra_hms,
                dec_dms=instance.dec_dms,
                pos_error=instance.pos_error,
            )
            # Check if it's worth triggering an obs
            proposal_worth_observing(prop_dec, instance)

        # Mark as unignored event
        event_group.ignored = False
        logger.info('Mark as unignored event')
        event_group.save()


def proposal_worth_observing(
    prop_dec,
    voevent,
    observation_reason="First observation."
):
    """For a proposal sees is this voevent is worth observing. If it is will trigger an observation and send off the relevant alerts.

    Parameters
    ----------
    prop_dec : `django.db.models.Model`
        The Django ProposalDecision model object.
    voevent : `django.db.models.Model`
        The Django Event model object.
    observation_reason : `str`, optional
        The reason for this observation. The default is "First Observation" but other potential reasons are "Repointing".
    """
    logger.info(
        f'Checking that proposal {prop_dec.proposal} is worth observing.')
    # Defaults if not worth observing
    trigger_bool = debug_bool = pending_bool = False
    decision_reason_log = prop_dec.decision_reason

    # Check if event has an accurate enough position
    if prop_dec.pos_error == 0.0:
        # Ignore the inaccurate event
        decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {voevent.id}: The Events positions uncertainty is 0.0 which is likely an error so not observing. \n"
    elif voevent.pos_error and (voevent.pos_error > prop_dec.proposal.maximum_position_uncertainty):
        # Ignore the inaccurate event
        decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {voevent.id}: The Events positions uncertainty ({voevent.pos_error:.4f} deg) is greater than {prop_dec.proposal.maximum_position_uncertainty:.4f} so not observing. \n"
    else:
        # Continue to next test

        if prop_dec.proposal.event_telescope is None or str(prop_dec.proposal.event_telescope).strip() == voevent.telescope.strip():
            # This project observes events from this telescope

            # Check if this proposal thinks this event is worth observing
            proj_source_bool = False
            if prop_dec.proposal.source_type == "GRB" and voevent.event_group_id.source_type == "GRB":
                # This proposal wants to observe GRBs so check if it is worth observing
                trigger_bool, debug_bool, pending_bool, decision_reason_log = worth_observing_grb(
                    # event values
                    event_duration=voevent.duration,
                    fermi_most_likely_index=voevent.fermi_most_likely_index,
                    fermi_detection_prob=voevent.fermi_detection_prob,
                    swift_rate_signif=voevent.swift_rate_signif,
                    hess_significance=voevent.hess_significance,
                    # Thresholds
                    event_any_duration=prop_dec.proposal.event_any_duration,
                    event_min_duration=prop_dec.proposal.event_min_duration,
                    event_max_duration=prop_dec.proposal.event_max_duration,
                    pending_min_duration_1=prop_dec.proposal.pending_min_duration_1,
                    pending_max_duration_1=prop_dec.proposal.pending_max_duration_1,
                    pending_min_duration_2=prop_dec.proposal.pending_min_duration_2,
                    pending_max_duration_2=prop_dec.proposal.pending_max_duration_2,
                    fermi_min_detection_prob=prop_dec.proposal.fermi_prob,
                    swift_min_rate_signif=prop_dec.proposal.swift_rate_signf,
                    minimum_hess_significance=prop_dec.proposal.minimum_hess_significance,
                    maximum_hess_significance=prop_dec.proposal.maximum_hess_significance,
                    # Other
                    decision_reason_log=decision_reason_log,
                    event_id=voevent.id,
                )
                proj_source_bool = True

            elif prop_dec.proposal.source_type == "FS" and voevent.event_group_id.source_type == "FS":
                # This proposal wants to observe FSs and there is no FS logic so observe
                trigger_bool = True
                decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {voevent.id}: Triggering on Flare Star {voevent.source_name}. \n"
                proj_source_bool = True
            elif prop_dec.proposal.source_type == "NU" and voevent.event_group_id.source_type == "NU":
                # This proposal wants to observe GRBs so check if it is worth observing
                trigger_bool, debug_bool, pending_bool, decision_reason_log = worth_observing_nu(
                    # event values
                    antares_ranking=voevent.antares_ranking,
                    telescope=voevent.telescope,
                    # Thresholds
                    antares_min_ranking=prop_dec.proposal.antares_min_ranking,
                    # Other
                    decision_reason_log=decision_reason_log,
                    event_id=voevent.id,
                )
                proj_source_bool = True

            elif prop_dec.proposal.source_type == "GW" and voevent.event_group_id.source_type == "GW":
                # This proposal wants to observe GRBs so check if it is worth observing
                trigger_bool, debug_bool, pending_bool, decision_reason_log = worth_observing_gw(
                    # Event values
                    lvc_binary_neutron_star_probability=voevent.lvc_binary_neutron_star_probability,
                    lvc_neutron_star_black_hole_probability=voevent.lvc_neutron_star_black_hole_probability,
                    lvc_binary_black_hole_probability=voevent.lvc_binary_black_hole_probability,
                    lvc_terrestial_probability=voevent.lvc_terrestial_probability,
                    lvc_includes_neutron_star_probability=voevent.lvc_includes_neutron_star_probability,
                    telescope=voevent.telescope,
                    # Thresholds
                    minimum_neutron_star_probability=prop_dec.proposal.minimum_neutron_star_probability,
                    maximum_neutron_star_probability=prop_dec.proposal.maximum_neutron_star_probability,
                    minimum_binary_neutron_star_probability=prop_dec.proposal.minimum_binary_neutron_star_probability,
                    maximum_binary_neutron_star_probability=prop_dec.proposal.maximum_binary_neutron_star_probability,
                    minimum_neutron_star_black_hole_probability=prop_dec.proposal.minimum_neutron_star_black_hole_probability,
                    maximum_neutron_star_black_hole_probability=prop_dec.proposal.maximum_neutron_star_black_hole_probability,
                    minimum_binary_black_hole_probability=prop_dec.proposal.minimum_binary_black_hole_probability,
                    maximum_binary_black_hole_probability=prop_dec.proposal.maximum_binary_black_hole_probability,
                    minimum_terrestial_probability=prop_dec.proposal.minimum_terrestial_probability,
                    maximum_terrestial_probability=prop_dec.proposal.maximum_terrestial_probability,
                    observe_low_significance=prop_dec.proposal.observe_low_significance,
                    observe_significant=prop_dec.proposal.observe_significant,
                    # Other
                    decision_reason_log=decision_reason_log,
                    event_id=voevent.id,
                )
                proj_source_bool = True
            # TODO set up other source types here

            if not proj_source_bool:
                # Proposal does not observe this type of source so update message
                decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {voevent.id}: This proposal does not observe {voevent.event_group_id.source_type}s. \n"
        else:
            # Proposal does not observe event from this telescope so update message
            decision_reason_log = f"{decision_reason_log}{datetime.datetime.utcnow()}: Event ID {voevent.id}: This proposal does not trigger on events from {voevent.telescope}. \n"

    if trigger_bool:
        # Check if you can observe and if so send off the observation
        logger.info(
            'Check if you can observe and if so send off the observation')
        decision, decision_reason_log = trigger_observation(
            prop_dec,
            decision_reason_log,
            reason=observation_reason,
            event_id=voevent.id,
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
    prop_dec.decision_reason = decision_reason_log
    prop_dec.save()

    # send off alert messages to users and admins
    logger.info('Sending alerts to users and admins')
    send_all_alerts(trigger_bool, debug_bool, pending_bool, prop_dec)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, proposal_decision_model):
    """
    """
    # Work out all the telescopes that observed the event
    logger.info(
        f'Work out all the telescopes that observed the event {trigger_bool, debug_bool, pending_bool, proposal_decision_model}')
    voevents = Event.objects.filter(
        event_group_id=proposal_decision_model.event_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ", ".join(list(set(telescopes)))

    # Work out when the source will go below the horizon
    telescope = proposal_decision_model.proposal.telescope
    location = EarthLocation(
        lon=telescope.lon * u.deg,
        lat=telescope.lat * u.deg,
        height=telescope.height * u.m
    )
    if (proposal_decision_model.ra and proposal_decision_model.dec):
        obs_source = SkyCoord(
            proposal_decision_model.ra,
            proposal_decision_model.dec,
            # equinox='J2000',
            unit=(u.deg, u.deg)
        )
        # Convert from RA/Dec to Alt/Az
        # 24 hours in 5 min increments
        delta_24h = np.linspace(0, 1440, 288) * u.min
        next_24h = obstime = Time.now() + delta_24h
        obs_source_altaz = obs_source.transform_to(
            AltAz(obstime=next_24h, location=location))
        # capture circumpolar source case
        set_time_utc = None
        for altaz, time in zip(obs_source_altaz, next_24h):
            if altaz.alt.deg < 1.:
                # source below horizon so record time
                set_time_utc = time
                break

    # Get all admin alert permissions for this project
    logger.info('Get all admin alert permissions for this project')
    alert_permissions = AlertPermission.objects.filter(
        proposal=proposal_decision_model.proposal)
    for ap in alert_permissions:
        # Grab user
        user = ap.user
        user_alerts = UserAlerts.objects.filter(
            user=user, proposal=proposal_decision_model.proposal)

        # Send off the alerts of types user defined
        for ua in user_alerts:
            # Check if user can recieve each type of alert
            # Trigger alert
            if ap.alert and ua.alert and trigger_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} TRIGGERING on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"Tracet scheduled the following {proposal_decision_model.proposal.telescope} observations:\n"
                # Send links for each observation
                obs = Observations.objects.filter(
                    proposal_decision_id=proposal_decision_model)
                for ob in obs:
                    message_type_text += f"{ob.website_link}\n"
                send_alert_type(ua.type, ua.address, subject, message_type_text,
                                proposal_decision_model, telescopes, set_time_utc)

            # Debug Alert
            if ap.debug and ua.debug and debug_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} INFO on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"This is a debug notification from TraceT."
                send_alert_type(ua.type, ua.address, subject, message_type_text,
                                proposal_decision_model, telescopes, set_time_utc)

            # Pending Alert
            if ap.approval and ua.approval and pending_bool:
                subject = f"TraceT {proposal_decision_model.proposal.proposal_id}: {proposal_decision_model.proposal.telescope_id} PENDING on {telescopes} {proposal_decision_model.event_group_id.source_type}"
                message_type_text = f"HUMAN INTERVENTION REQUIRED! TraceT is unsure about the following event."
                send_alert_type(ua.type, ua.address, subject, message_type_text,
                                proposal_decision_model, telescopes, set_time_utc)


def send_alert_type(alert_type, address, subject, message_type_text, proposal_decision_model, telescopes, set_time_utc):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    # Set up message text
    message_text = f"""{message_type_text}

Event Details are:
TraceT proposal:      {proposal_decision_model.proposal.proposal_id}
Detected by: {telescopes}
Event Type:  {proposal_decision_model.event_group_id.source_type}
Duration:    {proposal_decision_model.duration}
RA:          {proposal_decision_model.ra_hms} hours
Dec:         {proposal_decision_model.dec_dms} deg
Error Rad:   {proposal_decision_model.pos_error} deg
Event observed (UTC): {proposal_decision_model.event_group_id.earliest_event_observed}
Set time (UTC):       {set_time_utc}

Decision log:
{proposal_decision_model.decision_reason}

Proposal decision can be seen here:
https://mwa-trigger.duckdns.org/proposal_decision_details/{proposal_decision_model.id}/
"""

    if alert_type == 0:
        # Send an email
        logger.info('Send an email')
        send_mail(
            subject,
            message_text,
            settings.EMAIL_HOST_USER,
            [address],
            # fail_silently=False,
        )
    elif alert_type == 1:
        # Send an SMS
        logger.info('Send an SMS')
        message = client.messages.create(
            to=address,
            from_=my_number,
            body=message_text,
        )
    elif alert_type == 2:
        # Make a call
        logger.info('Make a call')
        call = client.calls.create(
            url='http://demo.twilio.com/docs/voice.xml',
            to=address,
            from_=my_number,
        )


@receiver(post_save, sender=User)
def create_admin_alerts_proposal(sender, instance, **kwargs):
    if kwargs.get('created'):
        # Create an admin alert for each proposal
        proposal_settings = ProposalSettings.objects.all()
        for prop_set in proposal_settings:
            s = AlertPermission(user=instance, proposal=prop_set)
            s.save()


@receiver(post_save, sender=ProposalSettings)
def create_admin_alerts_user(sender, instance, **kwargs):
    if kwargs.get('created'):
        # Create an admin alert for each user
        users = User.objects.all()
        for user in users:
            s = AlertPermission(user=user, proposal=instance)
            s.save()


def on_startup(sender, **kwargs):
    # Create a twistd comet status object and set it to stopped until the twistd_comet_wrapper.py is called
    if Status.objects.filter(name='twistd_comet').exists():
        Status.objects.filter(name='twistd_comet').update(status=2)
    else:
        Status.objects.create(name='twistd_comet', status=2)

    if Status.objects.filter(name='kafka').exists():
        Status.objects.filter(name='kafka').update(status=2)
    else:
        Status.objects.create(name='kafka', status=2)


# Getting a signal from views.py which indicates that the server has started
startup_signal = Signal()
# Run twistd startup function
startup_signal.connect(on_startup, dispatch_uid='models-startup')
