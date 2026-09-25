# 테스트 결과서 (Test Result Report) — WU-06 (법적 페이지 + 쿠키배너)

> **주의**: 05단계(`05-unit-developer`)가 `unit-06-note.md` §3에서 보고한 로컬 검증 결과(venv `.venv_wu06` 등은 이미 삭제됨)는
> 이번 06단계 검증의 근거로 **인용하지 않았다**. ORCHESTRATOR.md 규칙 C 및 이번 작업 지시("05단계가 보고한 검증을 신뢰하지 말고
> §8의 19개 인수조건을 처음부터 독립 재현")에 따라, 아래 모든 "실제 결과"는 이번 세션에서 새로 만든 venv(`webapp/.venv_test06`,
> 검증 후 삭제)와 새로 작성한 스크립트로 처음부터 재현한 것이다.

## 1. 개요
- 테스트 대상: WU-06(업무 단위) — 법적 페이지(개인정보처리방침/이용약관/쿠키 사용 고지, REQ-007/008/009) + 콘텐츠 정책(REQ-015) + 전역 CookieConsentBanner(REQ-008). 신규 `webapp/legal/`(`apps.py`/`constants.py`/`models.py`/`migrations/0001_initial.py`/`migrations/0002_create_legal_pages.py`/`templates/legal/legal_page.html`), 수정된 `webapp/config/settings/base.py`(INSTALLED_APPS)·`webapp/config/templates/base.html`(배너 마크업+인라인 스크립트)·`webapp/config/static/css/components.css`(`.legal-page*`/`.cookie-consent*`), 신규 `webapp/config/static/js/cookie-consent.js`
- 테스트 유형: 단위(Unit)
- 테스트 목적: `docs/harness/units/unit-06-note.md` §8의 인수조건(AC) 19개를 독립적으로 재현해 PASS/FAIL을 판정하고, 오케스트레이터가 명시적으로 지시한 5가지 핵심 확인 사항 — ① `/privacy-policy/`·`/terms/`·`/cookies/` 실제 200 및 TOC 앵커 생성 정확성, ② `legal` 앱 0001/0002 마이그레이션이 빈 DB에서 처음부터 성공하고 locale 관련 결함이 재발하지 않는지, ③ 쿠키배너의 최초노출/동의 후 재방문 미노출(localStorage)/non-modal/prefers-reduced-motion 존중/접근성 마크업, ④ `/terms/` 내 REQ-015 면책 문구 실제 포함 여부, ⑤ production 유사(HTTPS) 환경 회귀 없음 + sitemap/canonical 통합 — 을 실측으로 검증한다. 아울러 05단계가 발견한 `core/seo.py`의 `:80` 포트 아티팩트를 독립 재현하고 Critical/High 여부를 판단한다.
- 관련 산출물: `docs/harness/units/unit-06-note.md`(§8 AC1~19, §7 인계 사항), `docs/harness/03-system-design.md`(v1.2 §1.2/§3.2/§4/§5.5/§5.6), `docs/harness/04-ux-design.md`(S-05~S-07, 전역 컴포넌트, §5 접근성), `docs/harness/decisions.md`(DEC-017/019~022), `docs/harness/traceability.md`(REQ-007/008/009/015), `docs/harness/units/unit-05-test.md`(`:80` 아티팩트의 선행 규명 — TC-019(B) 참고)
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- 범위 (In-Scope): `unit-06-note.md` §8 AC1~19 전부 독립 재현. 추가로 (a) 05단계가 §3-3에서 관찰한 `core/seo.py`/`core/context_processors.py`의 `:80` 포트 아티팩트를 legal 페이지에서 독립 재현하고 WU-06 자체 결함인지 판정, (b) WU-01~05와의 회귀 여부, (c) 정적 분석/린트 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)의 실제 통과 여부 독립 재확인, (d) 인수조건에 없지만 명백히 위험한 경계 케이스(쿼리스트링 인젝션 시도, 이중 슬래시 경로, localStorage 접근 자체가 예외를 던지는 환경, `<script>` 이스케이프)를 규칙에 따라 추가 검증.
- 제외 범위 및 사유:
  - **실제 브라우저(Chrome/Playwright 등) 기반 E2E 검증** — DEC-001에 따라 이 프로젝트는 MCP(브라우저 자동화 포함)를 연동하지 않기로 이미 결정되어 있고, 이번 세션에도 브라우저 자동화 MCP가 연결되어 있지 않다. 작업 지시 자체가 "헤드리스로 검증하기 어려우면 서버렌더 마크업+localStorage 로직 존재를 코드로 확인"하라고 대체 방법을 명시했으므로, AC11(첫 방문 노출/동의 후 재방문 미노출/localStorage 삭제 후 재노출)과 AC12(키보드 포커스/ESC/포커스 트랩 없음)는 **jsdom(Node.js, 실제 `cookie-consent.js` 파일을 그대로 로드해 실행하는 준-브라우저 DOM 환경)으로 실제 JS 실행 결과를 검증**했다 — 단순 코드 읽기보다 강한 근거이지만, 실제 브라우저의 레이아웃/렌더링 엔진은 아니므로 시각적 애니메이션 재생 자체는 검증 대상에서 제외했다(§4 TC-011/TC-012 비고에 방법론 명시).
  - **AC13(`prefers-reduced-motion` 실제 애니메이션 비활성화)의 시각적 렌더링 확인** — jsdom은 CSS 레이아웃/애니메이션 엔진을 갖고 있지 않아 실제 애니메이션 재생 여부를 실행으로 확인할 수 없다. 대신 `components.css` 소스에서 `@keyframes`가 `@media (prefers-reduced-motion: no-preference)` 블록 안에만 존재하는지(즉 `reduce` 설정 시 그 규칙셋 자체가 적용되지 않는지)를 코드로 확인했다 — CSS 명세상 이 패턴이면 `reduce` 환경에서 애니메이션이 적용되지 않는 것이 브라우저 표준 동작이므로, 이 범위 내에서는 정적 검증으로 충분하다고 판단했다.
  - **법률 문구의 실제 법적 정확성/충분성 검토** — `unit-06-note.md` §7-1이 이미 명시한 대로 이 하네스의 범위가 아니다. 이번 06단계는 "요구된 문구가 실제로 화면에 정확한 문자열로 렌더링되는가"만 검증한다.
  - **Cloudflare R2/실제 도메인 기반 검증** — WU-06은 R2/도메인에 의존하지 않으므로 해당 없음(legal 페이지는 정적 콘텐츠).

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro, Python 3.13.9, Node.js(버전 확인됨, `node --check`/jsdom 실행용), Git Bash. `webapp/requirements.txt`(Django 5.2.17, wagtail 7.4.3 등, WU-01~05와 동일 버전 — 신규 패키지 없음, `pip install` 결과 재확인)를 새 venv(`webapp/.venv_test06`, 검증 후 완전 삭제)에 clean install.
- 테스트 데이터: `legal.0002_create_legal_pages` 데이터 마이그레이션이 생성하는 개인정보처리방침/이용약관/쿠키 사용 고지 3개 `LegalPage` 인스턴스(별도 픽스처 불필요 — WU-06 산출물 자체가 실데이터를 게시).
- 전제 조건:
  - 매 스크립트 실행마다 새 `django.test.Client()` 프로세스로 시작하므로 뷰 캐시(10분 TTL) 잔존값이 섞일 위험이 없다(각 시나리오가 한 프로세스 안에서 최초 요청 시점에 캐시를 채우고 그대로 사용 — 데이터가 실행 중 변경되지 않으므로 캐시로 인한 오탐 위험 없음).
  - AC18(production 유사 환경)을 위해 `webapp/config/settings/it_test_prodlike.py`(검증 후 삭제)를 임시로 만들어 `production.py`를 상속하고 `DATABASES`만 SQLite로 재정의했다. `SECRET_KEY`/`DATABASE_URL`/`DJANGO_ALLOWED_HOSTS=example.com`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL`(전부 더미)을 환경변수로 주입.
  - AC11/AC12(쿠키배너 JS 동작)을 위해 스크래치패드에 임시 Node 프로젝트(`jsdom` 1개 패키지만 설치, 검증 후 `node_modules`째 삭제)를 만들어 `webapp/config/static/js/cookie-consent.js`(실제 파일)를 그대로 로드해 실행했다.
  - 검증에 사용한 모든 산출물(venv, `db.sqlite3`, `db_prodlike.sqlite3`, `staticfiles/`, `media/`(생성 안 됨), `config/settings/it_test_prodlike.py`, `__pycache__`, 스크래치패드 임시 스크립트/Node 프로젝트)은 검증 완료 후 삭제했다(AC19, §6 근거 참고).

## 4. 테스트 케이스 및 결과

| ID | 시나리오 (대응 AC) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | venv 설치 (AC1) | `webapp/requirements.txt` | 새 venv 생성 후 `pip install -r requirements.txt` | 오류 없이 종료, 신규 패키지 없음 | `pip install` 종료 코드 0, 오류 로그 없음. `pip freeze`로 Django==5.2.17/wagtail==7.4.3 등 WU-01~05와 동일 버전 재확인 | PASS | |
| TC-002 | 빈 DB 마이그레이션, locale 결함 재발 여부 (AC2, 오케 지시 ②) | `DJANGO_SETTINGS_MODULE=config.settings.dev`, DB 파일 없음(신규 생성) | `python manage.py migrate` | 오류 없이 전체 적용, 특히 `legal.0002_create_legal_pages`가 `IntegrityError` 없이 성공 | 전체 마이그레이션 체인(`legal.0001_initial`→`legal.0002_create_legal_pages` 포함) 오류 없이 전부 OK, exit 0. `IntegrityError: NOT NULL constraint failed: wagtailcore_page.locale_id` 미발생(unit-06-note.md §3-1이 보고한 최초 결함이 재발하지 않음을 확인) | PASS | 빈 DB에서 "처음부터" 실행(기존 DB 재사용 아님) |
| TC-003 | 시스템 체크 (AC3) | TC-002 이후 | `python manage.py check` | "System check identified no issues" | 정확히 동일 문구 출력(0 silenced) | PASS | |
| TC-004 | 마이그레이션 드리프트 없음 (AC4) | TC-002 이후 | `python manage.py makemigrations --check --dry-run` | "No changes detected" | 정확히 동일 문구 출력 | PASS | |
| TC-005 | `/privacy-policy/` 실HTTP 200 + 내용 (AC5, 오케 지시 ①) | TC-002 | `GET /privacy-policy/` | 200, 본문에 "개인정보처리방침"/"최종 업데이트"/"Render"/"Neon"/"Cloudflare"/"GitHub"/"목차"/TOC 앵커 링크(`<a href="#...">`) 전부 포함 | 상태 200. 7개 문자열 토큰 전부 포함 확인(개별 assert). `<a href="#`로 시작하는 TOC 앵커 링크 존재 | PASS | |
| TC-006 | `/terms/` 200 + REQ-015 면책 문구 정확 문자열 (AC6, 오케 지시 ④) | TC-002 | `GET /terms/` | 200, "이용약관" 포함, "**금융/투자, 의료/건강, 법률, 보험**" 문구가 정확한 문자열로 포함 | 상태 200. "이용약관" 포함. "금융/투자, 의료/건강, 법률, 보험" 문자열이 정확히(오탈자/띄어쓰기 변형 없이) 포함됨을 문자열 `in` 비교로 확인 | PASS | REQ-015 면책 문구가 실사용자 응답 HTML에 실제로 렌더링됨을 실측 확인 |
| TC-007 | `/cookies/` 200 + 내용 (AC7) | TC-002 | `GET /cookies/` | 200, "쿠키 사용 고지"/"sessionid"/"csrftoken" 포함 | 상태 200, 3개 토큰 전부 포함 | PASS | |
| TC-008 | 홈 배너 id + 교차 화면 확인 (AC8) | TC-002 | `GET /`, `GET /privacy-policy/` | 두 화면 모두 `id="cookie-consent"`/`id="cookie-consent-accept"` 포함(배너가 전역임을 교차 확인) | `/`(홈) 200, 두 id 모두 포함. `/privacy-policy/`(TC-005 응답)에도 `id="cookie-consent"` 포함 확인 | PASS | 04-ux-design.md §2 "모든 화면 공통" 전역 컴포넌트 요건 충족 |
| TC-009 | Footer 링크 + 실제 resolve (AC9) | TC-002 | `GET /`에서 `href="/privacy-policy/"`/`href="/terms/"`/`href="/cookies/"` 존재 확인 후 3개 URL 각각 실제 요청 | 전부 존재 + 전부 200(WU-04가 남긴 "일시적 404" 해소) | 3개 href 전부 홈 응답에 존재. 3개 URL 각각 실제 요청 시 전부 200 | PASS | |
| TC-010 | TOC h2 앵커 개수/한글 슬러그 (AC10) | TC-005 | `/privacy-policy/` 응답에서 `<h2 id="...">` 정규식 추출 | 8개 이상, 그중 1개 이상 한글 슬러그 | `<h2 id="...">` 정확히 8개. UTF-8 파일로 직접 기록해 확인한 결과 8개 전부 한글 슬러그(`수집하는-개인정보-항목`, `쿠키cookie의-사용` 등)로 정확히 슬러그화됨(`allow_unicode=True` 동작 확인). 터미널 직접 출력은 콘솔 코드페이지 문제로 깨져 보이는 것과 실제 데이터 정상성을 분리해 재확인(unit-06-note.md와 동일한 검증 습관) | PASS | |
| TC-011 | 쿠키배너 최초노출/동의 후 저장/재방문 미노출/localStorage 삭제 후 재노출 (AC11, 오케 지시 ③) | jsdom(Node) 환경에 `base.html`의 실제 배너 마크업+인라인 스크립트(원문 그대로 복사)와 실제 `cookie-consent.js` 파일을 로드 | (1) localStorage 비어있는 새 DOM에서 배너 `hidden` 확인 (2) "확인" 버튼 클릭 이벤트 디스패치 후 `hidden`/`localStorage.getItem` 확인 (3) `cookie_consent_ack` 미리 설정된 새 DOM에서 인라인 스크립트만 실행한 시점의 `hidden` 확인(외부 JS 로드 전) (4) `localStorage.clear()` 후 재방문 시뮬레이션 | (1) `hidden=false` (2) 클릭 후 `hidden=true`, `localStorage.getItem("cookie_consent_ack")==="1"` (3) 인라인 스크립트만 실행한 시점에 이미 `hidden=true`(플래시 방지 동작) (4) `hidden=false`(다시 노출) | 전부 예상과 정확히 일치(4개 시나리오 9개 세부 assert 전부 PASS) — 실제 `cookie-consent.js` 파일을 그대로 실행한 결과이며 코드를 읽고 "그럴 것이다"로 추정한 것이 아니다 | PASS | **방법론**: 헤드리스 브라우저 MCP 미연동(§2)이므로 jsdom으로 실제 JS 실행. 최초 시도에서 `window.localStorage`를 plain assignment로 mock하려다 3건 FAIL이 났는데, 원인을 규명한 결과 jsdom의 `localStorage`가 getter-only 프로퍼티라 assignment가 조용히 무시된 **테스트 스크립트 자체의 결함**이었다(실제 jsdom 내장 Web Storage API를 직접 사용하도록 수정 후 재검증 PASS) — §4 하단 "테스트 스크립트 자체 결함" 절 참고 |
| TC-012 | 키보드 접근성: Tab 포커스/ESC 닫기/포커스 트랩 없음 (AC12) | TC-011과 동일 jsdom 환경 | "확인" 버튼에 `tabindex` 속성 없음 확인 → `.focus()`로 포커스 이동 확인 → `Escape` keydown 디스패치 → 배너 밖 버튼으로 `.focus()` 이동 가능 확인 | 버튼이 네이티브 포커스 가능 요소(tabindex 없음), 포커스 이동 성공, ESC로 배너 닫힘, 배너 밖으로 포커스 이동 제한 없음 | 6개 assert 전부 PASS: `acceptBtn.tagName==="BUTTON"`이고 `tabindex` 속성 없음, `banner`에도 `tabindex` 없음(트랩 없음), `.focus()` 후 `document.activeElement===acceptBtn`, ESC keydown 후 `banner.hidden===true`, 배너 밖 버튼으로 포커스 이동 성공 | PASS | |
| TC-013 | `prefers-reduced-motion: reduce` 시 애니메이션 비활성화 (AC13) | `webapp/config/static/css/components.css` | 소스에서 `@keyframes cookie-consent-in`을 참조하는 `animation` 선언이 어떤 미디어 쿼리 블록 안에 있는지 확인 | `.cookie-consent { animation: ... }` 규칙이 `@media (prefers-reduced-motion: no-preference)` 블록 **안에만** 존재(reduce일 때 규칙 자체가 매치되지 않아 애니메이션 미적용) | 정확히 그 구조로 존재함을 확인(`@media (prefers-reduced-motion: no-preference) { .cookie-consent { animation: cookie-consent-in 0.2s ease-out; } }`), 미디어 쿼리 밖에 동일 규칙의 중복/우회 선언 없음 | PASS | 실제 렌더링 애니메이션 재생은 jsdom이 검증 불가(§2 제외 범위) — CSS 표준 동작(미매치 미디어 쿼리는 규칙 미적용)에 근거한 정적 검증 |
| TC-014 | sitemap.xml 3종 포함 (AC14) | TC-002 | `GET /sitemap.xml` | 200, `/privacy-policy/`·`/terms/`·`/cookies/` 전부 포함 | 상태 200, 3개 경로 전부 포함 | PASS | |
| TC-015 | `/terms/` canonical (AC15) | TC-006 | `/terms/` 응답에서 `<link rel="canonical"` 확인 | 존재 | 존재 확인(WU-05 SEO 체계에 legal 페이지가 자동 편입됨 — 별도 코드 없이 컨텍스트 프로세서가 전역 적용) | PASS | |
| TC-016 | Wagtail 어드민 편집 폼 (AC16) | TC-002, 테스트용 슈퍼유저 생성(검증 후 삭제) | 로그인 후 3개 `LegalPage` 각각 `/cms-admin/pages/<pk>/edit/` 요청, HomePage 탐색기 요청 | 3개 전부 200 + `body` 필드 렌더링, 탐색기에 3개 자식 페이지 제목 노출 | 3개 전부 200, 응답에 `id_body`/`name="body"` 포함. 탐색기 응답에 "개인정보처리방침"/"이용약관"/"쿠키 사용 고지" 3개 전부 노출 | PASS | 테스트용 슈퍼유저는 검증 후 즉시 삭제(테스트 데이터 잔존 없음) |
| TC-017 | 회귀 — WU-01~05 기능 (AC17) | TC-002 | `GET /`, `/feed.xml`, `/sitemap.xml`, `/robots.txt`, `/cms-admin/login/`, `/not-a-real-page/` | 전부 이전과 동일 정상 동작(존재하지 않는 경로만 404) | `/` 200, `/feed.xml` 200, `/sitemap.xml` 200, `/robots.txt` 200, `/cms-admin/login/` 200, `/not-a-real-page/` 404 | PASS | |
| TC-018 | production 유사(HTTPS) 환경 회귀 (AC18, 오케 지시 ⑤) | `config/settings/it_test_prodlike.py`(§3), 더미 R2 환경변수 | `check`/`migrate`(빈 DB)/`collectstatic --noinput` 실행 → `HTTP_X_FORWARDED_PROTO: https` 헤더로 3개 legal URL 요청(200 기대) → 헤더 없이 요청(301 1회, 무한루프 아님 기대) | 전부 오류 없이 종료, HTTPS 헤더 있으면 200, 없으면 301 1회만(DEF-001 계열 회귀 없음) | `check` "no issues". `migrate` 빈 DB에서 전부 OK(legal 포함). `collectstatic --noinput` → "217 static files copied ... 635 post-processed"(오류 0건). 3개 legal URL 전부 `X-Forwarded-Proto: https` 헤더로 200. 헤더 없이 요청 시 3개 URL 전부 301 정확히 1회(`Location`이 `https://`로 시작, 루프 아님) | PASS | |
| TC-019 | 검증 산출물 정리 (AC19) | 전체 검증 종료 후 | venv/`db*.sqlite3`/`staticfiles/`/`media/`/임시 설정 모듈/스크래치패드 스크립트·Node 프로젝트/`__pycache__` 삭제 후 `git status --porcelain -- webapp docs/harness` 실행 | webapp/docs/harness diff에 검증 산출물 없음 | `git status --porcelain -- webapp docs/harness`가 검증 시작 전과 동일한 목록만 출력(신규 소스/문서 diff 외 venv/db/staticfiles/media/임시설정/Node 프로젝트/`__pycache__` 0건) | PASS | |
| TC-020 | **[오케스트레이터 명시 지시] `core/seo.py` `:80` 포트 아티팩트 독립 재현·판정** | `it_test_prodlike` 환경(TC-018과 동일) | (A) `HTTP_X_FORWARDED_PROTO: https` + `SERVER_NAME=example.com`만 지정(`Host` 헤더 없음)하고 `/terms/` 요청 후 canonical 확인 (B) 동일 조건에 `HTTP_HOST=example.com`(실제 리버스프록시가 항상 보내는 `Host` 헤더)까지 명시적으로 추가해 재요청 | (A) `:80`이 재현되는지, (B) `Host` 헤더가 있으면 재현되지 않는지(=실제 Render 트래픽 조건에서는 발생하지 않음을 실증) | (A) canonical=`https://example.com:80/terms/`(`:80` 아티팩트 실제로 재현됨 — legal 페이지에도 영향 있음을 확인) (B) canonical=`https://example.com/terms/`(포트 없음, 정상). Django 소스(`HttpRequest._get_raw_host`)를 직접 읽어 `HTTP_HOST`가 META에 있으면 그 값을 그대로 쓰고, 없을 때만 `SERVER_NAME`+`SERVER_PORT` 조합으로 폴백하며 이때만 `is_secure()`(True)와 `SERVER_PORT`(테스트 클라이언트 기본값 "80")가 불일치해 포트가 붙는다는 것을 확인. 실제 HTTP/1.1 요청은 `Host` 헤더가 필수이고, `production.py`(DEC-015 IT-04, unit-05-test.md TC-019(B))가 이미 "Render는 원본 Host 헤더를 그대로 전달한다"를 실측 확인해 두었으므로, (A)는 `Host` 헤더가 없는 비현실적 테스트 조건에서만 발생 | **PASS (WU-06 자체 결함 아님, 판정: Low — Critical/High 아님)** | 근거: unit-05-test.md가 동일 현상을 독립적으로 먼저 규명(테스트 스크립트 결함, 애플리케이션 결함 아님)해 둔 결론과 이번 재현 결과가 정확히 일치. `core/seo.py`/`core/context_processors.py`는 WU-05 소유 코드이므로 본 WU-06은 수정하지 않았다(범위 외 변경 금지). §7에 리스크로 기록 |

