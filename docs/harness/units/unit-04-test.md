# 단위테스트 결과서 — WU-04 (공개 열람 화면)

## 1. 개요
- 테스트 대상: WU-04(공개 열람 화면 — 목록/상세/카테고리/태그/RSS/404/500/반응형 레이아웃), REQ-003/REQ-004/REQ-014
- 테스트 유형: 단위(06단계)
- 테스트 목적: 05단계(`unit-04-note.md`)가 자체 실행 후 삭제한 검증(§3, "43건 전부 PASS")을 **신뢰하지 않고**, `unit-04-note.md` §8의 인수 조건(AC) 1~21번을 독립적으로 처음부터 재현해 실제로 PASS인지 증명한다(ORCHESTRATOR.md 규칙 C). 아울러 DEC-017(트리URL→정식URL 301 리다이렉트, 어드민 미리보기 비영향)이 실측으로도 성립하는지, 한글 슬러그 라우팅, srcset 실제 렌디션 연동(WU-03), 페이지네이션 경계값, 빈 상태/404 구분, 접근성 마크업, production 유사 설정 회귀, 어드민(WU-02/03) 회귀를 확인한다.
- 관련 산출물: `docs/harness/units/unit-04-note.md`(§8 AC1~21), `docs/harness/03-system-design.md`(v1.2, §4 라우트 계약), `docs/harness/04-ux-design.md`(v1.2, S-01~S-04/S-08/S-09, §5 접근성, §6 반응형), `docs/harness/decisions.md`(DEC-017/DEC-018), `docs/harness/units/unit-02-note.md`, `docs/harness/units/unit-03-note.md`
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- **범위(In-Scope)**:
  1. `unit-04-note.md` §8의 AC1~AC21 전부(코드 diff만 보고 05단계 서술은 근거로 인정하지 않음 — 매번 새 venv/DB로 처음부터 재현).
  2. 명백히 위험하다고 판단해 인수 조건에 없어도 추가한 케이스: 빈 slug 경로, SQL 인젝션성/XSS성 slug 입력, 페이지 번호 음수/초대형 정수, GET 전용 라우트에 대한 POST.
  3. **실제 500 서버 오류 페이지 렌더링**(Django 표준 `server_error` 핸들러 경로) — 05단계 노트는 이 경로를 한 번도 실제로 트리거하지 않았음을 §3 기록으로 확인했기에 이번 06단계에서 반드시 직접 재현.
  4. Wagtail 어드민 "미리보기" **엔드포인트 자체**(`/cms-admin/pages/<pk>/edit/preview/`, POST+GET)를 직접 HTTP로 호출해 DEC-017의 301 오버라이드가 실제로 영향을 주지 않는지 실증(05단계는 편집 화면 렌더링만 확인했고 실제 preview 엔드포인트는 소스 코드 정독으로만 검증했음 — 06단계는 동적 재현으로 보강).
  5. 어드민(WU-02/03) 회귀: 페이지 트리, Category 스니펫, 이미지 목록, `django-admin`.
  6. production 유사 설정(`production.py` 상속 + DB만 SQLite로 재정의, WU-01~03과 동일 방법론)에서 `check`/`migrate`/`collectstatic`, 그리고 HTTPS 경유 404/일반 라우트 정상 동작.
  7. 정적 분석/린트 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)가 실제로 수행됐는지 재확인(`pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml` 부재 재확인 + 변경된 Python 파일 전체에 대해 06단계가 직접 `py_compile` 재실행).
- **제외 범위(Out-of-Scope) 및 사유**:
  1. 실제 브라우저 렌더링(키보드 전용 수동 통과, 스크린리더 NVDA/VoiceOver 스팟체크, Lighthouse/axe-core 자동 검사), Pretendard 웹폰트 실제 로딩 — MCP(Playwright/Chrome 등) 미연동(DEC-001)으로 이번 06단계도 도구 기반 수행 불가. 05단계와 동일하게 미검증 사실을 그대로 승계·명시한다. 마크업 수준 정적 증거(스킵링크 클래스 존재, 랜드마크 태그 존재, 터치 타겟 CSS 규칙 존재)까지만 확인한다.
  2. NewsletterSubscribeForm, JSON-LD(BlogPosting/FAQPage) — DEC-018에 따라 WU-04 범위가 아니므로(WU-07/WU-05), 이번 WU 산출물에 애초에 존재하지 않는다. 인수 조건에도 없어 테스트 대상 아님.
  3. R2 오브젝트 스토리지 실제 네트워크 연동, Neon PostgreSQL 실제 연결 — WU-01~03과 동일하게 SQLite 대체 + 더미 R2 환경변수로 `check`/`migrate`/`collectstatic`의 코드 경로만 검증한다(실제 벤더 연동은 배포 단계 소관).
  4. Wagtail 예약발행 cron(`publish_scheduled_pages`) 실제 스케줄 실행 — unit-04-note.md §7-2가 이미 운영 파이프라인 몫으로 명시적으로 이관했으므로 이번 WU 코드 범위가 아니다.

## 3. 테스트 환경
- 실행 환경: Windows 10, Python 3.13.9, `webapp/.venv_test06`(이번 06단계가 처음부터 새로 생성, 검증 후 삭제)
- 패키지: `requirements.txt` 그대로(`pip install -r requirements.txt`, 신규 패키지 없음, Django 5.2.17 / Wagtail 7.4.3)
- DB: SQLite — dev 검증용 `db.sqlite3`(빈 DB에서 `migrate`부터 재생성), production 유사 검증용 `db_prodlike.sqlite3`(별도). 둘 다 검증 후 삭제.
- production 유사 설정: `config/settings/it_test_prodlike.py`(이번 06단계가 신규 생성 — `production.py` 상속 + `DATABASES`만 SQLite로 재정의, WU-01~03·05단계와 동일 방법론). 더미 R2 환경변수(`R2_ACCESS_KEY_ID` 등) 사용, 실제 네트워크 호출 없음. 검증 후 삭제.
- 테스트 도구: `django.test.Client`, `django.test.RequestFactory`(500 핸들러 직접 호출용), 임시 Python 스크립트(스크래치패드 경로에서 실행, 저장소 밖). 브라우저/axe-core/Lighthouse는 미사용(2절 제외 범위 사유).
- 테스트 데이터: Category 8종(기존 "기술" + 신규 7종, AC16 검증용), `CustomImage` 1건(PIL로 생성한 800x600 PNG, WU-03 `CustomImage` 모델에 실제 업로드), `BlogPostPage` 발행 12건(문단/이미지(alt_text 포함)/인용/FAQ 블록을 모두 포함한 1건 + 페이지네이션용 11건) + 미공개(`live=False`) 1건, 태그 "파이썬"(한글), 관리자 계정 1건(`is_superuser=True`).
- 전제 조건: WU-01(골격/보안설정)·WU-02(BlogPostPage/Category/Tag)·WU-03(CustomImage) 소스가 이미 저장소에 존재(커밋 전 워킹트리 상태)하고, `git status`상 WU-04 diff만 추가로 존재함을 시작 전 확인했다.

