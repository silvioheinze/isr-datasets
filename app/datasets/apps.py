from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'datasets'
    verbose_name = 'Datasets'
    
    def ready(self):
        # Import signal handlers
        try:
            import datasets.signals
        except ImportError:
            pass