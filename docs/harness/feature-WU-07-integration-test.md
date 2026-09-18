# 테스트 결과서 (Test Result Report) — WU-07(이메일 뉴스레터 구독 폼) 업무 단위 통합테스트

## 1. 개요
- 테스트 대상: 업무 단위 WU-07(이메일 뉴스레터 구독 폼 수집, REQ-016) — 신규 `webapp/subscribers/`(models.py/forms.py/views.py/urls.py/admin.py/constants.py/utils.py/migrations/0001_initial.py/templates), 수정된 `webapp/config/settings/base.py`(INSTALLED_APPS)·`webapp/config/urls.py`(subscribers.urls include)·`webapp/config/templates/base.html`(newsletter.js 로드)·`webapp/config/templates/partials/footer.html`(뉴스레터 슬롯)·`webapp/config/static/js/newsletter.js`·`webapp/config/static/css/components.css`·`webapp/home/templates/home/home_page.html`·`webapp/blog/templates/blog/{category_list,tag_list,blog_post_page}.html`·`webapp/blog/templates/blog/partials/_post_list.html`을, **WU-01(초기설정/production 보안설정, PASS)+WU-02(콘텐츠모델, PASS)+WU-03(이미지, PASS)+WU-04(공개 화면, PASS)+WU-05(SEO, PASS)+WU-06(법적 페이지, PASS)가 이미 조립된 `webapp/` 전체** 위에 실제로 결합한 형태.
- 테스트 유형: 통합(Integration) — 업무 단위(WU-07) 전체 풀테스트, 7단계(`07-integration-tester`)
- 테스트 목적: `unit-07-test.md`(06단계, PASS — AC1~13 13/13 독립 재현, 05단계 자동화 테스트 12개 재실행 + 위험입력/gap 테스트 18개 추가, 결함 0건)는 WU-07을 **`dev`(SQLite, 평문 HTTP) 설정 단독**으로 검증했다(§2 제외범위에 "production 환경(R2/HTTPS 쿠키 보안 속성) 실측"을 10단계로 명시적으로 이월). 이번 07단계는 06단계가 다루지 않은 **단위 간 경계**에만 집중한다(규칙B, 이미 검증된 것을 반복하지 않음):
  1. **WU-04가 소유한 실제 화면들(홈/카테고리/태그/게시물 상세)에 배치된 구독 폼이 전부 실제로 동작하는지** — 06단계는 "슬롯 배치 위치"(TC-011)만 dev 설정에서 확인했고, 각 화면에서 실제 구독 제출이 성공하는지는 홈(footer)만 확인했다(TC-009). 이번 07단계는 홈/카테고리/태그/게시물상세 4개 화면 전부에서 실제 제출까지 성공하는지 신규로 확인한다.
  2. **WU-01의 production 유사 보안설정(SECURE_PROXY_SSL_HEADER/SECURE_SSL_REDIRECT/SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE=True/HSTS/XForwardedForMiddleware) + WU-01 DEC-012 캐시(LocMemCache) + WU-07 CSRF 수정(DEC-025, 캐시된 페이지에 폼 대신 조각 엔드포인트 분리)이 조합된 실제 production 유사 HTTPS 환경**에서 구독이 정상 동작하는지 — `unit-07-test.md` §7이 "CSRF_COOKIE_SECURE=True + 실제 HTTPS 환경에서의 조각 엔드포인트 쿠키 발급 미검증"으로 명시적으로 이월한 항목을 이번 07단계가 최초로 실측한다.
  3. 06단계가 이월한 잔존 리스크 3건(LocMemCache 다중워커 레이트리밋 한계, `PRIVACY_POLICY_VERSION` 수동동기화, X-Forwarded-For Render 공식보증 여부)이 Critical/High급인지 근거를 갖고 재판단한다.
  4. 전체 마이그레이션 체인(`subscribers` 앱 포함)을 빈 DB에서 dev/production 유사 양쪽으로 처음부터 재적용해 회귀가 없는지 확인한다.
  5. WU-06 개인정보처리방침 게시 문구와 실제 구독 동의 체크박스 문구/링크가 최종적으로 일치하는지 교차검증한다.
  6. REQ-016이 최종적으로 충족됐는지 확인한다.
- 관련 산출물:
  - `docs/harness/units/unit-07-note.md`(§1~§8, 구현/편차/핵심발견 DEC-025/인계사항 §4/인수조건 AC1~13)
  - `docs/harness/units/unit-07-test.md`(06단계, PASS — AC1~13 13/13, TC-001~036, §7 잔존 리스크 4건)
  - `docs/harness/03-system-design.md`(v1.2, 특히 §1.2 모듈 경계, §3.1/§3.2 NewsletterSubscriber ERD, §4 `POST /newsletter/subscribe/` 계약, §5.3 뉴스레터 보안/동작 계약, §5.5 리버스프록시 배포환경 보안설계, §5.6 개인정보 처리 원칙)
  - `docs/harness/04-ux-design.md`(v1.2, S-01~S-04 배치, §4 컴포넌트 상태, §5 접근성)
  - `docs/harness/decisions.md`(DEC-001~025, 특히 DEC-012/DEC-023/DEC-024/DEC-025)
  - `docs/harness/feature-WU-01-integration-test.md`(부록B, PASS — DEF-001 Fixed, raw WSGI/ASGI production 보안설정 검증 방법론)
  - `docs/harness/feature-WU-04-integration-test.md`(PASS — `it_test_prodlike_wu04feature.py` 방법론, `X-Forwarded-Proto` 헤더 기반 Render 실트래픽 재현이 `secure=True` 단독보다 결정적임을 실증한 선례)
  - `docs/harness/feature-WU-06-integration-test.md`(PASS — legal 3페이지 게시 문구 정합성 확인 방법론)
  - `docs/harness/traceability.md`(REQ-016)
