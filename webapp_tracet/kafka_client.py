from gcn_kafka import Consumer
import os
from upload_xml import write_and_upload
from datetime import datetime
import voeventparse
import os
# Configure settings for project
# Need to run this before calling models from application!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp_tracet.settings')
import django
# Import settings
django.setup()
from django.conf import settings
from trigger_app.models import CometLog, Status

# Environment variables
GCN_KAFKA_CLIENT = os.getenv('GCN_KAFKA_CLIENT')
GCN_KAFKA_SECRET = os.getenv('GCN_KAFKA_SECRET')

# Connect as a consumer.
# Warning: don't share the client secret with others.
consumer = Consumer(client_id=GCN_KAFKA_CLIENT,
                    client_secret=GCN_KAFKA_SECRET)

# Subscribe to topics and receive alerts
consumer.subscribe(['gcn.classic.voevent.AMON_NU_EM_COINC',
                    'gcn.classic.voevent.FERMI_GBM_ALERT',
                    'gcn.classic.voevent.FERMI_GBM_FIN_POS',
                    'gcn.classic.voevent.FERMI_GBM_FLT_POS',
                    'gcn.classic.voevent.FERMI_GBM_GND_POS',
                    'gcn.classic.voevent.FERMI_GBM_POS_TEST',
                    'gcn.classic.voevent.FERMI_GBM_SUBTHRESH',
                    'gcn.classic.voevent.FERMI_LAT_MONITOR',
                    'gcn.classic.voevent.FERMI_LAT_OFFLINE',
                    'gcn.classic.voevent.FERMI_LAT_POS_TEST',
                    'gcn.classic.voevent.FERMI_POINTDIR',
                    'gcn.classic.voevent.LVC_INITIAL',
                    'gcn.classic.voevent.LVC_PRELIMINARY',
                    'gcn.classic.voevent.LVC_RETRACTION',
                    'gcn.classic.voevent.SWIFT_ACTUAL_POINTDIR',
                    'gcn.classic.voevent.SWIFT_BAT_GRB_LC',
                    'gcn.classic.voevent.SWIFT_BAT_GRB_POS_ACK',
                    'gcn.classic.voevent.SWIFT_BAT_GRB_POS_TEST',
                    'gcn.classic.voevent.SWIFT_BAT_QL_POS',
                    'gcn.classic.voevent.SWIFT_BAT_SCALEDMAP',
                    'gcn.classic.voevent.SWIFT_BAT_TRANS',
                    'gcn.classic.voevent.SWIFT_FOM_OBS',
                    'gcn.classic.voevent.SWIFT_POINTDIR',
                    'gcn.classic.voevent.SWIFT_SC_SLEW',
                    'gcn.classic.voevent.SWIFT_TOO_FOM',
                    'gcn.classic.voevent.SWIFT_TOO_SC_SLEW',
                    'gcn.classic.voevent.SWIFT_UVOT_DBURST',
                    'gcn.classic.voevent.SWIFT_UVOT_DBURST_PROC',
                    'gcn.classic.voevent.SWIFT_UVOT_EMERGENCY',
                    'gcn.classic.voevent.SWIFT_UVOT_FCHART',
                    'gcn.classic.voevent.SWIFT_UVOT_FCHART_PROC',
                    'gcn.classic.voevent.SWIFT_UVOT_POS',
                    'gcn.classic.voevent.SWIFT_UVOT_POS_NACK',
                    'gcn.classic.voevent.SWIFT_XRT_CENTROID',
                    'gcn.classic.voevent.SWIFT_XRT_IMAGE',
                    'gcn.classic.voevent.SWIFT_XRT_IMAGE_PROC',
                    'gcn.classic.voevent.SWIFT_XRT_LC',
                    'gcn.classic.voevent.SWIFT_XRT_POSITION',
                    'gcn.classic.voevent.SWIFT_XRT_SPECTRUM',
                    'gcn.classic.voevent.SWIFT_XRT_SPECTRUM_PROC',
                    'gcn.classic.voevent.SWIFT_XRT_SPER',
                    'gcn.classic.voevent.SWIFT_XRT_SPER_PROC',
                    'gcn.classic.voevent.SWIFT_XRT_THRESHPIX',
                    'gcn.classic.voevent.SWIFT_XRT_THRESHPIX_PROC'])

date = datetime.today()

# 2023-03-09T02:43:10+0000
print(f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Started')
CometLog.objects.create(
    log=f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Started')
try:
    while True:
        for message in consumer.consume(timeout=1):
            value = message.value()
            date = datetime.today()
            v = voeventparse.loads(value)

            kafka_status = Status.objects.get(name='kafka')
            kafka_status.status = 0
            kafka_status.save()
            print(
                f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Recieved {v.attrib["ivorn"]}')
            CometLog.objects.create(
                log=f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Recieved {v.attrib["ivorn"]}')
            print(
                f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Uploading {v.attrib["ivorn"]}')
            CometLog.objects.create(
                log=f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Uploading {v.attrib["ivorn"]}')
            res = write_and_upload(value)
            print(
                f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Response {res.status_code} {res.reason}')
            CometLog.objects.create(
                log=f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Response {res.status_code} {res.reason}')
except:
    print(f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error')
    CometLog.objects.create(
        log=f'{date.strftime("%Y-%m-%dT%H:%M:%S+0000")} KAFKA Error')
    kafka_status = Status.objects.get(name='kafka')
    kafka_status.status = 2
    kafka_status.save()
