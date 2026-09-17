# WU-07 — 이메일 뉴스레터 구독 폼(수집) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-07, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §1.2 `subscribers` 앱 모듈 경계, §3.1/§3.2 NewsletterSubscriber ERD, §4 `POST /newsletter/subscribe/` 계약, §5.3 뉴스레터 엔드포인트 보안/동작 계약, §5.5.4 X-Forwarded-For 유틸, §5.6 개인정보 처리 원칙), `docs/harness/04-ux-design.md`(v1.2, PASS, S-01/S-02/S-03/S-04 NewsletterSubscribeForm 배치, §4 컴포넌트 상태, §5 접근성), `docs/harness/decisions.md`(DEC-001~022), `docs/harness/02-planning.md`(REQ-016, WU-07 정의, §8 가정 A9 "이메일 수집 폼까지만 v1 범위"), `docs/harness/units/unit-01-note.md`(§Case C `XForwardedForMiddleware` 검증 패턴), `docs/harness/units/unit-06-note.md`(legal 앱 구조/이미 게시된 개인정보처리방침 본문)
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-016(이메일 뉴스레터 구독 폼, 수집까지)

---

## 0. 실행 요약

- REQ-016을 "이메일 수집"까지 구현했다(발송 인프라/자동 구독취소는 02 가정 A9·03 §5.3/§5.6에 따라 범위 밖).
- 구현 도중 **캐시된 공개 페이지에 CSRF 토큰이 포함된 폼을 직접 넣으면, 캐시 TTL 동안 첫 방문자를 제외한 모든 방문자의 구독 제출이 403으로 실패하는 치명적 결함**을 로컬에서 실제로 재현했다. 이를 캐시되지 않는 폼 조각/전용 페이지로 분리하는 방식으로 해결했다(§3, DEC-025).
- 규칙 A-③에 따라 오케스트레이터 지시(구독 취소 토큰 URL 구현)와 PASS된 03/02 설계서·이미 게시된 WU-06 법적 문구가 정면으로 배치되는 지점을 발견해, 설계서를 우선하고 **질문 목록**으로 남겼다(§1.3, DEC-023).

---

## 1. 구현 범위

WU-01(XForwardedForMiddleware 유틸)·WU-04(공개 화면 골격)·WU-06(개인정보처리방침 링크) 위에, 신규 `subscribers` 앱(03 §1.2가 이미 지정한 모듈 경계·이름)을 구현했다.

```
webapp/
  subscribers/                        (신규 앱)
    apps.py
    constants.py                      PRIVACY_POLICY_VERSION, RATE_LIMIT_MAX_ATTEMPTS/WINDOW_SECONDS
    utils.py                          mask_ip() — 마지막 옥텟/세그먼트 마스킹(03 §3.2/§5.6)
    models.py                         NewsletterSubscriber(UUID PK, email unique, consented_at, consent_version, source_ip_masked, status)
    forms.py                          NewsletterSubscribeForm(email/consent/hp_field, 03 §4 요청 필드 그대로)
    views.py                          POST /newsletter/subscribe/, GET /newsletter/form/(조각), GET /newsletter/(무-JS 전용 페이지)
    urls.py
    admin.py                          Django 어드민 등록(읽기 전용 — 03 §5.6 파기절차용 하드 삭제만 허용)
    migrations/0001_initial.py        (makemigrations로 생성)
    templates/subscribers/
      _newsletter_form.html           NewsletterSubscribeForm 컴포넌트(04 §4)
      _newsletter_slot.html           캐시된 페이지에 남기는 자리표시자(§3 참고)
      subscribe_result.html           무-JS 폴백 제출 결과 페이지
      newsletter_page.html            무-JS 폴백 목적지(/newsletter/, 캐시 안 함)
    tests.py                          (신규) 12개 자동화 테스트 — §5 검증 결과 참고
  config/
    settings/base.py                  (수정) INSTALLED_APPS에 "subscribers" 추가
    urls.py                           (수정) subscribers.urls를 wagtail_urls catch-all보다 먼저 include
    templates/base.html               (수정) newsletter.js 로드 추가
    templates/partials/footer.html    (수정) show_footer_newsletter 플래그 + 뉴스레터 슬롯(S-01/S-03/S-04 한정, 04 §2)
    static/js/newsletter.js           (신규) 점진적 향상 — 조각 fetch/주입 + 제출 인터셉트
    static/css/components.css         (수정) NewsletterSubscribeForm/InlineAlert/구독결과·전용페이지 스타일
  home/templates/home/home_page.html          (수정) footer 오버라이드 + 빈 상태 강조 배치(04 §2 S-01)
  blog/templates/blog/category_list.html      (수정) footer 오버라이드(S-03)
  blog/templates/blog/tag_list.html           (수정) footer 오버라이드(S-04)
  blog/templates/blog/blog_post_page.html     (수정) 본문 하단 인라인 슬롯(S-02), footer는 기본값(숨김) 유지
  blog/templates/blog/partials/_post_list.html (수정) empty_show_newsletter 옵션
docs/harness/decisions.md             DEC-023/024/025 추가
docs/harness/traceability.md          REQ-016 행 갱신
```