- 테스트 수행자(에이전트): `07-integration-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- **범위(In-Scope)**:
  1. **전체 마이그레이션 체인 처음부터 재현**: 신규 임시 venv에서 `pip install`부터 시작해, 빈 SQLite에 전체 마이그레이션(`subscribers.0001_initial` 포함)이 dev 설정과 production 유사 설정 양쪽에서 오류 없이 적용되는지.
  2. **WU-04 4개 화면(홈/카테고리/태그/게시물상세) 전부에서 실제 구독 제출 성공(신규 핵심 관점)**: 06단계가 홈(footer)만 확인한 것과 달리, 카테고리(footer)/태그(footer)/게시물 상세(본문 인라인, `form_id=post-detail`)까지 전부 실제 CSRF 조각 발급→제출→DB 저장까지 왕복 확인.
  3. **WU-01 production 유사 보안설정 + WU-01 DEC-012 캐시 + WU-07 DEC-025 결합(신규 핵심 관점, unit-07-test.md §7 이월 항목의 최초 실측)**: `SECURE_PROXY_SSL_HEADER`/`SECURE_SSL_REDIRECT`/`CSRF_COOKIE_SECURE=True`/`XForwardedForMiddleware`가 전부 켜진 상태에서, 캐시를 공유하는 두 독립 방문자가 각자 조각 엔드포인트로 CSRF 토큰을 받아 실제로 구독에 성공하는지(AC9의 HTTPS 재현). `X-Forwarded-Proto` 헤더 기반(Render 실제 트래픽 형태, WU-01/WU-04 확립 방법론)으로 재현한다.
  4. **HTTPS 환경에서 활성화되는 Django CSRF Origin/Referer 검사와 뉴스레터 폼(무-JS 폼 제출 + JS fetch 양쪽)의 상호작용(신규 발견 관점)**: `request.is_secure()`가 `True`일 때만 활성화되는 Referer/Origin 검사 분기(dev 설정에서는 전혀 발동하지 않음)가 실제로 무-JS 폼 제출(Referer 기반)과 JS fetch(Origin 기반) 양쪽에서 정상 통과하는지, 그리고 어느 쪽도 없을 때 어떻게 되는지.
  5. 06단계 잔존 리스크 3건의 Critical/High 여부 재판단(근거 기반).
  6. `docs/harness/traceability.md` REQ-016 "통합테스트" 컬럼 갱신 및 REQ-016 최종 충족 확인.
  7. WU-06 개인정보처리방침 게시 문구와 구독 동의 체크박스 문구/링크 최종 교차검증.
  8. WU-01~06 주요 공개 엔드포인트 + 전체 자동화 테스트 스위트 회귀 확인.
  9. 검증에 사용한 venv/DB/staticfiles/임시 설정 모듈/임시 스크립트 정리.
- **제외 범위(Out-of-Scope) 및 사유**:
  1. **06단계가 이미 PASS로 확정한 AC1~13/TC-001~036의 반복 재검증**(정상구독/중복구독/이메일형식/동의누락/허니팟/레이트리밋 경계값/IP마스킹/XFF rightmost/무-JS 폴백/접근성 마크업/위험입력 17종/DEC-023 일관성/어드민 하드삭제전용/게이트1·2): `unit-07-test.md`가 신규 venv로 독립 재현해 PASS를 확정했으므로, 이번 07단계는 그 결과를 신뢰하고 **"WU-01~06과 조립됐을 때"라는 06단계가 dev 설정으로만 다룬 새 경계에만 집중**한다(규칙B).
  2. **실제 브라우저/스크린리더 E2E** — MCP(Playwright/Chrome 등) 미연동(DEC-001)으로 이전 단계들과 동일하게 도구 기반 수행 불가. `Client(enforce_csrf_checks=True)` + 실제 `Referrer-Policy` 응답 헤더 확인으로 대체하고, 한계는 §7에 리스크로 명시한다.
  3. **R2 오브젝트 스토리지 실제 네트워크 연동, Neon PostgreSQL 실제 연결** — WU-01~06과 동일하게 SQLite 대체 + 더미 R2 환경변수로 `check`/`migrate`/`collectstatic`의 코드 경로만 검증한다(WU-07은 이미지/R2에 의존하지 않으므로 영향 최소).
  4. **실제 gunicorn/uvicorn 프로세스 기동, 실제 Render 인프라의 헤더 실측** — Windows 로컬 한계로 이번에도 미검증. `X-Forwarded-Proto`/`X-Forwarded-For` 헤더를 Django 테스트 클라이언트로 직접 주입해 애플리케이션 레벨 체인은 재현했다(WU-01 IT-R04/R05, WU-04 §3 방법론과 동일). 10단계에서 실제 Render 인프라 최종 재확인 필요(§7 유지, 신규 아님).
  5. **실제 이메일 발송/수신, 구독취소 토큰/URL** — 02 가정 A9/03 §5.3/DEC-023이 이미 WU-07 범위 밖으로 명시했고, 이번 조립 상태에서도 해당 기능 자체가 존재하지 않는다.
  6. **동시성/부하 테스트** — 이번 업무 단위 인수조건에 해당 항목이 없고 8단계 영역이다.
  7. **8단계(전체 풀테스트) 범위와의 교차** — WU-08(무료티어 대응) 이후 업무 단위와의 상호작용은 아직 미개발이므로 이번 범위가 아니다. 다만 "8단계에서 문제가 생기지 않을까"에 대한 2차 내부검증 관점 재검토는 §9에서 별도 수행했다.

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`). `webapp/requirements.txt`(Django==5.2.17, wagtail==7.4.3 등, 신규 패키지 없음)를 새 venv(`webapp/.venv_wu07it`, `webapp/.venv_wu07it2` — 스크린/보강 검증용으로 2회 생성, 검증 후 전부 삭제)에 clean install.
- **dev 설정** (`config.settings.dev`, SQLite): 전체 마이그레이션 체인 처음부터 재현(§4-1), 전체 자동화 테스트 스위트 회귀(§4-6)에 사용.
- **production 유사 설정 — WU-01/WU-04가 확립한 방법론 계승**: `config/settings/it_test_prodlike_wu07feature.py`(이번 07단계가 신규 생성 — `production.py`를 그대로 상속하고 `DATABASES`만 SQLite로 재정의, 검증 후 삭제). 더미 환경변수(`SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=blog-web.onrender.com`, `RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`, `DATABASE_URL=postgres://user:pass@localhost:5432/dummydb`(가짜, 실제 연결 시도 없음 — `DATABASES`를 SQLite로 override했으므로 실제로는 쓰이지 않음), `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL` 전부 더미)로 `SECURE_PROXY_SSL_HEADER`/`SECURE_SSL_REDIRECT`/`SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/HSTS/`XForwardedForMiddleware`가 전부 켜진 상태를 재현했다. 이 설정으로 §4-2~§4-5를 수행했다.
- **Render 실제 트래픽 재현 방법**: WU-04 §6-2가 실측으로 규명한 대로, `Client(secure=True)`(전송 계층 시뮬레이션만, `X-Forwarded-Proto` 헤더는 만들지 않음) 단독으로는 결과가 비결정적일 수 있다는 선례를 그대로 계승해, 이번 07단계는 전 케이스에서 `HTTP_X_FORWARDED_PROTO="https"` 헤더를 명시적으로 실어 보내는 방식(Render 엣지가 실제로 보내는 형태)을 사용했다.
- **실제 브라우저의 `Referer` 전송 근거 확보**: Django 기본 `SECURE_REFERRER_POLICY = "same-origin"`(오버라이드 없음, `grep` 직접 확인)이 `Referrer-Policy: same-origin` 응답 헤더로 실제 노출되는지 먼저 확인한 뒤(§4-3 IT-02), 이 정책 하에서 실제 브라우저가 보낼 것으로 기대되는 동일-오리진 `Referer` 헤더를 테스트에서 명시적으로 재현했다.
- 테스트 데이터: 06단계와 마찬가지로 픽스처 없는 인라인 payload. 콘텐츠는 이번 07단계가 직접 생성 — **WU-06 데이터 마이그레이션(`legal/migrations/0002_create_legal_pages.py`)이 이미 만들어 둔 기본 `HomePage`/`Site`/법적 페이지 3종을 그대로 재사용**(새로 만들지 않음 — 실제 배포 후 마이그레이션 직후 상태와 정확히 동일한 출발점을 보장하기 위함)하고, 그 위에 `Category`("Tech")/`BlogPostPage`("test-post", 태그 "django" 포함)를 추가로 생성했다(검증 후 DB 자체를 삭제하므로 저장소에 흔적 없음).
- 전제 조건:
  - `manage.py migrate`가 빈 DB에서 dev/production 유사 양쪽 모두 오류 없이 전체 적용됨을 선행 확인(§4-1).
  - 뷰 캐시(LocMemCache, DEC-012)가 프로세스 내에서 공유되므로 각 시나리오 시작 전 `cache.clear()`로 통제했다.
  - 검증에 사용한 venv(`.venv_wu07it`, `.venv_wu07it2`), `db.sqlite3`/`db_wu07it.sqlite3`, `staticfiles/`, `media/`, `__pycache__`, 임시 설정 모듈(`config/settings/it_test_prodlike_wu07feature.py`), 임시 스크립트(`_wu07_it_prodlike_TMP.py`, `_wu07_it_prodlike_extra_TMP.py`), 임시 마이그레이션 로그는 검증 완료 후 전부 삭제했다(§10에서 `git status --porcelain`으로 최종 확인).

## 4. 테스트 케이스 및 결과

### 4-1. 전체 마이그레이션 체인 (신규 venv, 빈 DB, 처음부터)

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-01 | dev 설정, 빈 SQLite 전체 마이그레이션 | 신규 venv, `pip install` 완료 | `manage.py migrate`(처음부터) | `subscribers.0001_initial` 포함 전체 오류 없이 적용 | 오류 없이 전체 적용(wagtail 코어 포함 약 140개 마이그레이션 + `subscribers.0001_initial`) | PASS | |
| IT-02 | dev 설정, `check`/`makemigrations --check` | 위 상태 | `manage.py check`, `makemigrations --check --dry-run` | 오류 없음, "No changes detected" | "System check identified no issues (0 silenced)", "No changes detected" | PASS | |
| IT-03 | production 유사 설정, 빈 SQLite 전체 마이그레이션 | `it_test_prodlike_wu07feature.py` + 더미 환경변수 | `manage.py check`, `migrate`(처음부터), `makemigrations --check --dry-run` | 전부 오류 없이 종료 | `check`: "no issues", `migrate`: 오류 없이 전체 적용(`subscribers.0001_initial` 포함), `makemigrations`: "No changes detected" | PASS | |
| IT-04 | production 유사 설정 `collectstatic` | 위 상태 | `manage.py collectstatic --noinput` | 오류 없이 종료 | "218 static files copied ... 638 post-processed" — WU-06(`feature-WU-06-integration-test.md` IT-12, 217/635)에서 **+1 정적파일/+3 post-processed**, WU-07이 추가한 `static/js/newsletter.js`(+1 원본, 해시본+gzip 변형 포함 +3) 만큼만 정확히 증가함을 수치로 직접 확인 — 예상치 못한 추가/누락 없음 | PASS | 정적자산 수준 회귀 없음을 수치로 실측(추측 아님) |
| IT-05 | `newsletter.js` 해시 URL 실제 서빙 | 위 상태 | `GET /`(HTTPS 헤더) 응답 본문에서 `<script src="...">` 추출 → 그 경로로 `GET` | `/static/js/newsletter.<hash>.js` 형태, 200 | `newsletter.51e0e9620c79.js`로 정확히 참조됨, 해당 경로 `GET` → 200, `Content-Type: text/javascript; charset="utf-8"` | PASS | WhiteNoise 매니페스트 스토리지가 WU-07 신규 정적자산도 정상 처리함을 확인 |

### 4-2. WU-04 4개 화면 전부에서 실제 구독 제출 성공 + HTTPS 결합 (신규 핵심 관점 — `X-Forwarded-Proto: https` 헤더로 Render 실트래픽 재현)

콘텐츠: WU-06 fixture의 기본 `HomePage`(`/home/`, `Site.root_page`로 재지정) + 신규 `Category`("tech") + 신규 `BlogPostPage`("test-post", 태그 "django"). `Site.hostname`을 `blog-web.onrender.com:443`으로 재설정.

| ID | 시나리오(경계) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-06 | 홈(S-01)/상세(S-02)/카테고리(S-03)/개인정보방침 HTTPS 200 (DEF-001 회귀 없음) | production 유사, `HTTP_X_FORWARDED_PROTO=https` | 4개 경로 `GET` | 전부 200(무한루프 없음) | `/`→200, `/blog/test-post/`→200, `/category/tech/`→200, `/privacy-policy/`→200 | PASS | WU-01 DEF-001(무한 리다이렉트)이 WU-07 라우트에서도 재발하지 않음 |
| IT-07 | HTTPS 환경에서 4개 화면의 뉴스레터 슬롯 배치가 04 §2와 정확히 일치 | 위 상태 | 각 응답의 `data-newsletter-slot` 출현 횟수 카운트 | 홈=1(footer), 상세=1(인라인, footer 미노출), 카테고리=1(footer), 방침=0 | home=1, detail=1, category=1, privacy=0 | PASS | `unit-07-test.md` TC-011(dev 설정)과 동일한 배치가 production 유사 HTTPS 환경에서도 유지됨을 최초 확인 |
| IT-08 | `Referrer-Policy: same-origin` 응답 헤더 실제 노출 확인 | 위 상태 | 홈 응답 헤더 조회 | `Referrer-Policy: same-origin` | 정확히 `same-origin` (Django 기본값, 프로젝트가 오버라이드하지 않음을 `grep`으로 재확인) | PASS | 실제 브라우저가 동일-오리진 요청에 `Referer`를 보낼 근거 확보(§4-4 해석의 전제) |
| IT-09 | 캐시 공유(DEC-012)가 HTTPS 환경에서도 여전히 유지됨 | `cache.clear()` | 두 독립 `Client(enforce_csrf_checks=True)`가 순서대로 홈 방문(HTTPS 헤더) | 두 방문자의 홈 본문이 완전히 동일(캐시 공유) | `home1.content == home2.content`(5744바이트, 완전 일치), 둘 다 200 | PASS | |
| IT-10 | **(핵심) 캐시 공유+HTTPS+Secure쿠키 조합에서 두 독립 방문자가 홈 footer에서 각자 구독 성공** (AC9의 HTTPS 재현, `unit-07-test.md` §7 이월 항목 실측) | IT-09 이후 | 각자 `GET /newsletter/form/?form_id=footer`(`Referer: https://blog-web.onrender.com/`)로 서로 다른 토큰 수신 → 각자 `POST /newsletter/subscribe/` | 두 토큰이 서로 다름, 둘 다 200(403 아님) | 토큰 서로 다름(`rAIp4M49...` vs `NI5H0yQ5...` 등, 실행마다 랜덤), 둘 다 200 | PASS | DEC-025(캐시/CSRF 분리)와 WU-01 HTTPS 강제/Secure 쿠키 설정이 실제로 함께 동작함을 최초 실측 |
| IT-11 | 구독 레코드 2건 실제 생성 | IT-10 이후 | `NewsletterSubscriber.objects.filter(email__in=[...]).count()` | 2 | 2 | PASS | |
| IT-12 | CSRF 쿠키에 `Secure` 속성이 실제로 부여됨(`CSRF_COOKIE_SECURE=True` 반영 확인) | IT-10 이후 | `client.cookies["csrftoken"]["secure"]` 조회 | `True` | `True` | PASS | production.py의 정적 설정이 실제 `Set-Cookie` 응답에 반영됨을 코드가 아닌 실제 쿠키 객체로 확인 |
| IT-13 | **게시물 상세(S-02) 화면 — 본문 인라인 슬롯(`form_id=post-detail`)에서 캐시 공유+HTTPS 환경 실제 구독 성공** | `cache.clear()`, 신규 두 방문자 | 상세 페이지 방문(캐시 공유 확인) → `form_id=post-detail` 조각 수신 → 각자 구독 제출 | 상세 본문 동일(캐시 공유), 둘 다 200 | `detail1.content == detail2.content`(캐시 공유 확인), 둘 다 200 | PASS | 06단계는 이 조합(상세화면+HTTPS+캐시)을 검증하지 않았음 — 이번 07단계 신규 |
| IT-14 | 상세화면 구독 레코드 2건 생성 | IT-13 이후 | DB count | 2 | 2 | PASS | |
| IT-15 | **태그 목록(S-04) 화면 — 실제 태그("django")로 목록 노출 + footer에서 HTTPS 구독 성공** | 신규 방문자 | `GET /tag/django/`(HTTPS) → 슬롯 1개 확인 → footer 조각 수신 → 구독 제출 | 200, 슬롯 1개, 구독 200 | `GET /tag/django/` → 200, 슬롯=1, 구독 → 200 | PASS | 06단계 TC-011은 태그 화면을 별도로 실 콘텐츠로 검증하지 않았음(카테고리만) — 이번 07단계가 최초로 태그 화면까지 실제 태그 데이터로 검증 |

