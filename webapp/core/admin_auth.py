"""관리자 로그인 무차별대입 방어 — Wagtail 어드민 + Django 기본 어드민
(WU-09, REQ-010, 03 §5.1. v1.3: DEF-09-01/DEC-039/DEC-040 규칙F 재작업으로
`/django-admin/login/`도 이 모듈이 함께 방어하도록 범위가 넓어졌다).

이 프로젝트는 로그인 폼을 제공하는 관리자 진입점이 `/cms-admin/login/`
(Wagtail, `RateLimitedLoginView`)과 `/django-admin/login/`(Django 기본
관리자, `RateLimitedAdminLoginView`) 두 개다. 둘 다 동일한 `auth_user`
슈퍼유저 계정을 공유하므로(03 §5.1 v1.3 인벤토리), 이 모듈의
`is_rate_limited(ip)` 카운터는 **URL을 구분하지 않고 IP만으로 두 뷰가
공유**한다 — 분리하면 공격자가 시도를 두 URL에 나눠 예산을 사실상 2배로
늘리는 우회가 가능해지기 때문이다.

각 뷰는 Wagtail/Django가 제공하는 원래 로그인 뷰(Wagtail 표준 로그인 뷰
`wagtail.admin.views.account.LoginView` / Django 기본 관리자
`admin.site.login()`)를 그대로 쓰되, POST 제출 앞단에서만 레이트리밋을
확인한다 — 뷰 자체를 재구현하지 않는다(04-ux-design.md §0 "Wagtail 어드민
UI 자체는 벤더 기본 제공 화면이며 새로 설계하지 않는다"는 원칙을 그대로
따름. Django 기본 관리자도 동일 원칙을 확장 적용).

새 패키지(django-axes/django-ratelimit 등, 03 §2.6 "확인 필요" 항목)를
도입하지 않고 DEC-024(뉴스레터 구독 레이트리밋)가 이미 채택한 LocMemCache
기반 카운터 패턴을 그대로 재사용한다(decisions.md DEC-029 참고) — 새 패키지의
라이선스를 다시 확인해야 하는 불확실성 자체를 회피하는 선택이다.

**IP 기준으로만 제한하고 계정(사용자명) 기준 잠금은 두지 않는다.** 계정
기준 잠금은 공격자가 알려진 운영자 계정명으로 고의 실패를 반복해 정당한
1인 운영자 본인을 잠그는 자기서비스거부(self-DoS) 경로를 새로 만든다(가정
A1, 1인/소규모 운영 — 계정을 잠그면 대체 관리자가 없어 복구 수단이
마땅치 않다). IP는 `config.middleware.XForwardedForMiddleware`(production
전용)가 이미 정규화해 둔 `REMOTE_ADDR`을 그대로 신뢰한다(03 §5.5.4).

**알려진 경계(6단계 unit-09-test.md에서 실측 확인, DEC-031 참고)**: 이
카운터는 Django 전역 `CsrfViewMiddleware`(config/settings/base.py
MIDDLEWARE에 항상 포함됨)가 요청을 먼저 거부하는 경우에는 증가하지
않는다 — 그 미들웨어는 `process_view()` 단계에서 뷰(이 클래스의
`dispatch()` 포함)가 호출되기도 전에 403으로 응답을 끝내기 때문이다.
아래 `dispatch()`가 고친 것은 별개의 문제다: Django
`contrib.auth.views.LoginView.dispatch`에 걸린 `csrf_protect` 데코레이터
(부모 클래스 수준의 이중 체크)는 `super().dispatch()` 호출 "안에서"
실행되므로 이 클래스의 `dispatch()`가 실행되는 시점보다 항상 늦다 — 이
경로는 이 클래스가 카운트를 우선 수행한 "이후"에 걸리므로 문제없다(6단계가
`RequestFactory`로 CsrfViewMiddleware 없이 재현해 확인: 403이 나와도
카운터는 정상 증가함). 문제는 오직 URL 디스패치보다 앞서 실행되는
전역 미들웨어 단계뿐이다. 이 경계는 실질적인 무차별대입 방어 결함이
아니다 — CSRF 검증에 실패하는 요청은 사용자명/비밀번호를 전혀 검사하지
않고 항상 동일하게 거부되므로(자격증명 추측이 애초에 불가능), 카운트되지
않아도 공격자가 얻는 이득이 없다. 반대로 자격증명을 실제로 시험할 수 있는
모든 요청(유효한 CSRF 토큰을 전제로 함)은 예외 없이 이 카운터를 통과한다
(6단계가 `Client(enforce_csrf_checks=True)`로 실측: CSRF-무효 트래픽을
아무리 많이 흘려보내도 그 IP의 카운터는 전혀 소모되지 않고, 이후 유효한
CSRF로 전환하면 정확히 새 10회 예산을 그대로 받는다)."""