### 1.1 데이터 모델 — REQ-016

03 §3.1 ERD/§3.2를 그대로 따랐다: `NewsletterSubscriber`는 Wagtail Page가 아닌 순수 Django 모델(UUID PK, `email`(unique, 저장 전 소문자 정규화), `consented_at`, `consent_version`, `source_ip_masked`, `status`(active/unsubscribed, 03 §3.2가 "v1은 자동으로 전환되지 않는 선제적 스키마"라고 명시한 대로 그대로 둠), `created_at`).

회원가입이 없으므로(DEC-009) 이 레코드가 구독자의 유일한 식별 수단이다.

### 1.2 구독 엔드포인트 — 03 §4/§5.3 계약

`POST /newsletter/subscribe/`가 03 §4 표와 §5.3의 4단계 계약을 그대로 구현한다:

1. IP 기준 레이트리밋(10분당 5회, `views.py`가 폼 검증보다 먼저 확인 — 형식이 틀린 대량 요청도 동일하게 방어)을 초과하면 429.
2. 폼이 유효하지 않으면(이메일 형식/동의 누락) 400, 필드별 에러.
3. 허니팟(`hp_field`)에 값이 있으면 200으로 위장 응답하되 저장하지 않음.
4. 이메일이 DB에 없으면 신규 생성(`status=active`), 있으면(대소문자 무관, `email__iexact`) 새 레코드를 만들지 않고 `consented_at`/`consent_version`/`status=active`만 갱신 — 세 경우 모두 **동일한 성공 메시지**를 반환해 이메일 열거 공격을 방지한다(03 §5.3).

응답 형식은 `X-Requested-With: XMLHttpRequest` 헤더로 분기한다: 일반 폼 제출(무-JS)은 HTML 결과 페이지(`subscribe_result.html`, 200/400/429 상태코드 그대로)를, fetch 기반 점진적 향상은 JSON(`{"success", "rate_limited", "errors"}`)을 받는다.

### 1.3 구독 취소 토큰/URL — 이번 WU에서 구현하지 않음 (질문 목록, 규칙 A-③)

오케스트레이터의 이번 작업 지시 §3은 "구독 취소 토큰 URL을 생성하는 모델/뷰 레벨까지만 구현"하라고 명시했다. 그러나 다음 근거로 **이번 WU에서 구현하지 않기로 자체판단**했고(DEC-023), 이를 질문 목록으로 남긴다:

