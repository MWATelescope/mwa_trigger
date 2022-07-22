
from django.views.generic.list import ListView
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.db import transaction
from django.db import models as dj_model
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, InvalidPage
import django_filters

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from . import models, serializers, forms, signals
from .telescope_observe import trigger_observation

import sys
import voeventparse as vp
from astropy.coordinates import SkyCoord
from astropy import units as u
import datetime

from tracet import parse_xml
import atca_rapid_response_api as arrApi

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
        filter_overrides = {
            dj_model.CharField: {
                'filter_class': django_filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'icontains',
                },
            },
        }


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


class ProposalDecisionFilter(django_filters.FilterSet):
    recieved_data = django_filters.DateTimeFromToRangeFilter()

    class Meta:
        model = models.ProposalDecision
        fields = '__all__'


def ProposalDecisionList(request):
    # Apply filters
    f = ProposalDecisionFilter(request.GET, queryset=models.ProposalDecision.objects.all())
    ProposalDecision = f.qs

    # Get position error units
    poserr_unit = request.GET.get('poserr_unit', 'deg')

    # Paginate
    page = request.GET.get('page', 1)
    paginator = Paginator(ProposalDecision, 100)
    try:
        ProposalDecision = paginator.page(page)
    except InvalidPage:
        # if the page contains no results (EmptyPage exception) or
        # the page number is not an integer (PageNotAnInteger exception)
        # return the first page
        ProposalDecision = paginator.page(1)
    return render(request, 'trigger_app/proposaldecision_list.html', {'filter': f, "page_obj":ProposalDecision, "poserr_unit":poserr_unit})


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
    source_name_list = []
    for tevent in trigger_group_ids:
        trigger_group_voevents = voevents.filter(trigger_group_id=tevent)
        telescope_list.append(
            ' '.join(set(trigger_group_voevents.values_list('telescope', flat=True)))
        )
        sources = trigger_group_voevents.values_list('source_type', flat=True)
        # remove Nones
        sources =  [ i for i in sources if i ]
        if len(sources) > 0:
            source_list.append(' '.join(set(sources)))
        else:
            source_list.append(' ')
        source_name_list.append(trigger_group_voevents.first().source_name)


    # Paginate
    page = request.GET.get('page', 1)
    # zip the trigger event and the tevent_telescope_list together so I can loop over both in the html
    paginator = Paginator(list(zip(trigger_group_ids, telescope_list, source_list, source_name_list)), 100)
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


def home_page(request):
    comet_status = models.Status.objects.get(name='twistd_comet')
    prop_settings = models.ProposalSettings.objects.all()
    recent_triggers = models.TriggerID.objects.all()[:5]

    telescope_list = []
    source_name_list = []
    proposal_decision_list = []
    for trig in recent_triggers:
        trigger_group_voevents = models.VOEvent.objects.filter(trigger_group_id=trig)
        telescope_list.append(
            ' '.join(set(trigger_group_voevents.values_list('telescope', flat=True)))
        )
        source_name_list.append(trigger_group_voevents.first().source_name)
        # grab decision for each proposal
        decision_list = []
        for prop in prop_settings:
            this_decision = models.ProposalDecision.objects.filter(trigger_group_id=trig, proposal=prop)
            if this_decision.exists():
                decision_list.append(this_decision.first().get_decision_display())
            else:
                decision_list.append("")
        proposal_decision_list.append(decision_list)

    recent_triggers_info = list(zip(recent_triggers, telescope_list, source_name_list, proposal_decision_list))

    return render(request, 'trigger_app/home_page.html', {'twistd_comet_status': comet_status,
                                                          'settings':prop_settings,
                                                          'remotes':", ".join(settings.VOEVENT_REMOTES),
                                                          'tcps':", ".join(settings.VOEVENT_TCP),
                                                          "recent_triggers":recent_triggers_info})


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
    obs = []
    for prop_dec in prop_decs:
        obs += models.Observations.objects.filter(proposal_decision_id=prop_dec)

    # Get position error units
    poserr_unit = request.GET.get('poserr_unit', 'deg')

    return render(request, 'trigger_app/trigger_group_id_details.html', {'trigger_event':trigger_event,
                                                                     'voevents':voevents,
                                                                     'obs':obs,
                                                                     'prop_decs':prop_decs,
                                                                     'telescopes':telescopes,
                                                                     'poserr_unit':poserr_unit,})


def ProposalDecision_details(request, id):
    prop_dec = models.ProposalDecision.objects.get(id=id)

    # Work out all the telescopes that observed the event
    voevents = models.VOEvent.objects.filter(trigger_group_id=prop_dec.trigger_group_id)
    telescopes = []
    event_types = []
    for voevent in voevents:
        telescopes.append(voevent.telescope)
        event_types.append(voevent.event_type)
    # Make sure they are unique and put each on a new line
    telescopes = ".\n".join(list(set(telescopes)))
    event_types = " \n".join(list(set(event_types)))

    observations = models.Observations.objects.filter(proposal_decision_id=id)

    content = {
        'prop_dec':prop_dec,
        'telescopes':telescopes,
        'voevents': voevents,
        'event_types': event_types,
        'obs': observations,
    }
    return render(request, 'trigger_app/proposal_decision_details.html', content)


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
    if prop_set.source_type == "GRB":
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
  style N fill:orange,color:white'''
    else:
        mermaid_script += '''
  F[GRB] --> END'''
    if prop_set.source_type == "FS":
        mermaid_script += f'''
  E --> G[Flare Star] --> L[Trigger Observation]'''
    else:
        mermaid_script += '''
  E --> G[Flare Star] --> END'''
    if prop_set.source_type == "NU":
        mermaid_script += f'''
  E --> I[Neutrino]
  I[Neutrino] --> |Antares Event| RANK{{Is the Antares ranking less than or equal to {prop_set.antares_min_ranking}?}}
  RANK --> |YES| L[Trigger Observation]
  RANK --> |NO| END
  I[Neutrino] --> |Non-Antares Event| L[Trigger Observation]
