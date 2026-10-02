"""WU-05(REQ-005)·WU-08(REQ-011/012) — 사이트 전역 보조 뷰.

- `robots_txt`: WU-05, REQ-005.
- `healthz`: WU-08, REQ-011/012. 03 §4 계약대로 DB 접속까지 확인하지 않는
  얕은(shallow) 헬스체크다 — Neon 콜드스타트 중 오탐으로 인한 불필요한
  재시작/알림을 피하기 위한 의도적 설계(03 §4 "shallow" 각주).
- `usage_dashboard`: WU-08, REQ-012. `core/wagtail_hooks.py`가 Wagtail
  어드민(`/cms-admin/usage/`)에 연결한다. superuser 전용.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.urls import reverse

from . import monitoring


def ads_txt(request):
    """DEC-053 — 애드센스 게시자 확인용 `ads.txt`(구글 공식 요구사항).
    `adsense_client_id`가 비어 있으면 404를 반환한다 — 애드센스 계정이
    아직 없는 지금 상태에서는 이 파일 자체가 존재하지 않는 게 맞는
    동작이다(값이 없다고 500이 나서는 안 된다는 원칙은 지키되, robots.txt
    처럼 "항상 200"이어야 할 이유는 없는 파일이라 404가 정확하다)."""
    from core.models import SiteSettings

    client_id = SiteSettings.for_request(request).adsense_client_id
    if not client_id:
        return HttpResponseNotFound()

    publisher_id = client_id[len("ca-"):] if client_id.startswith("ca-") else client_id
    line = f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0"
    return HttpResponse(line, content_type="text/plain")


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("blog:sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /cms-admin/",
        "Disallow: /django-admin/",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def superuser_required(view_func):
    """운영 지표(사용량 대시보드) 열람은 스태프 전체가 아니라 superuser로
    한정한다(최소 권한 원칙) — DEC-009의 세션 인증 모델을 그대로 쓰되,
    Wagtail 로그인 페이지(`wagtailadmin_login`, `/cms-admin/login/`)로
    리다이렉트해 이 사이트의 실제 관리자 로그인 경로와 일치시킨다."""

    @wraps(view_func)
    @login_required(login_url="wagtailadmin_login")
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


@superuser_required
def usage_dashboard(request):
    context = {
        "snapshot": monitoring.get_usage_snapshot(),
        "criteria": monitoring.UPGRADE_CRITERIA,
    }
    return render(request, "core/usage_dashboard.html", context)
