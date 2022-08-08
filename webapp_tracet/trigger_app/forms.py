
# import the standard Django Forms
# from built-in library
from django import forms

import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .models import UserAlerts, ProposalSettings, TelescopeProjectID
from .validators import atca_proposal_id, atca_freq_bands, mwa_proposal_id, mwa_freqspecs, mwa_horizon_limit

account_sid = os.environ.get('TWILIO_ACCOUNT_SID', None)
auth_token = os.environ.get('TWILIO_AUTH_TOKEN', None)

# creating a form
class UserAlertForm(forms.ModelForm):
    def clean(self):
        if self.cleaned_data['type'] == 1 or self.cleaned_data['type'] == 2:
            # Test that twilio can send a message to the user
            client = Client(account_sid, auth_token)
            try:
                message = client.messages.create(
                        to=self.cleaned_data['address'],
                        from_='+17755216557',
                        body="This is a test text message from TraceT",
                )
                print(f"MESAGESTART{message}MESSGAEEND")
            except TwilioRestException:
                raise forms.ValidationError("Error sending test text message. Please ensure you have included your area code and verified your number on Twilio as explained in https://tracet.readthedocs.io/en/latest/new_user.html#verifying-your-phone-number-on-twilio")

    # specify the name of model to use
    class Meta:
        model = UserAlerts
        fields = ['proposal', 'type', 'address', 'alert', 'debug', 'approval']


class ProjectSettingsForm(forms.ModelForm):
    def clean(self):
        # Check proposal ID
        if len(self.cleaned_data['proposal_id']) < 6 or self.cleaned_data['proposal_id'] is None:
            raise forms.ValidationError("Please create a proposal ID with at least 6 character")


        # Telescope specific validation
        if 'telescope' in self.cleaned_data.keys():
            telescope = self.cleaned_data['telescope']
            if str(telescope).startswith("MWA"):
                # MWA validation

                # Check the MWA frequency channel specifications are valid
                if self.cleaned_data['mwa_freqspecs']:
                    mwa_freqspecs(self.cleaned_data['mwa_freqspecs'])
                else:
                    raise forms.ValidationError({'mwa_freqspecs': "No Frequency channel Specifications suppled."})

                # Check user selected a horizon limit that won't be rejected by the MWA backend
                mwa_horizon_limit(self.cleaned_data['mwa_horizon_limit'])

            elif str(telescope) == "ATCA":
                # ATCA validation

                # Check user has chosen at least one band
                if not self.cleaned_data['atca_band_3mm'] and not self.cleaned_data['atca_band_7mm'] and \
                   not self.cleaned_data['atca_band_15mm'] and not self.cleaned_data['atca_band_4cm'] and \
                   not self.cleaned_data['atca_band_16cm']:
                    raise forms.ValidationError("Please choose at least 1 ATCA frequency band.")

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


    # specify the name of model to use
    class Meta:
        model = ProposalSettings
        fields = '__all__'

class TelescopeProjectIDForm(forms.ModelForm):
    def clean(self):
        # Make sure the project ID is works
        if 'telescope' in self.cleaned_data.keys():
            telescope = self.cleaned_data['telescope']
            if str(telescope).startswith("MWA"):
                mwa_proposal_id(self.cleaned_data['id'], self.cleaned_data['password'])
            elif str(telescope) == "ATCA":
                atca_proposal_id(
                    self.cleaned_data['id'],
                    self.cleaned_data['password'],
                    self.cleaned_data['atca_email'],
                )


    # specify the name of model to use
    class Meta:
        model = TelescopeProjectID
        fields = '__all__'


class TestEvent(forms.Form):
    #xml_file = forms.FileField()
    xml_packet = forms.CharField(max_length=10000, required=False)