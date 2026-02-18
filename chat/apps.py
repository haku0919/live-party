from django.apps import AppConfig


# chat 앱의 Django AppConfig임.
class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
