"""WU-09, REQ-010 — Render 무료 티어 최초 슈퍼유저 계정 부트스트랩.

**왜 필요한가**: Render 공식 문서(render.com/docs/free "Other limitations",
2026-09-17 직접 조회)로 확인한 결과, Free 웹 서비스는 "Shell access via SSH
or the Render Dashboard"와 "Running one-off jobs"를 **지원하지 않는다**.
03 §6.3/DEC-011이 v1을 Render 무료 티어로 유지하기로 확정했으므로(스핀다운
UX 저하를 의도적으로 수용), 운영자가 배포된 인스턴스에 접속해 대화형으로
`python manage.py createsuperuser`를 실행할 방법이 없다. 반면 `build.sh`는
모든 요금제에서 배포마다 실행되는 빌드 단계이므로(이미 `migrate --noinput`이
증명), 이 커맨드를 빌드 단계에서 실행하는 것이 free 티어에서 유일하게
안전한 최초 계정 생성 경로다(webapp/ADMIN_ACCESS_GUIDE.md 참고).

**멱등성**: 슈퍼유저가 이미 하나라도 있으면 아무것도 하지 않는다 — 재배포마다
env var 값으로 비밀번호를 덮어써 운영자가 어드민에서 직접 바꾼 비밀번호를
조용히 되돌리는 사고를 막기 위함이다(최초 1회 부트스트랩 전용, 이후
비밀번호 변경/로테이션은 Wagtail 어드민 자체 기능으로 운영자가 직접 수행).

**비밀번호 정책 재사용**: `AUTH_PASSWORD_VALIDATORS`(config/settings/base.py,
03 §5.1)를 그대로 통과시켜, 약한 값이 담긴 환경변수로 슈퍼유저가 만들어지는
것을 막는다. 검증에 실패하면 배포 자체를 막지 않고(다른 배포 단계까지
연쇄로 실패시키는 것은 과도함) 경고만 남기고 건너뛴다 — 운영자가 값을
고쳐 다음 배포에서 재시도하면 된다.

**환경변수가 비어 있으면 조용히 건너뛴다**: 최초 배포 이후에는 이 값들을
Render 환경변수에서 지워도 되고(권장, ADMIN_ACCESS_GUIDE.md 참고), 지운다고
기존 계정에 영향이 없다 — R2/DATABASE_URL과 달리 이 기능은 앱 구동 자체의
필수 전제가 아니므로 `_require_env` 방식(production.py)을 쓰지 않는다.
"""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "환경변수 기반으로 최초 슈퍼유저 계정을 멱등하게 생성한다(WU-09, REQ-010)."

    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("슈퍼유저가 이미 존재합니다. 건너뜁니다.")
            return

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            self.stdout.write(
                "DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_PASSWORD가 설정되지 "
                "않아 슈퍼유저 생성을 건너뜁니다."
            )
            return

        try:
            validate_password(password)
        except ValidationError as exc:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_PASSWORD가 비밀번호 정책(AUTH_PASSWORD_VALIDATORS)을 "
                    "통과하지 못해 슈퍼유저를 생성하지 않습니다: " + "; ".join(exc.messages)
                )
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"슈퍼유저 '{username}' 계정을 생성했습니다."))