### 테스트 스크립트 자체 결함 발견·수정 기록 (규칙 — "테스트 자체가 잘못 설계되어 결함을 놓칠 가능성 항상 의심")
검증 도중 **테스트 스크립트 자체의 결함 1건**을 발견하고 수정 후 재검증했다(애플리케이션 결함 아님, §6에는 포함하지 않음):
1. **TC-011 최초 시도의 jsdom localStorage mock 무효화**: 최초 스크립트가 `window.localStorage = {getItem, setItem, ...}`로 직접 덮어써 상태를 추적하려 했으나, 클릭 후에도 mock의 내부 저장소가 비어 있고(`{}`) 재방문 시나리오도 배너가 숨겨지지 않는(예상: 숨김) 3건의 FAIL이 발생했다. 원인을 추적한 결과 jsdom이 `http://` origin에서 `window.localStorage`를 **getter-only 프로�터티**로 이미 구현해 두고 있어, plain assignment가 예외 없이 조용히 무시되고(비strict 모드) `cookie-consent.js`는 실제로 jsdom의 진짜 Web Storage에 값을 쓰고 있었으며, 테스트 스크립트만 자신의 mock 변수를 잘못 검사하고 있었다. jsdom의 실제 `localStorage.setItem/getItem/clear`를 직접 사용하도록 테스트 스크립트를 수정하자(mock 제거) 3건 모두 PASS로 전환됐다 — **앱 코드(`cookie-consent.js`)는 처음부터 정상 동작하고 있었다.**
2. **TC-020(A)의 `:80` 포트 아티팩트**: unit-05-test.md TC-019(B)가 이미 규명한 것과 동일한 원인(Django `_get_raw_host()`가 `HTTP_HOST` 부재 시에만 `SERVER_NAME`+`SERVER_PORT` 폴백을 타며, 이때만 포트가 잘못 붙음)이며, `HTTP_HOST` 헤더를 추가한 대조군(TC-020(B))으로 실제 Render 트래픽 조건에서는 재현되지 않음을 확정했다. 이는 애플리케이션 결함이 아니라 "Host 헤더가 없는 비현실적 테스트 조건"에서만 나타나는 현상이다.

