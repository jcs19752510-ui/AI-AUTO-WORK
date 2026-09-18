from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from wagtail.models import Page

from blog.constants import VIEW_CACHE_SECONDS
from blog.models import BlogPostPage
from blog.pagination import paginate
from core.seo import absolute_page_url


class HomePage(Page):
    """Wagtail 페이지 트리의 루트. 실제 블로그 콘텐츠 모델(BlogPostPage 등)은
    WU-02에서 이 트리의 하위 페이지로 추가되었다(03 §3.1 ERD).

    S-01(홈/블로그 목록, REQ-003)은 Wagtail의 표준 `get_context()` 패턴을
    그대로 사용한다 — `/`는 이미 Wagtail이 사이트 루트로 서빙하므로(03 §4
    `GET /`), blog 앱처럼 별도 URLconf 라우트가 필요 없다. 목록 조회/정렬
    로직 자체는 03 §1.2가 "공개 목록/상세 뷰"의 소유 앱으로 지정한 `blog`에
    두고(`BlogPostPage.published()`), 이 메서드는 그 결과를 페이지네이션해
    템플릿에 연결하는 얇은 어댑터 역할만 한다.
    """

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["page_obj"] = paginate(request, BlogPostPage.published())
        return context

    @method_decorator(cache_page(VIEW_CACHE_SECONDS))
    def serve(self, request, *args, **kwargs):
        # 03 §2.5(DEC-012) 뷰 캐시(5~15분 TTL) — blog/views.py의 다른 공개
        # 목록/상세 뷰와 동일한 TTL을 적용한다.
        return super().serve(request, *args, **kwargs)

    def get_sitemap_urls(self, request=None):
        # REQ-005 — blog.models.BlogPostPage.get_sitemap_urls와 동일한 이유로
        # core.seo.absolute_page_url을 쓴다(해당 함수 docstring 참고).
        return [
            {
                "location": absolute_page_url(self, request),
                "lastmod": self.last_published_at,
            }
        ]
