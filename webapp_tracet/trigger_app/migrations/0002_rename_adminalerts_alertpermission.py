# Generated by Django 4.0.4 on 2022-07-22 03:29

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trigger_app', '0001_squashed_0002_alter_telescopeprojectid_password'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='AdminAlerts',
            new_name='AlertPermission',
        ),
    ]