- 03-system-design.md §3.2(PASS, v1.2): "`status` 필드는 **v1에서 자동으로는 절대 `unsubscribed`로 전환되지 않는다**... v1은 더블옵트인/발송 인프라가 없어 자동 구독취소 링크를 만들 수 없기 때문이다... v1의 실제 삭제 경로는 §5.6에 명시한 대로 운영자의 수동 하드 삭제뿐이다"라고 **반복적으로, 명시적으로** 못박았다.
- 03 §5.3: "더블 옵트인(확인 메일 발송)은 v1에서 구현하지 않는다 — 실제 발송 인프라 자체가 별도 WU로 분리되어 있기 때문".
- 02-planning.md §9/가정 A9: WU-07 범위를 "이메일 수집 폼까지"로만 한정하고, "발송 인프라(벤더 선택 포함)는 별도 Work Unit으로 분리"라고 명시.
- **이미 게시된 WU-06 개인정보처리방침 본문**(`webapp/legal/migrations/0002_create_legal_pages.py`)이 이용자에게 "본 사이트는 현재 자동 구독취소 기능을 제공하지 않으므로, 탈퇴를 원하시면 아래 '문의처'로 연락해 주시기 바랍니다"라고 명시적으로 고지한 상태다.

지금 임의로 토큰 스킴(URL 경로, 만료 정책, 서명 방식)을 설계하면 (a) PASS된 설계서/이미 배포된 법적 고지와 직접 모순되고, (b) 실제 발송 인프라 WU가 착수될 때 그 인프라의 요구사항에 맞춰 다시 설계해야 할 가능성이 높아 과설계이기도 하다. **질문**: 구독 취소 토큰/URL을 지금 선제적으로 만들어야 한다면, 03 설계서의 "v1은 자동 구독취소 링크 없음" 조항부터 규칙 F(피드백 루프)로 먼저 갱신해 줄 것을 요청한다 — 설계서 갱신 없이 코드만 앞서가면 문서-코드 불일치가 발생한다.

### 1.4 구독 폼 UX 반영 — 04 §2/§4

04-ux-design.md가 지정한 위치에 정확히 배치했다(단, §3에서 설명하는 이유로 실제 렌더링은 캐시되지 않는 조각으로 분리):

| 화면 | 배치 | 04 근거 |
|---|---|---|
| S-01 홈(빈 상태) | 본문 강조 배치(`variant="emphasis"`) | §2 "빈 상태를 구독 전환 기회로 전환" |
| S-01/S-03/S-04(홈/카테고리/태그) | Footer | §2 Footer "홈/목록형 화면 한정" |
| S-02 게시물 상세 | 본문 하단 인라인, Footer는 기본값(숨김) 유지 | §2 "상세 화면은 본문 하단 인라인과 중복 배치하지 않음" |
| S-05/06/07(법적 페이지)/404/500 | 없음 | "홈/목록형 화면 한정"에 해당하지 않음 |

접근성(04 §5)을 그대로 반영했다: `<label for>` 명시 연결, 에러 텍스트를 `aria-describedby`로 필드와 연결, 허니팟은 `aria-hidden="true"` 컨테이너 + `tabindex="-1"`로 스크린리더/키보드 흐름에서 완전히 제외, 체크박스 터치 타겟 24×24px 이상.

### 1.5 개인정보처리방침 연계 — REQ-007과의 교차

구독 폼에 "개인정보처리방침에 따른 개인정보 수집·이용에 동의합니다" 체크박스를 필수로 두고(`/privacy-policy/`로 링크), 미동의 시 400으로 거부한다(03 §5.6). 동의 시점의 `consent_version`(`subscribers/constants.py`)을 스냅샷으로 저장한다 — §3.2에 소스/근거를 남겼다.

---

## 2. 설계서 대비 편차

