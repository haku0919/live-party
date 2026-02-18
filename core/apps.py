from django.apps import AppConfig


# core 앱의 Django AppConfig임.
class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
