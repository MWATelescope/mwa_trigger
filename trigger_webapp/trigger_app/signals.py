from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from .models import ProjectDecision, UserAlerts, VOEvent, TriggerEvent, CometLog, Status, AdminAlerts, ProjectSettings, ProjectDecision, Observations
from .telescope_observe import trigger_observation

from mwa_trigger.parse_xml import parsed_VOEvent
from mwa_trigger.trigger_logic import worth_observing_grb
import voeventparse

import os
import threading
import time
from schedule import Scheduler
from subprocess import PIPE, Popen
from twilio.rest import Client
from astropy.coordinates import SkyCoord
from astropy import units as u

import logging
logger = logging.getLogger(__name__)

account_sid = os.environ['TWILIO_ACCOUNT_SID']
auth_token = os.environ['TWILIO_AUTH_TOKEN']


@receiver(post_save, sender=VOEvent)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest VOEvent has already been observered or if it is new and update the models accordingly
    """
    # instance is the new VOEvent
    if not instance.ignored:
        trigger_id = instance.trigger_id
        if TriggerEvent.objects.filter(trigger_id=trigger_id).exists():
            # Trigger event already exists so link the new VOEvent
            prev_trig = TriggerEvent.objects.get(trigger_id=trigger_id)
            # For some reason can't update with the instance
            voevent = VOEvent.objects.filter(trigger_id=trigger_id)
            voevent.update(trigger_group_id=prev_trig)

            #TODO add some checks to see if you want to update here
        else:
            # Make a new trigger event
            new_trig = TriggerEvent.objects.create(trigger_id=instance.trigger_id,
                duration=instance.duration,
                ra=instance.ra,
                dec=instance.dec,
                pos_error=instance.pos_error,
                source_type=instance.source_type,
            )
            # Link the VOEvent
            instance.trigger_group_id = new_trig
            instance.save()

            # Check if it's worth triggering an obs
            vo = parsed_VOEvent(None, packet=str(instance.xml_packet))
            # covert ra and dec to HH:MM:SS.SS format
            c = SkyCoord( instance.ra, instance.dec, frame='icrs', unit=(u.deg,u.deg))
            raj = c.ra.to_string(unit=u.hour, sep=':')
            decj = c.dec.to_string(unit=u.degree, sep=':')

            # Loop over settings
            project_settings = ProjectSettings.objects.all()
            for proj_set in project_settings:
                # Create a ProjectDecision object to record what each project does
                proj_dec = ProjectDecision.objects.create(
                    #decision=decision,
                    #decision_reason=trigger_message,
                    project=proj_set,
                    trigger_group_id=new_trig,
                    duration=instance.duration,
                    ra=instance.ra,
                    dec=instance.dec,
                    raj=raj,
                    decj=decj,
                    pos_error=instance.pos_error,
                )

                # Defaults if not worth observing
                trigger_bool = debug_bool = pending_bool = False
                trigger_message = ""
                proj_source_bool = False

                # Check if this project thinks this event is worth observing
                if proj_set.grb and instance.source_type == "GRB":
                    # This project wants to observe GRBs so check if it is worth observing
                    trigger_bool, debug_bool, pending_bool, trigger_message = worth_observing_grb(
                        vo,
                        trig_min_duration=proj_set.trig_min_duration,
                        trig_max_duration=proj_set.trig_max_duration,
                        pending_min_duration=proj_set.pending_min_duration,
                        pending_max_duration=proj_set.pending_max_duration,
                        fermi_prob=proj_set.fermi_prob,
                        rate_signif=proj_set.swift_rate_signf,
                    )
                    proj_source_bool = True
                # TODO set up other source types here

                if not proj_source_bool:
                    # Project does not observe this type of source so update message
                    trigger_message += f"This project does not observe {instance.get_source_type_display()}s. "

                if trigger_bool:
                    # Check if you can observe and if so send off the observation
                    decision, trigger_message = trigger_observation(
                        proj_dec,
                        trigger_message,
                        horizion_limit=proj_set.horizon_limit,
                        pretend=proj_set.testing,
                        reason="First Observation",
                    )
                elif pending_bool:
                    # Send off a pending decision
                    decision = 'P'
                else:
                    decision = 'I'

                # Update project decision and log
                proj_dec.decision = decision
                proj_dec.decision_reason = trigger_message
                proj_dec.save()

                # TODO do something smart with these results to decide which telescope to observe with
                # but hopefully the project settings will describe if you want to observe or not.

                # send off alert messages to users and admins
                send_all_alerts(trigger_bool, debug_bool, pending_bool, proj_dec)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, project_decision_model):
    """
    """
    # Work out all the telescopes that observed the event
    voevents = VOEvent.objects.filter(trigger_group_id=project_decision_model.trigger_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ", ".join(list(set(telescopes)))

    # Get all admin alert permissions
    admin_alerts = AdminAlerts.objects.all()
    for aa in admin_alerts:
        # Grab user
        user = aa.user
        user_alerts = UserAlerts.objects.filter(user=user)

        # Send off the alerts of types user defined
        for ua in user_alerts:
            # Check if user can recieve each type of alert
            # Trigger alert
            if aa.alert and ua.alert and trigger_bool:
                subject = f"Trigger Web App Observation {project_decision_model.id}"
                message_type_text = f"The trigger web service scheduled the following {project_decision_model.project.telescope} observations:\n"
                # Send links for each observation
                obs = Observations.objects.filter(project_decision_id=project_decision_model)
                for ob in obs:
                    message_type_text += f"{ob.website_link}\n"
                send_alert_type(ua.type, ua.address, subject, message_type_text, project_decision_model, telescopes)

            # Debug Alert
            if aa.debug and ua.debug and debug_bool:
                subject = f"Trigger Web App Debug {project_decision_model.id}"
                message_type_text = f"This is a debug notification from the trigger web service."
                send_alert_type(ua.type, ua.address, subject, message_type_text, project_decision_model, telescopes)

            # Pending Alert
            if aa.approval and ua.approval and pending_bool:
                subject = f"PENDING Trigger Web App {project_decision_model.id}"
                message_type_text = f"HUMAN INTERVENTION REQUIRED! The trigger web service is unsure about the following event."
                send_alert_type(ua.type, ua.address, subject, message_type_text, project_decision_model, telescopes)

def send_alert_type(alert_type, address, subject, message_type_text, project_decision_model, telescopes):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    # Set up message text
    logs = ".\n".join(project_decision_model.decision_reason.split(". "))
    message_text = f"""{message_type_text}

