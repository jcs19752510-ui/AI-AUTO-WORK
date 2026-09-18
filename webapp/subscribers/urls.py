"""뉴스레터 구독 라우트 (WU-07, 03-system-design.md §4).

`/newsletter/subscribe/`는 Wagtail 페이지가 아니므로 `config/urls.py`가
`wagtail_urls` catch-all보다 먼저 include해야 한다(blog/core 앱과 동일한
패턴).
"""

from django.urls import path

from . import views

app_name = "subscribers"

urlpatterns = [
    path("newsletter/subscribe/", views.newsletter_subscribe, name="subscribe"),
    # 캐시되지 않는 폼 조각/전용 페이지 — views.py 모듈 docstring의 CSRF/캐시
    # 상호작용 설명 참고.
    path("newsletter/form/", views.newsletter_form_fragment, name="form_fragment"),
    path("newsletter/", views.newsletter_page, name="page"),
]