> 정상 경로(Happy Path)뿐 아니라 경계값(TOC 8개 h2, 페이지네이션 없음 — 해당 없음), 예외 입력(쿼리스트링에 `<script>` 삽입 시도, 이중 슬래시 경로, localStorage 접근 자체가 예외를 던지는 프라이빗 모드 시뮬레이션 — 아래 TC-EDGE 참고), 권한 경계(비로그인 어드민 로그인 화면 회귀, 테스트 전용 슈퍼유저를 검증 후 즉시 삭제)를 포함했다. 동시성/부하 테스트는 이번 WU 인수조건에 해당 항목이 없고 단위 테스트 통상 범위를 벗어나 제외했다(8단계 전체 풀테스트에서 다룰 사안).

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-EDGE-01 | 쿼리스트링 인젝션 시도 | - | `GET /privacy-policy/?evil=<script>alert(1)</script>` | 500 없이 정상 응답(뷰가 쿼리스트링을 본문에 반영하지 않으므로 200) | 200 | PASS | 규칙에 따른 "명백히 위험한 케이스" 추가 검증(AC 범위 밖) |
| TC-EDGE-02 | 이중 슬래시 경로 | - | `GET //privacy-policy/` | 500이 아닌 정상 처리(200/301/302/404 중 하나) | 200 | PASS | |
| TC-EDGE-03 | localStorage 접근 자체가 예외를 던지는 환경(프라이빗 모드 유사) | jsdom, `window.localStorage` getter가 예외를 던지도록 재정의 | 인라인 스크립트 + `cookie-consent.js` 로드 후 "확인" 버튼 클릭 | 예외가 스크립트 밖으로 전파되지 않고(페이지 크래시 없음), 배너는 계속 닫히는 동작 자체는 수행(저장만 실패) | 예외 전파 없음(threw=false), 클릭 후 `hidden=true`(닫기 동작은 정상 — `try/catch`가 저장 실패만 흡수하고 UI 동작은 정직하게 유지) | PASS | unit-06-note.md §1.5가 명시한 "조용히 죽지 않고 폴백" 설계를 실제 예외 주입으로 실증 |
| TC-EDGE-04 | JSON-LD/스크립트 이스케이프 회귀 없음(legal 페이지에는 JSON-LD 없음 — 대신 리치텍스트 내 앰퍼샌드/따옴표 처리 확인) | TC-005 | `/privacy-policy/` 본문의 "국외 이전" 섹션(원문에 `&`, 따옴표 없는 순수 리스트) 렌더링 확인 | `<ul>`/`<li>` 정상 렌더링, 태그 깨짐 없음 | `<li>Render(웹 호스팅, 미국)</li>` 등 정상 렌더링, `<ul>` 태그 짝 일치 | PASS | 리치텍스트 → `expand_db_html` → 정규식 anchor 삽입 파이프라인의 회귀 없음 확인 |

