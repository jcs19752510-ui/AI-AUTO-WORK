# 07단계(WU-09 통합테스트) 전용 임시 설정 모듈. WU-01/04/05/07/08과 동일
# 방법론: production.py를 그대로 상속하고 DATABASES만 SQLite로 재정의한다.
# 검증 완료 후 이 파일은 삭제한다.
from .production import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_wu09_integ_prodlike.sqlite3",  # noqa: F405
    }
}
