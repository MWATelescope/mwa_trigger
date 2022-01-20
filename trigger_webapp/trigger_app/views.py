
from django.views.generic.list import ListView
from django.conf import settings
from django.http import HttpResponse
from django.db import transaction
from django.shortcuts import render

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
import mimetypes

from . import models, serializers

import os
import voeventparse as vp
import logging
logger = logging.getLogger(__name__)

class VOEventList(ListView):
    # specify the model for list view
    model = models.VOEvent

class TriggerEventList(ListView):
    # specify the model for list view
    model = models.TriggerEvent

def home_page(request):
    return render(request, 'trigger_app/home_page.html', {})

def voevent_view(request, id):
    voevent = models.VOEvent.objects.get(id=id)
    v = vp.loads(voevent.xml_packet.encode())
    xml_pretty_str = vp.prettystr(v)
    print(xml_pretty_str)
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