subgraph NU
  I
  RANK
end'''
    else:
        mermaid_script += '''
  E --> I[Neutrino] --> END'''
    mermaid_script += '''
  E --> H[GW] --> END
  style A fill:blue,color:white
  style END fill:red,color:white
  style L fill:green,color:white
  style R fill:#21B6A8,color:white'''

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
        alert_permissions = models.AlertPermission.objects.get(user=u, proposal=prop)
        # Put them into a dict that can be looped over in the html
        prop_alert_list.append({
            "proposal":prop,
            "user":user_alerts,
            "permission":alert_permissions,
        })
    return render(request, 'trigger_app/user_alert_status.html', {'prop_alert_list': prop_alert_list})


@login_required
def user_alert_delete(request, id):
    u = request.user
    user_alert = models.UserAlerts.objects.get(user=u, id=id)
    user_alert.delete()
    return HttpResponseRedirect('/user_alert_status/')


@login_required
def user_alert_create(request):
    if request.POST:
        # Create UserAlert that already includes user and proposal
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


@login_required
def proposal_form(request, id=None):
    # grab source type telescope dict
    src_tele = parse_xml.SOURCE_TELESCOPES
    if id:
        proposal = models.ProposalSettings.objects.get(id=id)
        title = f"Editing Proposal #{id}"
    else:
        proposal = None
        title = "New Proposal"
    if request.POST:
        form = forms.ProjectSettingsForm(request.POST, instance=proposal)
        if form.is_valid():
            saved = form.save()
            # on success, the request is redirected as a GET
            return redirect(proposal_decision_path, id=saved.id)
    else:
        form = forms.ProjectSettingsForm(instance=proposal)
    return render(request, 'trigger_app/proposal_form.html', {'form':form, "src_tele": src_tele, "title":title})


def test_upload_xml(request):
    proposals = models.ProposalSettings.objects.filter(testing=False)
    if request.method == "POST":
        form = forms.TestVOEvent(request.POST)
        if form.is_valid():
            # Parse and submit the VOEvent
            xml_string = str(request.POST['xml_packet'])
            trig = parse_xml.parsed_VOEvent(None, packet=xml_string)
            logger.debug(trig.event_observed)
            logger.debug(type(trig.event_observed))
            models.VOEvent.objects.get_or_create(
                telescope=trig.telescope,
                xml_packet=xml_string,
                duration=trig.trig_duration,
                trigger_id=trig.trig_id,
                sequence_num=trig.sequence_num,
                event_type=trig.event_type,
                role=trig.role,
                ra=trig.ra,
                dec=trig.dec,
                ra_hms=trig.ra_hms,
                dec_dms=trig.dec_dms,
                pos_error=trig.err,
                ignored=trig.ignore,
                source_name=trig.source_name,
                source_type=trig.source_type,
                event_observed=datetime.datetime.strptime(str(trig.event_observed), "%Y-%m-%dT%H:%M:%S.%f"),
                fermi_most_likely_index=trig.fermi_most_likely_index,
                fermi_detection_prob=trig.fermi_detection_prob,
                swift_rate_signif=trig.swift_rate_signif,
                antares_ranking=trig.antares_ranking,
            )
            return HttpResponseRedirect('/')
    else:
        form = forms.TestVOEvent()
    return render(request, 'trigger_app/test_upload_xml_form.html', {'form': form, "proposals": proposals})


def cancel_atca_observation(request, id=None):
    # Grab obs and proposal data
    obs = models.Observations.objects.filter(obsid=id).first()
    proposal_settings = obs.proposal_decision_id.proposal
    trigger_message = obs.proposal_decision_id.decision_reason

    # Create the cancel request
    rapidObj = { 'requestDict': { 'cancel': obs.obsid, 'project': proposal_settings.project_id.id } }
    rapidObj["authenticationToken"] = proposal_settings.project_id.password
    rapidObj["email"] = proposal_settings.project_id.atca_email

    # Send the request.
    atca_request = arrApi.api(rapidObj)
    try:
        response = atca_request.send()
    except arrApi.responseError as r:
        logger.error(f"ATCA return message: {r}")
        trigger_message += f"ATCA cancel failed, return message: {r}\n "
        decision = 'E'
    else:
        trigger_message += f"ATCA observation canceled at {datetime.datetime.utcnow()}. \n"
        decision = 'C'
    # Update propocal decision
    proposal_decision = obs.proposal_decision_id
    proposal_decision.decision_reason = trigger_message
    proposal_decision.decision = decision
    proposal_decision.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))