from os import sched_get_priority_max
from django.db import models
from django.contrib.auth.models import User
from django.contrib import admin


GRB = 'GRB'
FS = 'FS'
NU = 'NU'
GW = 'GW'
SOURCE_CHOICES = (
    (GRB, 'Gamma-ray burst'),
    (FS, 'Flare star'),
    (NU, 'Neutrino'),
    (GW, 'Gravitational wave'),
)

class ProjectSettings(models.Model):
    id = models.AutoField(primary_key=True)
    telescope = models.CharField(max_length=64, blank=True, null=True, verbose_name="Telescope name", help_text="E.g. MWA_VCS, MWA_correlate or ATCA.")
    project_id = models.CharField(max_length=64, blank=True, null=True, help_text="This will be used to schedule observations.")
    project_description = models.CharField(max_length=256, blank=True, null=True, help_text="A brief description of the project. Only needs to be enough to distinguish it from the other projects.")
    trig_min_duration = models.FloatField(blank=True, null=True, verbose_name="Min")
    trig_max_duration = models.FloatField(blank=True, null=True, verbose_name="Max")
    pending_min_duration = models.FloatField(blank=True, null=True, verbose_name="Min")
    pending_max_duration = models.FloatField(blank=True, null=True, verbose_name="Max")
    fermi_prob = models.FloatField(blank=True, null=True, help_text="The minimum probability to observe for Fermi sources (it appears to be a percentage, e.g. 50).")
    swift_rate_signf = models.FloatField(blank=True, null=True, help_text="The minimum \"RATE_SIGNIF\" (appears to be a signal-to-noise ratio) to observe for SWIFT sources (in sigma).")
    repointing_limit = models.FloatField(blank=True, null=True, help_text="An updated position must be at least this far away from a current observation before repointing (in degrees).")
    horizon_limit = models.FloatField(blank=True, null=True, help_text="The minimum elevation of the source to observe (in degrees).")
    testing = models.BooleanField(default=False, help_text="If testing, will not schedule any observations.")
    grb = models.BooleanField(default=False, verbose_name="Observe Gamma-ray Bursts?")
    flare_star = models.BooleanField(default=False, verbose_name="Observe Flare Stars?")
    gw = models.BooleanField(default=False, verbose_name="Observe Gravitational Waves?")
    neutrino = models.BooleanField(default=False, verbose_name="Observe Neutrinos?")

    def __str__(self):
        return f"{self.id}_{self.telescope}_{self.project_id}"

class ProjectSettingsAdmin(admin.ModelAdmin):
    model = ProjectSettings
    fieldsets = (
        ("Telescope Settings", {
            'fields':(
                'telescope',
                'project_id',
                'project_description',
                'repointing_limit',
                'horizon_limit',
                'testing',
            ),
        }),
        ("Trigger Duration Range (s)", {
            'fields':(
                ('trig_min_duration', 'trig_max_duration'),
            ),
            'description': "The inclusive duration range of an event that will automatically trigger an observation.",
        }),
        ("Pending Duration Range (s)", {
            'fields':(
                ('pending_min_duration', 'pending_max_duration'),
            ),
            'description': "The inclusive duration range of an event that will notify users and let them decided if an observations should be triggered.",
        }),
        ('Source Settings', {
            'fields': (
                'fermi_prob',
                'swift_rate_signf',
                'grb',
                'flare_star',
                'gw',
                'neutrino',
            ),
        }),
    )


class TriggerEvent(models.Model):
    id = models.AutoField(primary_key=True)
    trigger_id = models.IntegerField(blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-id']


class ProjectDecision(models.Model):
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
    decision_reason = models.CharField(max_length=2056, blank=True, null=True)
    project = models.ForeignKey(ProjectSettings, on_delete=models.SET_NULL, blank=True, null=True)
    trigger_group_id = models.ForeignKey(TriggerEvent, on_delete=models.SET_NULL, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    raj = models.CharField(max_length=32, blank=True, null=True)
    decj = models.CharField(max_length=32, blank=True, null=True)
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
    event_type = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    xml_packet = models.CharField(max_length=10000)
    ignored = models.BooleanField(default=True)
    source_name = models.CharField(max_length=128, blank=True, null=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)

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


class Observations(models.Model):
    obsid = models.IntegerField(primary_key=True)
    telescope = models.CharField(max_length=64, blank=True, null=True)
    project_decision_id = models.ForeignKey(ProjectDecision, on_delete=models.SET_NULL, blank=True, null=True)
    website_link = models.URLField(max_length=256)
    reason = models.CharField(max_length=256, blank=True, null=True)