| # | 편차 | 사유 |
|---|---|---|
| 1 | 구독 취소 토큰/URL 미구현(오케스트레이터 지시 §3과 다름) | §1.3/DEC-023 참고. PASS된 03/02 설계서와 이미 게시된 WU-06 법적 문구를 우선했다. |
| 2 | `consent_version` 값을 `legal.LegalPage`에서 동적으로 읽지 않고 `subscribers/constants.py`의 정적 문자열로 스냅샷 | 03 §3.2가 "버전 스냅샷"만 요구하고 구체적 소스를 지정하지 않았고, `legal.LegalPage`(DEC-022)에는 버전 필드가 없다. `subscribers`가 `legal`을 import하면 03 §1.2 "경계 원칙"(개인정보 앱과 공개 콘텐츠 앱 격리)을 깬다. DEC-024 참고 — 방침 본문이 바뀌면 이 상수를 수동으로 갱신해야 하는 운영 절차가 필요하다(§4에 명시). |
| 3 | 레이트리밋을 전용 패키지(django-ratelimit 등) 없이 기존 `LocMemCache`(DEC-012)로 구현 | 03 §5.3이 구현 수단을 지정하지 않았고, 새 의존성 추가는 운영 규모 대비 과설계로 판단(DEC-024). LocMemCache는 프로세스 로컬이라 Gunicorn 워커가 여러 개면 워커별로 카운터가 분리되는 한계가 있음을 인지하고 기록한다. |
| 4 | **폼(및 CSRF 토큰)을 `@cache_page`가 걸린 페이지의 캐시된 HTML에 직접 렌더링하지 않고, 캐시되지 않는 조각 엔드포인트(`GET /newsletter/form/`)+무-JS 전용 페이지(`GET /newsletter/`)로 분리** | §3/DEC-025 참고. 로컬 검증에서 직접 재현한 치명적 결함(캐시된 폼 제출 시 403)에 대한 필수 수정이며, 03은 이 캐시/CSRF 상호작용을 언급하지 않았다. |

---

## 3. 핵심 발견: 캐시된 페이지 + CSRF 폼 결함, 그리고 해결 방식

`@cache_page(VIEW_CACHE_SECONDS)`가 걸린 홈/카테고리/태그/게시물 상세(WU-04/05 소유)에 뉴스레터 폼을 `{% csrf_token %}`과 함께 직접 렌더링하면, **Django의 캐시 HIT은 뷰를 재실행하지 않는다** — 즉 `get_token()`이 호출되지 않아:

- 캐시를 채운 첫 방문자 이후의 방문자는 CSRF 쿠키 자체를 받지 못하거나,
- 받더라도 캐시에 박제된 첫 방문자의 토큰과 일치하지 않는다.

`Client(enforce_csrf_checks=True)`(기본 테스트 Client는 CSRF 검사를 건너뛰어 이 결함을 가리므로 반드시 이 옵션으로 재현해야 한다)로 실제 재현한 결과:

```
c1 = Client(enforce_csrf_checks=True); c1.get("/")   # 캐시 MISS, c1은 쿠키를 받음
c2 = Client(enforce_csrf_checks=True); c2.get("/")   # 캐시 HIT, c2는 쿠키를 못 받음(Set-Cookie 없음)
# c2가 캐시된 HTML 속 토큰으로 제출 -> 403 Forbidden (CSRF cookie not set.)
```

이는 REQ-016의 핵심 기능(구독 제출) 자체가 캐시 TTL(10분) 동안 사실상 항상 실패하는 치명적 결함이라 이번 WU 범위 내에서 반드시 고쳐야 했다(다른 WU 소유 코드를 건드리지 않는 선에서). 참고로 `Vary: Cookie` 헤더 자체는 세션/인증 컨텍스트 프로세서 때문에 **WU-07 이전부터 모든 페이지에 이미 존재**했음을 확인했다(`/privacy-policy/`로 재현) — 이는 WU-07이 새로 만든 문제가 아니다. WU-07이 실제로 새로 만들 뻔했던 문제는 "캐시된 페이지에 CSRF 토큰을 박아 넣어 다른 방문자에게 그대로 재사용시키는 것"이었다.

**해결**: 캐시된 페이지에는 정적인 자리표시자(`_newsletter_slot.html`, `{% url %}`만 포함 — 방문자별로 달라지지 않으므로 캐시에 안전)만 남기고, 실제 폼은 두 개의 **캐시하지 않는** 엔드포인트로 분리했다.