## 5. 커버리지
- 커버리지 지표: `unit-06-note.md` §8 AC1~19 = 19/19(100%) 전부 최소 1개 이상의 TC로 1:1 매핑되어 독립 재현·PASS. 오케스트레이터가 이번에 추가로 명시한 5가지 핵심 확인 사항(①TC-005/006/007/010, ②TC-002, ③TC-011/012/013, ④TC-006, ⑤TC-018)과 `:80` 포트 아티팩트 판정(TC-020)까지 전부 커버됨.
- 커버되지 않은 부분과 사유: §2 제외 범위에 명시한 3건 — (a) 실제 브라우저 E2E(MCP 미연동, jsdom으로 대체 완료), (b) `prefers-reduced-motion`의 실제 애니메이션 렌더링 재생(jsdom이 CSS 애니메이션 엔진을 갖지 않음, CSS 소스 정적 검증으로 대체), (c) 법률 문구의 실제 법적 정확성(이 하네스의 범위 밖, `unit-06-note.md` §7-1이 이미 명시). Wagtail Site가 여러 개로 늘어나는 시나리오의 이론적 리스크(unit-05-test.md §7이 이미 잔존 리스크로 승계한 것과 동일 범주)는 legal 페이지가 blog와 동일한 `core.seo.absolute_page_url` 헬퍼를 재사용하므로 같은 리스크를 상속하지만, 현재 인프라(Site 1개)로는 이번 단위테스트 범위에서 물리적으로 재현 불가능하다(§7에 기록).

