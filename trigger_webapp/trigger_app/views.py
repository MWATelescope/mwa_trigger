
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

from . import models, serializers, forms, signals
from .telescope_observe import trigger_observation

import os
import sys
import voeventparse as vp
from astropy.coordinates import SkyCoord
from astropy import units as u
import requests
import subprocess
import shutil

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

class ProjectSettingsList(ListView):
    # specify the model for list view
    model = models.ProjectSettings

class ProjectDecisionList(ListView):
    # specify the model for list view
    model = models.ProjectDecision


def home_page(request):
    comet_status = models.Status.objects.get(name='twistd_comet')
    settings = models.ProjectSettings.objects.all()
    return render(request, 'trigger_app/home_page.html', {'twistd_comet_status': comet_status,
                                                          'settings':settings})


def TriggerEvent_details(request, tid):
    trigger_event = models.TriggerEvent.objects.get(id=tid)
    # covert ra and dec to HH:MM:SS.SS format
    c = SkyCoord( trigger_event.ra, trigger_event.dec, frame='icrs', unit=(u.deg,u.deg))
    trigger_event.ra = c.ra.to_string(unit=u.hour, sep=':')
    trigger_event.dec = c.dec.to_string(unit=u.degree, sep=':')

    voevents = models.VOEvent.objects.filter(trigger_group_id=trigger_event)
    proj_decs = models.ProjectDecision.objects.filter(trigger_group_id=trigger_event)
    mwa_obs = []
    for proj_dec in proj_decs:
        mwa_obs += models.Observations.objects.filter(project_decision_id=proj_dec)
    return render(request, 'trigger_app/triggerevent_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'mwa_obs':mwa_obs,
                                                                     'proj_decs':proj_decs})


def ProjectDecision_details(request, id):
    proj_dec = models.ProjectDecision.objects.get(id=id)

    # Work out all the telescopes that observed the event
    voevents = models.VOEvent.objects.filter(trigger_group_id=proj_dec.trigger_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ".\n".join(list(set(telescopes)))

    return render(request, 'trigger_app/project_decision_details.html', {'proj_dec':proj_dec,
                                                                         'telescopes':telescopes})


def ProjectDecision_result(request, id, decision):
    proj_dec = models.ProjectDecision.objects.get(id=id)

    if decision:
        # Decision is True (1) so trigger an observation
        obs_decision, trigger_message = trigger_observation(
            proj_dec,
            f"{proj_dec.decision_reason}User decided to trigger. ",
            horizion_limit=proj_dec.project.horizon_limit,
            pretend=proj_dec.project.testing,
            reason="First Observation",
        )
        if obs_decision == 'E':
            # Error observing so send off debug
            trigger_bool = False
            debug_bool = True
        else:
            # Succesfully observed
            trigger_bool = True
            debug_bool = False

        proj_dec.decision_reason = trigger_message
        proj_dec.decision = obs_decision

        # send off alert messages to users and admins
        signals.send_all_alerts(trigger_bool, debug_bool, False, proj_dec)
    else:
        # False (0) so just update decision
        proj_dec.decision_reason += "User decided not to trigger. "
        proj_dec.decision = "I"
    proj_dec.save()

    return HttpResponseRedirect(f'/project_decision_details/{id}/')


def project_decision_path(request, id):
    proj_set = models.ProjectSettings.objects.get(id=id)
    telescope = "TODO"

    # Create decision tree flow diagram
    # Set up mermaid javascript
    mermaid_script = '''
flowchart TD
  A(VOEvent) --> B{Is Event from TODO?}
  B --> |YES| C{"Have we observed\nthis event before?"}
  B --> |NO| END(Ignore)
  C --> |YES| D{"Has the position improved\nenough to reobserve?"}
  D --> |YES| R(Reobserve)
  C --> |NO| E{Source type?}
  D --> |NO| END
  E --> F[GRB]'''
    if proj_set.grb:
        mermaid_script += f'''
  F --> J{{"Fermi GRB probability > {proj_set.fermi_prob}\\nor\\nSWIFT Rate_signif > {proj_set.swift_rate_signf} sigma"}}
  J --> |YES| K{{"Trigger duration between\n {proj_set.trig_min_duration} and {proj_set.trig_max_duration} s"}}
  J --> |NO| END
  K --> |YES| L[Trigger Observation]
  K --> |NO| M{{"Trigger duration between\n{proj_set.pending_min_duration} and {proj_set.pending_max_duration} s"}}
  M --> |YES| N[Pending a human's decision]
  M --> |NO| END
subgraph GRB
  J
  K
  L
  M
  N
end
  style L fill:green,color:white
  style N fill:orange,color:white'''
    else:
        mermaid_script += '''
  F[GRB] --> END'''
    mermaid_script += '''
  E --> G[Flare Star] --> END
  E --> H[GW] --> END
  E --> I[Neutrino] --> END
  style A fill:blue,color:white
  style END fill:red,color:white'''

    return render(request, 'trigger_app/project_decision_path.html', {'image_loc':f'images/project_decision_path_{id}.png',
                                                                      'project':proj_set,
                                                                      'mermaid_script':mermaid_script})


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