## 4. 테스트 케이스 및 결과

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001(AC1) | 신규 venv에 의존성 설치 | 빈 venv | `pip install -r requirements.txt` | 오류 없이 종료 | 오류 없이 종료(신규 패키지 없음, WU-01~03과 동일 버전) | PASS | |
| TC-002(AC2) | 빈 DB에서 마이그레이션 | dev 설정, 빈 SQLite | `manage.py migrate` | 오류 없이 전체 적용 | 오류 없이 전체 적용 | PASS | |
| TC-003(AC3) | 시스템 체크 | 위 상태 | `manage.py check` | "System check identified no issues" | 동일 문구 출력 | PASS | |
| TC-004(AC4) | 마이그레이션 누락 여부 | 위 상태 | `manage.py makemigrations --check --dry-run` | "No changes detected" | 동일 문구 출력 | PASS | 이번 WU가 모델 스키마를 변경하지 않았음을 재확인 |
| TC-005(AC5) | 홈 빈 상태 | 게시물 0건 | `GET /` | 200, "아직 게시된 글이 없습니다" 포함 | 200, 문구 포함 확인 | PASS | |
| TC-023(A11Y-1) | 스킵링크 마크업(추가) | 위 응답 | 응답 본문에서 `class="skip-link"` 검색 | 존재 | 존재 확인 | PASS | AC 범위 밖이나 04 §5 필수 요건이라 검증 |
| TC-024(A11Y-2) | 시맨틱 랜드마크(추가) | 위 응답 | `<header>`/`<nav`/`id="main-content"`/`<footer>` 존재 검색 | 전부 존재 | 전부 존재 확인 | PASS | 04 §5 요건 |
| TC-006(AC6) | 게시물 상세 전체 블록 렌더링 | Category "기술" + `CustomImage` + `BlogPostPage`(문단/이미지(alt_text)/인용/FAQ) 발행 | `GET /blog/first-post/` | 200, 제목/카테고리 배지/태그 칩/문단/이미지 alt/인용/FAQ 질문 전부 렌더 | 200, 8개 세부 항목(제목/카테고리/태그/문단/이미지alt/인용/FAQ×2) 전부 True | PASS | |
| TC-007(AC7) | 반응형 이미지 | 위 게시물 | 응답 body에서 `srcset`/`alt`/`loading="lazy"` 확인 | `400w`/`800w` 포함, `alt="<이미지 title>"`, `loading="lazy"` | 실제 응답: `srcset="/media/images/hero_XXXX.width-400.png 400w, .../width-800.png 800w"`, `alt="테스트 대표이미지"`, `loading="lazy"`, `width="800" height="600"` | PASS | |
| TC-034(추가) | srcset URL이 실제 파일로 존재(WU-03 연동) | 위 응답 | `media/images/` 디렉터리에서 `hero_*.width-400.png`/`width-800.png` 실존 확인 | 파일 실재 | 두 렌디션 파일 모두 디스크에 실재 확인 | PASS | 05단계는 URL 문자열만 확인, 06단계는 실제 렌디션 파일 생성까지 확인 |
| TC-008(AC8) | 트리 URL → 정규 URL 301 | 위 게시물 | `GET /first-post/`(트리 URL, follow 안 함) | 301, `Location: /blog/first-post/` | 301, `Location=/blog/first-post/` | PASS | DEC-017 실증 |
| TC-009(AC9) | 미공개/미존재 게시물 404 | `live=False` 게시물 1건(`unit-04-note.md` AC9 문구 "live=False로 만들거나" 그대로 명시적 `live=False`로 생성) + 존재하지 않는 slug | `GET /blog/draft-post/`, `GET /blog/no-such-slug/` | 둘 다 404 | 둘 다 404 | PASS | 최초 시도에서 `save_revision()`만 호출하고 `live` 플래그를 명시하지 않아 Wagtail 기본값(`live=True`)으로 생성되어 200이 나온 **테스트 스크립트 자체의 결함**을 발견 → Wagtail 소스(`Page.live` 필드 기본값)로 원인 규명 후 `live=False` 명시로 스크립트를 수정, 재실행해 PASS 확인(애플리케이션 결함 아님, unit-02-test.md 06단계가 겪은 것과 동일 유형의 자기 검증 실패 → 원인 규명 → 재확인 과정) |
| TC-010(AC10) | 카테고리 목록: 게시물 있음/빈 상태 구분 | 게시물 있는 카테고리("기술") + 게시물 0건인 카테고리("카테고리-1") | `GET /category/기술/`, `GET /category/category-1/` | 둘 다 200, 전자는 카드 노출, 후자는 "이 카테고리에는 아직 게시된 글이 없습니다." | 둘 다 200, 문구/카드 정확히 일치 | PASS | 404가 아님을 명시적으로 확인 |
| TC-011(AC11) | 존재하지 않는 카테고리 | - | `GET /category/no-such-category/` | 404 | 404 | PASS | |
| TC-012(AC12) | 한글 slug 태그 목록 | 게시물에 태그 "파이썬" 추가 | `GET /tag/파이썬/`(한글 그대로) | 200, 카드 노출 | 200, 게시물 카드 노출 확인 | PASS | `str:` 컨버터 교체(DEC-017) 실증 |
| TC-013(AC13) | 존재하지 않는 태그 | - | `GET /tag/no-such-tag/` | 404 | 404 | PASS | |
| TC-014(AC14) | RSS 피드 | 발행 게시물 1건 + 미공개 1건 | `GET /feed.xml` | 200, `application/rss+xml`, 발행글 제목/정규URL 포함, 미공개 제외 | 200, `Content-Type: application/rss+xml; charset=utf-8`, 발행글 제목·`/blog/first-post/` 포함, "초안 글" 미포함 | PASS | |
| TC-015(AC15) | 페이지네이션(정상/2페이지/범위초과/비정상값) | 발행 게시물 12건(10건/페이지) | `GET /`, `GET /?page=2`, `GET /?page=9999`, `GET /?page=abc` | 전부 200, 1페이지 응답에 `class="pagination"` 노출, 범위초과/비정상값도 예외 없이 200(보정) | 전부 200, `class="pagination"` 노출 확인 | PASS | |
| TC-028(RISK-4) | page=음수(추가) | 위와 동일 | `GET /?page=-1` | 예외 없이 200(보정) | 200 | PASS | 인수 조건에 없으나 "잘못된 값" 범주에 해당해 위험 케이스로 추가 |
| TC-029(RISK-5) | page=초대형 정수(추가) | 위와 동일 | `GET /?page=999999999999999999999999` | 예외 없이 200(보정) | 200 | PASS | Python 정수 오버플로 없음(`int` 임의정밀도) — `Paginator.get_page` 내부에서 안전 처리 확인 |
| TC-016(AC16) | 헤더 카테고리 "더보기" | Category 8종(정렬순) | `GET /` | `<details><summary>더보기</summary>` 노출, 7번째 이후 카테고리 포함 | 노출 확인, 8번째 카테고리명 포함 확인 | PASS | |
| TC-017(AC17) | 어드민 로그인 페이지 회귀(WU-01) | 비로그인 | `GET /cms-admin/login/` | 200 | 200 | PASS | |
| TC-018(AC18) | 어드민 편집 화면(OP-03 비영향, 1차) | 관리자 로그인, 위 게시물 | `GET /cms-admin/pages/<pk>/edit/` | 200, 편집 폼 정상 렌더(301로 새지 않음) | 200 | PASS | |
| TC-019(추가, AC18 심화) | Wagtail 실제 미리보기 엔드포인트(OP-03, 2차) | 관리자 로그인 | `reverse('wagtailadmin_pages:preview_on_edit', args=[pk])` 조회 → 세션 데이터 없이 `GET`, 편집폼 최소 데이터로 `POST`(`{"is_valid": true, "is_available": true}` 응답 확인), 이어서 `GET` | 세 요청 모두 200(301로 리다이렉트되지 않음), 마지막 `GET` 응답에 게시물 제목 포함 | `GET`(세션 無) 200(Wagtail "Preview not available" 안내), `POST` 200 `{"is_valid": true, "is_available": true}`, `GET`(세션 有) 200, 제목 포함 확인, 301/302 없음 | PASS | 05단계는 편집 화면 렌더링(TC-018 수준)과 Wagtail 소스 정독으로만 OP-03을 검증했음 — 06단계는 실제 `preview_on_edit` 엔드포인트를 POST+GET으로 직접 호출해 `BlogPostPage.serve()`의 301 오버라이드가 이 경로에 전혀 개입하지 않음을 동적으로 실증(DEC-017 결론을 한 단계 더 강하게 재확인) |
| TC-033(추가) | 어드민 회귀(WU-02/03) | 관리자 로그인 | `GET /cms-admin/`, `/cms-admin/pages/`, `/cms-admin/snippets/blog/category/`, `/cms-admin/images/`, `/django-admin/` | 전부 200 | 전부 200 | PASS | WU-04가 `BlogPostPage.serve()`/`get_url_parts()`를 오버라이드했으므로 어드민 트리·스니펫·이미지 관리 화면에 회귀가 없는지 명시적으로 확인 |
| TC-020(AC19) | dev collectstatic | dev 설정 | `manage.py collectstatic --noinput` | 오류 없이 종료, `components.css`/`nav.js` 수집 | "216 static files copied", `staticfiles/css/components.css`·`staticfiles/js/nav.js` 실재 확인 | PASS | |
| TC-021(AC20) | production 유사 설정 회귀 | `config/settings/it_test_prodlike.py`(production.py 상속 + SQLite) + 더미 R2 환경변수 | `manage.py check`, `migrate`(처음부터), `collectstatic --noinput` | 전부 오류 없이 종료 | `check`: "no issues", `migrate`: 전체 적용, `collectstatic`: "0 static files copied, 216 unmodified, 632 post-processed" | PASS | 05단계 §3-3 수치(216/632)와 정확히 일치 — WhiteNoise 매니페스트 스토리지 정상 |
| TC-031(추가, Critical) | **500 서버 오류 페이지 실제 렌더링** | production 유사 설정(`DEBUG=False`), Django 표준 미처리 예외 경로 | `django.views.defaults.server_error(request)`를 `RequestFactory` 요청으로 직접 호출(Django가 실제 미처리 예외를 500으로 변환할 때 내부적으로 호출하는 것과 동일한 함수) | 200, `500.html` 렌더, "일시적인 오류가 발생했습니다" 포함 | **`django.template.exceptions.TemplateSyntaxError: Invalid block tag on line 4: 'static'. Did you forget to register or load this tag?`** — 템플릿 자체가 컴파일되지 않아 500 페이지가 전혀 렌더링되지 않음 | **FAIL** | **DEF-001(Critical)** — 아래 6절 참고. dev 설정(`config.settings.dev`)에서도 동일하게 재현됨(설정과 무관한 템플릿 파싱 단계의 결함) |
| TC-032(추가) | 404 페이지 브랜드 렌더링(회귀) | production 유사 설정, `DEBUG=False`, HTTPS(SECURE_SSL_REDIRECT 통과) | `Client(SERVER_NAME="example.com").get("/blog/no-such-slug-prodlike/", secure=True)` | 404, "페이지를 찾을 수 없습니다" 포함 | 404, 문구 포함 확인 | PASS | HTTP(비보안)로 먼저 시도했을 때는 `SECURE_SSL_REDIRECT`로 301이 나와 "결함처럼" 보였으나, 이는 WU-01 보안설정(§5.5, DEC-015)이 의도한 정상 동작임을 확인하고 `secure=True`로 재시도해 실제 404 브랜드 페이지를 확인함(테스트 설계 보정) |
| TC-025(RISK-1) | 빈 slug(추가) | - | `GET /blog//` | 매칭 실패 → 404 | 404 | PASS | |
| TC-026(RISK-2) | SQL 인젝션성 slug(추가) | - | `GET /blog/' OR '1'='1/` | 500 아님, 404(ORM 파라미터 바인딩으로 안전 처리) | 404 | PASS | Django ORM만 사용(raw SQL 없음, 03 §5.2)이 실제로 지켜짐을 확인 |
| TC-027(RISK-3) | XSS성 slug(추가) | - | `GET /blog/<script>alert(1)</script>/`(URL 인코딩) | 404, 응답에 `<script>alert(1)</script>`가 이스케이프 없이 반사되지 않음 | 404, 미이스케이프 반사 없음 확인 | PASS | |
| TC-030(RISK-6, 정보성) | GET 전용 라우트에 POST(추가) | - | `POST /blog/first-post/` | (인수 조건 없음, 정보 수집 목적) | 200 — 뷰에 메서드 제한이 없어 GET과 동일하게 처리됨(캐시는 `cache_page`가 GET/HEAD만 캐싱하므로 POST는 매번 재실행) | 정보성(결함 아님) | 상태를 변경하는 부수효과가 없는 순수 조회 뷰이고 CSRF 보호 대상도 아니므로 보안/데이터 무결성 위험은 없음. 다만 향후 뷰가 늘어날 때 `require_GET` 명시를 권고(7절 리스크로 기록, Low, 블로킹 아님) |
| TC-035(추가) | 정적 분석/린트 게이트 재확인 | 저장소 루트 | `pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml` 탐색 + 변경된 Python 파일 전체 `py_compile` 재실행(06단계가 독립적으로) | 린트 설정 없음(05단계 서술과 일치) + 전부 컴파일 성공 | 파일 탐색 결과 0건(설정 없음 확인), `py_compile` 15개 파일 전부 성공(`exit=0`) | PASS | 05단계 §4 서술을 06단계가 직접 재현해 확인(그대로 믿지 않음, 규칙C) |
| TC-022(AC21) | 검증 산출물 정리 | 위 모든 테스트 완료 | `.venv_test06`, `db.sqlite3`, `db_prodlike.sqlite3`, `media/`, `staticfiles/`, `config/settings/it_test_prodlike.py`, 임시 스크립트, `webapp/unit04_results.json`(스크립트가 cwd에 실수로 남긴 파일) 삭제 후 `git status --porcelain -- webapp` 확인 | WU-04 소스 diff만 남음 | 삭제 완료. `git status`에 `webapp/blog/`, `webapp/custom_images/`, `webapp/config/static/css/components.css`, `webapp/config/static/js/`, `webapp/config/templates/partials/`(신규) + 기존 수정 파일(`config/urls.py`, `config/settings/base.py`, `config/templates/404.html`/`500.html`/`base.html`, `home/models.py`, `home/templates/home/home_page.html`, `render.yaml`, `.env.example`)만 남음, 테스트 산출물 없음 | PASS | 06단계 자신이 만든 임시 파일(`unit04_results.json`)도 빠짐없이 정리했는지 별도 확인함 |

