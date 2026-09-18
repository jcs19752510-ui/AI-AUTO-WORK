"""공개 열람 화면 라우트 (WU-04, 03-system-design.md §4).

`/blog/<slug>/`·`/category/<slug>/`·`/tag/<slug>/`·`/feed.xml`은 Wagtail 페이지
트리 서빙이 아니라 이 URLconf가 직접 정의하는 평면 경로다(views.py 상단 설명,
models.py의 BlogPostPage.get_url_parts/serve 오버라이드와 짝을 이룬다).
`config/urls.py`가 이 모듈을 Wagtail catch-all(`wagtail_urls`)보다 먼저
`include()`해야 한다.
"""

from django.urls import path

from wagtail.contrib.sitemaps.views import sitemap as wagtail_sitemap

from . import views
from .feeds import LatestPostsFeed

app_name = "blog"

# Django의 `slug:` 경로 컨버터는 ASCII만 매칭한다(`[-a-zA-Z0-9_]+`). Wagtail의
# 기본 설정(`WAGTAIL_ALLOW_UNICODE_SLUGS=True`)과 django-taggit의 기본
# slugify(allow_unicode=True)가 한글 슬러그(예: "기술", "파이썬")를 그대로
# 생성하므로, 여기서 `slug:` 대신 `str:`(슬래시를 제외한 임의 문자열)을
# 써야 한글 slug가 실제로 라우팅된다. 조회는 아래 뷰의 get_object_or_404가
# 정확히 일치하는 slug만 통과시키므로 str 컨버터로 넓혀도 안전하다.
urlpatterns = [
    path("blog/<str:slug>/", views.post_detail, name="post_detail"),
    path("category/<str:slug>/", views.category_list, name="category_list"),
    path("tag/<str:slug>/", views.tag_list, name="tag_list"),
    path("feed.xml", LatestPostsFeed(), name="feed"),
    # 03 §4 `GET /sitemap.xml`(REQ-005, WU-05) — wagtail.contrib.sitemaps
    # 표준 뷰를 그대로 사용한다(03 §1.2 모듈 경계: 사이트맵은 blog 소유).
    path("sitemap.xml", wagtail_sitemap, name="sitemap"),
]
