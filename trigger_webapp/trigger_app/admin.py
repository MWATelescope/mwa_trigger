from django.contrib import admin
from trigger_app.models import VOEvent, TriggerEvent, AdminAlerts, ProjectSettings

# Register your models here.
admin.site.register(VOEvent)
admin.site.register(TriggerEvent)
admin.site.register(AdminAlerts)
admin.site.register(ProjectSettings)