Event Details are:
Duration:    {project_decision_model.duration}
RA:          {project_decision_model.raj} hours
Dec:         {project_decision_model.decj} deg
Error Rad:   {project_decision_model.pos_error} deg
Detected by: {telescopes}

Decision log:
{logs}

Project decision can be seen here:
http://127.0.0.1:8000/project_decision_details/{project_decision_model.id}/
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
def create_admin_alerts(sender, instance, **kwargs):
    if kwargs.get('created'):
        s = AdminAlerts(user=instance)
        s.save()


def output_popen_stdout(process):
    output = process.stdout.readline()
    if output:
        # New output so send it to the log
        CometLog.objects.create(log=output.strip().decode())
    comet_status = Status.objects.get(name='twistd_comet')
    poll = process.poll()
    if poll is None:
        # Process is still running
        comet_status.status = 0
    elif poll == 0:
        # Finished for some reason
        comet_status.status = 2
    else:
        # Broken
        comet_status.status = 1



def run_continuously(self, interval=10):
    """Got from
    https://stackoverflow.com/questions/44896618/django-run-a-function-every-x-seconds

    Continuously run, while executing pending jobs at each elapsed
    time interval.
    @return cease_continuous_run: threading.Event which can be set to
    cease continuous run.
    Please note that it is *intended behavior that run_continuously()
    does not run missed jobs*. For example, if you've registered a job
    that should run every minute and you set a continuous run interval
    of one hour then your job won't be run 60 times at each interval but
    only once.
    """

    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):

        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                self.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.setDaemon(True)
    continuous_thread.start()
    return cease_continuous_run

Scheduler.run_continuously = run_continuously


# Getting a signal from views.py which indicates that the server has started
startup_signal = Signal()

def on_startup(sender, **kwargs):
    print("Starting twistd")
    process = Popen("twistd -n comet --local-ivo=ivo://hotwired.org/test --remote=voevent.4pisky.org --cmd=/home/nick/code/mwa_trigger/trigger_webapp/upload_xml.py", shell=True, stdout=PIPE)
    scheduler = Scheduler()
    scheduler.every(1).minutes.do(output_popen_stdout, process=process)
    scheduler.run_continuously()
    # Create status model if not already made
    Status.objects.get_or_create(name='twistd_comet', status=0)

startup_signal.connect(on_startup, dispatch_uid='models-startup')