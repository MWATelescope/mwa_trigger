
from django.views.generic.list import ListView
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db.models import Count, Q, F, Value, Subquery, OuterRef, CharField
from django.db.models.functions import Concat
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.postgres.aggregates import StringAgg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger, InvalidPage
from sqlalchemy import subquery
import django_filters

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

if 'runserver' in sys.argv:
    # Send off start up signal because server is launching in development
    startup_signal.send(sender=startup_signal)

class VOEventFilter(django_filters.FilterSet):
    recieved_data = django_filters.DateTimeFromToRangeFilter()
    event_observed = django_filters.DateTimeFromToRangeFilter()

    duration__lte = django_filters.NumberFilter(field_name='duration', lookup_expr='lte')
    duration__gte = django_filters.NumberFilter(field_name='duration', lookup_expr='gte')

    ra__lte = django_filters.NumberFilter(field_name='ra', lookup_expr='lte')
    ra__gte = django_filters.NumberFilter(field_name='ra', lookup_expr='gte')

    dec__lte = django_filters.NumberFilter(field_name='dec', lookup_expr='lte')
    dec__gte = django_filters.NumberFilter(field_name='dec', lookup_expr='gte')

    pos_error__lte = django_filters.NumberFilter(field_name='pos_error', lookup_expr='lte')
    pos_error__gte = django_filters.NumberFilter(field_name='pos_error', lookup_expr='gte')

    fermi_detection_prob__lte = django_filters.NumberFilter(field_name='fermi_detection_prob', lookup_expr='lte')
    fermi_detection_prob__gte = django_filters.NumberFilter(field_name='fermi_detection_prob', lookup_expr='gte')

    swift_rate_signif__lte = django_filters.NumberFilter(field_name='swift_rate_signif', lookup_expr='lte')
    swift_rate_signif__gte = django_filters.NumberFilter(field_name='swift_rate_signif', lookup_expr='gte')

    class Meta:
        model = models.VOEvent
        fields = '__all__'


def VOEventList(request):
    # Apply filters
    f = VOEventFilter(request.GET, queryset=models.VOEvent.objects.all())
    voevents = f.qs

    # Get position error units
    poserr_unit = request.GET.get('poserr_unit', 'deg')

    # Paginate
    page = request.GET.get('page', 1)
    paginator = Paginator(voevents, 100)
    try:
        voevents = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        voevents = paginator.page(1)
    return render(request, 'trigger_app/voevent_list.html', {'filter': f, "page_obj":voevents, "poserr_unit":poserr_unit})

def PossibleEventAssociationList(request):
    # Find all telescopes for each trigger event
    voevents = models.VOEvent.objects.filter(ignored=False)
    trigger_event = models.PossibleEventAssociation.objects.all()

    # Loop over the trigger events and grab all the telescopes of the VOEvents
    tevent_telescope_list = []
    for tevent in trigger_event:
        tevent_telescope_list.append(
            ' '.join(
                set(voevents.filter(associated_event_id=tevent).values_list('telescope', flat=True))
            )
        )

    # Paginate
    page = request.GET.get('page', 1)
    # zip the trigger event and the tevent_telescope_list together so I can loop over both in the html
    paginator = Paginator(list(zip(trigger_event, tevent_telescope_list)), 100)
    try:
        object_list = paginator.page(page)
    except InvalidPage:
        object_list = paginator.page(1)
    return render(request, 'trigger_app/possible_event_association_list.html', {'object_list':object_list})


def TriggerIDList(request):
    # Find all telescopes for each trigger event
    trigger_group_ids = models.TriggerID.objects.all()
    voevents = models.VOEvent.objects.all()

    # Loop over the trigger events and grab all the telescopes and soruces of the VOEvents
    telescope_list = []
    source_list = []
    for tevent in trigger_group_ids:
        telescope_list.append(
            ' '.join(set(voevents.filter(trigger_group_id=tevent).values_list('telescope', flat=True)))
        )
        sources = voevents.filter(trigger_group_id=tevent).values_list('source_type', flat=True)
        # remove Nones
        sources =  [ i for i in sources if i ]
        if len(sources) > 0:
            source_list.append(' '.join(set(sources)))
        else:
            source_list.append(' ')


    # Paginate
    page = request.GET.get('page', 1)
    # zip the trigger event and the tevent_telescope_list together so I can loop over both in the html
    paginator = Paginator(list(zip(trigger_group_ids, telescope_list, source_list)), 100)
    try:
        object_list = paginator.page(page)
    except InvalidPage:
        object_list = paginator.page(1)
    return render(request, 'trigger_app/trigger_group_id_list.html', {'object_list':object_list})


