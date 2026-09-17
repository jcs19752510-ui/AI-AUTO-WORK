"""콘텐츠 모델 (WU-02, REQ-001/REQ-002).

DEC-007에 따라 BlogPostPage는 Wagtail Page 트리를 상속하고, 임시저장/예약발행
(go_live_at/expire_at)·리비전 이력은 Wagtail 코어(PageRevision 등)를 그대로
사용한다 — 커스텀 재구현하지 않는다. Category/Tag는 03-system-design.md §3.2가
지시한 대로 각각 Snippet과 django-taggit 표준 through 모델 패턴으로 분리한다.
"""

import html as html_lib

from django.conf import settings
from django.db import models
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import slugify

from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase

from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.images import get_image_model_string
from wagtail.models import Page, Site
from wagtail.snippets.models import register_snippet

from core.seo import absolute_page_url

from .blocks import BlogStreamBlock


@register_snippet
class Category(models.Model):
    """블로그 게시물 분류 체계(REQ-002). Wagtail Snippet으로 어드민에서 별도
    CRUD한다(03-system-design.md §3.2)."""

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
    ]

    class Meta:
        verbose_name = "카테고리"
        verbose_name_plural = "카테고리"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        # 어드민에서 slug를 비워두면 name으로부터 자동 생성한다(운영자 입력 편의).
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPageTag(TaggedItemBase):
    """django-taggit 표준 through 모델(Wagtail 공식 권장 패턴, 03 §3.2). REQ-002."""

    content_object = ParentalKey(
        "blog.BlogPostPage",
        related_name="tagged_items",
        on_delete=models.CASCADE,
    )