## 6. 결함(Defect) 목록
**결함 없음.** 아래 근거로 확인했다:
- AC1~19 전부(TC-001~019) 독립 재현 PASS, 예상 결과와 실제 결과를 문자열/상태코드/DOM 상태 단위로 직접 비교(단순 "에러 없음"이 아니라 정확한 문자열 토큰, `<h2 id="...">` 개수/슬러그 내용, `localStorage` 실제 값, `document.activeElement` 등 구체적 값을 검증).
- 오케스트레이터가 특별히 우려한 `core/seo.py`의 `:80` 포트 아티팩트(TC-020)를 실제로 재현했으나, 대조군(`Host` 헤더 유무)으로 원인을 Django 표준 동작까지 추적한 결과 **실제 프로덕션 트래픽 조건(Host 헤더 항상 존재)에서는 재현되지 않음**을 확정했다. 이는 WU-05 소유 코드의 특성이며(§1.2 모듈 경계 — `core` 앱은 WU-05 소유), WU-06(legal 앱)은 그 헬퍼를 호출만 할 뿐 로직을 소유하지 않으므로 **WU-06 자체 결함으로 분류하지 않는다**(§7에 리스크로 기록, 판정 근거는 TC-020 참고).
- 검증 중 발견된 이상 징후(TC-011 최초 3건 FAIL)는 원인을 근본까지 추적한 결과 **테스트 스크립트(jsdom mock) 자체의 결함**으로 확정되었고, 수정 후 대조 재실행으로 앱 코드(`cookie-consent.js`)에는 문제가 없음을 재확인했다. "테스트가 실패하면 무조건 테스트 탓으로 돌리지 않는다"는 원칙에 따라, jsdom의 `localStorage` 프로퍼티 디스크립터를 직접 확인(`Object.defineProperty`로 덮어쓰면 성공하지만 plain assignment는 무시됨)한 뒤에만 "테스트 결함"으로 결론 내렸다.
- 게이트1(정적분석/린트, §4 원 산출물)·게이트2(자체 코드 리뷰 체크리스트, §5 원 산출물)를 `unit-06-note.md`에서 그대로 베끼지 않고 독립 재확인했다: 저장소 루트/`webapp/`에 `pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml`이 존재하지 않음을 직접 검색으로 재확인(린트 설정 부재는 사실), 변경된 Python 6개 파일(`legal/apps.py`/`constants.py`/`models.py`/`migrations/0001_initial.py`/`migrations/0002_create_legal_pages.py`/`config/settings/base.py`) 전부 `python -m py_compile` exit 0으로 직접 재실행 확인, `cookie-consent.js`는 `node --check`로 구문 오류 없음 직접 확인(Python 파일만 확인했던 `unit-06-note.md` §4보다 검증 범위를 JS까지 넓힘).

