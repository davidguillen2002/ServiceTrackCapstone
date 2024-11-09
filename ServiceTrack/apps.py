# ServiceTrack/apps.py
from django.apps import AppConfig

class ServicetrackConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ServiceTrack'

    def ready(self):
        import ServiceTrack.signals