- `GET /newsletter/form/` — JS(`newsletter.js`)가 fetch로 이 슬롯을 채운다. 매 요청마다 새로 렌더링되므로 항상 요청자 본인의 쿠키와 일치하는 토큰을 만든다.
- `GET /newsletter/` — `<noscript>` 링크의 목적지. JS 없이도 항상 동작한다(04 §0).

재검증 결과, 두 독립 방문자가 **동일한 캐시된 홈 페이지 본문**(DEC-012 공유 캐시 유지 확인)을 받으면서도 각자 올바른 CSRF 토큰으로 구독에 성공함을 확인했다(`subscribers/tests.py::NewsletterCachedPageCsrfTests`, §5 참고). WU-04/05/06이 소유한 `@cache_page` 설정 자체는 전혀 건드리지 않았다.

---

## 4. 수동 확인이 필요한 부분 (6단계 테스터 참고)

1. **`PRIVACY_POLICY_VERSION` 수동 동기화**: `subscribers/constants.py`의 값은 `legal/migrations/0002_create_legal_pages.py`의 개인정보처리방침 본문 게시일과 수동으로 맞춰야 한다. 향후 WU-06이 방침 본문을 실질적으로 개정하면 이 상수도 함께 갱신해야 하며, 자동 동기화 장치는 없다(DEC-024).
2. **LocMemCache 기반 레이트리밋의 다중 워커 한계**: production에서 Gunicorn 워커를 2개 이상 띄우면 IP당 카운터가 워커별로 분리되어 실질적으로 임계치가 `RATE_LIMIT_MAX_ATTEMPTS × 워커 수`에 가까워진다. 현재 render.yaml/03 설계가 단일 인스턴스를 전제하므로 v1에서는 허용 가능한 트레이드오프로 판단했으나, 워커 수를 늘리면 재검토가 필요하다.
3. **`/newsletter/csrf/` 계열 엔드포인트를 만들지 않은 이유**: `ensure_csrf_cookie`로 쿠키만 미리 굽는 방식도 검토했으나, 캐시된 HTML에 박힌 토큰과 방문자 쿠키가 여전히 어긋나는 문제(§3)가 그대로 남아 채택하지 않았다 — 최종적으로 폼 자체를 캐시 밖으로 빼는 방식(조각 엔드포인트)으로 귀결했다.
4. **X-Forwarded-For 신뢰 방식 확인 필요 이월**: 03 §5.5.4가 남긴 "Render가 X-Forwarded-For를 자체적으로 신뢰 보증하는지 공식 문서로 확인 필요" 항목은 이번 WU에서도 재확인하지 못했다 — WU-01/unit-01-note.md가 이미 이월한 사항 그대로, 10단계에서 실측 필요.
5. **R2/실제 배포 환경에서의 CSRF_COOKIE_SECURE 상호작용**: production.py는 `CSRF_COOKIE_SECURE = True`다. 로컬 검증은 전부 `dev` 설정(HTTP, `CSRF_COOKIE_SECURE` 미설정)으로 수행했으므로, 실제 HTTPS(Render) 환경에서 조각 엔드포인트의 쿠키 발급이 동일하게 동작하는지는 10단계 실측 대상이다(WU-01/DEC-015 패턴과 동일한 성격의 이월).

---

## 5. 로컬 검증 결과 (venv/DB는 정리 완료, 소스만 남음)

`webapp/`에 임시 가상환경(`.venv_wu07`, requirements.txt 그대로 설치)과 SQLite DB(`db.sqlite3`, `dev` 설정 기본값)를 만들어 검증한 뒤 **둘 다 삭제**했다. 검증 근거는 `subscribers/tests.py`(12개, `manage.py test subscribers`로 재실행 가능)와 아래 수동 재현이다.

### 5.1 자동화 테스트 (`subscribers/tests.py`, 12개 전부 PASS)