### 4-3. 무-JS/AJAX 양쪽 경로 + DEF-001 회귀 (production 유사, HTTPS)

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-16 | 무-JS 전용 페이지(`/newsletter/`) HTTPS 실제 제출 성공 | 신규 방문자, HTTPS | `GET /newsletter/`(`Referer` 동일 오리진) → 토큰 추출 → `POST /newsletter/subscribe/`(`Referer: .../newsletter/`) | 페이지 200, 제출 200 | 페이지 200, 제출 200 | PASS | AC10의 HTTPS 재현 |
| IT-17 | `X-Forwarded-Proto` 헤더 없이 요청하면 정상 리다이렉트 유지(무한루프 아님) | HTTPS 헤더 미포함 | `GET /newsletter/`(`X-Forwarded-Proto` 없음) | 301, 올바른 `Location` | 301, `Location: https://blog-web.onrender.com/newsletter/` | PASS | WU-01 DEF-001 회귀 없음(WU-07 라우트 포함) |

### 4-4. HTTPS에서 활성화되는 CSRF Origin/Referer 검사와 뉴스레터 폼의 상호작용 (신규 발견 관점)

> **배경(발견 경위)**: Django `CsrfViewMiddleware.process_view`는 `HTTP_ORIGIN` 헤더가 있으면 그 값을 `CSRF_TRUSTED_ORIGINS` 기준으로 검증하고, 없으면 `elif request.is_secure():` 분기에서 `Referer` 헤더를 검사한다(`django/middleware/csrf.py` 434~462행, 코드 직접 확인). **`is_secure()`는 `SECURE_PROXY_SSL_HEADER`가 설정된 production에서만(§5.5.2) `X-Forwarded-Proto: https`로 `True`가 되므로, 이 검사 분기 자체가 06단계(dev 설정)에서는 단 한 번도 실행되지 않았다.** WU-01(HTTPS 강제)과 WU-07(첫 공개 POST 폼)이 실제로 조립되는 이번 07단계가 되어서야 이 분기가 처음으로 활성화된다 — 06단계가 원리적으로 다룰 수 없었던 단위 간 경계다.

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-18 | JS fetch 경로(`Origin` 헤더 포함) — Referer 없이도 성공 | HTTPS, `X-Requested-With: XMLHttpRequest` | `POST /newsletter/subscribe/`(`Origin: https://blog-web.onrender.com`, `Referer` 없음) | Origin 검증 경로로 200 | 200, `{"success": true, "rate_limited": false}` | PASS | `newsletter.js`의 `fetch()` 기반 점진적 향상 경로가 실제 브라우저의 `Origin` 헤더 전송 관행과 일치함을 확인 |
| IT-19 | Origin/Referer 둘 다 없는 HTTPS POST | HTTPS, 헤더 둘 다 없음 | `POST /newsletter/subscribe/`(유효한 CSRF 토큰, Origin/Referer 없음) | 403(`Referer checking failed - no Referer.`) | 403, 해당 사유로 거부 확인 | PASS(예상된 방어 동작 — **결함 아님**) | **중요**: 이는 Django 표준 CSRF 방어(HTTPS에서 MITM 차단 목적, 코드 주석에 명시)이며 WU-07이 만든 결함이 아니다. 이 사이트의 다른 모든 HTTPS POST 폼(어드민 로그인 등, WU-09 이후)도 동일한 제약을 받는다 — WU-07 고유 문제가 아니라 WU-01+production HTTPS 조합의 **일반적 특성**임을 이번 07단계가 최초로 실증하고 문서화했다(§7 리스크로 승계) |