class BlogPostPage(Page):
    """블로그 게시물(REQ-001). 03-system-design.md §3.1 ERD의
    ``BLOGPOSTPAGE }o--|| CATEGORY`` 관계에 따라 category는 필수(정확히 1개) FK다.
    featured_image는 ERD/§3.2가 명시한 대로 nullable이다."""

    intro = models.CharField(
        max_length=255,
        blank=True,
        help_text="목록/카드에 노출되는 짧은 요약(04-ux-design.md S-01 PostCard)",
    )
    body = StreamField(BlogStreamBlock(), blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="blog_posts",
        help_text="게시물이 속한 카테고리(필수, 03 §3.1 ERD)",
    )
    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    tags = ClusterTaggableManager(through="blog.BlogPageTag", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        FieldPanel("featured_image"),
        FieldPanel("category"),
        FieldPanel("tags"),
        FieldPanel("body"),
    ]

    # 03 §3.1 ERD상 게시물은 홈 트리 하위에 위치하고, 그 자체는 하위 페이지를
    # 갖지 않는다.
    parent_page_types = ["home.HomePage"]
    subpage_types = []

    class Meta:
        verbose_name = "블로그 게시물"
        verbose_name_plural = "블로그 게시물"

    @classmethod
    def published(cls):
        """공개 목록/상세(S-01~S-04)가 사용하는 발행된 게시물 쿼리셋(03 §4).

        Wagtail의 `live` 플래그만 확인한다 — `go_live_at`/`expire_at`이 실제
        `live` 값에 반영되려면 Wagtail의 예약발행 관리 명령
        (`publish_scheduled_pages`)이 주기적으로(cron 등) 실행되어야 한다.
        이 주기 실행 설정은 배포/운영 파이프라인 구성이며 03/04 어디에도
        담당 WU가 명시되어 있지 않다 — WU-04는 뷰 구현만 담당하므로 운영
        스케줄러 설정은 범위 밖으로 남기고 unit-04-note.md에 인계 사항으로
        기록한다.
        """
        return cls.objects.live().order_by("-first_published_at")

    def get_url_parts(self, request=None):
        """03 §4가 못박은 평면 경로(`/blog/<slug>/`)를 정규 URL로 반환한다.

        BlogPostPage는 페이지 트리상 HomePage 바로 아래(parent_page_types)에
        있어, Wagtail 기본 트리 URL 규칙을 따르면 `/<slug>/`가 된다 — 이는
        03 §4 라우트 계약과 일치하지 않는다. Wagtail 공식 문서가 권장하는
        대로(`get_url_parts` docstring: "pages with custom URL routing should
        override this method") 여기서 오버라이드해 `page.url`/`page.full_url`
        및 이를 참조하는 모든 곳(어드민 "실제 페이지 보기" 링크 등)이 정규
        URL을 가리키게 한다. 실제 요청 라우팅(트리 경로 자체 접근)은
        `serve()` 오버라이드가 이 URL로 리다이렉트해 중복 URL을 막는다.
        """
        result = super().get_url_parts(request=request)
        if result is None:
            return None
        site_id, root_url, page_path = result
        if root_url is None and page_path is None:
            # 상위 구현이 NoReverseMatch로 판단한 경우(사이트에 연결되지 않음
            # 등) 그대로 전달한다 — 우리가 새로 판단할 근거가 없다.
            return result
        return (site_id, root_url, reverse("blog:post_detail", args=[self.slug]))

    def serve(self, request, *args, **kwargs):
        """트리 URL(`/<slug>/`) 접근을 정규 URL(`/blog/<slug>/`)로 리다이렉트한다.

        같은 콘텐츠가 두 경로로 각각 렌더링되면(트리 URL + 정규 URL) 중복
        콘텐츠가 되어 SEO/캐시 측면에서 바람직하지 않다. `serve_preview()`는
        Wagtail 코어에서 이 메서드를 호출하지 않고 `get_preview_template`/
        `get_preview_context`를 통해 독립적으로 렌더링하므로, 운영자의
        어드민 미리보기(OP-03)는 이 리다이렉트의 영향을 받지 않는다.
        """
        canonical_url = self.get_url(request=request)
        if canonical_url is None:
            # 정규 URL을 계산할 수 없는 예외적 상황(사이트 설정 오류 등)에는
            # 기본 동작으로 폴백한다 — 조용히 실패하지 않고 프레임워크
            # 기본 처리(템플릿 탐색 → 없으면 500)에 맡긴다.
            return super().serve(request, *args, **kwargs)
        return HttpResponsePermanentRedirect(canonical_url)

    def get_json_ld(self, request):
        """schema.org BlogPosting 구조화 데이터(REQ-005, 03-system-design.md
        §4 필드 매핑을 그대로 따른다: headline←title, datePublished←
        first_published_at, dateModified←last_published_at, image←
        featured_image, author←owner의 표시 이름 또는 사이트 대표 이름).

        03 §4는 author의 대체값으로 "SiteSettings.site_title"을 언급했지만,
        어떤 WU도 아직 SiteSettings 모델을 만들지 않았다(그 모델은 03 §1.2가
        REQ-011/012 담당 `core` 앱 몫으로 지정했고, 이번 WU-05는 REQ-005만
        구현한다 — 아직 존재하지 않는 모델을 이 WU가 앞서 만드는 것은 범위
        확장이라고 판단했다). 대신 "사이트를 대표하는 이름"이라는 §4의 취지를
        Wagtail `Site.site_name`(footer.html이 이미 같은 목적으로 쓰는 값) →
        `settings.WAGTAIL_SITE_NAME`(항상 값이 있는 전역 설정, feeds.py가
        이미 같은 용도로 쓰는 값) 순서의 2단계 대체로 충족한다 — 로컬
        검증에서 기본 Wagtail Site 픽스처의 `site_name`이 비어 있을 수
        있음을 실제로 확인했다(§3).

        mainEntityOfPage의 `@id`는 `Page.get_full_url()`(Wagtail Site의
        hostname 설정에 의존) 대신 `core.seo.absolute_page_url`을 쓴다 —
        그 이유는 해당 함수 docstring 참고(canonical_url 컨텍스트
        프로세서와 항상 같은 값이 나오게 하기 위함).
        """
        data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": self.title,
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": absolute_page_url(self, request),
            },
        }
        if self.first_published_at:
            data["datePublished"] = self.first_published_at.isoformat()
        if self.last_published_at:
            data["dateModified"] = self.last_published_at.isoformat()
        if self.featured_image:
            rendition = self.featured_image.get_rendition("width-800")
            data["image"] = [request.build_absolute_uri(rendition.url)]

        author_name = None
        if self.owner:
            author_name = self.owner.get_full_name() or self.owner.username
        if author_name:
            data["author"] = {"@type": "Person", "name": author_name}
        else:
            site = Site.find_for_request(request)
            org_name = (site.site_name if site else "") or settings.WAGTAIL_SITE_NAME
            if org_name:
                data["author"] = {"@type": "Organization", "name": org_name}
        return data

    def get_sitemap_urls(self, request=None):
        """REQ-005 `GET /sitemap.xml` — Wagtail 기본 구현(`Page.get_full_url()`
        기반)을 오버라이드해 `core.seo.absolute_page_url`을 쓴다. 기본
        구현을 그대로 두면 Wagtail Site의 hostname 설정에 따라 실제 배포
        도메인과 다른 URL이 사이트맵에 실릴 수 있음을 로컬 검증에서 직접
        재현했다(unit-05-note.md §2/§3 — 이 프로젝트의 초기 마이그레이션이
        만드는 기본 Site의 hostname이 "localhost"로 고정되어 있고 이를
        운영 도메인으로 갱신하는 절차가 아직 없다)."""
        return [
            {
                "location": absolute_page_url(self, request),
                "lastmod": self.last_published_at,
            }
        ]

    def get_faq_json_ld(self):
        """REQ-017 — 본문(body)에 FAQ 블록이 있으면 별도 FAQPage JSON-LD를
        반환한다. 03 §4가 "FAQPage JSON-LD를 선택적으로 추가할 수 있도록
        템플릿 블록을 분리해 둔다"고 명시한 대로, BlogPosting과 합치지 않고
        독립된 <script> 태그로 구현한다(템플릿에서 별도 렌더링). FAQ 블록이
        없거나 질문/답변이 비어 있으면 None을 반환해 빈 구조화 데이터가
        렌더링되지 않게 한다."""
        questions = []
        for block in self.body:
            if block.block_type != "faq":
                continue
            for item in block.value.get("items", []):
                question = item.get("question")
                answer_html = item.get("answer")
                if not question or not answer_html:
                    continue
                # strip_tags는 태그만 제거하고 `&amp;` 같은 HTML 엔티티는
                # 그대로 남기므로, schema.org의 순수 텍스트 필드에 맞게
                # html.unescape로 실제 문자로 되돌린다(WU-05 로컬 검증에서
                # `&amp;`가 그대로 남는 것을 실제로 확인하고 수정, §3 참고).
                answer_text = html_lib.unescape(strip_tags(str(answer_html))).strip()
                if not answer_text:
                    continue
                questions.append(
                    {
                        "@type": "Question",
                        "name": str(question),
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": answer_text,
                        },
                    }
                )
        if not questions:
            return None
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": questions,
        }