## 7. 리스크 및 잔존 이슈
- **`core/seo.py`/`core/context_processors.py`의 `:80` 포트 표기 — WU-06 소유 아님, Low로 판정**: TC-020에서 독립 재현한 결과, `Host` 헤더가 없는 비현실적 테스트 조건에서만 발생하고 실제 Render 배포 트래픽(항상 `Host` 헤더 포함, DEC-015 IT-04로 이미 실측 확인됨)에서는 재현되지 않는다. `unit-05-test.md`(WU-05 자신의 단위테스트)가 이미 동일한 결론에 도달해 있어 이번 WU-06의 독립 재현 결과와 일치한다. **따라서 Critical/High가 아니라 Low(정보성 리스크)로 판정**하며, WU-06 자체의 결함 목록(§6)에는 포함하지 않는다. 다만 legal 페이지도 동일한 `core.seo.absolute_page_url` 헬퍼를 호출하므로 이 리스크를 그대로 상속한다는 사실은 10단계(배포테스트)가 실제 Render 환경에서 최종 재확인할 항목으로 남긴다(WU-05 재작업이 필요하다고 판단되면 그건 WU-05 담당 범위).
- **Wagtail Site 다중화 시나리오의 이론적 리스크** — unit-05-test.md §7이 이미 기록한 리스크를 legal 페이지도 동일한 헬퍼 재사용으로 상속한다. 현재 인프라(Site 1개)로는 재현 불가능, 10단계 이후 재검증 권고.
- **법적 문구 초안 상태** — `unit-06-note.md` §7-1/§1.2 참고. 실제 공개 전 법률 전문가 검토 필요(페이지 본문에도 명시됨). 이 하네스의 범위 밖이며 06단계는 "문구가 화면에 렌더링되는가"만 검증했다.
- **개인정보처리방침 "문의처"에 구체적 연락 채널 없음** — `SiteSettings` 모델 미구현(unit-06-note.md §7-2 그대로 승계). 담당 WU가 `SiteSettings`를 구현하면 본문 갱신 필요.
- **REQ-016(뉴스레터) 미구현과의 정합성** — 개인정보처리방침이 뉴스레터 수집을 설명하지만 실제 구독 폼(WU-07)은 아직 없음. unit-06-note.md §7-4가 이미 "정책이 기능보다 먼저 존재하는 정상적인 점진적-완성 상태"로 판단해 두었고, 이번 06단계도 이 판단에 이견 없음(모순이 아님).
- **뷰 캐시(10분 TTL)** — 운영자가 어드민에서 법적 페이지를 수정해도 최대 10분간 이전 내용이 보일 수 있음(unit-04-note.md §7-3과 동일 트레이드오프, WU-06도 동일하게 상속). 07단계(통합테스트) 수행 시 캐시를 고려한 테스트 순서 설계 또는 `cache.clear()` 필요.