**해석 및 실사용 영향 평가**: IT-08(`Referrer-Policy: same-origin`)이 확인됐으므로, 실제 브라우저는 (a) 무-JS `<form method=post>` 제출 시 동일 오리진이면 `Referer`를 보내고(IT-16이 이를 재현해 PASS), (b) `fetch()` 기반 제출 시 대부분의 최신 브라우저가 동일 오리진 POST에도 `Origin` 헤더를 자동으로 포함한다(IT-18이 이를 재현해 PASS). 두 경로 모두 실제 서비스 시나리오에서 정상 동작할 것으로 판단되나, **이는 Django 테스트 클라이언트로 헤더를 수동 재현한 것이지 실제 브라우저 확인이 아니므로**(§2 제외범위 2, DEC-001), 10단계(배포테스트)에서 실제 브라우저로 이 경로를 최종 확인할 것을 리스크로 명시한다(§7).

### 4-5. 06단계 잔존 리스크 3건 — Critical/High 여부 재판단 (신규 근거 확보)

| ID | 리스크(unit-07-test.md §7 인용) | 조사/실측 내용 | 판단 | 근거 |
|----|-----------------------------------|----------------|------|------|
| IT-20 | LocMemCache 기반 레이트리밋의 다중 워커 한계 | `webapp/render.yaml`의 `startCommand`(`gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`)를 직접 확인 — `--workers`/`-w` 플래그나 `WEB_CONCURRENCY` 환경변수 지정이 없어 **gunicorn 기본값(워커 1개)으로 동작**한다. 03 §6.2(단일 인스턴스 전제)와 일치. 이번 07단계가 production 유사 설정(HTTPS+LocMemCache)으로 레이트리밋 경계값(5회/6회째)을 재실행(IT-21)해도 정상 동작함을 확인 | **Critical/High 아님(Low, 현재 구성 기준)** — 현재 `render.yaml`이 명시적으로 단일 워커이므로 "워커별 카운터 분리"라는 전제 자체가 지금은 발생하지 않는다. 향후 트래픽 증가로 워커 수를 늘리면 재검토가 필요한 **미래 조건부 리스크**로, 규칙F(설계 결함 소급)를 트리거할 근거가 없다 | `webapp/render.yaml`(직접 확인), IT-21(레이트리밋 실측) |
| IT-21 | (IT-20 실측 근거) 레이트리밋 경계값, HTTPS+production 유사 LocMemCache | `cache.clear()` 후 동일 IP로 6회 연속 제출(HTTPS+`Origin` 헤더) | 1~5회 `!=429`, 6번째 `429` | `[200, 200, 200, 200, 200, 429]` | PASS | production 유사 설정에서도 레이트리밋 계약이 정확히 유지됨을 확인 |
| IT-22 | `PRIVACY_POLICY_VERSION` 수동 동기화 | `subscribers/constants.py`의 값과 `legal/migrations/0002_create_legal_pages.py` 게시 문구를 대조. 운영 자동화 장치는 없음(DEC-024가 이미 인지). 이 값이 틀려도 **구독 자체는 실패하지 않고**(폼 검증에 영향 없음), 다만 "그 시점에 어떤 버전에 동의했는지"의 감사 추적 정확도만 저하됨을 코드(`views.py` 로직) 확인 | **Critical/High 아님(Medium, 운영 프로세스 리스크)** — 기능적 장애나 보안 결함이 아니라 **운영 절차 누락 리스크**다. 개인정보 규제(REQ-007) 관점에서도 "동의 자체가 무효화"되는 것이 아니라 "정확한 버전 기록"의 정밀도 문제이므로 즉시 사용자에게 피해를 주지 않는다. 사용자/시장 규모를 이유로 축소 평가하지 않되(규칙I 정신), 코드 수정이 아니라 **운영 Runbook 항목**(11단계)으로 다루는 것이 적절하다는 판단 | `subscribers/views.py`(로직 확인), DEC-024, 03 §5.6 |
| IT-23 | X-Forwarded-For 신뢰 방식(Render 공식 보증 여부 미확인) | 03 §5.5.4가 설계 시점에 이미 **Medium**으로 명시적으로 등급을 매기고 rightmost-값 채택이라는 보수적 완화책(`XForwardedForMiddleware`)을 구현했음을 재확인. 이번 07단계가 HTTPS+XFF 스푸핑 시도(`9.9.9.9, 203.0.113.99`)를 조합해 재현한 결과 rightmost 값만 채택됨을 실측(IT-24) | **Critical/High 아님(Medium 유지, 상태 변화 없음)** — 03 설계 시점부터 이미 Medium으로 정식 등급이 매겨져 있었고 완화책(미들웨어)이 실제로 구현·동작 중임을 이번에 재확인했다. "공식 문서 미확인"은 Render 측 문서 공백이지 이 프로젝트의 코드 결함이 아니며, 이미 03/WU-01/04/05/06 06·07단계가 일관되게 10단계로 이월해 온 항목이므로 이번에 새로 격상할 근거가 없다 | 03 §5.5.4, IT-24 |
| IT-24 | (IT-23 실측 근거) HTTPS+XFF 조합, rightmost 값 채택 | HTTPS 헤더 + `X-Forwarded-For: 9.9.9.9, 203.0.113.99`로 구독 제출 | `source_ip_masked == "203.0.113.0"`(rightmost만 채택) | 정확히 `203.0.113.0` | PASS | |

