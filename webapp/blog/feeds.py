"""RSS 피드 (WU-04, REQ-004, 03-system-design.md §4 `GET /feed.xml`).

Django 표준 syndication 프레임워크(`django.contrib.syndication`)를 사용한다 —
별도 패키지 설치나 `INSTALLED_APPS` 등록이 필요 없다(뷰 모듈일 뿐, 모델/템플릿
태그가 없음). 출력은 Django가 XML 이스케이프를 자동 처리한다(03 §5.2).
"""

from django.conf import settings
from django.contrib.syndication.views import Feed

from .models import BlogPostPage

FEED_ITEM_LIMIT = 20


class LatestPostsFeed(Feed):
    title = settings.WAGTAIL_SITE_NAME
    link = "/"
    description = f"{settings.WAGTAIL_SITE_NAME} 최신 게시물"

    def items(self):
        return BlogPostPage.published()[:FEED_ITEM_LIMIT]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        # intro는 blank=True(WU-02)라 비어 있을 수 있다 — 완전히 빈
        # <description/>을 피하기 위해 제목으로 폴백한다.
        return item.intro or item.title

    def item_link(self, item):
        return item.get_url()

    def item_pubdate(self, item):
        return item.first_published_at
