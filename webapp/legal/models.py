"""법적 페이지 모델 (WU-06, REQ-007/008/009/015).

DEC-022에 따라 개인정보처리방침/이용약관/쿠키 사용 고지 3종을 각각 별도
서브클래스로 나누지 않고, 03-system-design.md §3.2가 명시한 두 번째 옵션
("공통 RichTextPage 1개 모델을 재사용")을 채택한 단일 `LegalPage` 모델로
관리한다. 세 페이지 모두 `home.HomePage`의 직계 자식(slug=privacy-policy/
terms/cookies)으로 생성되므로, Wagtail 기본 트리 URL 규칙이 그대로 03 §4
라우트 계약(`/privacy-policy/`, `/terms/`, `/cookies/`)과 일치한다 —
HomePage가 사이트 루트라 트리 URL에서 `/home/` 접두어가 제거되는 것은
blog.models.BlogPostPage.get_url_parts docstring이 이미 확인한 동작과 동일
하다. 따라서 blog 앱과 달리 URL을 강제하기 위한 별도 라우팅 오버라이드가
필요 없다.
"""

import re

from django.db import models
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.views.decorators.cache import cache_page

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.rich_text import expand_db_html

from core.seo import absolute_page_url

from .constants import VIEW_CACHE_SECONDS

_HEADING_RE = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)


def _add_heading_anchors(html):
    """본문 리치텍스트 안의 `<h2>` 제목에 앵커 id를 부여하고, 목차(TOC) 항목
    목록을 함께 만든다(04-ux-design.md §2 S-06 "목차(TOC) 앵커 링크").

    04번은 TOC를 S-06(이용약관)에만 명시했지만, 페이지 종류별로 분기하는
    대신 "본문에 h2 제목이 있으면 자동으로 목차를 만든다"는 일반 규칙으로
    구현했다 — 새 데이터/라우트 요구 없이 동일 컴포넌트를 모든 LegalPage
    인스턴스가 재사용하는 가역적 판단이며(unit-06-note.md §2 참고), S-05/
    S-07도 구조적 제목을 쓰면 자연히 같은 이점을 얻는다.

    입력 html은 `expand_db_html()`을 거친, Wagtail 리치텍스트 에디터의 허용
    태그 화이트리스트를 통과한 운영자(에디터) 입력이다(03 §5.1 "에디터가 곧
    운영자") — 03 §5.2가 JSON-LD 필드에 적용한 것과 동일한 신뢰 경계 논리로,
    슬러그화된 id 속성만 주입하는 이 정규식 치환 결과를 `mark_safe`로
    렌더링한다(방문자 입력이 아님, 새로 태그를 추가하지 않고 기존 h2 태그에
    속성만 추가함).
    """
    toc = []
    seen_slugs = {}

    def _replace(match):
        inner = match.group(1)
        text = strip_tags(inner).strip()
        base_slug = slugify(text, allow_unicode=True) or "section"
        count = seen_slugs.get(base_slug, 0)
        seen_slugs[base_slug] = count + 1
        anchor = base_slug if count == 0 else f"{base_slug}-{count}"
        toc.append((text, anchor))
        return f'<h2 id="{anchor}">{inner}</h2>'

    new_html = _HEADING_RE.sub(_replace, html)
    return new_html, toc


class LegalPage(Page):
    """개인정보처리방침(REQ-007)/이용약관(REQ-009, 콘텐츠 정책 REQ-015 하위
    섹션 포함)/쿠키 사용 고지(REQ-008) 공용 모델. 리치텍스트 본문 하나로
    세 페이지를 모두 표현한다(03 §3.2).
    """

    body = RichTextField(help_text="법적 고지 본문. h2 제목마다 자동으로 목차가 생성된다.")

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    class Meta:
        verbose_name = "법적 페이지"
        verbose_name_plural = "법적 페이지"

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        body_html, toc_items = _add_heading_anchors(expand_db_html(self.body))
        context["body_html"] = mark_safe(body_html)
        context["toc_items"] = toc_items
        return context

    @method_decorator(cache_page(VIEW_CACHE_SECONDS))
    def serve(self, request, *args, **kwargs):
        # 03 §2.5(DEC-012) 뷰 캐시 — WU-04(HomePage/blog 뷰)가 모든 공개
        # GET 뷰에 적용한 것과 동일한 정책을 법적 페이지에도 일관되게 적용한다.
        return super().serve(request, *args, **kwargs)

    def get_sitemap_urls(self, request=None):
        # REQ-005 — blog.models.BlogPostPage.get_sitemap_urls와 동일한 이유로
        # core.seo.absolute_page_url을 쓴다(해당 함수 docstring, DEC-021 참고).
        return [
            {
                "location": absolute_page_url(self, request),
                "lastmod": self.last_published_at,
            }
        ]