## 5. 커버리지
- **인수 조건 커버리지**: `unit-04-note.md` §8 AC1~AC21 **21개 전부** 최소 1개 이상의 TC로 1:1 매핑해 재현했다(위 표의 "ID" 열 괄호 안 AC 번호 참고). 100% 커버.
- **추가 커버리지(범위 밖이나 위험해서 포함)**: 빈 입력(TC-025), SQL 인젝션성/XSS성 입력(TC-026/027), 페이지네이션 경계값 음수/초대형(TC-028/029), 접근성 마크업 최소 증거(TC-023/024), 어드민 회귀 확장(TC-033), 미리보기 엔드포인트 동적 재현(TC-019), **실제 500 오류 페이지 렌더링(TC-031, 이번에 결함 발견)**, 404 브랜드 페이지의 production 유사 회귀(TC-032), 정적 분석 게이트 재확인(TC-035).
- **커버되지 않은 부분과 사유**:
  1. 실제 브라우저(키보드 전용 통과, 스크린리더, Lighthouse/axe-core), Pretendard 폰트 로딩 — MCP 미연동(DEC-001). 05단계와 동일한 한계이며 이번 06단계도 도구 기반 검증을 대체할 수단이 없어 마크업 정적 증거로만 대체했다(2절 제외범위 1).
  2. R2/Neon 실제 네트워크 연동 — SQLite/더미 환경변수 대체(2절 제외범위 3), 실제 벤더 연동은 배포단계(10~12단계) 소관.
  3. 동시성/부하 테스트 — 이번 WU는 읽기 전용 콘텐츠 뷰이고 02-planning.md가 명시한 트래픽 규모(월 500UV)에서 부하 테스트를 요구하지 않아(03 §2.5 DEC-012 캐시 전략으로 대응) 범위에 포함하지 않았다.
  4. 뷰 캐시(10분 TTL)로 인한 데이터 갱신 지연 자체의 정확한 만료 시각 검증 — 매 TC 전 `cache.clear()`로 우회했으므로 TTL 값 자체(정확히 600초)를 시간 기반으로 실측하지는 않았다(값은 `blog/constants.py` 코드 값을 직접 확인하는 것으로 충분하다고 판단).

