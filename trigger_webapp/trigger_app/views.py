
from django.views.generic.list import ListView
from .models import Trigger

class TriggerList(ListView):
    # specify the model for list view
    model = Trigger
