from django.contrib import admin
from trigger_app.models import VOEvent, TriggerEvent, AdminAlerts, ProposalSettings, ProposalDecision, Telescope


class ProposalSettingsAdmin(admin.ModelAdmin):
    model = ProposalSettings
    list_display = ('id', 'telescope', 'project_id', 'proposal_description')
    fieldsets = (
        ("Telescope Settings: Common", {
            'fields':(
                'telescope',
                'project_id',
                'proposal_description',
                'repointing_limit',
                'horizon_limit',
                'testing',
            ),
        }),
        ("Telescope Settings: MWA (only fill out if using the MWA)", {
            'fields':(
                'mwa_freqspecs',
                'mwa_nobs',
                'mwa_exptime',
                'mwa_calibrator',
                'mwa_calexptime',
                'mwa_freqres',
                'mwa_inttime',
                'mwa_avoidsun',
                'mwa_buffered',
            ),
        }),
        ("Telescope Settings: ATCA (only fill out if using the ATCA)", {
            'description': "ATCA has five receivers, so we can cycle the observations through each of them each time they repoint. Here is the documentation (see table 1.1) https://www.narrabri.atnf.csiro.au/observing/users_guide/html/atug.html#Signal-Path. All receives can observe at two frequency ranges (2 GHz bands) except for 16cm, which only observes has a 2GHz bandwidth, so only has one choice.",
            'fields':(
                ('atca_band_3mm', 'atca_band_3mm_freq1', 'atca_band_3mm_freq2'),
                ('atca_band_7mm', 'atca_band_7mm_freq1', 'atca_band_7mm_freq2'),
                ('atca_band_15mm', 'atca_band_15mm_freq1', 'atca_band_15mm_freq2'),
                ('atca_band_4cm', 'atca_band_4cm_freq1', 'atca_band_4cm_freq2'),
                'atca_band_16cm',
                'atca_nobs',
                'atca_exptime',
                'atca_calexptime',
            ),
        }),
        ("Source Settings: Trigger Duration Range (s)", {
            'fields':(
                ('trig_min_duration', 'trig_max_duration'),
            ),
            'description': "The inclusive duration range of an event that will automatically trigger an observation.",
        }),
        ("Source Settings: Pending Duration Range (s)", {
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