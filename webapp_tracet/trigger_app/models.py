from django.db import models
from django.contrib.auth.models import User


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


class Telescope(models.Model):
    name = models.CharField(max_length=64, verbose_name="Telescope name", help_text="E.g. MWA_VCS, MWA_correlate or ATCA.", unique=True)
    lon = models.FloatField(verbose_name="Telescope longitude in degrees")
    lat = models.FloatField(verbose_name="Telescope latitude in degrees")
    height = models.FloatField(verbose_name="Telescope height above sea level in meters")
    def __str__(self):
        return f"{self.name}"


class EventTelescope(models.Model):
    name = models.CharField(max_length=64, verbose_name="Event Telescope name", help_text="Telescope that we receive Events from (e.g. SWIFT or Fermi)", unique=True)
    def __str__(self):
        return f"{self.name}"


class TelescopeProjectID(models.Model):
    id = models.CharField(primary_key=True, max_length=64, verbose_name="Telescope Project ID", help_text="The project ID for the telescope used to automatically schedule observations.")
    password = models.CharField(max_length=1024, verbose_name="Telescope Project Password", help_text="The project password for the telescope used to automatically schedule observations.")
    description = models.CharField(max_length=256, help_text="A brief description of the project.")
    atca_email = models.CharField(blank=True, null=True, max_length=256, verbose_name="ATCA Proposal Email", help_text="The email address of someone that was on the ATCA observing proposal. This is an authentication step only required for ATCA.")
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        help_text="Telescope this proposal will observer with. If the telescope you want is not here add it on the admin page.",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.telescope}_{self.id}"

class ProposalSettings(models.Model):
    id = models.AutoField(primary_key=True)
    telescope = models.ForeignKey(
        Telescope,
        to_field="name",
        verbose_name="Telescope name",
        help_text="Telescope this proposal will observer with. If the telescope you want is not here add it on the admin page.",
        on_delete=models.CASCADE,
    )
    project_id = models.ForeignKey(
        TelescopeProjectID,
        to_field="id",
        verbose_name="Project ID",
        help_text="This is the target telescopes's project ID that is used with a password to schedule observations.",
        on_delete=models.CASCADE,
    )
    proposal_id = models.CharField(max_length=16, unique=True, verbose_name="Proposal ID", help_text="A short identifier of the proposal of maximum lenth 16 charcters.")
    proposal_description = models.CharField(max_length=256, help_text="A brief description of the proposal. Only needs to be enough to distinguish it from the other proposals.")
    event_telescope = models.ForeignKey(EventTelescope, to_field="name", help_text="The telescope that this proposal will accept at least one Event from before observing. Leave blank if you want to accept all telescopes.", blank=True, null=True, on_delete=models.SET_NULL)
    trig_any_duration = models.BooleanField(default=False, verbose_name="Any duration?", help_text="Will trigger on events with any duration which includes if they have None.")
    trig_min_duration = models.FloatField(verbose_name="Min", default=0.256)
    trig_max_duration = models.FloatField(verbose_name="Max", default=1.024)
    pending_min_duration_1 = models.FloatField(verbose_name="Min", default=1.025)
    pending_max_duration_1 = models.FloatField(verbose_name="Max", default=2.056)
    pending_min_duration_2 = models.FloatField(verbose_name="Min", default=0.128)
    pending_max_duration_2 = models.FloatField(verbose_name="Max", default=0.255)
    maximum_position_uncertainty = models.FloatField(verbose_name="Maximum Position Uncertainty (deg)", help_text="A Event must have less than or equal to this position uncertainty to be observed.", default=0.05)
    fermi_prob = models.FloatField(help_text="The minimum probability to observe for Fermi sources (it appears to be a percentage, e.g. 50).", default=50)
    swift_rate_signf = models.FloatField(help_text="The minimum \"RATE_SIGNIF\" (appears to be a signal-to-noise ratio) to observe for SWIFT sources (in sigma).", default=0.)
    antares_min_ranking = models.IntegerField(help_text="The minimum rating (1 is best) to observe for Antares sources.", default=2)
    repointing_limit = models.FloatField(verbose_name="Repointing Limit (deg)", help_text="An updated position must be at least this far away from a current observation before repointing (in degrees).", default=10.)
    testing = models.BooleanField(default=False, help_text="If testing, will not schedule any observations.")
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, verbose_name="What type of source to will you trigger on?")

    # MWA settings
    mwa_freqspecs = models.CharField(default="144,24", max_length=256, verbose_name="MWA frequency specifications", help_text="The frequency channels IDs for the MWA to observe at.")
    mwa_nobs = models.IntegerField(default=1, verbose_name="Number of Observations", help_text="The number of observations to schedule.")
    mwa_exptime = models.IntegerField(default=896, verbose_name="Observation time (s)", help_text="Exposure time of each observation scheduled, in seconds (must be modulo-8 seconds).")
    mwa_calexptime = models.FloatField(default=120., verbose_name="Calibrator Observation time (s)", help_text="Exposure time of the trailing calibrator observation, if applicable, in seconds.")
    mwa_freqres = models.FloatField(default=10., verbose_name="Frequency Resolution (kHz)", help_text="Correlator frequency resolution for observations. None to use whatever the current mode is, for lower latency. Eg 40.")
    mwa_inttime = models.FloatField(default=0.5, verbose_name="Intergration Time (s)", help_text="Correlator integration time for observations in seconds. None to use whatever the current mode is, for lower latency. Eg 0.5.")
    mwa_horizon_limit = models.FloatField(verbose_name="Horizon limit (deg)", help_text="The minimum elevation of the source to observe (in degrees).", default=10.)

    # ATCA setting
    atca_band_3mm = models.BooleanField(default=False, verbose_name="Use 3mm Band (83-105 GHz)?")
    atca_band_3mm_exptime = models.IntegerField(default=60, verbose_name="Band Exposure Time (mins)", help_text="Total exposure time of the observation cycle at this frequency band.")
    atca_band_3mm_freq1 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 1 (MHz)", help_text="The centre of the first frequency channel in MHz.")
    atca_band_3mm_freq2 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 2 (MHz)", help_text="The centre of the second frequency channel in MHz.")
    atca_band_7mm = models.BooleanField(default=False, verbose_name="Use 7mm Band (30-50 GHz)?")
    atca_band_7mm_exptime = models.IntegerField(default=60, verbose_name="Band Exposure Time (mins)", help_text="Total exposure time of the observation cycle at this frequency band.")
    atca_band_7mm_freq1 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 1 (MHz)", help_text="The centre of the first frequency channel in MHz.")
    atca_band_7mm_freq2 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 2 (MHz)", help_text="The centre of the second frequency channel in MHz.")
    atca_band_15mm = models.BooleanField(default=False, verbose_name="Use 15mm Band (16-25 GHz)?")
    atca_band_15mm_exptime = models.IntegerField(default=60, verbose_name="Band Exposure Time (mins)", help_text="Total exposure time of the observation cycle at this frequency band.")
    atca_band_15mm_freq1 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 1 (MHz)", help_text="The centre of the first frequency channel in MHz.")
    atca_band_15mm_freq2 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 2 (MHz)", help_text="The centre of the second frequency channel in MHz.")
    atca_band_4cm = models.BooleanField(default=False, verbose_name="Use 4cm Band (3.9-11.0 GHz)?")
    atca_band_4cm_exptime = models.IntegerField(default=60, verbose_name="Band Exposure Time (mins)", help_text="Total exposure time of the observation cycle at this frequency band.")
    atca_band_4cm_freq1 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 1 (MHz)", help_text="The centre of the first frequency channel in MHz.")
    atca_band_4cm_freq2 = models.IntegerField(blank=True, null=True, verbose_name="Centre frequency 2 (MHz)", help_text="The centre of the second frequency channel in MHz.")
    atca_band_16cm = models.BooleanField(default=False, verbose_name="User 16cm Band (1.1-3.1 GHz)?")
    atca_band_16cm_exptime = models.IntegerField(default=60, verbose_name="Band Exposure Time (mins)", help_text="Total exposure time of the observation cycle at this frequency band.")
    atca_max_exptime = models.IntegerField(default=720, verbose_name="Maximum Exposure Time (mins)", help_text="Total exposure time of all the observations combined.")
    atca_min_exptime = models.IntegerField(default=30,  verbose_name="Minimum Exposure Time (mins)", help_text="Minimum total exposure time of all the observations combined for the observation to be viable. If this amount of time is not available, the observation will not be scheduled.")
    atca_prioritise_source = models.BooleanField(default=False, verbose_name="Prioritise Source?", help_text="Prioritise time on source rather than time on calibrator.")


    def __str__(self):
        return f"{self.proposal_id}"