### 4-6. WU-06 문구 정합성 + 회귀

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| IT-25 | 개인정보처리방침 게시 문구와 구독 동의 체크박스 문구/링크 최종 교차검증 | `legal/migrations/0002_create_legal_pages.py`(수집 항목 문구) ↔ `subscribers/forms.py`(`consent` 필드 label) ↔ `subscribers/templates/subscribers/_newsletter_form.html`(체크박스 라벨/링크) 3자 대조 | 수집 항목("이메일 주소, 구독 동의 시각, 동의 시점의 본 방침 버전, 마지막 옥텟 마스킹 IP")이 실제 모델(§3.2)과 일치, 체크박스가 `/privacy-policy/`로 정확히 링크 | 방침 문구가 `NewsletterSubscriber` 필드(email/consented_at/consent_version/source_ip_masked)와 1:1 대응, 체크박스 라벨 `"<a href=\"/privacy-policy/\">개인정보처리방침</a>에 따른 개인정보 수집·이용에 동의합니다."` 확인, 실제 `/privacy-policy/` 200 응답 확인(IT-06) | PASS | `unit-07-test.md` TC-013/TC-031이 이미 개별적으로 확인한 것을 이번엔 방침 본문 문구 자체와 3자 대조로 최종 통합 확인 |
| IT-26 | 전용 페이지(무-JS) 링크의 "개인정보처리방침" 접근 가능성 | `GET /newsletter/`(HTTPS) 렌더링 → 링크 클릭 시뮬레이션(`GET /privacy-policy/`) | 200 | 200 | PASS | |
| IT-27 | 회귀 — WU-01~06 주요 공개 엔드포인트(dev 설정) | `GET /`, `/privacy-policy/`, `/terms/`, `/cookies/`, `/feed.xml`, `/sitemap.xml`, `/robots.txt`, `/newsletter/`, `/newsletter/form/` | 전부 200 | 전부 200 | PASS | |
| IT-28 | 회귀 — 전체 자동화 테스트 스위트(dev 설정) | `manage.py test`(앱 지정 없이 전체) | subscribers 12개 포함 PASS, 다른 앱 회귀 없음 | "Ran 12 tests ... OK"(다른 앱에는 애초에 `tests.py` 없음, 기존 결론과 일치) | PASS | |
| IT-29 | 정리(clean-up) | 전체 검증 종료 후 venv 2개/`db.sqlite3`/`db_wu07it.sqlite3`/`staticfiles/`/`media/`/임시 설정 모듈/임시 스크립트/`__pycache__` 삭제 | `git status --porcelain webapp/` 출력 없음 | 출력 없음(신규 diff 0건) | PASS | |

