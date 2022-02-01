
from django.views.generic.list import ListView
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
import mimetypes

from . import models, serializers, forms

import os
import sys
import voeventparse as vp
import logging
logger = logging.getLogger(__name__)

# Create a startup signal
from trigger_app.signals import startup_signal

if len(sys.argv) >= 2:
    if sys.argv[1] == 'runserver':
        # Send off start up signal because server is launching
        startup_signal.send(sender=startup_signal)

class VOEventList(ListView):
    # specify the model for list view
    model = models.VOEvent

class TriggerEventList(ListView):
    # specify the model for list view
    model = models.TriggerEvent

class CometLogList(ListView):
    # specify the model for list view
    model = models.CometLog


def home_page(request):
    comet_status = models.Status.objects.get(name='twistd_comet')
    settings = models.TriggerSettings.objects.all()
    return render(request, 'trigger_app/home_page.html', {'twistd_comet_status': comet_status,
                                                          'settings':settings})


def TriggerEvent_details(request, tid):
    trigger_event = models.TriggerEvent.objects.get(id=tid)
    voevents = models.VOEvent.objects.filter(trigger_group_id=trigger_event)
    mwa_obs = models.MWAObservations.objects.filter(trigger_group_id=trigger_event)
    return render(request, 'trigger_app/triggerevent_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'mwa_obs':mwa_obs})


@login_required
def user_alert_status(request):
    u = request.user
    admin_alerts = models.AdminAlerts.objects.get(user=u)
    user_alerts = models.UserAlerts.objects.filter(user=u)
    return render(request, 'trigger_app/user_alert_status.html', {'admin_alerts': admin_alerts,
                                                                  'user_alerts' : user_alerts})


@login_required
def user_alert_delete(request, id):
    u = request.user
    user_alert = models.UserAlerts.objects.get(user=u, id=id)
    user_alert.delete()
    return HttpResponseRedirect('/user_alert_status/')


@login_required
def user_alert_create(request):
    if request.POST:
        # Create UserAlert that already includes user
        u = request.user
        ua = models.UserAlerts(user=u)
        # Let user update everything else
        form = forms.UserAlertForm(request.POST, instance=ua)
        if form.is_valid():
            try:
                form.save()
                # on success, the request is redirected as a GET
                return HttpResponseRedirect('/user_alert_status/')
            except:
                pass # handling can go here
    else:
        form = forms.UserAlertForm()
    return render(request, 'trigger_app/form.html', {'form':form})


def voevent_view(request, id):
    voevent = models.VOEvent.objects.get(id=id)
    v = vp.loads(voevent.xml_packet.encode())
    xml_pretty_str = vp.prettystr(v)
    return HttpResponse(xml_pretty_str, content_type='text/xml')


@api_view(['POST'])
@transaction.atomic
def voevent_create(request):
    voe = serializers.VOEventSerializer(data=request.data)
    if voe.is_valid():
        voe.save()
        return Response(voe.data, status=status.HTTP_201_CREATED)
    logger.debug(request.data)
    return Response(voe.errors, status=status.HTTP_400_BAD_REQUEST)

# def download_file(request, filepath):
#     # fill these variables with real values
#     fl_path = os.path.join(settings.MEDIA_ROOT, filepath)

#     fl = open(fl_path, 'r')
#     mime_type, _ = mimetypes.guess_type(fl_path)
#     response = HttpResponse(fl, content_type=mime_type)
#     response['Content-Disposition'] = "attachment; filename=%s" % filepath
#     return response