## 8. 결론 및 판정
- [x] **PASS** — 다음 단계(07 업무단위 통합테스트) 진행 가능
- 판정 근거: AC1~19(19/19) 독립 재현 PASS, 오케스트레이터 지시 5대 핵심 확인 사항 전부 실측 PASS, `:80` 포트 아티팩트는 독립 재현 후 Low로 판정(WU-06 자체 결함 아님, 근거는 TC-020/§6/§7), 결함 0건, 게이트1/2 독립 재확인 통과.
- **규칙F 판단 명시(오케스트레이터 요청 사항)**: `core/seo.py`의 `:80` 아티팩트에 대해 "실제로 존재하는지 독립 재현"하고 "WU-06 페이지에도 영향을 주는지"(영향 있음 — legal 페이지도 동일 헬퍼 사용, TC-020(A)로 실증), "Critical/High급인지" 판단한 결과, **Host 헤더가 존재하는 실제 프로덕션 트래픽 조건에서는 재현되지 않으므로 Critical/High가 아니라 Low로 판정**한다. `core/seo.py`/`core/context_processors.py`는 WU-05 소유 코드이므로 이번 WU-06이 직접 수정하지 않았으며(범위 외 변경 금지 원칙), WU-05로의 재작업 요청(규칙F)이 이번 06단계 판단으로는 **불필요**하다 — WU-05 자신의 단위테스트(`unit-05-test.md`)가 이미 동일한 결론(테스트 조건의 비현실성, 애플리케이션 결함 아님)에 도달해 있다는 사실이 이번 독립 재현으로 다시 한번 교차 확인됐다. 다만 legal 페이지가 이 리스크를 상속한다는 사실은 §7에 정직하게 기록해 10단계가 놓치지 않도록 승계한다.

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자 관점 자가 재검토 — AC1~19와 TC-001~019의 1:1 매핑 완결성, 오케스트레이터 지시 5대 사항 및 `:80` 아티팩트 판정이 실제 TC로 커버되는지, "실제 결과" 컬럼이 전부 이번 세션 실행 근거인지(05단계 보고 인용 없음) 확인. 결함 0건.
- 2차 검증 결과 요약: "07단계에 이 결과서를 그대로 넘겨도 되는가"를 의심하는 독립 심사자 관점 — TC-011의 최초 이상 징후를 테스트 결함으로 성급히 단정하지 않고 jsdom 프로퍼티 디스크립터까지 확인해 대조 재검증했는지, TC-020의 판정("Low, WU-06 결함 아님")이 근거(Host 헤더 유무 대조군 + unit-05-test.md 교차 확인) 없이 축소 평가된 것은 아닌지, AC11/12에 대해 "코드만 읽고 그럴듯하게 PASS 처리"하지 않고 실제 jsdom 실행 결과로 검증했는지, §7 잔존 리스크가 §8 결론에서 은폐되지 않았는지 재확인. 결함 0건.
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-06-test.md`

## 절차 흐름 (참고용 다이어그램)
> 아래 다이어그램은 위 절차를 시각적으로 요약한 참고 자료다. 규칙/조건의 최종 근거는 항상 위 텍스트다.

```mermaid
flowchart TD
    A["대상/범위/환경 정의(1~3절)"] --> B["테스트 케이스 작성·실행(4절)<br/>AC1~19 + :80 아티팩트 재현(TC-020) + 경계케이스(TC-EDGE)"]
    B --> C["커버리지 확인(5절) — 19/19"]
    C --> D["결함 목록 기록(6절) — 결함 없음"]
    D --> E{Critical/High 결함?}
    E -->|No, :80은 Low로 판정| G["verification-log 2회 이상(9절)"]
    G -->|PASS| H["PASS 판정 → 07단계(통합테스트) 진행"]
```

---

## 부록 — 재작업 라운드 2 (규칙F, `contact_email` 소비, 2026-09-25)

- **신규 AC**: `unit-06-note.md` §10 참고 — `legal.tests.PrivacyPolicyContactEmailTests` 4케이스(미설정 시 미노출 / 설정 시 mailto 렌더링 / 약관·쿠키 페이지 미노출 2건).
- **실행 결과**: 4케이스 개별 PASS, 전체 회귀 42케이스 OK(`unit-08-note.md` §10 인용). 캐시(`cache_page` 10분) 오염 방지를 위해 `setUp()`에서 `cache.clear()` 수행함을 확인 — 기존 WU-09 레이트리밋 테스트와 동일 패턴.
- **판정**: PASS — 다음 단계는 7단계(`feature-WU-06-integration-test.md`) addendum.
