"""뉴스레터 구독 뷰 (WU-07, REQ-016, 03-system-design.md §4/§5.3).

`POST /newsletter/subscribe/` 하나가 03 §4가 명시한 계약(200/302 성공,
400 형식오류/동의누락, 429 레이트리밋, 허니팟 시 200 위장응답)을 전부
처리한다. 무-JS 폴백(항상 동작)과 fetch 기반 점진적 향상(페이지 이동 없이
인라인 갱신, 04 §4 NewsletterSubscribeForm 상태값) 양쪽에 동일한 판정
로직을 재사용하고, 응답 형식(HTML/JSON)만 `X-Requested-With` 헤더로
분기한다.

**폼을 `@cache_page`가 걸린 페이지(홈/카테고리/태그/게시물 상세, WU-04/05/06
소유)의 캐시된 HTML에 직접 렌더링하지 않는다.** 로컬 검증(unit-07-note.md
§3)에서 실제로 재현한 결함 때문이다 — `{% csrf_token %}`이 포함된 응답이
캐시되면, 첫 방문자의 CSRF 토큰이 담긴 HTML이 캐시 TTL 동안 다른 모든
방문자에게 그대로 재사용되는데, 그 방문자들은 쿠키를 아예 받지 못하거나
(캐시 HIT은 뷰를 다시 실행하지 않아 `get_token()`이 호출되지 않음) 받더라도
캐시에 박힌 토큰과 다른 값이라, 실제 제출 시 100% `403 CSRF` 응답으로
이어진다(REQ-016 핵심 기능 자체가 동작하지 않는 치명적 결함). 그래서 이
뷰가 렌더링하는 폼 조각(`newsletter_form_fragment`)과 무-JS 전용 페이지
(`newsletter_page`)는 둘 다 캐시하지 않는다 — 매 요청마다 다시 실행되어
`get_token()`이 항상 그 요청의 쿠키와 정확히 일치하는 토큰을 만든다.
캐시된 페이지 쪽에는 정적인(요청과 무관한) 프래그먼트 URL만 남기고, 실제
폼은 JS가 그 URL을 fetch해 채우거나(향상), JS가 없으면 `noscript` 링크로
이 앱의 전용 `/newsletter/` 페이지로 보낸다(config/templates/partials/
footer.html 등 참고).
"""

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .constants import (
    PRIVACY_POLICY_VERSION,
    RATE_LIMIT_MAX_ATTEMPTS,
    RATE_LIMIT_WINDOW_SECONDS,
)
from .forms import NewsletterSubscribeForm
from .models import NewsletterSubscriber
from .utils import mask_ip


# 04 §5 "라벨-에러 연결"을 위해 컴포넌트가 요구하는 고유 id 접미사 —
# 쿼리파라미터로 임의 값을 받는 대신 화이트리스트로 제한한다(요청/응답
# 경계에서의 입력 검증, 게이트2 체크리스트 항목).
_ALLOWED_FORM_IDS = {"footer", "post-detail", "home-empty"}
_ALLOWED_VARIANTS = {"", "emphasis"}


def _safe_next(raw):
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return "/"


def _is_rate_limited(ip):
    if not ip:
        return False
    key = f"subscribers:newsletter:ratelimit:{ip}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
        count = 1
    return count > RATE_LIMIT_MAX_ATTEMPTS


def _respond(request, is_ajax, status, next_url, *, form=None, success=False, rate_limited=False):
    if is_ajax:
        payload = {"success": success, "rate_limited": rate_limited}
        if form is not None:
            payload["errors"] = form.errors.get_json_data()
        return JsonResponse(payload, status=status)

    return render(
        request,
        "subscribers/subscribe_result.html",
        {
            "success": success,
            "rate_limited": rate_limited,
            "form": form,
            "next_url": next_url,
        },
        status=status,
    )


@require_POST
def newsletter_subscribe(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    next_url = _safe_next(request.POST.get("next", ""))
    ip = request.META.get("REMOTE_ADDR", "")

    # 레이트리밋을 폼 검증보다 먼저 확인한다 — 형식이 틀린 대량 요청으로부터도
    # 동일하게 보호하기 위함(03 §5.3 "IP 기준 레이트리밋").
    if _is_rate_limited(ip):
        return _respond(request, is_ajax, 429, next_url, rate_limited=True)

    form = NewsletterSubscribeForm(request.POST)
    if not form.is_valid():
        return _respond(request, is_ajax, 400, next_url, form=form)

    if form.cleaned_data["hp_field"]:
        # 03 §4: hp_field에 값이 있으면 200으로 위장 응답하되 실제 저장은 하지 않는다.
        return _respond(request, is_ajax, 200, next_url, success=True)

    email = form.cleaned_data["email"]
    now = timezone.now()

    # 03 §5.3 중복 제출 계약: 존재 여부를 사전 조회해 유니크 제약 위반을
    # 애플리케이션에서 회피하고, active/unsubscribed 모두 활성 상태로 갱신한다.
    subscriber = NewsletterSubscriber.objects.filter(email__iexact=email).first()
    if subscriber is None:
        NewsletterSubscriber.objects.create(
            email=email,
            consented_at=now,
            consent_version=PRIVACY_POLICY_VERSION,
            source_ip_masked=mask_ip(ip),
            status=NewsletterSubscriber.STATUS_ACTIVE,
        )
    else:
        subscriber.consented_at = now
        subscriber.consent_version = PRIVACY_POLICY_VERSION
        subscriber.status = NewsletterSubscriber.STATUS_ACTIVE
        subscriber.save(update_fields=["consented_at", "consent_version", "status"])

    return _respond(request, is_ajax, 200, next_url, success=True)


@require_GET
def newsletter_form_fragment(request):
    """캐시되지 않는 폼 조각. static/js/newsletter.js가 캐시된 공개 페이지의
    빈 슬롯을 이 응답으로 채운다(모듈 docstring 참고) — 매 요청마다 새로
    렌더링되므로 `{% csrf_token %}`이 항상 이 요청의 쿠키와 일치한다.
    """
    form_id = request.GET.get("form_id", "footer")
    if form_id not in _ALLOWED_FORM_IDS:
        form_id = "footer"
    variant = request.GET.get("variant", "")
    if variant not in _ALLOWED_VARIANTS:
        variant = ""
    return render(request, "subscribers/_newsletter_form.html", {"form_id": form_id, "variant": variant})


@require_GET
def newsletter_page(request):
    """JS 없이도 항상 동작하는 전용 구독 페이지(04 §0). 캐시하지 않는다 —
    위 모듈 docstring과 동일한 이유."""
    return render(request, "subscribers/newsletter_page.html", {"form_id": "dedicated"})
