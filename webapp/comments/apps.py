from django.apps import AppConfig


class CommentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "comments"
    verbose_name = "댓글"

    def ready(self):
        # DEC-055 반복 거부 자동차단 신호 등록. 앱 레지스트리가 준비된
        # 뒤에만 import해야 하는 Django 표준 패턴(circular import 방지).
        from . import signals  # noqa: F401