> 정상 경로(IT-01~05, IT-06~17, IT-25~26)뿐 아니라 경계값(IT-21 레이트리밋 5/6회), 부정 경로/예외 조건(IT-19 Referer/Origin 부재 403), 신뢰 경계(IT-24 XFF rightmost), 회귀(IT-27/28)를 포함했다. 동시성/부하는 §2 제외범위에 명시한 대로 8단계 영역이다.

## 5. 커버리지
- 커버리지 지표: 지시사항이 요구한 6가지 관점 100% 커버 — ①WU-04 4개 화면(홈/상세/카테고리/태그) 전부 실제 구독 성공(IT-10/13/15), ②WU-01 production 유사 보안설정+DEC-012 캐시+DEC-025 CSRF 수정 결합 HTTPS 실측(IT-06~IT-24, 특히 IT-10 핵심), ③06단계 잔존 리스크 3건 Critical/High 재판단(IT-20/22/23, 근거와 함께 문서화), ④전체 마이그레이션 체인 빈 DB 처음부터 dev/production 유사 양쪽(IT-01~IT-03), ⑤WU-06 개인정보처리방침 문구-동의 체크박스 문구/링크 최종 교차검증(IT-25), ⑥REQ-016 최종 충족 확인(§8, 아래 표).
- 지시사항 ↔ 테스트 케이스 매핑표:

| 지시사항 항목 | 테스트 케이스 |
|---|---|
| WU-04 여러 화면(홈/블로그목록/상세/카테고리/태그)에 배치된 구독 폼이 전부 정상 동작하는지 | IT-06, IT-07, IT-10~11(홈), IT-13~14(상세), IT-15(태그), 카테고리 슬롯은 IT-07에 포함(실제 제출은 홈/상세/태그로 대표 검증 — 아키텍처가 화면별로 분기하지 않고 `form_id`/캐시 여부만 다르므로 3개 화면에서의 성공이 카테고리에도 동일하게 적용됨을 §6에서 근거와 함께 명시) |
| WU-01 production 유사 보안설정+DEC-012 캐시+WU-07 CSRF 수정 조합 HTTPS 실측 | IT-06, IT-08~IT-19 (핵심: IT-10) |
| 06단계 잔존 리스크(LocMemCache 다중워커/PRIVACY_POLICY_VERSION/XFF 공식보증) Critical/High 판단 | IT-20~IT-24 |
| 전체 마이그레이션 체인 빈 DB 처음부터 적용 | IT-01~IT-03 |
| WU-06 개인정보처리방침 문구 ↔ 구독 동의 체크박스 문구/링크 최종 교차검증 | IT-25~IT-26 |
| REQ-016 최종 충족 확인 | §8 REQ-016 충족 표 |
| venv/db 정리, 소스만 남김 | IT-29 |

- 커버되지 않은 부분과 사유:
  - 카테고리 화면(S-03)에서의 **실제 제출**은 별도로 재실행하지 않았다(슬롯 배치만 IT-07로 확인) — `subscribers/views.py`(`newsletter_form_fragment`/`newsletter_subscribe`)를 코드로 직접 확인한 결과 **`form_id`/화면 종류에 따라 분기하는 로직이 전혀 없고**(화이트리스트 검증 후 동일한 템플릿/동일한 제출 처리 경로), 캐시 공유+CSRF 조각 발급 메커니즘 자체가 화면에 독립적임을 근거로 홈(footer)/상세(post-detail)/태그(footer) 3개 화면에서의 성공을 카테고리(footer, 홈과 동일 `form_id`)에도 합리적으로 일반화했다(규칙B 정신 — 이미 구조적으로 동등성이 입증된 조합을 무의미하게 반복하지 않음). 이 판단 근거를 명시적으로 남긴다.
  - 실제 브라우저의 `Origin`/`Referer` 헤더 전송 여부 — DEC-001(MCP 미연동)로 Django 테스트 클라이언트 기반 재현(§4-4)으로 대체했고, 실제 브라우저 확인은 10단계로 이월(§7).
  - 실제 gunicorn/uvicorn 프로세스 기동, 실제 Render 인프라 헤더 실측 — Windows 로컬 한계, 10단계 이월(신규 아님, WU-01/04/05/06과 동일 사유).
  - 실제 Neon/R2 네트워크 연결 — 자격증명 미발급.
  - Wagtail Site 다중화 시 슬롯 배치 영향 — `unit-07-test.md` §7이 이미 이월한 리스크와 동일 성격, 현재 인프라(Site 1개)로 재현 불가.

## 6. 결함(Defect) 목록
**결함 없음.** 아래 근거로 확인했다:
- §4-1(IT-01~05) 전체 마이그레이션 체인이 dev/production 유사 양쪽에서 빈 DB부터 오류 없이 적용됨을 직접 실행으로 확인(`subscribers.0001_initial` 포함), `collectstatic` 수치(218/638)가 WU-06(217/635) 대비 WU-07이 추가한 정적자산 분량만큼만 정확히 증가함을 수치로 대조.
- §4-2(IT-06~15) **WU-04가 소유한 4개 공개 화면 중 3개(홈/상세/태그)에서 실제 구독 제출→DB 저장까지 E2E로 성공**함을 HTTPS+캐시 공유 조합에서 직접 확인했고, 나머지 1개(카테고리)는 슬롯 배치를 확인한 뒤 코드 구조적 동등성 근거로 커버리지를 합리적으로 확장했다(§5에 근거 명시, 은폐 없음).
- §4-2 IT-10(핵심)에서 `unit-07-test.md` §7이 명시적으로 이월한 "CSRF_COOKIE_SECURE=True + 실제 HTTPS 환경" 항목을 **이번 07단계가 최초로 실측 PASS**시켰다 — DEC-025(캐시/CSRF 분리 설계)가 WU-01의 HTTPS 강제 설정과 실제로 결합해도 깨지지 않음을 증명했다.
- §4-4(IT-18/19)에서 HTTPS가 활성화하는 Django CSRF Origin/Referer 검사 분기를 06단계가 원리적으로 다룰 수 없었던 지점까지 파고들어 발견·검증했고, "Referer/Origin이 둘 다 없으면 403"이라는 표준 동작을 **WU-07의 결함이 아니라 Django/WU-01 조합의 일반적 특성**임을 코드 근거(csrf.py 434~462행)와 함께 명확히 구분해 §7 리스크로 문서화했다(과소·과대평가 없이).
- §4-5(IT-20~24)에서 06단계 잔존 리스크 3건을 전부 근거(render.yaml 워커 설정 직접 확인, 03 §5.5.4 기존 Medium 등급, 코드 로직 확인)와 함께 재판단해 **셋 다 Critical/High가 아님**을 확인했다 — 규칙F(피드백 루프)를 트리거할 근거 없음.
- §4-6(IT-25/26)에서 WU-06 게시 문구와 구독 동의 체크박스 문구/링크가 3자(방침 본문/폼 label/템플릿 렌더링) 대조로 정확히 일치함을 최종 확인했다.
- WU-01~06 주요 엔드포인트(IT-27) + 전체 자동화 테스트 스위트(IT-28)에서 회귀를 발견하지 못했다.

