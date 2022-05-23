
# import the standard Django Forms
# from built-in library
from django import forms
from .models import UserAlerts, ProposalSettings
from .validators import atca_freq_bands, mwa_proposal_id, mwa_freqspecs

# creating a form
class UserAlertForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = UserAlerts
        fields = ['type', 'address', 'alert', 'debug', 'approval']


class ProjectSettingsForm(forms.ModelForm):
    def clean(self):
        # Validate that the user chose ATCA Frequency values within each band
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


        # Make sure the project ID is works
        if 'telescope' in self.cleaned_data.keys():
            telescope = self.cleaned_data['telescope']
            if str(telescope).startswith("MWA"):
                mwa_proposal_id(self.cleaned_data['project_id'])

                # Check the MWA frequency channel specifications are valid
                if self.cleaned_data['mwa_freqspecs']:
                    mwa_freqspecs(self.cleaned_data['mwa_freqspecs'])
                else:
                    raise forms.ValidationError({'mwa_freqspecs': "No Frequency channel Specifications suppled."})
            elif str(telescope) == "ATCA":
                if not self.cleaned_data['atca_band_3mm'] and not self.cleaned_data['atca_band_7mm'] and \
                   not self.cleaned_data['atca_band_15mm'] and not self.cleaned_data['atca_band_4cm'] and \
                   not self.cleaned_data['atca_band_16cm']:
                    raise forms.ValidationError("Please choose at least 1 ATCA frequency band.")
                # TODO also check ATCA's project ID


    # specify the name of model to use
    class Meta:
        model = ProposalSettings
        fields = '__all__'