## 6. 결함(Defect) 목록

| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| DEF-001 | **`config/templates/500.html`이 `TemplateSyntaxError`로 컴파일 자체가 되지 않아, 실제 프로덕션(DEBUG=False) 환경에서 미처리 예외가 발생하면 S-09(브랜드 500 페이지)가 전혀 표시되지 않는다.** 원인: 파일 최상단 `{# ... #}` 주석이 여러 줄에 걸쳐 있는데(1~6행), Django의 `{# #}` 주석 태그는 한 줄을 넘어갈 수 없다(공식 문서: "This comment tag can not span multiple lines"). 그 결과 파서가 이 주석을 하나의 토큰으로 인식하지 못하고, 주석 설명 텍스트 안에 있던 `{% static %}`이라는 문구(4행, "static도 마찬가지 이유로 쓰지 않고"라는 **설명 문장의 일부일 뿐 실제 태그 호출 의도가 아님**)를 실제 템플릿 태그로 잘못 해석해 "Invalid block tag" 오류를 낸다. `git diff`로 확인한 결과 WU-01 버전(3줄 주석, 태그 문자열 없음)까지는 잠재적으로만 유효하지 않은 문법이었을 뿐 실제로는 무해했고, **WU-04가 이 주석에 `{% static %}` 문구를 설명용으로 추가하면서 잠재적 하자가 실제 파싱 오류로 전환**됐다(근본 원인은 WU-04 diff 내부에 있음, WU-01 재작업 불필요). | 1) `config/settings/dev.py` 또는 production 유사 설정 아무 것이나 로드, 2) `RequestFactory().get(아무 URL)`로 요청 객체 생성, 3) `django.views.defaults.server_error(request)` 호출(Django가 미처리 예외를 500으로 변환할 때 실제로 호출하는 것과 동일한 함수), 4) `TemplateSyntaxError` 발생 확인(TC-031). Production 유사 설정(`DEBUG=False`)에서도 동일하게 재현됨(설정과 무관, 템플릿 파싱 단계의 결함이므로 환경 독립적). | **Critical** | Open | **05단계(WU-04)로 반려 요청.** 조치 방향(택1, 세부 판단은 5단계 재량): (a) 1~6행 주석을 `{% comment %}...{% endcomment %}`로 교체(다중 라인 주석에 Django가 공식 지원하는 유일한 방법), (b) 주석을 한 줄로 축약, (c) 설명 문장에서 `{% static %}`이라는 리터럴 표기를 피하고 "static 태그"처럼 중괄호 없는 표현으로 대체. 수정 후 TC-031(및 TC-032/전체 회귀)을 반드시 재실행할 것. 동일 계열 위험(다중 라인 `{# #}` 주석)이 `blog/templates/blog/blog_post_page.html`(4~9행)에도 있으나 그 주석 안에는 `{%`/`{{` 리터럴이 없어 **현재는 무해함을 TC-006/007로 실측 확인했다** — 다만 향후 그 주석을 수정하는 개발자가 실수로 `{%`류 문구를 추가하면 같은 방식으로 깨질 수 있으므로, 5단계가 500.html을 고칠 때 같은 파일도 함께 `{% comment %}`로 정리할 것을 권고한다(Critical 결함의 직접 원인은 아니므로 블로킹 요건은 아님, Low 권고). |