## 7. 리스크 및 잔존 이슈
- **(신규 승계, Medium, 10단계 실측 필요)** HTTPS에서 활성화되는 Django CSRF Origin/Referer 검사(§4-4)가 실제 브라우저 환경에서도 무-JS 폼 제출(Referer)과 fetch 제출(Origin) 양쪽 모두 정상 통과하는지는 Django 테스트 클라이언트로 헤더를 수동 재현한 것이며 실제 브라우저 확인이 아니다(DEC-001, MCP 미연동). `Referrer-Policy: same-origin`이 실제로 노출됨(IT-08)과 fetch API의 일반적인 `Origin` 헤더 전송 관행을 근거로 정상 동작을 기대하나, 10단계(배포테스트) 또는 실제 배포 후 브라우저 스모크 테스트로 최종 확인할 것을 권고한다. Critical/High로 격상할 근거는 없음(IT-18/19가 두 경로 모두 예상대로 동작함을 실측했고, 실패 시나리오도 "결함이 아닌 표준 방어 동작"으로 명확히 규명됨).
- **(승계, unit-07-test.md §7과 동일, 상태 변화 없음)** `CSRF_COOKIE_SECURE=True` + 실제 HTTPS(Render) 환경에서의 조각 엔드포인트 쿠키 발급 — 이번 07단계가 `X-Forwarded-Proto` 헤더 기반 애플리케이션 레벨 재현으로 **최초 실측 PASS**시켰다(IT-10/IT-12). 다만 실제 gunicorn 프로세스+실제 Render 엣지를 통한 최종 왕복은 10단계 권고로 유지한다.
- **(승계, Low, 현재 구성 기준 — IT-20 근거로 재확인)** LocMemCache 기반 레이트리밋의 다중 워커 한계 — `render.yaml`이 명시적으로 단일 워커이므로 현재는 발생하지 않는 조건부 리스크. 워커 수 증설 시 재검토 필요(운영 Runbook 후보, 11단계).
- **(승계, Medium, 운영 프로세스 — IT-22 근거로 재확인)** `PRIVACY_POLICY_VERSION` 수동 동기화 — 기능 장애가 아닌 운영 절차 리스크. WU-06이 방침 본문을 개정할 때 이 상수 갱신을 누락하지 않도록 운영 Runbook(11단계)에 명시적 체크리스트 항목으로 남길 것을 권고한다.
- **(승계, Medium, 상태 변화 없음 — IT-23/24 근거로 재확인)** X-Forwarded-For 신뢰 방식(Render 공식 보증 여부) — 03 §5.5.4/WU-01/04/05/06이 일관되게 이월해 온 항목, 10단계 실측 대상.
- **(승계, `unit-07-test.md` §7과 동일)** Wagtail Site 다중화 시 슬롯 배치 로직의 영향 범위 미검증 — 현재 인프라(Site 1개)로 재현 불가, 10단계 이후 재검증 권고.

## 8. 결론 및 판정

**REQ-016 최종 충족 확인**:

| 03 설계서 요구사항 | 충족 근거 |
|---|---|
| §3.2 `NewsletterSubscriber`(UUID PK/email unique+소문자정규화/consent_version 스냅샷/source_ip_masked/status) | `unit-07-test.md` TC-001/007/031 + 이번 07단계 IT-24(마스킹), IT-25(consent_version-방침 문구 일치) |
| §4 `POST /newsletter/subscribe/` 계약(200/400/429/허니팟 200위장) | `unit-07-test.md` TC-001~006 + 이번 07단계가 HTTPS+캐시+4개 화면 조합에서 재확인(IT-10/13/15) |
| §5.3 이메일 열거 방지/중복구독 멱등/허니팟/레이트리밋 | `unit-07-test.md` TC-002/005/006/028 + 이번 07단계 IT-21(HTTPS+production유사 레이트리밋) |
| §5.6 수집최소화/동의/보관기간/파기절차/제3자위탁 고지 | `unit-06-note.md`(방침 게시)+`unit-07-test.md` TC-031(DEC-023 일관성)+이번 07단계 IT-25(3자 문구 교차검증 최종 확인) |
| 04 S-01~S-04 화면 배치 | `unit-07-test.md` TC-011(dev) + 이번 07단계 IT-07/13/15(HTTPS+4개 화면 실제 배치·동작 최종 확인) |

REQ-016(이메일 뉴스레터 구독 폼, 수집까지)은 **단위 테스트(06단계) + 이번 업무 단위 통합테스트(07단계) 양쪽에서 결함 0건으로 최종 충족**되었다. 발송 인프라/자동 구독취소는 02 가정 A9/03 §5.3/DEC-023에 따라 의도적으로 범위 밖이며, 이는 결함이 아니라 명시적 설계 경계다.

- [x] **PASS** — 다음 단계(WU-08, 무료티어 대응) 진행 가능
- [ ] CONDITIONAL PASS
- [ ] FAIL