class CometLogList(ListView):
    model = models.CometLog
    paginate_by = 100

class ProposalSettingsList(ListView):
    model = models.ProposalSettings

class ProposalDecisionList(ListView):
    model = models.ProposalDecision
    paginate_by = 100


def home_page(request):
    comet_status = models.Status.objects.get(name='twistd_comet')
    prop_settings = models.ProposalSettings.objects.all()
    return render(request, 'trigger_app/home_page.html', {'twistd_comet_status': comet_status,
                                                          'settings':prop_settings,
                                                          'remotes':", ".join(settings.VOEVENT_REMOTES),
                                                          'tcps':", ".join(settings.VOEVENT_TCP)})


def PossibleEventAssociation_details(request, tid):
    trigger_event = models.PossibleEventAssociation.objects.get(id=tid)

    # covert ra and dec to HH:MM:SS.SS format
    c = SkyCoord( trigger_event.ra, trigger_event.dec, frame='icrs', unit=(u.deg,u.deg))
    trigger_event.ra = c.ra.to_string(unit=u.hour, sep=':')
    trigger_event.dec = c.dec.to_string(unit=u.degree, sep=':')

    # grab telescope names
    voevents = models.VOEvent.objects.filter(associated_event_id=trigger_event)
    telescopes = ' '.join(set(voevents.values_list('telescope', flat=True)))

    # grab event ID
    event_id = list(dict.fromkeys(voevents.values_list('trigger_id')))[0][0]

    # list all voevents with the same id
    if event_id:
        event_id_voevents = models.VOEvent.objects.filter(trigger_id=event_id)
    else:
        event_id_voevents = []

    # Get position error units
    poserr_unit = request.GET.get('poserr_unit', 'deg')

    return render(request, 'trigger_app/possible_event_association_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'telescopes':telescopes,
                                                                     'event_id':event_id,
                                                                     'event_id_voevents':event_id_voevents,
                                                                     'poserr_unit':poserr_unit,})


def TriggerID_details(request, tid):
    trigger_event = models.TriggerID.objects.get(id=tid)

    # grab telescope names
    voevents = models.VOEvent.objects.filter(trigger_group_id=trigger_event)
    telescopes = ' '.join(set(voevents.values_list('telescope', flat=True)))

    # list all prop decisions
    prop_decs = models.ProposalDecision.objects.filter(trigger_group_id=trigger_event)

    # Grab MWA obs if the exist
    mwa_obs = []
    for prop_dec in prop_decs:
        mwa_obs += models.Observations.objects.filter(proposal_decision_id=prop_dec)

    # Get position error units
    poserr_unit = request.GET.get('poserr_unit', 'deg')

    return render(request, 'trigger_app/trigger_group_id_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'mwa_obs':mwa_obs,
                                                                     'prop_decs':prop_decs,
                                                                     'telescopes':telescopes,
                                                                     'poserr_unit':poserr_unit,})


def ProposalDecision_details(request, id):
    prop_dec = models.ProposalDecision.objects.get(id=id)

    # Work out all the telescopes that observed the event
    voevents = models.VOEvent.objects.filter(associated_event_id=prop_dec.associated_event_id)
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
    mermaid_script = f'''flowchart TD
  A(VOEvent) --> B{{"Have we observed\nthis event before?"}}
  B --> |YES| D{{"Is the new event further away than\nthe repointing limit ({prop_set.repointing_limit} degrees)?"}}
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
  style N fill:orange,color:white
  style R fill:#21B6A8,color:white'''
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