- 위 1건을 제외하면 결함 없음. 이는 위 4절의 34개 TC 중 33개가 실제 HTTP 요청/명령 실행으로 PASS를 직접 확인했기 때문이며(추측/서류상 판단 없음), 특히 05단계가 실제로 검증하지 않았던 영역(TC-019 미리보기 엔드포인트 동적 호출, TC-031 실제 500 렌더링, TC-032 production 유사 404, TC-033 어드민 회귀 확장, TC-034 srcset 파일 실존, TC-035 정적분석 게이트 재확인)까지 독립적으로 새로 재현해 근거를 남겼다.

## 7. 리스크 및 잔존 이슈
- **DEF-001로 인한 실질적 리스크**: 현재 상태로 배포되면, 실제 운영 중 미처리 예외(예: DB 순간 장애, 예상치 못한 데이터 이상)가 발생했을 때 사용자에게 브랜드 500 페이지 대신 Django/Gunicorn의 원시 오류 응답이 노출될 수 있다. 이는 S-09(04-ux-design.md)의 설계 목적을 정면으로 무력화하며, 하필 장애 상황(가장 사용자 신뢰가 중요한 순간)에 UX가 가장 나빠지는 결과로 이어진다. **7단계(통합테스트) 착수 전 반드시 해소되어야 한다.**
- `blog/templates/blog/blog_post_page.html`의 동일 계열(다중 라인 `{# #}`) 주석 — 현재는 무해하지만 잠재적 지뢰(Low, 6절 권고 참고).
- `RISK-6`(POST가 GET 전용 콘텐츠 뷰에서 거부되지 않음) — 보안/무결성 영향 없음(부수효과 없는 순수 조회), 다만 코드 명확성을 위해 `require_GET` 데코레이터 도입을 권고(Low, 블로킹 아님).
- 뷰 캐시(10분 TTL) 특성상 발행 직후 즉시 반영을 기대하고 테스트를 설계하면 거짓 결함으로 오인될 수 있음 — unit-04-note.md §7-3이 이미 인계했고, 이번 06단계도 매 TC 전 `cache.clear()`로 실제 우회해 검증했다(재확인).
- 실제 브라우저/스크린리더/Lighthouse 미검증(2절/5절) — MCP 미연동(DEC-001) 한계가 05→06 그대로 이어짐. 7단계 이후 별도 도구 도입 시점까지 잔존 리스크로 유지.
- Pretendard 웹폰트 미구현(unit-04-note.md §2-4 승계) — 접근성/기능 영향 없음, 시각 완성도 항목으로 잔존.

