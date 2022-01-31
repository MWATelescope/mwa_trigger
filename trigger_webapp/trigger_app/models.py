from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class TriggerEvent(models.Model):
    id = models.AutoField(primary_key=True)
    P = 'P'
    I = 'I'
    E = 'E'
    T = 'T'
    CHOICES = (
        (P, 'Pending'),
        (I, 'Ignored'),
        (E, 'Error'),
        (T, 'Triggered'),
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

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-id']


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

    class Meta:
        ordering = ['-id']


class CometLog(models.Model):
    id = models.AutoField(primary_key=True)
    log = models.CharField(max_length=256, blank=True, null=True)
    class Meta:
        ordering = ['-id']


class Status(models.Model):
    RUNNING = 0
    BROKEN = 1
    STOPPED = 2
    STATUS_CHOICES = (
        (RUNNING, 'Running'),
        (BROKEN, 'Broken'),
        (STOPPED, 'Stopped')
    )
    name = models.CharField(max_length=64, blank=True, null=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)


class AdminAlerts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    alert = models.BooleanField(default=True)
    debug = models.BooleanField(default=False)
    approval = models.BooleanField(default=False)
    def __str__(self):
        return "{}_Alerts".format(self.user)


class UserAlerts(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    EMAIL = 0
    SMS = 1
    PHONE_CALL = 2
    TYPE_CHOICES = (
        (EMAIL, 'Email'),
        (SMS, 'SMS'),
        (PHONE_CALL, 'Phone Call')
    )
    type = models.PositiveSmallIntegerField(choices=TYPE_CHOICES)
    address = models.CharField(max_length=64, blank=True, null=True)
    alert = models.BooleanField(default=True)
    debug = models.BooleanField(default=True)
    approval = models.BooleanField(default=True)


class MWAObservations(models.Model):
    obsid = models.IntegerField(primary_key=True)
    trigger_group_id = models.ForeignKey(TriggerEvent, on_delete=models.SET_NULL, blank=True, null=True)
    voevent_id = models.ForeignKey(VOEvent, on_delete=models.SET_NULL, blank=True, null=True)
    reason = models.CharField(max_length=256, blank=True, null=True)