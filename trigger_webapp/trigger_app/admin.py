from django.contrib import admin
from trigger_app.models import VOEvent, TriggerEvent, AdminAlerts, ProjectSettings, ProjectDecision


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
        ("MWA Telescope Settings (only fill out if using the MWA)", {
            'fields':(
                'centrefreq',
                'mwaexptime',
                'mwacalibrator',
                'mwacalexptime',
                'freqres',
                'inttime',
                'avoidsun',
                'buffered',
            ),
        }),
        ("ATCA Telescope Settings (only fill out if using the ATCA)", {
            'fields':(
                'freq1',
                'freq2',
                'nobs',
                'atcaexptime',
                'atcacalexptime',
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


# Register your models here.
admin.site.register(VOEvent)
admin.site.register(TriggerEvent)
admin.site.register(AdminAlerts)
admin.site.register(ProjectDecision)
admin.site.register(ProjectSettings, ProjectSettingsAdmin)