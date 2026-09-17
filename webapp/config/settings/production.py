import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False


def _require_env(name):
    value = os.environ.get(name)
    if not value:
        raise ImproperlyConfigured(f"{name} environment variable is required in production.")
    return value


SECRET_KEY = _require_env("SECRET_KEY")

# Render가 자동 주입하는 호스트명(03 §2.4) + 운영자가 직접 지정하는 추가 호스트.
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS += [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

# CSRF_TRUSTED_ORIGINS는 반드시 ALLOWED_HOSTS(Render 도메인 + 운영자 지정
# 커스텀 도메인)에서만 파생시킨다 — 목록 밖 오리진을 하드코딩으로 추가하지
# 않아 임의 오리진이 CSRF 신뢰 목록에 끼어들 여지를 원천 차단한다
# (03 §5.5.3 CSRF_TRUSTED_ORIGINS 요구사항).
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

# Render는 원본 Host 헤더를 변경하지 않고 그대로 전달하는 단일 홉 투명
# 프록시다(03 §5.5.3 IT-04 실측 확인). USE_X_FORWARDED_HOST를 불필요하게
# True로 켜면 X-Forwarded-Host가 새로운 스푸핑 경로가 될 수 있으므로 켜지
# 않고 기본값(False)을 유지한다.

if RENDER_EXTERNAL_HOSTNAME:
    WAGTAILADMIN_BASE_URL = f"https://{RENDER_EXTERNAL_HOSTNAME}"  # noqa: F405

# Neon PostgreSQL 필수 연결 (DEC-004). CONN_MAX_AGE=0은 Neon scale-to-zero
# 콜드스타트와 장시간 유지 연결이 충돌하지 않도록 보수적으로 설정한 것이다
# (03 §6.4). Neon 대시보드에서 pooled connection string 제공 여부는 실제 Neon
# 프로젝트가 생성되는 배포 단계(10~12단계)에서 재확인 필요(03 §6.4 확인 필요 항목,
# 아직 미해결로 이월).
DATABASE_URL = _require_env("DATABASE_URL")
DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=0,
        ssl_require=True,
    )
}

# 전송 보안 (03 §5.5) — Render는 관리형 TLS를 기본 제공하므로 HTTPS를 강제한다.
#
# Render 엣지가 TLS를 종료하고 앱에는 평문 HTTP로 전달하므로(03 §5.5.1),
# X-Forwarded-Proto 헤더를 신뢰하도록 명시해야 한다. 이게 없으면
# request.is_secure()가 항상 False로 판정되어 SECURE_SSL_REDIRECT=True와
# 결합해 무한 리다이렉트 루프가 발생한다(DEF-001, feature-WU-01-integration-test.md
# IT-02/IT-03). 이 헤더를 신뢰하는 것은 앱 컨테이너가 Render 엣지로부터만
# 트래픽을 받는 단일 홉 구조에서만 안전하다(03 §5.5.2 신뢰 경계 주의).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS는 배포 후 HTTPS가 안정적으로 동작함을 확인한 뒤 값을 늘려간다(1주 -> 이후 1년).
# 처음부터 max-age를 길게 잡으면 문제가 생겼을 때 되돌리기 어렵기 때문(브라우저 캐시).
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# 클라이언트 실제 IP 처리 (03 §5.5.4, Medium) — REMOTE_ADDR이 Render 엣지의
# 내부 IP로 고정되는 것을 막기 위해 X-Forwarded-For의 rightmost 값을
# REMOTE_ADDR로 재설정한다. WU-07(뉴스레터 스팸 방지)/WU-09(로그인
# 레이트리밋)가 이 값을 그대로 신뢰해 쓸 수 있도록 미들웨어 체인 가장
# 앞단에 둔다(SecurityMiddleware 등 이후 단계가 올바른 REMOTE_ADDR을 보도록).
MIDDLEWARE = ["config.middleware.XForwardedForMiddleware", *MIDDLEWARE]  # noqa: F405

# Cloudflare R2(S3 호환) — media-public 버킷 (03 §2.3, DEC-008). 실제 버킷/키는
# 아직 발급되지 않았으므로 환경변수가 비어 있으면 애플리케이션 기동 시점에만
# 값이 없다는 사실이 드러난다(원칙: 값은 여기서 추측/하드코딩하지 않는다).
AWS_ACCESS_KEY_ID = _require_env("R2_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _require_env("R2_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = _require_env("R2_BUCKET_NAME")
AWS_S3_ENDPOINT_URL = _require_env("R2_ENDPOINT_URL")
AWS_S3_REGION_NAME = os.environ.get("R2_REGION", "auto")
AWS_S3_CUSTOM_DOMAIN = os.environ.get("R2_PUBLIC_BASE_URL") or None
# R2는 S3의 오브젝트 ACL 헤더를 지원하지 않는다(버킷 자체의 공개 설정으로 대신함,
# 03 §2.3 버킷 분리). ACL을 보내면 Cloudflare가 요청을 거부하므로 반드시 None.
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

STORAGES["default"] = {  # noqa: F405
    "BACKEND": "storages.backends.s3.S3Storage",
}
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}

# 백업 전용 버킷(backup-private, 03 §2.3 버킷 분리/DEC-008, DEC-010 백업
# 아키텍처) — media-public과 물리적으로 분리된 별도 버킷이므로, 버킷 정책
# 실수 한 번으로 백업이 인터넷에 공개 노출되는 사고를 구조적으로 막는다.
# 이번 WU(WU-03)는 STORAGES 별칭 골격만 구성한다: 실제 pg_dump 백업
# 업로드/GitHub Actions 워크플로 구현은 WU-10 범위다. 버킷이 아직 발급되지
# 않았을 수 있으므로(R2_BACKUP_BUCKET_NAME 미설정) default 스토리지처럼
# _require_env로 기동을 막지 않는다 — 지금은 아무 코드도 이 별칭을 쓰지
# 않기 때문에, 값이 없다고 기동을 실패시키는 것은 불필요한 운영 마찰이다.
R2_BACKUP_BUCKET_NAME = os.environ.get("R2_BACKUP_BUCKET_NAME")
if R2_BACKUP_BUCKET_NAME:
    STORAGES["backup"] = {  # noqa: F405
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": R2_BACKUP_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "region_name": AWS_S3_REGION_NAME,
            # 최소 권한 원칙: 백업 버킷 전용 자격증명이 별도로 발급되면 그
            # 값을 쓴다. 아직 없으면(v1 시점) media-public용 자격증명을
            # 임시로 재사용하되, WU-10 착수 시 버킷 범위가 분리된 별도
            # R2 API 토큰 발급을 반드시 재검토할 것(단일 자격증명이 두
            # 버킷 모두에 접근 가능하면 버킷 분리의 장애 격리 이점이
            # 자격증명 유출 시나리오에서는 상쇄된다).
            "access_key": os.environ.get("R2_BACKUP_ACCESS_KEY_ID") or AWS_ACCESS_KEY_ID,
            "secret_key": os.environ.get("R2_BACKUP_SECRET_ACCESS_KEY") or AWS_SECRET_ACCESS_KEY,
            "default_acl": None,
            "querystring_auth": False,
        },
    }

try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass
