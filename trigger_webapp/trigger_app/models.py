from django.db import models

# Create your models here.
class TriggerEvent(models.Model):
    id = models.AutoField(primary_key=True)
    P = 'P'
    I = 'I'
    T = 'T'
    CHOICES = (
        ('P', 'Pending'),
        ('I', 'Ignored'),
        ('T', 'Triggered'),
    )
    decision = models.CharField(max_length=32, choices=CHOICES, default=P)
    decision_reason = models.CharField(max_length=256, blank=True, null=True)
    telescope = models.CharField(max_length=64, blank=True, null=True)
    trigger_id = models.IntegerField(blank=True, null=True)
    trigger_type = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)


class VOEvent(models.Model):
    id = models.AutoField(primary_key=True)
    trigger_group_id = models.ForeignKey(TriggerEvent, on_delete=models.SET_NULL, blank=True, null=True)
    telescope = models.CharField(max_length=64, blank=True, null=True)
    trigger_id = models.IntegerField(blank=True, null=True)
    sequence_num = models.IntegerField(blank=True, null=True)
    trigger_type = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    xml_packet = models.CharField(max_length=10000)
    ignored = models.BooleanField(default=True)