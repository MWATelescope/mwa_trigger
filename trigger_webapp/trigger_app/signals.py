from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from .models import UserAlerts, VOEvent, TriggerEvent, CometLog, Status, AdminAlerts,  MWAObservations, TriggerSettings
from .mwa_observe import trigger_mwa_observation

from mwa_trigger.parse_xml import parsed_VOEvent
from mwa_trigger.trigger_logic import worth_observing
import voeventparse

import os
import threading
import time
from schedule import Scheduler
from subprocess import PIPE, Popen
from twilio.rest import Client

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
            new_trig = TriggerEvent.objects.create(telescope=instance.telescope,
                                  trigger_id=instance.trigger_id,
                                  event_type=instance.event_type,
                                  duration=instance.duration,
                                  ra=instance.ra,
                                  dec=instance.dec,
                                  pos_error=instance.pos_error)
            # Link the VOEvent
            instance.trigger_group_id = new_trig
            instance.save()

            # Check if it's worth triggering an obs
            vo = parsed_VOEvent(None, packet=str(instance.xml_packet))

            # Loop over settings
            observations_settings = TriggerSettings.objects.all()
            for obs_set in observations_settings:
                trigger_bool, debug_bool, short_bool, trigger_message = worth_observing(vo, max_duration=obs_set.max_duration, fermi_prob=obs_set.fermi_prob)
                # TODO do something smart with these results to decide which telescope to observe with. For now just using last choice

            if trigger_bool:
                # Check if you can observer and if so send off mwa observation
                decision, trigger_message, obsids = trigger_mwa_observation(instance, trigger_message)
                if decision == 'E':
                    # Error observing so send off debug
                    debug_bool = True
                new_trig.decision = decision
                new_trig.decision_reason = trigger_message
                new_trig.save()
                for obsid in obsids:
                    # Create new obsid model
                    mwa_obs = MWAObservations.objects.create(obsid=obsid,
                                                   trigger_group_id=new_trig,
                                                   voevent_id=instance,
                                                   reason="First Observation")
            else:
                new_trig.decision = 'I'
                new_trig.decision_reason = trigger_message
                new_trig.save()

            # send off alert messages to users and admins
            send_all_alerts(trigger_bool, debug_bool, False, trigger_message)


def send_all_alerts(trigger_bool, debug_bool, pending_bool, trigger_message):
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
                send_alert_type(ua.type, ua.address, trigger_message)

            # Debug Alert
            if aa.debug and ua.debug and debug_bool:
                send_alert_type(ua.type, ua.address, trigger_message)

            # Pending Alert
            if aa.approval and ua.approval and pending_bool:
                send_alert_type(ua.type, ua.address, trigger_message)

def send_alert_type(alert_type, address, trigger_message):
    # Set up twillo client for SMS and calls
    client = Client(account_sid, auth_token)

    if alert_type == 0:
        # Send an email
        send_mail(
            'MWA Trigger Alert',
            trigger_message,
            settings.EMAIL_HOST_USER,
            [address],
            #fail_silently=False,
        )
    elif alert_type == 1:
        # Send an SMS
        message = client.messages.create(
                    to=address,
                    from_='+17755216557',
                    body=trigger_message,
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