"""WU-08, REQ-012 — 사용량 모니터링 대시보드를 Wagtail 어드민에 연결한다.

Wagtail 공식 문서: `register_admin_urls`로 추가한 URL에는 Wagtail이 로그인/
권한 검사를 자동으로 걸어주지 않는다("it's up to the developer to do this
within the view") — 그래서 `core.views.usage_dashboard`가 자체적으로
`superuser_required`를 적용한다(뷰 쪽 책임, 여기서는 라우팅/메뉴 등록만).
"""

from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import views


@hooks.register("register_admin_urls")
def register_usage_dashboard_url():
    return [
        path("usage/", views.usage_dashboard, name="core_usage_dashboard"),
    ]


class UsageDashboardMenuItem(MenuItem):
    def is_shown(self, request):
        return request.user.is_active and request.user.is_superuser


@hooks.register("register_admin_menu_item")
def register_usage_dashboard_menu_item():
    return UsageDashboardMenuItem(
        _("사용량 모니터링"),
        reverse("core_usage_dashboard"),
        icon_name="time",
        order=10000,
    )
