from django.contrib import admin
from trigger_app.models import Event, PossibleEventAssociation, AlertPermission, ProposalSettings, ProposalDecision, Telescope, Status, EventGroup, TelescopeProjectID, UserAlerts, Observations
from trigger_app.forms import ProjectSettingsForm, TelescopeProjectIDForm


class ProposalSettingsAdmin(admin.ModelAdmin):
    form = ProjectSettingsForm
    model = ProposalSettings
    list_display = ('id', 'telescope', 'project_id', 'proposal_description')
    fieldsets = (
        ("Telescope Settings: Common", {
            'fields':(
                'telescope',
                'project_id',
                'proposal_description',
                'event_telescope',
                'repointing_limit',
                'testing',
            ),
        }),
        ("Telescope Settings: MWA (only fill out if using the MWA)", {
            'fields':(
                'mwa_freqspecs',
                'mwa_nobs',
                'mwa_exptime',
                'mwa_calexptime',
                'mwa_freqres',
                'mwa_inttime',
                'mwa_horizon_limit',
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
            ),
        }),
        ("Source Settings: Event Duration Range (s)", {
            'fields':(
                ('event_min_duration', 'event_max_duration'),
            ),
            'description': "The inclusive duration range of an event that will automatically trigger an observation.",
        }),
        ("Source Settings: Pending Duration Range 1 (s)", {
            'fields':(
                ('pending_min_duration_1', 'pending_max_duration_1'),
            ),
            'description': "The inclusive duration range of an event that will notify users and let them decided if an observations should be triggered.",
        }),
        ("Source Settings: Pending Duration Range 2 (s)", {
            'fields':(
                ('pending_min_duration_2', 'pending_max_duration_2'),
            ),
            'description': "A second inclusive duration range of an event that will notify users and let them decided if an observations should be triggered.",
        }),
        ('Source Settings', {
            'fields': (
                'fermi_prob',
                'swift_rate_signf',
                'source_type',
            ),
        }),
    )


class TelescopeProjectIDAdmin(admin.ModelAdmin):
    form = TelescopeProjectIDForm
    model = TelescopeProjectID

class UserAlertsAdmin(admin.ModelAdmin):
    list_display = ('user', 'proposal', 'type', 'address', 'alert', 'debug', 'approval')

# Register your models here.
admin.site.register(ProposalSettings, ProposalSettingsAdmin)
admin.site.register(TelescopeProjectID, TelescopeProjectIDAdmin)
admin.site.register(UserAlerts, UserAlertsAdmin)

admin.site.register(Event)
admin.site.register(EventGroup)
admin.site.register(PossibleEventAssociation)
admin.site.register(AlertPermission)
admin.site.register(ProposalDecision)
admin.site.register(Telescope)
admin.site.register(Status)
admin.site.register(Observations)