## 8. 결론 및 판정
- [ ] PASS
- [ ] CONDITIONAL PASS
- [x] **FAIL** — 사유: DEF-001(Critical, 500 서버 오류 페이지가 실제로 렌더링되지 않음)이 Open 상태. AC1~21은 21개 전부 PASS했지만(4절), 이번 06단계가 인수 조건에는 없어도 "명백히 위험한 케이스"로 추가한 실제 500 렌더링 검증(TC-031)에서 Critical 결함이 발견되어 ORCHESTRATOR.md 규칙에 따라 **5단계(05-unit-developer, WU-04)로 되돌려 재작업을 요청**한다. 재작업 범위는 `config/templates/500.html`(및 권고사항으로 `blog/blog_post_page.html`의 동일 계열 주석) 수정이며, 3단계(설계서)·4단계(디자인서)까지 거슬러 올라갈 필요는 없다 — 근본 원인이 WU-04 자신의 구현 세부사항(Django 템플릿 주석 문법)에 있고 설계/디자인 계약과는 무관하기 때문이다(규칙 F-1, 근본 원인 발생 단계까지만 소급). 수정 후에는 TC-031을 포함해 이 결과서 전체를 재실행하고, 이 파일의 "변경 이력"에 재작업 라운드를 기록해야 한다.
- 재작업 완료 후 재확인 절차: 5단계가 수정 diff를 넘기면, 06단계는 (1) TC-031을 최우선으로 재실행, (2) 500.html 수정이 다른 TC(특히 TC-005~TC-021)에 회귀를 일으키지 않는지 4절 표 전체를 재실행, (3) 결함 0건 확인 시 PASS로 전환하고 `docs/harness/traceability.md`를 갱신한다.

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자(06-unit-tester) 관점 — `unit-04-note.md` §8 AC1~21이 4절 표에 전부 1:1 매핑됐는지, 각 "실제 결과"가 이번 세션에서 직접 실행한 명령/HTTP 응답에 근거하는지(추측 없음), test-report-template.md 9개 절 전부 실질 내용으로 채워졌는지 확인. 최초 실행 시 TC-009가 FAIL로 나온 것이 애플리케이션 결함이 아니라 테스트 스크립트가 Wagtail의 `Page.live` 기본값(`True`)을 고려하지 않은 자체 결함임을 Wagtail 소스로 규명하고 스크립트를 수정·재실행해 PASS로 정정한 과정을 기록했다. 결함 없음(스크립트 자체의 결함은 결과서 v0 작성 전에 이미 해소).
- 2차 검증 결과 요약: "이 결과서를 오늘 처음 받아, 다음으로 7단계(통합테스트)를 맡을 담당자" 관점 — (1) AC 범위 밖이지만 위험한 케이스(빈 입력/SQLi/XSS/페이지 경계값)가 누락 없이 포함됐는지 재검토해 통과 확인. (2) "이 테스트를 통과했다고 7단계로 넘겨도 되는가"를 의심하며 05단계 §3-2의 "43건 전부 PASS"라는 서술을 그대로 신뢰하지 않고 **모든 TC를 이번 세션에서 새 venv/DB로 처음부터 재실행**했는지 재확인(재확인 완료 — 05단계 산출물을 코드로만 참고, 결과 수치는 인용하지 않음). (3) 05단계가 "OP-03 미리보기 비영향"을 편집 화면 렌더링(TC-018 수준)과 소스 코드 정독으로만 확인했다는 점을 의심해, 실제 `preview_on_edit` 엔드포인트를 동적으로 호출하는 TC-019를 신규 설계해 추가했다. (4) 마찬가지로 "500 서버 오류"가 03 §4/04 §2 S-09에 명시적 계약으로 존재함에도 05단계 §3-2에 한 번도 실제로 트리거된 적이 없다는 점을 발견하고, TC-031(RequestFactory + `server_error` 직접 호출)을 신규 설계해 실행한 결과 **DEF-001(Critical)을 발견**했다. (5) DEF-001 발견 이후, 같은 계열의 다중 라인 `{# #}` 주석이 다른 신규 템플릿(`blog_post_page.html`)에도 있는지 저장소 전체를 `grep`으로 재검색해, 그 파일은 현재 무해함을 TC-006/007 결과로 재확인하고 권고사항으로만 6절에 남겼다(과잉 결함 보고 방지, 그러나 잠재 위험은 은폐하지 않음). (6) 검증에 사용한 모든 임시 산출물(venv 2종 경로, DB 2종, `config/settings/it_test_prodlike.py`, 06단계 스크립트가 실수로 cwd에 남긴 `unit04_results.json`)이 빠짐없이 삭제되어 `git status`에 WU-04 소스 diff만 남는지 재확인(TC-022).
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-04-test.md`

---

## 10. 재작업 재검증 — 2라운드 (규칙 F 피드백 루프, DEF-001 재확인)

- **트리거**: `docs/harness/units/unit-04-note.md` §10(재작업 이력 1라운드) — 5단계가 `webapp/config/templates/500.html`의 1~6행 다중 라인 `{# #}` 주석을 `{% comment %}...{% endcomment %}`로 교체하고, 주석 본문의 `{% static %}` 리터럴 표기를 "static 태그"로 수정했다고 보고. 이번 06단계는 그 수정 diff만을 신뢰 근거로 삼지 않고, 위 §1~9(1라운드)와 동일한 원칙(규칙 C)으로 **처음부터 새 venv/DB(`webapp/.venv_test06_round2`, `db.sqlite3`, `db_prodlike_round2.sqlite3`, 전부 검증 후 삭제)를 만들어 독립적으로 재현**했다.
- **재검증 일시**: 2026-09-17
- **재검증 범위**: (1) TC-031 최우선 재실행(dev + production 유사 설정 양쪽), (2) 회귀 방지를 위해 4절 표 35개 TC 전부 재실행(요청 지시가 "특히 TC-005~TC-021, TC-032"를 강조했으나, "기존 PASS 20개 인수조건도 최소한으로 재확인"까지 함께 지시받아 실제로는 AC1~21에 대응하는 TC 전체 + 추가 위험/회귀 TC까지 누락 없이 전부 재실행했다), (3) `unit-04-note.md` §10이 주장한 "TC-031 예상 결과 200은 서술 오탈자" 판단의 독립 재검증, (4) 게이트1/게이트2 재확인 여부 검증.

### 10.1 TC-031 예상 결과 "200" 서술에 대한 독립 재검증

`unit-04-note.md` §10-4는 "server_error()의 실제 반환 상태코드는 500이며, TC-031의 예상 결과 200 서술은 오탈자"라고 주장했다. 이를 05단계 서술을 그대로 신뢰하지 않고 Django 소스 코드를 직접 열어 확인했다.

- `django/views/defaults.py`의 `server_error()`는 성공 시 `return HttpResponseServerError(template.render())`를 반환한다.
- `django/http/response.py`의 `class HttpResponseServerError(HttpResponse): status_code = 500`으로 상태코드가 하드코딩되어 있다(오버라이드 불가능한 구조).

즉 server_error()가 정상적으로 템플릿을 렌더링에 성공하는 것과 상태코드 200을 반환하는 것은 동시에 성립할 수 없는 모순이며, "200, 500.html 렌더"라는 1라운드 TC-031의 예상 결과 문구는 (a) 상태코드 자체를 잘못 적었거나 (b) "렌더링이 200(오류 없이 성공)처럼 정상적으로 끝난다"는 의미를 상태코드 필드에 잘못 옮겨 적은 서술 오류로 판단하는 것이 타당하다. 05단계의 판단(오탈자)과 독립적으로 동일한 결론에 도달했다 — 따라서 이번 재검증의 판정 기준은 "① TemplateSyntaxError(또는 그 밖의 예외) 없이 템플릿이 정상 렌더링되는가, ② 실제 상태코드가 500(Django 표준 동작)인가, ③ 기대 문구가 포함되는가" 3가지로 확정한다.

### 10.2 TC-031 재실행 결과 (최우선)

| 환경 | 실행 절차 | 결과 |
|------|-----------|------|
| dev(`config.settings.dev`) | `RequestFactory().get("/anything")` → `django.views.defaults.server_error(request)` 직접 호출 | 예외 없음(TemplateSyntaxError 재현 안 됨), status_code=500, 응답 본문에 "일시적인 오류가 발생했습니다" 포함(길이 1306바이트) |
| production 유사(`config.settings.it_test_prodlike_round2`, `production.py` 상속 + `DATABASES`만 SQLite 재정의 + 더미 SECRET_KEY/DATABASE_URL/R2_*/DJANGO_ALLOWED_HOSTS, WU-01~06과 동일 방법론) | 위와 동일 절차 | 예외 없음, status_code=500, 동일 문구 포함(길이 1306바이트, dev와 바이트 단위로 동일 — 인라인 스타일만 쓰는 500.html 특성상 설정 차이가 출력에 영향을 주지 않음을 확인) |

**TC-031 판정: PASS** (10.1의 판정 기준 3가지 전부 충족). DEF-001의 근본 원인(다중 라인 `{# #}` 주석 안에 `{% static %}` 리터럴이 섞여 파서가 실제 태그로 오인)이 `{% comment %}...{% endcomment %}` 교체로 해소되었음을 직접 실행으로 실증했다.

### 10.3 4절 전체(35개 TC) 회귀 재실행 결과

지시받은 "특히 TC-005~TC-021, TC-032"를 포함해 4절의 TC-001~TC-035 전부를 새 venv/DB에서 재실행했다(TC-030은 원래도 정보성이며 인수 조건 없음, 그대로 유지). 시나리오/사전조건/실행 절차는 4절 원본과 동일하므로 재기재하지 않고, 이번 라운드에서 실제로 실행해 확인한 결과만 아래에 요약한다.

| ID | 재실행 결과 | 비고 |
|----|------------|------|
| TC-001(AC1) | PASS | 신규 venv, `pip install -r requirements.txt` 오류 없음(신규 패키지 없음, 1라운드와 동일 버전) |
| TC-002(AC2) | PASS | 빈 SQLite에서 migrate 처음부터 오류 없이 전체 적용 |
| TC-003(AC3) | PASS | "System check identified no issues (0 silenced)" |
| TC-004(AC4) | PASS | "No changes detected" |
| TC-005(AC5) | PASS | 200, "아직 게시된 글이 없습니다" 포함 |
| TC-023(A11Y-1) | PASS | `class="skip-link"` 존재 |
| TC-024(A11Y-2) | PASS | header/nav/id="main-content"/footer 전부 존재 |
| TC-006(AC6) | PASS | 200, 제목/카테고리 배지/태그 칩/문단/이미지alt/인용/FAQ x2 8개 세부 항목 전부 True |
| TC-007(AC7) | PASS | srcset 400w/800w, alt="테스트 대표이미지", loading="lazy" 전부 포함 |
| TC-034 | PASS | media/images/hero.width-400.png, hero.width-800.png 실제 렌디션 파일 디스크 실재 확인 |
| TC-008(AC8) | PASS | 301, Location=/blog/first-post/ |
| TC-009(AC9) | PASS | live=False 게시물 404, 존재하지 않는 slug 404(1라운드가 규명한 Page.live 기본값 함정을 이번 스크립트도 처음부터 live=False 명시로 회피, 재발 없음) |
| TC-010(AC10) | PASS | 게시물 있는 카테고리 200+카드, 게시물 0건 카테고리 200+빈 상태 문구 |
| TC-011(AC11) | PASS | 존재하지 않는 카테고리 404 |
| TC-012(AC12) | PASS | 한글 slug /tag/파이썬/ 200 + 카드 노출 |
| TC-013(AC13) | PASS | 존재하지 않는 태그 404 |
| TC-014(AC14) | PASS | 200, Content-Type: application/rss+xml; charset=utf-8, 발행글 제목/`/blog/first-post/` 포함, "초안 글" 미포함 |
| TC-015(AC15) | PASS | page=1/2/9999/abc 전부 200, class="pagination" 노출 |
| TC-028(RISK-4) | PASS | page=-1 → 200(예외 없이 보정) |
| TC-029(RISK-5) | PASS | page=999999999999999999999999 → 200(예외 없이 보정) |
| TC-016(AC16) | PASS | 8종 카테고리(기술+7) 중 헤더에 details/summary 더보기 노출 |
| TC-017(AC17) | PASS | 비로그인 /cms-admin/login/ 200 |
| TC-018(AC18) | PASS | 로그인 후 편집 화면 200 |
| TC-019 | PASS | preview_on_edit GET(세션無) 200 → POST 200(JSON 응답 파싱 성공) → GET(세션有) 200, 301/302 없음 |
| TC-033 | PASS | /cms-admin/, /cms-admin/pages/, /cms-admin/snippets/blog/category/, /cms-admin/images/, /django-admin/ 전부 200 |
| TC-020(AC19) | PASS | dev collectstatic --noinput → "216 static files copied", staticfiles/css/components.css, staticfiles/js/nav.js 실재 |
| TC-021(AC20) | PASS | production 유사(it_test_prodlike_round2) check(no issues)/migrate(전체 적용)/collectstatic("0 static files copied, 216 unmodified, 632 post-processed") — 1라운드 수치(216/632)와 정확히 일치, 500.html 수정이 정적 자산 매니페스트에 부작용을 주지 않음을 확인 |
| TC-031(추가, Critical) | PASS(10.2 상세 참고) | 1라운드 FAIL → 이번 라운드 PASS로 전환. DEF-001 해소 |
| TC-032(추가) | PASS | production 유사 + HTTPS(Client(SERVER_NAME="example.com").get(..., secure=True)) → 404, "페이지를 찾을 수 없습니다" 포함 |
| TC-025(RISK-1) | PASS | GET /blog// → 404 |
| TC-026(RISK-2) | PASS | SQL 인젝션성 slug(작은따옴표 OR 조건, URL 인코딩) → 404(ORM 파라미터 바인딩, raw SQL 없음) |
| TC-027(RISK-3) | PASS | XSS성 slug(script alert(1) 태그, URL 인코딩) → 404, 미이스케이프 반사 없음 |
| TC-030(RISK-6, 정보성) | 정보성(결함 아님) | POST /blog/first-post/ → 200(1라운드와 동일, 뷰에 메서드 제한 없음 — 회귀 아님, 기존 Low 권고 유지) |
| TC-035(추가) | PASS | 저장소 전체에 pyproject.toml/.flake8/ruff.toml/.pre-commit-config.yaml 여전히 부재(재탐색 결과 0건) — 이번 라운드는 Python 파일을 변경하지 않았으므로(500.html 템플릿 1개만 수정) py_compile 대상 신규/변경 파일 없음(N/A, 결함 아님) |
| TC-022(AC21) | PASS | .venv_test06_round2, db.sqlite3, db_prodlike_round2.sqlite3, media/, staticfiles/, config/settings/it_test_prodlike_round2.py, __pycache__류, 스크래치패드 임시 스크립트 전부 삭제 후 git status --porcelain -- webapp 확인 → WU-04 소스 diff(및 05단계가 아직 커밋하지 않은 .env.example/production.py/render.yaml 등 기존 변경분)만 남고 테스트 산출물 없음 |

**회귀 결과: 35개 TC 전부 PASS, 결함 0건.** 1라운드에서 지적한 "5절 커버되지 않은 부분"(실제 브라우저/스크린리더/Lighthouse, R2/Neon 실연동, 동시성/부하, 캐시 TTL 실측)은 이번 재작업이 500.html 주석 한 곳만 수정했고 그 범위와 무관하므로 재확인 대상에서 제외했다(범위 변경 없음).

### 10.4 게이트 1/게이트 2 재확인

- **게이트 1(정적 분석/린트)**: `unit-04-note.md` §10이 "이번 재작업은 Python 파일을 변경하지 않았다(HTML 템플릿 1개만 수정)"고 서술한 내용을 06단계가 직접 재확인했다 — git diff(2절 재현)상 변경 파일은 webapp/config/templates/500.html 1개뿐이며 .py 파일 변경 없음. 저장소 전체에 Python lint/type-check/formatter 설정 파일이 없다는 사실도 재탐색으로 재확인했다(있는데 건너뛴 것이 아님, WU-01~06과 동일 결론).
- **게이트 2(자체 코드 리뷰 체크리스트)**: `unit-04-note.md` §10의 5개 체크 항목(설계서 일치/에러 처리/입력값 검증/하드코딩 시크릿/범위 외 변경 없음, 전부 체크됨)이 실제 diff(500.html 주석·문구 수정 1건, 그 외 파일 무변경)와 일치함을 `git diff -- webapp/config/templates/500.html` 전체 diff를 직접 읽어 대조 확인했다 — 서술과 실제 코드 변경 범위가 정확히 일치, 과장/누락 없음.

### 10.5 내부 검증 (최소 2회) — 라운드 2

- 1차 검증(작성자 관점): 위 10.1~10.4가 (a) TC-031을 최우선으로 실제 실행했는지(실행함), (b) 지시받은 "TC-005~TC-021, TC-032"뿐 아니라 4절 전체 35개 TC를 빠짐없이 재실행했는지(표로 1:1 확인 가능), (c) "200"이 오탈자라는 05단계 주장을 그대로 베끼지 않고 Django 소스로 독립 재확인했는지(10.1 참고), (d) 검증에 쓴 venv/DB/media/staticfiles/임시 설정 모듈이 전부 삭제되고 git status가 소스 diff만 남기는지(TC-022 참고) 자가 점검. 결함 0건.
- 2차 검증("이 재검증 결과를 오늘 처음 받아, 7단계(통합테스트)에 handoff할지 결정해야 하는 오케스트레이터" 관점): (a) 1라운드에서 FAIL을 유발했던 정확히 같은 재현 경로(RequestFactory + server_error() 직접 호출, dev/production 유사 양쪽)로 재현했는지 재확인(동일 재현 경로 사용, 우연히 다른 경로를 써서 결함을 놓쳤을 가능성 배제). (b) 500.html 수정이 다른 파일에 영향을 줄 리 없다고 안이하게 생략하지 않고 캐시 뷰(홈/상세/카테고리/태그)·어드민·RSS·정적자산까지 4절 전체를 재실행해 수치(216/632 등)까지 1라운드와 대조했는지 재확인(10.3 참고). (c) DEF-001 외에 이번 재작업이 새로운 결함을 만들지 않았는지 의심 — blog_post_page.html의 동일 계열 주석(1라운드 Low 권고)이 이번 재작업 대상이 아니었음을 git diff 재확인으로 검증(변경 없음, 5단계가 사용자 지시대로 손대지 않았고 이는 원래도 무해함이 TC-006/007로 이미 실측됨). (d) traceability.md 갱신 누락 여부 확인. 결함 0건.
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-04-test.md`(라운드 2 섹션에 같은 형식으로 추가 기록)

### 10.6 최종 판정(갱신)

- [x] **PASS** — 사유: DEF-001(Critical)이 webapp/config/templates/500.html의 `{% comment %}...{% endcomment %}` 교체로 해소됨을 dev/production 유사 설정 양쪽에서 TC-031 재실행으로 직접 실증했다(10.2). 4절 전체 35개 TC를 전부 재실행해 회귀 없음을 확인했다(10.3, 결함 0건). 1라운드 §8의 FAIL 기록은 이 문서에서 삭제하지 않고 그대로 보존한다(규칙 F, 재작업 이력 추적성) — 최종 판정은 이 §10.6이 §8을 대체(override)한다.
- **7단계(통합테스트) 진행 가능.**
