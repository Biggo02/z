from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'
    verbose_name = 'Administration Fasthome'

    def ready(self):
        # django.contrib.admin est placé avant dashboard dans INSTALLED_APPS,
        # donc son autodiscover a déjà enregistré les ModelAdmin à ce stade.
        from .admin_labels import apply_french_admin_labels
        apply_french_admin_labels()
