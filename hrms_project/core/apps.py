from django.apps import AppConfig
from django.contrib import admin


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    def ready(self):
        # import signals to connect handlers
        try:
            import core.signals  # noqa: F401
        except Exception:
            # avoid import-time crash
            pass

        # Apply admin branding when the registry is ready
        try:
            admin.site.site_header = "RH PROCESS – Administration"
            admin.site.site_title = "RH PROCESS"
            admin.site.index_title = "Tableau de bord RH"
            admin.site.enable_nav_sidebar = False
        except Exception:
            # admin might not be installed in some contexts (e.g., certain tests)
            pass
