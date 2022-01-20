
from django.views.generic.list import ListView
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from . import models, serializers
import mimetypes
import os
import voeventparse as vp

class VOEventList(ListView):
    # specify the model for list view
    model = models.VOEvent

def voevent_view(request, id):
    voevent = models.VOEvent.objects.get(id=id)
    v = vp.loads(voevent.xml_packet.encode())
    xml_pretty_str = vp.prettystr(v)
    print(xml_pretty_str)
    return HttpResponse(xml_pretty_str, content_type='text/xml')

# def download_file(request, filepath):
#     # fill these variables with real values
#     fl_path = os.path.join(settings.MEDIA_ROOT, filepath)

#     fl = open(fl_path, 'r')
#     mime_type, _ = mimetypes.guess_type(fl_path)
#     response = HttpResponse(fl, content_type=mime_type)
#     response['Content-Disposition'] = "attachment; filename=%s" % filepath
#     return response