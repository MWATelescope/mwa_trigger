from django.db import models

# Create your models here.

class VOEvent(models.Model):
    id = models.AutoField(primary_key=True)
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
