from django.contrib import admin
from trigger_app.models import VOEvent, TriggerEvent, AdminAlerts, ProposalSettings, ProposalDecision, Telescope


class ProposalSettingsAdmin(admin.ModelAdmin):
    model = ProposalSettings
    fieldsets = (
        ("Telescope Settings", {
            'fields':(
                'telescope',
                'project_id',
                'proposal_description',
                'repointing_limit',
                'horizon_limit',
                'testing',
            ),
        }),
        ("MWA Telescope Settings (only fill out if using the MWA)", {
            'fields':(
                'mwa_centrefreq',
                'mwa_exptime',
                'mwa_calibrator',
                'mwa_calexptime',
                'mwa_freqres',
                'mwa_inttime',
                'mwa_avoidsun',
                'mwa_buffered',
            ),
        }),
        ("ATCA Telescope Settings (only fill out if using the ATCA)", {
            'fields':(
                'atca_freq1',
                'atca_freq2',
                'atca_nobs',
                'atca_exptime',
                'atca_calexptime',
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
admin.site.register(ProposalDecision)
admin.site.register(ProposalSettings, ProposalSettingsAdmin)
admin.site.register(Telescope)