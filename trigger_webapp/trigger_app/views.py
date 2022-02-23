
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

class ProposalSettingsList(ListView):
    # specify the model for list view
    model = models.ProposalSettings

class ProposalDecisionList(ListView):
    # specify the model for list view
    model = models.ProposalDecision


def home_page(request):
    comet_status = models.Status.objects.get(name='twistd_comet')
    settings = models.ProposalSettings.objects.all()
    return render(request, 'trigger_app/home_page.html', {'twistd_comet_status': comet_status,
                                                          'settings':settings})


def TriggerEvent_details(request, tid):
    trigger_event = models.TriggerEvent.objects.get(id=tid)
    # covert ra and dec to HH:MM:SS.SS format
    c = SkyCoord( trigger_event.ra, trigger_event.dec, frame='icrs', unit=(u.deg,u.deg))
    trigger_event.ra = c.ra.to_string(unit=u.hour, sep=':')
    trigger_event.dec = c.dec.to_string(unit=u.degree, sep=':')

    voevents = models.VOEvent.objects.filter(trigger_group_id=trigger_event)
    prop_decs = models.ProposalDecision.objects.filter(trigger_group_id=trigger_event)
    mwa_obs = []
    for prop_dec in prop_decs:
        mwa_obs += models.Observations.objects.filter(proposal_decision_id=prop_dec)
    return render(request, 'trigger_app/triggerevent_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'mwa_obs':mwa_obs,
                                                                     'prop_decs':prop_decs})


def ProposalDecision_details(request, id):
    prop_dec = models.ProposalDecision.objects.get(id=id)

    # Work out all the telescopes that observed the event
    voevents = models.VOEvent.objects.filter(trigger_group_id=prop_dec.trigger_group_id)
    telescopes = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
    # Make sure they are unique and put each on a new line
    telescopes = ".\n".join(list(set(telescopes)))

    return render(request, 'trigger_app/proposal_decision_details.html', {'prop_dec':prop_dec,
                                                                         'telescopes':telescopes})


def ProposalDecision_result(request, id, decision):
    prop_dec = models.ProposalDecision.objects.get(id=id)

    if decision:
        # Decision is True (1) so trigger an observation
        obs_decision, trigger_message = trigger_observation(
            prop_dec,
            f"{prop_dec.decision_reason}User decided to trigger. ",
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

        prop_dec.decision_reason = trigger_message
        prop_dec.decision = obs_decision

        # send off alert messages to users and admins
        signals.send_all_alerts(trigger_bool, debug_bool, False, prop_dec)
    else:
        # False (0) so just update decision
        prop_dec.decision_reason += "User decided not to trigger. "
        prop_dec.decision = "I"
    prop_dec.save()

    return HttpResponseRedirect(f'/proposal_decision_details/{id}/')


def proposal_decision_path(request, id):
    prop_set = models.ProposalSettings.objects.get(id=id)
    telescope = prop_set.event_telescope

    # Create decision tree flow diagram
    # Set up mermaid javascript
    mermaid_script = '''flowchart TD
  A(VOEvent) --> B{"Have we observed\nthis event before?"}
  B --> |YES| D{"Has the position improved\nenough to repoint?"}
  D --> |YES| R(Repoint)
  D --> |NO| END(Ignore)'''
    if telescope is None:
        mermaid_script += '''
  B --> |NO| E{Source type?}'''
    else:
        mermaid_script += f'''
  B --> |NO| C{{Is Event from {telescope}?}}
  C --> |NO| END
  C --> |YES| E{{Source type?}}'''
    mermaid_script += '''
  E --> F[GRB]'''
    if prop_set.grb:
        mermaid_script += f'''
  F --> J{{"Fermi GRB probability > {prop_set.fermi_prob}\\nor\\nSWIFT Rate_signif > {prop_set.swift_rate_signf} sigma"}}
  J --> |YES| K{{"Trigger duration between\n {prop_set.trig_min_duration} and {prop_set.trig_max_duration} s"}}
  J --> |NO| END
  K --> |YES| L[Trigger Observation]
  K --> |NO| M{{"Trigger duration between\n{prop_set.pending_min_duration_1} and {prop_set.pending_max_duration_1} s\nor\n{prop_set.pending_min_duration_2} and {prop_set.pending_max_duration_2} s"}}
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

    return render(request, 'trigger_app/proposal_decision_path.html', {'proposal':prop_set,
                                                                       'mermaid_script':mermaid_script})


@login_required
def user_alert_status(request):
    proposals = models.ProposalSettings.objects.all()
    prop_alert_list = []
    for prop in proposals:
        # For each proposals find the user and admin alerts
        u = request.user
        user_alerts = models.UserAlerts.objects.filter(user=u, proposal=prop)
        admin_alerts = models.AdminAlerts.objects.get(user=u, proposal=prop)
        # Put them into a dict that can be looped over in the html
        prop_alert_list.append({
            "proposal":prop,
            "user":user_alerts,
            "admin":admin_alerts,
        })
    return render(request, 'trigger_app/user_alert_status.html', {'prop_alert_list': prop_alert_list})


@login_required
def user_alert_delete(request, id):
    u = request.user
    user_alert = models.UserAlerts.objects.get(user=u, id=id)
    user_alert.delete()
    return HttpResponseRedirect('/user_alert_status/')


@login_required
def user_alert_create(request, id):
    if request.POST:
        # Create UserAlert that already includes user and proposal
        u = request.user
        prop = models.ProposalSettings.objects.get(id=id)
        ua = models.UserAlerts(user=u, proposal=prop)
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