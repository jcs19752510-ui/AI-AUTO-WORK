"""댓글 라우트 (REQ-019, 03-system-design.md §4).

`config/urls.py`가 `wagtail_urls` catch-all보다 먼저 include해야 한다
(subscribers/blog/core 앱과 동일한 패턴).

**2026-09-25 실제 브라우저 테스트에서 발견·수정한 버그**: Django `slug:`
경로 컨버터는 ASCII만 매칭한다(`[-a-zA-Z0-9_]+`). Wagtail이 한글 제목에서
자동 생성하는 slug(`WAGTAIL_ALLOW_UNICODE_SLUGS=True`, 예:
"교토-3박-4일-가을-여행기")는 이 컨버터와 매칭되지 않아
`comment_write_page`로의 `{% url %}` 리버스가 `NoReverseMatch`로 실패했다
— `blog/urls.py`가 이미 동일한 이유로 `str:`을 채택해 뒀던 선례를
이번 WU-11 착수 시 놓쳤던 것이 근본 원인이다. `blog/urls.py`와 동일하게
`str:`로 교체해 해소한다.
"""

from django.urls import path

from . import views

app_name = "comments"

urlpatterns = [
    path("comments/submit/", views.comment_submit, name="submit"),
    path("comments/form-fragment/", views.comment_form_fragment, name="form_fragment"),
    path("blog/<str:slug>/comment/", views.comment_write_page, name="write_page"),
]
