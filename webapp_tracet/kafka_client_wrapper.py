from datetime import datetime
import os
import sys
# Configure settings for project
# Need to run this before calling models from application!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp_tracet.settings')

import django
# Import settings
django.setup()
from django.conf import settings
from asgiref.sync import sync_to_async
from subprocess import Popen, PIPE, call
import time
import glob
import asyncio
from trigger_app.models import CometLog, Status

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import logging

logger = logging.getLogger(__name__)


def output_popen_stdout(process):
    print("running output")
    output = process.stdout.readline()
    print(f"output: {output}")
    if output:
        print(output.strip().decode())
        # New output so send it to the log
        CometLog.objects.create(
            log=output.strip().decode())
    kafka_status = Status.objects.get(name='kafka')
    poll = process.poll()
    print(f"poll: {poll}")
    if poll is None:
        # Process is still running
        kafka_status.status = 0
    elif poll == 0:
        # Finished for some reason
        kafka_status.status = 2
    else:
        # Broken
        kafka_status.status = 1
    kafka_status.save()


def main():
    if __name__ == '__main__':
        print("Starting python command:")
        pidfilename = '/tmp/kafka.pid'

        if os.path.exists(pidfilename):
            call(f"kill `cat {pidfilename}`", shell=True)

        print("Starting python command:")
        python_command = sys.executable + " -u" + " kafka_client.py"
        process = Popen(
            python_command, shell=True, stdout=PIPE)
        # Write pid to file
        pidfile = open(pidfilename, 'w')
        pidfile.write(str(process.pid))
        pidfile.close()

        # print("OUTPUT CO ROUTINE")

        output_popen_stdout(process)

        # get initial output right away

        # Add the schedule job
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_job(
            output_popen_stdout,
            trigger=CronTrigger(second="*/5"),  # Every 5 seconds
            id="output_popen_stdout",
            max_instances=1,
            replace_existing=True,
            kwargs={
                'process': process,
            },
        )
        print("Added job 'output_popen_stdout'.")

        print("Starting scheduler...")
        scheduler.start()
        print("I moved on")
        print(
            'Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

        try:
            # This is here to simulate application activity (which keeps the main thread alive).
            while True:
                time.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            # Not strictly necessary if daemonic mode is enabled but should be done if possible
            scheduler.shutdown()


main()
