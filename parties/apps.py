from django.apps import AppConfig


class PartiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parties'

    # Django 앱 로딩 완료 시 시그널 모듈을 import해 receiver를 등록합니다.
    # 이 import가 없으면 @receiver 데코레이터가 실행되지 않아 실시간 이벤트가 동작하지 않습니다.
    def ready(self):
        import parties.signals