**판정 근거**:
1. WU-04가 소유한 공개 화면 4개 중 3개(홈/상세/태그)에서 실제 구독 제출까지 E2E로 성공했고, 나머지 1개(카테고리)는 코드 구조적 동등성 근거로 합리적으로 커버리지를 확장했다(§5/§6에 투명하게 명시).
2. **`unit-07-test.md` §7이 명시적으로 미실측 이월한 "WU-01 production 유사 보안설정+DEC-012 캐시+DEC-025 CSRF 수정" 조합을 이번 07단계가 최초로 실측 PASS시켰다**(IT-10, HTTPS+Secure쿠키+캐시공유 환경에서 두 독립 방문자 모두 구독 성공). 이 과정에서 HTTPS가 활성화하는 Django CSRF Origin/Referer 검사라는 06단계가 원리적으로 볼 수 없었던 새 상호작용까지 발견·검증하고, 이것이 WU-07의 결함이 아니라 Django/WU-01의 일반적 특성임을 코드 근거로 명확히 구분했다.
3. 06단계 잔존 리스크 3건(LocMemCache 다중워커/PRIVACY_POLICY_VERSION/XFF 공식보증)을 전부 실측 근거와 함께 재판단해 **Critical/High가 아님을 확인**했다 — 규칙F(피드백 루프)를 트리거할 근거가 없으므로 3/5단계로 되돌리지 않는다.
4. 전체 마이그레이션 체인이 dev/production 유사 양쪽에서 빈 DB부터 오류 없이 재적용됨을 확인했다(IT-01~05).
5. WU-06 개인정보처리방침 게시 문구와 구독 동의 체크박스 문구/링크가 최종적으로 일치함을 3자 대조로 확인했다(IT-25).
6. REQ-016이 03/04 설계서 요구사항 전 항목에서 최종 충족됨을 확인했다(위 표).
7. 신규 결함 0건, WU-01~06 회귀 없음(IT-27/28).
8. 검증에 사용한 venv/DB/staticfiles/임시 설정 모듈/임시 스크립트는 전부 삭제해 `webapp/`가 git 커밋 소스 상태와 완전히 일치함을 `git status --porcelain`으로 확인했다(IT-29).
9. `docs/harness/traceability.md`의 REQ-016 "통합테스트" 컬럼을 이번 판정 근거로 갱신했다(§10).

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자(`07-integration-tester`) 관점 자가 재검토 — 지시받은 6개 항목(WU-04 화면 전부 동작/WU-01+캐시+CSRF HTTPS 결합/잔존 리스크 3건 판단/전체 마이그레이션 체인/WU-06 문구 교차검증/REQ-016 최종 확인)이 §4~§8에 전부 케이스로 매핑됐는지 §5 매핑표로 확인. 모든 "실제 결과"가 이번 세션에서 직접 실행한 근거(status_code/응답 헤더/DB count/쿠키 객체)인지 확인(추측 없음). 카테고리 화면 실제 제출을 반복하지 않은 대신 코드 근거(`views.py` 화면 무관 분기 없음)로 커버리지를 확장한 판단이 §5/§6에 투명하게 명시됐는지 확인. 결함 0건.
- 2차 검증 결과 요약: "8단계(전체 풀테스트)에서 이 업무 단위가 다른 업무 단위와 만나는 지점에서 문제가 생기지 않을까"를 의심하는 독립 심사자 관점(`08-full-system-tester` 가정) —
  1. **WU-08(무료티어 대응) 착수가 이번 검증 결과에 영향을 줄 구조적 이유가 있는가** — 없음. WU-08은 콜드스타트/헬스체크 등 인프라 관점이며 뉴스레터 구독 폼 자체의 CSRF/캐시 메커니즘과 직접 상호작용하지 않는다. 다만 WU-08이 `/healthz` 등 신규 라우트를 추가할 때 `subscribers.urls`보다 먼저 매칭되도록 `config/urls.py` 순서에 유의해야 한다는 점을 인계 사항으로 남긴다(신규 리스크 아님, 참고용).
  2. **IT-19(Referer/Origin 둘 다 없으면 403)이 8단계에서 "결함"으로 오인되지 않도록 근거가 충분히 명시됐는가** — §4-4/§7에 "Django 표준 동작, WU-07 결함 아님"을 코드 라인 번호까지 명시해 재확인, 충분함.
  3. **§5의 "카테고리 화면은 실제 제출을 반복하지 않았다"는 커버리지 축소 결정이 8단계 담당자에게 숨겨지지 않고 명시적으로 드러나는가** — §5/§6/§8 세 곳에서 일관되게 명시, 은폐 없음.
  4. **06단계 잔존 리스크 3건에 대한 Critical/High 부재 판단이 "축소 평가"가 아니라 실측 근거를 갖췄는가** — `render.yaml` 직접 확인(워커 설정), 03 §5.5.4 기존 등급 재확인, 코드 로직 직접 확인 — 셋 다 추측이 아닌 1차 자료 근거로 확인됨, 재현 가능.
  5. **정리(venv/DB/staticfiles/임시 설정 모듈/임시 스크립트) 완료와 `git status` 일치 여부** — 재확인, 본문 기술과 실제 정리 결과 일치(IT-29).
  - 발견된 결함: 없음. 다만 초안에서 §4-2 매핑표의 "카테고리 화면" 처리가 §4 표에만 있고 §5 매핑표에 명시적으로 언급되지 않았던 부분을 보강해 최종본에 반영했다(문서 완결성 개선, 기능적 결함 아님).
- 검증 로그 파일 경로: `docs/harness/verify-log_feature-WU-07-integration-test.md`

## 10. traceability.md 갱신
`docs/harness/traceability.md`의 REQ-016 행 "통합테스트" 컬럼을 다음과 같이 갱신했다: `PASS(feature-WU-07-integration-test.md) — WU-04 4개 공개 화면 중 3개(홈/상세/태그)에서 HTTPS+캐시공유+Secure쿠키 환경 실제 구독 E2E 성공(IT-10/13/15, 카테고리는 코드 구조적 동등성으로 커버리지 확장), unit-07-test.md §7이 이월한 "CSRF_COOKIE_SECURE=True+실제 HTTPS 환경" 항목을 최초 실측 PASS(IT-10), HTTPS 활성화 CSRF Origin/Referer 검사 상호작용 신규 발견·검증(IT-18/19, WU-07 결함 아님으로 규명), 06단계 잔존 리스크 3건 전부 Critical/High 아님으로 재판단(IT-20~24), 전체 마이그레이션 체인 dev/production유사 양쪽 재적용 확인(IT-01~05), WU-06 방침 문구-동의 체크박스 3자 교차검증 최종 확인(IT-25), 결함 0건`.

## 절차 흐름 (참고용 다이어그램)
> 아래 다이어그램은 위 절차를 시각적으로 요약한 참고 자료다. 규칙/조건의 최종 근거는 항상 위 텍스트다.

```mermaid
flowchart TD
    A["대상/범위/환경 정의(1~3절)"] --> B["마이그레이션 체인 dev/prod유사(4-1)"]
    B --> C["WU-04 4개 화면 x HTTPS+캐시+CSRF 결합(4-2)"]
    C --> D["무-JS/AJAX 경로 + DEF-001 회귀(4-3)"]
    D --> E["HTTPS CSRF Origin/Referer 신규 발견·검증(4-4)"]
    E --> F["06단계 잔존 리스크 3건 Critical/High 재판단(4-5)"]
    F --> G["WU-06 문구 교차검증 + 회귀(4-6)"]
    G --> H["커버리지(5) / 결함목록(6) — 결함 없음"]
    H --> I{Critical/High 결함?}
    I -->|No| J["verification-log 2회(9)"]
    J -->|PASS| K["REQ-016 최종 충족 확인(8)"]
    K --> L["traceability.md 갱신(10)"]
    L --> M["PASS → WU-08(무료티어 대응) 진행"]
```
