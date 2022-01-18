from django.db import models
from django.utils import timezone

# Create your models here.

class Trigger(models.Model):
    xml = models.FileField(upload_to='xml_files/')
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    duration = models.FloatField(blank=True, null=True)
    trigger_id = models.CharField(max_length=64, blank=True, null=True)
    trigger_type = models.CharField(max_length=64, blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    