- `NewsletterSubscribeTests`(9개): 정상 구독→DB 저장(`test_subscribe_creates_record`), 중복 구독(대소문자 다른 재제출, `test_duplicate_subscribe_does_not_create_second_record`), 잘못된 이메일 형식 거부(`test_invalid_email_rejected`), 동의 누락 거부(`test_missing_consent_rejected`), 허니팟 위장 응답+미저장(`test_honeypot_filled_pretends_success_without_saving`), 레이트리밋 429(`test_rate_limit_blocks_after_threshold`), AJAX JSON 응답(`test_ajax_request_returns_json`), GET 405(`test_get_not_allowed`), **X-Forwarded-For 시뮬레이션**(`test_x_forwarded_for_rightmost_value_used_as_client_ip` — unit-01-note.md §Case C와 동일하게 `XForwardedForMiddleware`를 뷰에 직접 감싸 `X-Forwarded-For: 9.9.9.9, 203.0.113.77` 헤더를 보내고 rightmost 값만 채택되어 `source_ip_masked == "203.0.113.0"`이 됨을 확인).
- `NewsletterCachedPageCsrfTests`(3개, §3 결함의 회귀 테스트): 캐시된 홈 페이지에 폼이 직접 렌더링되지 않음(`test_cached_home_page_does_not_embed_a_form`), 캐시를 공유하는 두 독립 방문자가 각자 성공적으로 구독함(`test_two_independent_visitors_can_each_subscribe_after_shared_cache_fill`), 전용 페이지가 JS 없이도 동작함(`test_dedicated_newsletter_page_works_without_js`).

```
$ manage.py test subscribers -v 2
...
Ran 12 tests in 0.2xx s
OK
```

`manage.py test`(전체)도 함께 실행해 다른 앱에 회귀가 없음을 확인했다(다른 앱에는 기존에 tests.py가 없어 12개 그대로 통과).

### 5.2 수동 재현 (Django shell/test client)

- 실제 `BlogPostPage`/`Category`를 만들어 홈(`/`)·게시물 상세(`/blog/test-post/`)·카테고리(`/category/tech/`)·법적 페이지(`/privacy-policy/`)에서 뉴스레터 슬롯 노출 위치를 직접 확인: 홈/카테고리는 footer 슬롯 1개(`form_id=footer`), 게시물 상세는 본문 인라인 슬롯 1개(`form_id=post-detail`, footer 중복 없음), 법적 페이지는 슬롯 0개 — 04 §2 배치 표(§1.4)와 정확히 일치. 검증에 쓴 테스트 게시물/카테고리는 삭제 완료.
- `Vary: Cookie`가 WU-07 이전부터(`/privacy-policy/`, 뉴스레터 폼 없음) 이미 존재함을 확인해, 이 헤더 자체는 이번 WU가 새로 만든 문제가 아님을 검증(§3).
- 400 응답의 무-JS 결과 페이지(`subscribe_result.html`)가 필드별 에러 문구를 실제로 렌더링함을 확인.
- AJAX 400 응답의 JSON 구조(`errors.email[0].message`, `errors.consent[0].message`)가 `newsletter.js`가 기대하는 구조와 일치함을 확인.

### 5.3 정적 분석/린트 (게이트 1)

`AI-AUTO-WORK` 저장소 전체(및 `webapp/`)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 이번에도 재확인**했다(직접 검색, WU-01~06과 동일 결론) — 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 Python 파일 전체에 `python -m py_compile`을 실행해 구문 오류 없음을 확인했고, `manage.py check`/`makemigrations --check --dry-run`(변경 없음 확인)/`manage.py test`(§5.1)로 실행 기반 검증을 대신했다. CSS/JS/HTML 템플릿 린터도 설정되어 있지 않아, 실제 렌더링(§5.2)으로 구문·참조 오류가 없음을 실행 기반으로 확인했다.

---

