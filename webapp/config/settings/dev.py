import os

import dj_database_url

from .base import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# 실제 운영 시크릿을 절대 여기 하드코딩하지 않는다(03 §5.4). 이 값은 "로컬에서
# 바로 실행 가능"하도록 하는 개발 전용 기본값이며 DEBUG=True에서만 쓰인다.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-only-do-not-use-in-production"
)

ALLOWED_HOSTS = ["*"]

# DATABASE_URL 미설정 시 SQLite로 폴백한다. 로컬 Postgres로 테스트하고 싶으면
# .env에 DATABASE_URL=postgres://... 를 지정하면 코드 변경 없이 전환된다
# (WU-01 지시사항 §2, 02-planning.md 입력 계약).
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass
