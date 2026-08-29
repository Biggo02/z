from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'properties'
    verbose_name = 'Logements'

    def ready(self):
        from .photo_optimization import install
        install()