## 6. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 4건은 전부 사유와 함께 명시했다. 편차 1(구독 취소 토큰 미구현)은 오케스트레이터 지시와는 다르지만 PASS된 03/02 설계서 및 이미 게시된 법적 문구와는 일치하는 방향으로, 질문 목록으로 남겼다(§1.3).
- [x] **에러 처리가 누락된 경로가 없는가** — 레이트리밋 초과/폼 검증 실패/허니팟/중복 이메일 네 갈래 모두 명시적으로 분기해 처리한다(예외를 삼키고 무시하는 코드 없음). fetch 네트워크 오류는 `newsletter.js`가 사용자에게 명시적 에러 메시지를 보여주고 재시도를 유도한다(조용히 실패하지 않음). 조각(`/newsletter/form/`) fetch 실패 시에만 슬롯이 비어 보일 수 있는 드문 트레이드오프를 §4에 명시했다.
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 이메일/동의는 `NewsletterSubscribeForm`(서버사이드)이 검증한다. `form_id`/`variant` 쿼리파라미터는 화이트리스트로 제한한다(`views.py` `_ALLOWED_FORM_IDS`/`_ALLOWED_VARIANTS`). `next` 리다이렉트 값은 `_safe_next()`가 로컬 경로(`/`로 시작, `//` 아님)만 허용해 오픈 리다이렉트를 방지한다. `X-Forwarded-For`는 WU-01의 `XForwardedForMiddleware`가 이미 정규화한 `REMOTE_ADDR`을 그대로 신뢰한다(03 §5.5.4).
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 이번 변경분은 DB 모델/폼/뷰/정적 자산만 다루며 시크릿이 필요한 코드가 없다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `blog/models.py`, `home/models.py`, `core/`, `legal/`(WU-02/04/05/06 소유 핵심 로직)는 건드리지 않았다. `home_page.html`/`category_list.html`/`tag_list.html`/`blog_post_page.html`/`_post_list.html`/`footer.html`은 이번 WU가 뉴스레터 슬롯을 삽입하기 위해 반드시 손대야 하는 지점만 최소로 수정했다(기존 블록 구조·다른 컴포넌트는 그대로 유지). §3의 캐시/CSRF 수정은 WU-07 자신의 기능(뉴스레터 폼)이 실제로 동작하게 하기 위한 필수 조치였고, WU-04/05/06이 소유한 `@cache_page` 데코레이터 자체는 어떤 파일에서도 수정하지 않았다.

---

## 7. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-016 행을 갱신했다: "작업 단위"는 이미 WU-07로 지정되어 있었고, "구현 상태"를 "Not Started" → "구현 완료(`unit-07-note.md`, 구현 근거 파일 경로)"로, "단위테스트"를 "대기(6단계)"로 채웠다. "비고"에 발송 인프라/자동 구독취소 범위 밖 사실과 §3에서 발견·해결한 캐시/CSRF 결함을 추가로 명시했다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다.

---

## 8. 6단계 테스터를 위한 인수 조건 (Acceptance Criteria)

모두 `dev` 설정(SQLite) 기준, 별도 `.venv`에서 `pip install -r requirements.txt` 후 재현 가능. `manage.py migrate` 선행 필요.

**AC1. 정상 구독**
`POST /newsletter/subscribe/`에 `email=user@example.com`, `consent=on`, `hp_field=`(빈 값)을 CSRF 토큰과 함께 보내면 200을 반환하고, `NewsletterSubscriber` 테이블에 `email="user@example.com"`, `status="active"` 레코드가 정확히 1건 생성된다.

**AC2. 중복 구독(대소문자 무관)**
AC1 이후 같은 이메일을 `User@Example.com`처럼 대소문자만 바꿔 재제출해도 200을 반환하고, 레코드는 여전히 1건이며 `consented_at`만 최신 시각으로 갱신된다(신규 레코드가 추가로 생기지 않음).

