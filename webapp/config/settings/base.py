"""
Django settings shared by all environments.

Env-specific overrides live in dev.py / production.py (03-system-design.md
§2.4 dj-database-url/Render 표준 관례 및 WU-01 지시사항 §1에 따른 base/dev/
production 분리).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_DIR.parent

# .env는 로컬 개발 편의용이다. Render/GitHub Actions 등 실제 배포 환경은 플랫폼이
# 주입하는 실제 환경변수를 그대로 사용하고 .env 파일을 두지 않는다 (03 §5.4).
load_dotenv(BASE_DIR / ".env")


# Application definition

INSTALLED_APPS = [
    "core",
    "blog",
    "custom_images",
    "legal",
    "subscribers",
    "home",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.sitemaps",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django_filters",
    "django.contrib.admin",
    "django.contrib.sitemaps",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    # WU-08, REQ-012 — 요청량/응답시간 경량 집계(core/monitoring.py). 응답
    # 시간을 최대한 온전히 재는 것이 목적이므로 맨 앞(다른 미들웨어를 전부
    # 감싸는 위치)에 둔다. production.py가 XForwardedForMiddleware를 이
    # 리스트 맨 앞에 다시 prepend하므로, 최종 실행 순서는 XFF(요청 IP 정규화,
    # 거의 즉시 끝남) -> RequestMetrics(그 이후 전체) 순이 된다.
    "core.middleware.RequestMetricsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            PROJECT_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # 04-ux-design.md §2 전역 Header/Nav 카테고리 목록 (WU-04)
                "blog.context_processors.nav_categories",
                # REQ-005(SEO) canonical URL — DEC-017 정규 URL 설계와 정합 (WU-05)
                "core.context_processors.canonical_url",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# 04-ux-design.md §5 접근성 기준: <html lang="ko">, 단일 언어(REQ-021 Out-of-Scope)

LANGUAGE_CODE = "ko"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [
    PROJECT_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "/static/"

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# 기본값은 로컬 파일시스템(dev)과 Django 기본 정적파일 스토리지다.
# production.py가 "default"(미디어, media-public 버킷)는 Cloudflare
# R2(storages.backends.s3.S3Storage)로(03 §2.3, DEC-008), "staticfiles"는
# WhiteNoise의 매니페스트 스토리지로 각각 덮어쓴다.
# 정적 CSS/JS는 WhiteNoise가 Django 프로세스 안에서 직접 서빙하므로 R2로 보내지
# 않는다(03 §2.4, 과설계 방지). dev에서 매니페스트 스토리지를 쓰지 않는 이유는
# collectstatic을 매번 실행하지 않고 runserver로 바로 개발하기 위함이다.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Django sets a maximum of 1000 fields per form by default, but particularly complex page models
# can exceed this limit within Wagtail's page editor.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10_000


# Django LocMemCache — v1 캐싱 전략 (DEC-012, 03 §2.5). Redis/Render Key Value는
# 범위 밖. 실제 뷰 캐시 TTL(5~15분) 적용은 뷰가 구현되는 각 WU(예: WU-04)에서 처리.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


# Wagtail settings

WAGTAIL_SITE_NAME = "블로그"

# Search
# https://docs.wagtail.org/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = os.environ.get("WAGTAILADMIN_BASE_URL", "http://localhost:8000")

# Allowed file extensions for documents in the document library.
WAGTAILDOCS_EXTENSIONS = [
    "csv",
    "docx",
    "key",
    "odt",
    "pdf",
    "pptx",
    "rtf",
    "txt",
    "xlsx",
    "zip",
]

# Maximum upload size for documents in bytes (03 §5.5).
WAGTAILDOCS_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB

# 커스텀 이미지 모델 (WU-03, REQ-006, 03 §3.2 CustomImage/CustomRendition, DEC-008).
WAGTAILIMAGES_IMAGE_MODEL = "custom_images.CustomImage"

# 이미지 업로드 검증 (REQ-006, 03 §5.5의 "임의 파일 업로드 방지" 원칙을 이미지
# 업로드 경로에도 동일하게 적용). 아래 값은 Wagtail 기본값과 동일하지만, 보안
# 의도(허용 확장자를 화이트리스트로 명시, 특히 XSS 위험이 있는 svg를 허용
# 목록에서 제외)를 코드에 명시적으로 남기기 위해 값을 그대로 선언한다 —
# WAGTAILDOCS_* 설정과 동일한 패턴(위 §180 참고).
WAGTAILIMAGES_EXTENSIONS = ["avif", "gif", "jpg", "jpeg", "png", "webp"]
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
WAGTAILIMAGES_MAX_IMAGE_PIXELS = 128 * 1000000  # 디컴프레션 폭탄(초대형 픽셀) 방지
