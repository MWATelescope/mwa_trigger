
# import the standard Django Forms
# from built-in library
from django import forms
from .models import UserAlerts, ProposalSettings
from .validators import atca_freq_bands

# creating a form
class UserAlertForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = UserAlerts
        fields = ['type', 'address', 'alert', 'debug', 'approval']


class ProjectSettingsForm(forms.ModelForm):
    def clean(self):
        # Validate that the user chose Frequency values within each band
        band1 = self.cleaned_data['atca_band_3mm']
        if band1:
            # min_freq, max_freq, freq, field_name
            atca_freq_bands(83000, 105000, self.cleaned_data['atca_band_3mm_freq1'], 'atca_band_3mm_freq1')
            atca_freq_bands(83000, 105000, self.cleaned_data['atca_band_3mm_freq2'], 'atca_band_3mm_freq2')
        band2 = self.cleaned_data['atca_band_7mm']
        if band2:
            atca_freq_bands(30000, 50000, self.cleaned_data['atca_band_7mm_freq1'], 'atca_band_7mm_freq1')
            atca_freq_bands(30000, 50000, self.cleaned_data['atca_band_7mm_freq2'], 'atca_band_7mm_freq2')
        band3 = self.cleaned_data['atca_band_15mm']
        if band3:
            atca_freq_bands(16000, 25000, self.cleaned_data['atca_band_15mm_freq1'], 'atca_band_15mm_freq1')
            atca_freq_bands(16000, 25000, self.cleaned_data['atca_band_15mm_freq2'], 'atca_band_15mm_freq2')
        band4 = self.cleaned_data['atca_band_4cm']
        if band4:
            atca_freq_bands(3900, 11000, self.cleaned_data['atca_band_4cm_freq1'], 'atca_band_4cm_freq1')
            atca_freq_bands(3900, 11000, self.cleaned_data['atca_band_4cm_freq2'], 'atca_band_4cm_freq2')

    # specify the name of model to use
    class Meta:
        model = ProposalSettings
        fields = '__all__'