**AC3. 잘못된 이메일 형식 거부**
`email=not-an-email`로 제출하면 400을 반환하고, DB에 레코드가 생성되지 않는다. 응답 본문(무-JS 경로) 또는 JSON(`X-Requested-With: XMLHttpRequest`, AJAX 경로)에 이메일 형식 오류 메시지가 포함된다.

**AC4. 동의 누락 거부**
`consent` 필드를 비운 채 제출하면 400을 반환하고 DB에 레코드가 생성되지 않는다.

**AC5. 허니팟(스팸 방지)**
`hp_field`에 아무 값(예: `bot`)을 채워 제출하면 200을 반환하지만(봇에게 성공한 것처럼 위장), DB에는 어떤 레코드도 생성되지 않는다.

**AC6. 레이트리밋(스팸 방지)**
같은 `REMOTE_ADDR`에서 서로 다른 이메일로 6회 연속 제출하면, 6번째 요청은 429를 반환한다(임계치는 `subscribers/constants.py`의 `RATE_LIMIT_MAX_ATTEMPTS=5`, `RATE_LIMIT_WINDOW_SECONDS=600`).

**AC7. IP 기록 및 마스킹**
`REMOTE_ADDR=203.0.113.42`로 정상 구독하면, 생성된 레코드의 `source_ip_masked`가 `"203.0.113.0"`(마지막 옥텟 0으로 마스킹)이다.

**AC8. X-Forwarded-For 시뮬레이션**
`config.middleware.XForwardedForMiddleware`로 뷰를 감싼 뒤(또는 production 유사 설정에서) `X-Forwarded-For: 9.9.9.9, 203.0.113.77` 헤더로 요청하면, `REMOTE_ADDR`이 rightmost 값(`203.0.113.77`)으로 재설정되어 `source_ip_masked`가 `"203.0.113.77"`이 아니라 `"203.0.113.0"`이 된다(leftmost `9.9.9.9`는 채택되지 않음).

**AC9. 캐시된 페이지에서의 실제 제출 성공 (핵심 회귀 조건, §3 참고)**
`Client(enforce_csrf_checks=True)`(또는 실제 브라우저) 두 개의 독립 세션으로 순서대로 홈(`/`)을 방문하면 — 첫 방문(캐시 MISS)과 두 번째 방문(캐시 HIT, 동일한 본문)에서 각각 `GET /newsletter/form/?form_id=footer`로 폼 조각을 받아, **두 세션 모두** 유효한 CSRF 토큰/쿠키 쌍으로 `POST /newsletter/subscribe/`가 200을 반환해야 한다(둘 다 403이 아니어야 함). 이 조건이 깨지면 §3에서 기록한 결함이 재발한 것이다.

**AC10. 무-JS 폴백**
JS를 비활성화한 브라우저(또는 `document.querySelector('[data-newsletter-slot]')`의 `<noscript>` 링크를 직접 따라가는 시나리오)로 `GET /newsletter/`에 접근하면, 실제로 동작하는 폼(유효한 CSRF 토큰 포함)이 렌더링되고 그 폼으로 제출하면 AC1과 동일하게 동작한다.

**AC11. 화면 배치**
홈(빈 상태)/카테고리/태그 화면에는 Footer에 뉴스레터 폼 슬롯이 노출되고, 게시물 상세 화면에는 본문 하단에만 슬롯이 노출되며 Footer에는 노출되지 않는다(중복 배치 없음). 법적 페이지(개인정보처리방침/이용약관/쿠키고지)·404·500에는 슬롯이 없다.

**AC12. 접근성**
이메일 입력/동의 체크박스 각각에 `<label for>`가 정확히 연결되어 있고, 검증 실패 시 해당 필드의 에러 텍스트가 `aria-describedby`로 연결된 요소에 노출된다. 허니팟 입력은 `aria-hidden="true"` 컨테이너 안에 있고 `tabindex="-1"`이라 Tab 키로 도달할 수 없다.

**AC13. 개인정보처리방침 연계**
동의 체크박스 라벨의 "개인정보처리방침" 링크가 `/privacy-policy/`로 정확히 연결된다.
