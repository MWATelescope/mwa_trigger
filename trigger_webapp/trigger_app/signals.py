from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import VOEvent, TriggerEvent

from mwa_trigger.parse_xml import parsed_VOEvent
from mwa_trigger.trigger_logic import worth_observing
import voeventparse


@receiver(pre_save, sender=VOEvent)
def group_trigger(sender, instance, **kwargs):
    """Check if the latest VOEvent has already been observered or if it is new and update the models accordingly
    """
    new_voevent = instance
    if not new_voevent.ignored:
        trigger_id = new_voevent.trigger_id
        if TriggerEvent.objects.filter(trigger_id=trigger_id).exists():
            # Trigger event already exists so link the new VOEvent
            prev_trig = TriggerEvent.objects.filter(trigger_id=trigger_id)[0]
            instance.trigger_group_id = prev_trig

            #TODO add some checks to see if you want to update here
        else:
            # Make a new trigger event
            new_trig = TriggerEvent.objects.create(telescope=instance.telescope,
                                  trigger_id=instance.trigger_id,
                                  trigger_type=instance.trigger_type,
                                  duration=instance.duration,
                                  ra=instance.ra,
                                  dec=instance.dec,
                                  pos_error=instance.pos_error)
            # Link the VOEvent
            instance.trigger_group_id = new_trig

            # Check if it's worth triggering an obs
            vo = parsed_VOEvent(None, packet=str(instance.xml_packet))
            vo.parse()
            trigger_bool, debug_bool, short_bool, trigger_message = worth_observing(vo)
            new_trig.decision_reason = trigger_message
            if trigger_bool:
                new_trig.decision = 'T'
                #TODO Put send of trigger here
            else:
                new_trig.decision = 'I'
            new_trig.save()

            #TODO add debug message to admins here

