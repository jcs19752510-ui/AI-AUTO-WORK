"""댓글 뷰 (REQ-019, 03-system-design.md §4/§3.2-1).

`subscribers/views.py`와 동일한 구조: 무-JS 폴백(항상 동작)과 fetch 기반
점진적 향상 양쪽에 동일한 판정 로직을 재사용하고, 응답 형식(HTML/JSON)만
`X-Requested-With` 헤더로 분기한다.

**폼을 `@cache_page`가 걸린 게시물 상세 페이지의 캐시된 HTML에 직접
렌더링하지 않는다** — `subscribers/views.py` 모듈 docstring이 설명한 것과
정확히 동일한 이유(캐시된 CSRF 토큰이 재사용되어 403으로 이어지는 결함,
unit-07-note.md §3이 실제로 재현). 그래서 `comment_form_fragment`(캐시
안 됨)만 캐시된 페이지의 슬롯을 채우고, 무-JS 사용자는 캐시 안 되는 전용
페이지(`comment_write_page`)로 이동한다.
"""

from django.core.cache import cache
from django.http import HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from blog.models import BlogPostPage

from .constants import RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_WINDOW_SECONDS
from .forms import CommentForm
from .models import Comment
from .notifications import notify_new_comment
from .utils import mask_ip


def _is_rate_limited(ip):
    if not ip:
        return False
    key = f"comments:submit:ratelimit:{ip}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
        count = 1
    return count > RATE_LIMIT_MAX_ATTEMPTS


def _get_commentable_post_or_none(page_id):
    """댓글 대상은 반드시 공개(live) 게시물이어야 한다 — 비공개/존재하지
    않는 게시물에 대한 댓글 제출은 400으로 거부한다(03 §4).

    2026-09-25 09단계 재작업(DEF-09-07) 회귀 수정: `page_id`가 정수로
    변환되지 않는 값(예: "abc")이면 `int()`가 `ValueError`를 던진다 —
    이전에는 이 예외가 뷰 밖으로 전파되어 400 대신 미처리 500이 됐다
    (Django 기본 로깅이 `DJANGO_ADMIN_EMAIL`로 알림까지 보내 노이즈
    유발). 정수가 아니면 그냥 "대상 없음"으로 취급해 정상적으로 400
    으로 거부한다."""
    if not page_id:
        return None
    try:
        page_id = int(page_id)
    except (TypeError, ValueError):
        return None
    return BlogPostPage.published().filter(id=page_id).first()


def _create_pending_comment(post, author_name, body, ip):
    """댓글 저장 + 운영자 알림(사용자 요청, 2026-09-25)을 한 곳에서
    처리한다 — comment_submit/comment_write_page 두 제출 경로가 동일하게
    호출해 중복을 피한다."""
    comment = Comment.objects.create(
        page=post,
        author_name=author_name,
        body=body,
        source_ip_masked=mask_ip(ip),
        status=Comment.STATUS_PENDING,
    )
    notify_new_comment(comment)
    return comment


def _respond(request, is_ajax, status, *, form=None, success=False, rate_limited=False, redirect_url=None):
    if is_ajax:
        payload = {"success": success, "rate_limited": rate_limited}
        if form is not None:
            payload["errors"] = form.errors.get_json_data()
        return JsonResponse(payload, status=status)

    return render(
        request,
        "comments/submit_result.html",
        {
            "success": success,
            "rate_limited": rate_limited,
            "form": form,
            "redirect_url": redirect_url,
        },
        status=status,
    )


@require_POST
def comment_submit(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ip = request.META.get("REMOTE_ADDR", "")

    # 레이트리밋을 폼 검증보다 먼저 확인한다(subscribers와 동일 원칙 — 03 §5.3).
    if _is_rate_limited(ip):
        return _respond(request, is_ajax, 429, rate_limited=True)

    post = _get_commentable_post_or_none(request.POST.get("page_id"))
    if post is None:
        return _respond(request, is_ajax, 400)

    form = CommentForm(request.POST)
    if not form.is_valid():
        return _respond(request, is_ajax, 400, form=form, redirect_url=post.url)

    if form.cleaned_data["hp_field"]:
        # 03 §3.2-1: hp_field에 값이 있으면 200으로 위장 응답하되 실제 저장은 하지 않는다.
        return _respond(request, is_ajax, 200, success=True, redirect_url=post.url)

    _create_pending_comment(post, form.cleaned_data["author_name"], form.cleaned_data["body"], ip)

    return _respond(request, is_ajax, 200, success=True, redirect_url=post.url)


@require_GET
def comment_form_fragment(request):
    """캐시되지 않는 폼 조각. 매 요청마다 새로 렌더링되므로
    `{% csrf_token %}`이 항상 이 요청의 쿠키와 일치한다(subscribers와 동일)."""
    post = _get_commentable_post_or_none(request.GET.get("page_id"))
    if post is None:
        return HttpResponseNotFound()
    return render(request, "comments/_comment_form.html", {"post": post})


def comment_write_page(request, slug):
    """JS 없이도 항상 동작하는 전용 댓글 작성 페이지(04 §0). 캐시하지
    않는다 — comment_form_fragment와 동일한 이유. GET은 폼을 보여주고,
    POST는 comment_submit과 동일한 로직으로 직접 처리한 뒤 게시물로
    리다이렉트한다(무-JS 환경에서는 fetch가 없으므로 페이지 이동이 곧
    "인라인" 갱신을 대체하는 정상 동작)."""
    post = get_object_or_404(BlogPostPage.published(), slug=slug)

    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR", "")
        if _is_rate_limited(ip):
            return render(request, "comments/submit_result.html", {"rate_limited": True, "redirect_url": post.url}, status=429)

        form = CommentForm(request.POST)
        if form.is_valid():
            if not form.cleaned_data["hp_field"]:
                _create_pending_comment(post, form.cleaned_data["author_name"], form.cleaned_data["body"], ip)
            return redirect(post.url + "?comment_submitted=1")

        return render(request, "comments/comment_write_page.html", {"post": post, "form": form}, status=400)

    return render(request, "comments/comment_write_page.html", {"post": post, "form": CommentForm()})