class PossibleEventAssociation(models.Model):
    id = models.AutoField(primary_key=True)
    earliest_event_observed = models.DateTimeField(blank=True, null=True)
    latest_event_observed = models.DateTimeField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=64, blank=True, null=True)
    dec_dms = models.CharField(max_length=64, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-id']


class EventGroup(models.Model):
    id = models.AutoField(primary_key=True)
    trig_id = models.BigIntegerField(unique=True)
    earliest_event_observed = models.DateTimeField(blank=True, null=True)
    latest_event_observed = models.DateTimeField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=64, blank=True, null=True)
    dec_dms = models.CharField(max_length=64, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)

    def __str__(self):
        return str(self.id)
    class Meta:
        ordering = ['-id']


class ProposalDecision(models.Model):
    id = models.AutoField(primary_key=True)
    P = 'P'
    I = 'I'
    E = 'E'
    T = 'T'
    C = 'C'
    CHOICES = (
        (P, 'Pending'),
        (I, 'Ignored'),
        (E, 'Error'),
        (T, 'Triggered'),
        (C, 'Canceled'),
    )
    decision = models.CharField(max_length=32, choices=CHOICES, default=P)
    decision_reason = models.CharField(max_length=2056, blank=True, null=True)
    proposal = models.ForeignKey(ProposalSettings, on_delete=models.SET_NULL, blank=True, null=True)
    #associated_event_id = models.ForeignKey(PossibleEventAssociation, on_delete=models.SET_NULL, blank=True, null=True)
    event_group_id = models.ForeignKey(EventGroup, on_delete=models.SET_NULL, blank=True, null=True)
    trig_id = models.BigIntegerField(blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=32, blank=True, null=True)
    dec_dms = models.CharField(max_length=32, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        ordering = ['-id']


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    associated_event_id = models.ForeignKey(
        PossibleEventAssociation,
        on_delete=models.SET_NULL,
        related_name="voevent",
        blank=True,
        null=True,
    )
    event_group_id = models.ForeignKey(
        EventGroup,
        on_delete=models.SET_NULL,
        related_name="voevent",
        blank=True,
        null=True,
    )
    trig_id = models.BigIntegerField(blank=True, null=True)
    telescope = models.CharField(max_length=64, blank=True, null=True)
    sequence_num = models.IntegerField(blank=True, null=True)
    event_type = models.CharField(max_length=64, blank=True, null=True)
    role = models.CharField(max_length=64, blank=True, null=True)
    duration = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    ra_hms = models.CharField(max_length=64, blank=True, null=True)
    dec_dms = models.CharField(max_length=64, blank=True, null=True)
    pos_error = models.FloatField(blank=True, null=True)
    recieved_data = models.DateTimeField(auto_now_add=True, blank=True)
    event_observed = models.DateTimeField(blank=True, null=True)
    xml_packet = models.CharField(max_length=10000)
    ignored = models.BooleanField(default=True)
    source_name = models.CharField(max_length=128, blank=True, null=True)
    source_type = models.CharField(max_length=3, choices=SOURCE_CHOICES, null=True)
    fermi_most_likely_index = models.FloatField(blank=True, null=True)
    fermi_detection_prob = models.FloatField(blank=True, null=True)
    swift_rate_signif = models.FloatField(blank=True, null=True)
    antares_ranking = models.IntegerField(blank=True, null=True)

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
    name = models.CharField(max_length=64, blank=True, null=True, unique=True)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)


class AlertPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    proposal = models.ForeignKey(ProposalSettings, on_delete=models.CASCADE)
    alert = models.BooleanField(default=True)
    debug = models.BooleanField(default=False)
    approval = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.user}_{self.proposal.id}_{self.proposal.telescope}_{self.proposal.project_id}_Alerts"


class UserAlerts(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    proposal = models.ForeignKey(ProposalSettings, on_delete=models.CASCADE)
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
    obsid = models.CharField(max_length=128, primary_key=True)
    telescope = models.ForeignKey(Telescope, to_field="name", verbose_name="Telescope name", on_delete=models.CASCADE)
    proposal_decision_id = models.ForeignKey(ProposalDecision, on_delete=models.SET_NULL, blank=True, null=True)
    website_link = models.URLField(max_length=256)
    reason = models.CharField(max_length=256, blank=True, null=True)