from django.contrib import admin
from django.core.cache import cache
from django.http import HttpResponse
from django.views import View

from wagtail.admin.views.account import LoginView as WagtailLoginView

RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 15 * 60


def is_rate_limited(ip):
    if not ip:
        return False
    key = f"core:admin_login:ratelimit:{ip}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
        count = 1
    return count > RATE_LIMIT_MAX_ATTEMPTS


class RateLimitedLoginView(WagtailLoginView):
    """`config/urls.py`가 `wagtailadmin_login`이라는 동일한 URL 이름으로
    Wagtail 기본 제공 뷰 대신 이 뷰를 등록한다 — 어드민 내부의 다른 곳에서
    `reverse("wagtailadmin_login")`을 호출해도 동일한 경로를 가리키므로
    영향이 없다.

    `post()`가 아니라 `dispatch()`에서 확인한다 — Django `LoginView`는
    `dispatch()` 자체에 `csrf_protect` 데코레이터가 걸려 있어(부모 클래스
    `django.contrib.auth.views.LoginView`), `post()`를 오버라이드하면 CSRF
    검증을 통과한 요청만 레이트리밋 대상이 된다(로컬 테스트로 실제 재현
    확인, unit-09-note.md §3). IP 기준 요청 수 자체를 제한하는 것이 목적이므로
    CSRF 통과 여부와 무관하게 카운트해야 한다. 다만 이 클래스 자체보다
    먼저 실행되는 전역 `CsrfViewMiddleware`가 요청을 거부하는 경우는 이
    `dispatch()`가 아예 호출되지 않으므로 이 처리 범위 밖이다 — 이 모듈
    docstring의 "알려진 경계" 절 참고."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            ip = request.META.get("REMOTE_ADDR", "")
            if is_rate_limited(ip):
                return HttpResponse(
                    "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
        return super().dispatch(request, *args, **kwargs)


class RateLimitedAdminLoginView(View):
    """Django 기본 관리자(`django.contrib.admin`) 로그인 무차별대입 방어
    (v1.3 규칙F 재작업, DEF-09-01/DEC-039/DEC-040, 03 §5.1 구현 지침 1~3).

    `/cms-admin/login/`(`RateLimitedLoginView`, 위)과 반드시 같은
    `is_rate_limited(ip)` 카운터를 공유한다 — 새로 만들지 않는다. 두
    로그인 화면이 동일한 `auth_user` 슈퍼유저 계정을 공유하므로, 카운터를
    URL별로 분리하면 공격자가 시도를 두 URL에 나눠 예산을 사실상 2배(IP당
    20회)로 늘리는 우회가 가능해진다(03 §5.1 v1.3 참고).

    Wagtail 쪽처럼 `wagtail.admin.views.account.LoginView`를 상속하지 않는
    이유는, Django 기본 관리자 로그인 폼은 그 뷰 클래스를 상속할 대상이
    없기 때문이다 — `django.contrib.admin.sites.AdminSite.login()`은
    클래스가 아니라 바운드 메서드이며, 내부적으로
    `django.contrib.auth.views.LoginView.as_view(...)`를 즉석에서 만들어
    호출한다. 그래서 이 뷰는 `django.views.View`를 상속해 `dispatch()`에서
    레이트리밋만 확인하고, 통과하면 `admin.site.login()`에 그대로 위임한다
    (Wagtail 쪽이 `WagtailLoginView`에 위임하는 것과 동일한 패턴)."""

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            ip = request.META.get("REMOTE_ADDR", "")
            if is_rate_limited(ip):
                return HttpResponse(
                    "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
                    status=429,
                    content_type="text/plain; charset=utf-8",
                )
        return admin.site.login(request, *args, **kwargs)
