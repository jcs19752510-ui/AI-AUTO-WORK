"""공개 목록/상세 뷰 (WU-04, REQ-003/REQ-014, 03-system-design.md §4).

Wagtail 페이지 트리의 기본 URL 규칙(부모 slug 기반)은 03 §4가 못박은 평면 경로
`/blog/<slug>/`·`/category/<slug>/`·`/tag/<slug>/`와 일치하지 않는다 —
BlogPostPage는 HomePage 바로 아래에 위치해 트리 URL은 `/<slug>/`가 되기 때문이다.
그래서 이 라우트들은 Wagtail의 페이지 트리 서빙이 아니라 일반 Django 뷰로
구현했다. `models.py`의 `BlogPostPage.get_url_parts()`/`serve()` 오버라이드가
정규 URL을 계산/강제하는 짝이다.

카테고리 목록(S-03)/태그 목록(S-04)은 "카테고리·태그 자체가 없으면 404,
있지만 소속 게시물이 0건이면 빈 상태"를 구분한다(04-ux-design.md §2 S-03/S-04).
"""

from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from taggit.models import Tag

from .constants import VIEW_CACHE_SECONDS
from .models import BlogPostPage, Category
from .pagination import paginate


@cache_page(VIEW_CACHE_SECONDS)
def post_detail(request, slug):
    post = get_object_or_404(BlogPostPage.published(), slug=slug)

    # REQ-005 Open Graph/Twitter 이미지 — 대표이미지가 있을 때만 절대 URL을
    # 계산한다(models.BlogPostPage.get_json_ld의 image 매핑과 동일한 렌디션
    # 스펙을 재사용해 값 불일치를 피한다).
    og_image_rendition = None
    og_image_url = None
    if post.featured_image:
        og_image_rendition = post.featured_image.get_rendition("width-800")
        og_image_url = request.build_absolute_uri(og_image_rendition.url)

    context = {
        "page": post,
        "json_ld": post.get_json_ld(request),
        "faq_json_ld": post.get_faq_json_ld(),
        "og_image_rendition": og_image_rendition,
        "og_image_url": og_image_url,
        # REQ-019(댓글, v1.5) — 승인된 댓글만(03 §3.2-1). 이 페이지가
        # cache_page로 캐시되므로 새 댓글이 반영되기까지 최대
        # VIEW_CACHE_SECONDS만큼 지연될 수 있다(기존 캐시 정책과 동일,
        # DEC-012).
        "approved_comments": post.comments.filter(status="approved"),
    }
    return render(request, "blog/blog_post_page.html", context)


@cache_page(VIEW_CACHE_SECONDS)
def category_list(request, slug):
    category = get_object_or_404(Category, slug=slug)
    posts = BlogPostPage.published().filter(category=category)
    context = {
        "category": category,
        "page_obj": paginate(request, posts),
    }
    return render(request, "blog/category_list.html", context)


@cache_page(VIEW_CACHE_SECONDS)
def tag_list(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    posts = BlogPostPage.published().filter(tags__slug=tag.slug).distinct()
    context = {
        "tag": tag,
        "page_obj": paginate(request, posts),
    }
    return render(request, "blog/tag_list.html", context)
