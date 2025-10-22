from django.apps import AppConfig

class ComplaintsConfig(AppConfig):
    """
    This class registers the 'complaints' app with Django.
    The 'name' attribute is critical.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'complaints' # This tells Django which app these settings are for

    def ready(self):
        """
        This method is called when the app is ready.
        It's where we import our signals.py file.
        """
        import complaints.signals # noqa