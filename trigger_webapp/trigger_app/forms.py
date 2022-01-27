
# import the standard Django Forms
# from built-in library
from django import forms
from .models import UserAlerts

# creating a form
class UserAlertForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = UserAlerts
        fields = ['type', 'address', 'alert', 'debug', 'approval']