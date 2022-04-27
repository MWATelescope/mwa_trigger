import os
# Configure settings for project
# Need to run this before calling models from application!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trigger_webapp.settings')
import django
# Import settings
django.setup()
from django.conf import settings

from subprocess import Popen, PIPE, call
import time
import glob

from trigger_app.models import CometLog, Status

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore

import logging
logger = logging.getLogger(__name__)


def output_popen_stdout(process):
    output = process.stdout.readline()
    logger.debug(f"output: {output}")
    if output:
        # New output so send it to the log
        CometLog.objects.create(log=output.strip().decode())
    comet_status = Status.objects.get(name='twistd_comet')
    poll = process.poll()
    logger.debug(f"poll: {poll}")
    if poll is None:
        # Process is still running
        comet_status.status = 0
    elif poll == 0:
        # Finished for some reason
        comet_status.status = 2
    else:
        # Broken
        comet_status.status = 1
    comet_status.save()


if __name__ == '__main__':
    # kill unterminated twistd jobs
    if os.path.exists("/tmp/twistd_comet.pid"):
        call("kill `cat /tmp/twistd_comet.pid`", shell=True)

    # Collect all the remote servers
    remote_command = ""
    for tc_id, remote in enumerate(settings.VOEVENT_REMOTES):
        remote_command += f"--remote={remote} "

    logger.info("Starting twistd")
    process = Popen(f"twistd --pidfile /tmp/twistd_comet.pid -n comet --local-ivo=ivo://hotwired.org/test {remote_command} --cmd=upload_xml.py", shell=True, stdout=PIPE)
    # get initial output right away
    output_popen_stdout(process)

    # Add the schedule job
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_job(
        output_popen_stdout,
        trigger=CronTrigger(second="*/59"),  # Every 60 seconds
        id="output_popen_stdout",
        max_instances=1,
        replace_existing=True,
        kwargs={
            'process':process,
        },
    )
    logger.info("Added job 'output_popen_stdout'.")

    logger.info("Starting scheduler...")
    scheduler.start()
    logger.info("I moved on")
    logger.info('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()