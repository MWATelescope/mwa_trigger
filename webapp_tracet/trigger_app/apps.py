from django.apps import AppConfig


class TriggerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trigger_app'
    def ready(self):
        import trigger_app.signals