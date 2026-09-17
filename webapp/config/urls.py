from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from blog import urls as blog_urls
from core import urls as core_urls
from core.admin_auth import RateLimitedLoginView
from subscribers import urls as subscribers_urls

# Wagtail 어드민 경로를 기본값(/admin/)에서 변경해 자동화 공격 노출을 줄인다
# (03 §4, §5.1, DEC-009).
urlpatterns = [
    path("django-admin/", admin.site.urls),
    # 로그인 레이트리밋(WU-09, REQ-010, core/admin_auth.py) — 아래
    # wagtailadmin_urls의 기본 로그인 라우트보다 먼저 매칭되도록 두되, URL
    # 이름(wagtailadmin_login)은 그대로 유지해 어드민 내부 reverse() 호출과
    # 충돌하지 않게 한다.
    path("cms-admin/login/", RateLimitedLoginView.as_view(), name="wagtailadmin_login"),
    path("cms-admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    # 03 §4 라우트 계약(REQ-003/REQ-004, WU-04) — 반드시 아래 wagtail_urls
    # catch-all보다 먼저 매칭되어야 한다.
    path("", include(blog_urls)),
    # robots.txt(REQ-005, WU-05) — 마찬가지로 wagtail_urls catch-all보다 먼저.
    path("", include(core_urls)),
    # 뉴스레터 구독(REQ-016, WU-07) — 마찬가지로 wagtail_urls catch-all보다 먼저.
    path("", include(subscribers_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("", include(wagtail_urls)),
]
