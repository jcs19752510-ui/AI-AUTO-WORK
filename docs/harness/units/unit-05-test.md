# 테스트 결과서 (Test Result Report) — WU-05 (SEO/AI검색 대응)

> **주의**: 05단계(`05-unit-developer`)가 `unit-05-note.md`에서 보고한 로컬 검증 결과(venv `.venv_wu05` 등은 이미 삭제됨)는
> 이번 06단계 검증의 근거로 **인용하지 않았다**. ORCHESTRATOR.md 규칙 C("결함 0건 보고는 재현 가능한 형태로 남겨야 유효")와
> 이번 작업 지시("05단계가 보고한 검증을 신뢰하지 말고 §8의 18개 인수조건을 처음부터 독립 재현")에 따라, 이 결과서의 모든
> "실제 결과"는 06단계가 이번 세션에서 새로 만든 venv(`.venv_test05`, `.venv_test05b`, 검증 후 삭제)와 새로 작성한 스크립트로
> **처음부터 재현**한 것이다.

## 1. 개요
- 테스트 대상: WU-05(업무 단위) — SEO 기본 구현(REQ-005) + AI 검색 대응 콘텐츠 가이드라인(REQ-017), `webapp/core/`(신규), `webapp/blog/models.py`·`views.py`·`blocks.py`·`urls.py`(수정), `webapp/home/models.py`(수정), `webapp/config/settings/base.py`·`urls.py`(수정), `webapp/config/templates/base.html`(수정), `webapp/CONTENT_GUIDE.md`(신규)
- 테스트 유형: 단위(Unit)
- 테스트 목적: `docs/harness/units/unit-05-note.md` §8의 인수조건(AC) 18개를 독립적으로 재현해 PASS/FAIL을 판정하고, 오케스트레이터가 이번에 명시적으로 지시한 4가지 핵심 확인 사항(sitemap.xml/robots.txt 실응답, 상세페이지 메타/JSON-LD 렌더링·파싱, production 유사 HTTPS 환경에서의 절대 URL 정확성, WU-04 `BlogPostPage.serve()`의 Site.hostname 의존 여부 및 리다이렉트 정확성)을 실측으로 검증한다.
- 관련 산출물: `docs/harness/units/unit-05-note.md`(§8 AC1~18, §7 이연 이슈), `docs/harness/03-system-design.md`(v1.2 §4), `docs/harness/decisions.md`(DEC-017, DEC-019~021), `docs/harness/02-planning.md`(§4 REQ-005/017)
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- 범위 (In-Scope): `unit-05-note.md` §8 AC1~18 전부 독립 재현. 추가로 규칙 C/F에 따라 (a) WU-04 `BlogPostPage.serve()`가 동일한 Site.hostname 의존 메커니즘을 쓰는지 코드 확인 + production 유사 HTTPS 환경 실제 요청으로 검증(오케스트레이터 명시 지시), (b) WU-01~04 화면/피드/마이그레이션 체인과의 회귀 여부, (c) 정적 분석/린트 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)의 실제 통과 여부 재확인.
- 제외 범위 및 사유:
  - 실제 브라우저 기반 OG/Twitter 카드 미리보기(Facebook 공유 디버거/Twitter Card Validator), Google Search Console 실제 색인 제출 — MCP 미연동(DEC-001) + 실제 공개 도메인 부재. `unit-05-note.md` §7-3과 동일 사유로 이번 06단계도 수행 불가(10단계 이후 실측 권고, 그대로 유지).
  - robots.txt의 "Render 스핀다운 중 플랫폼이 disallow-all로 가로채는" 리스크의 실측 재현 — 실제 Render 인프라가 있어야 재현 가능하며 애플리케이션 코드로 해결 불가능한 플랫폼 제약이다(03 §6.3). 10단계(배포테스트) 대상으로 이관, 이번 06단계는 "정상 기동 중" 응답만 검증.
  - Cloudflare R2 실연동(실제 네트워크 업로드) — WU-03(REQ-006) 소유 범위이며 이미 `unit-03-test.md`/`feature-WU-03-integration-test.md`에서 검증됨. 이번 06단계는 production 유사 설정에서 R2 엔드포인트에 실제 접속하지 않기 위해 `STORAGES["default"]`만 임시로 로컬 파일시스템으로 재정의했다(§3 테스트 환경에 사유 명시) — SEO(URL 계산)와 오브젝트 스토리지 선택은 서로 독립적인 관심사이므로 이 재정의가 이번 테스트 대상(REQ-005/017)의 타당성에 영향을 주지 않는다.
  - NewsletterSubscribeForm 실제 제출 동작 — REQ-016(WU-07 미구현)이며 DEC-018/unit-05-note.md §7-4가 이미 범위 밖으로 명시함.

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro, Python 3.13.9, Git Bash. `webapp/requirements.txt`(Django 5.2.17, wagtail 7.4.3 등, WU-01~04와 동일 버전 — 신규 패키지 없음)를 새 venv 2개(`C:\Users\mega\AppData\Local\Temp\claude\...\scratchpad\wu05\.venv_test05`, `.venv_test05b`, 둘 다 검증 후 완전 삭제)에 clean install.
- 테스트 데이터: SQLite(dev — 빈 DB에서 `migrate`부터 새로 실행), Category 1건, `CustomImage` 1건(PIL로 실제 생성한 100x100 PNG), `BlogPostPage` 발행 게시물 15건(본문 FAQ 질문 2개 중 1개는 답변을 비워 AC9 "빈 답변 제외" 케이스 확보, 특수문자(`<`, `>`, `&`, `"`) 포함 게시물 1건, 페이지네이션 검증용 12건), 태그 1건.
- 전제 조건:
  - 매 시나리오 전 `django.core.cache.cache.clear()` 실행(공개 뷰가 `@cache_page(10분)`이므로 unit-05-note.md §8 주의사항 그대로 준수).
  - AC15(production 유사 환경)를 위해 `webapp/config/settings/it_test_prodlike_wu05.py`(검증 후 삭제)를 임시로 만들어 `production.py`를 상속하고 `DATABASES`만 SQLite로, `STORAGES["default"]`만 로컬 파일시스템으로 재정의했다(사유는 §2 참고). `SECRET_KEY`/`DATABASE_URL`/`DJANGO_ALLOWED_HOSTS=example.com`/`R2_*`(더미)를 환경변수로 주입.
  - 검증에 사용한 모든 산출물(venv 2개, `db.sqlite3`, `db_prodlike_wu05.sqlite3`, `media/`, `staticfiles/`, `config/settings/it_test_prodlike_wu05.py`, `__pycache__`, 스크래치패드 임시 스크립트)은 검증 완료 후 삭제했다(AC18, §6 근거 참고).

## 4. 테스트 케이스 및 결과

| ID | 시나리오 (대응 AC) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | venv 설치 (AC1) | webapp/requirements.txt | 새 venv 생성 후 `pip install -r requirements.txt` | 오류 없이 종료 | `pip install` 종료 코드 0, 오류 로그 없음(신규 패키지 없음, WU-01~04와 동일 버전 재확인) | PASS | |
| TC-002 | 빈 DB 마이그레이션 (AC2) | `DJANGO_SETTINGS_MODULE=config.settings.dev`, DB 파일 없음 | `python manage.py migrate` | 오류 없이 전부 OK | 전체 마이그레이션(home→blog→custom_images→core 순 포함 전체 체인) 오류 없이 완료, exit 0 | PASS | core 앱은 모델이 없어 자체 마이그레이션 없음(§4 설계와 일치) |
| TC-003 | 시스템 체크 (AC3) | TC-002 이후 | `python manage.py check` | "System check identified no issues" | 정확히 동일 문구 출력(0 silenced) | PASS | prodlike 설정에서도 동일 문구 재확인(TC-015 준비 단계) |
| TC-004 | 마이그레이션 드리프트 없음 (AC4) | TC-002 이후 | `python manage.py makemigrations --check --dry-run` | "No changes detected" | 정확히 동일 문구 출력 | PASS | prodlike 설정에서도 동일 재확인 |
| TC-005 | 테스트 데이터 준비 (AC5) | TC-002 이후 | Category/CustomImage 생성 → `HomePage.add_child()`로 대표이미지 포함 `BlogPostPage` 생성, 본문 FAQ 2문항(1개는 답변 비움) → `save_revision().publish()` | 오류 없이 생성·발행 | `BlogPostPage(pk=4, slug=test-post)` 등 정상 생성/발행 확인(`BlogPostPage.published().count()`로 발행 상태 재확인) | PASS | |
| TC-006 | 게시물 상세 메타/HEAD 요소 (AC6) | TC-005 | `GET /blog/test-post/` | 200 + `<title>`에 제목, `<meta name="description">`, canonical이 요청 host와 정확히 일치, `og:type=article`, `og:url==canonical`, `og:image`/`twitter:image`(대표이미지 有), `twitter:card=summary_large_image`, RSS `<link rel="alternate" ... href="/feed.xml">` | 상태 200. `<title>`에 "테스트 게시물" 포함. `<meta name="description">`에 "테스트 요약" 포함. canonical=`http://testserver/blog/test-post/`(요청 host와 완전 일치). `og:type=article` 존재. `og:url`=canonical과 정확히 동일. `og:image`/`twitter:image` 존재(대표이미지 등록됨). `twitter:card=summary_large_image` 존재. `<link rel="alternate" type="application/rss+xml" ... href="/feed.xml">` 존재. 11개 세부 항목 전부 확인 | PASS | 세부 결과는 스크래치패드 `run_checks.py` TC-006a~k 로그(43건 중) 참고 |
| TC-007 | JSON-LD 개수/파싱 유효성 (AC7) | TC-006 | 응답 HTML에서 `<script type="application/ld+json">` 정규식 추출 후 각각 `json.loads()` | 정확히 2개(BlogPosting/FAQPage), 둘 다 예외 없이 파싱 성공 | `<script type="application/ld+json">` 정확히 2개. 둘 다 `json.loads` 성공(예외 0건). `@type`이 각각 "BlogPosting"/"FAQPage" | PASS | WU-04 DEF-001(TemplateSyntaxError)과 같은 계열의 함정을 실측으로 배제 |
| TC-008 | BlogPosting 필드 (AC8) | TC-007 | 파싱된 BlogPosting dict 필드 검사 | headline==제목, datePublished/dateModified ISO 8601, mainEntityOfPage.@id==canonical, image가 절대 URL, author 존재(owner 없으면 Organization) | headline="테스트 게시물"(제목과 정확 일치). datePublished/dateModified 존재(ISO 8601 `T`구분자 형식). mainEntityOfPage.@id=`http://testserver/blog/test-post/` (TC-006 canonical과 정확 일치). image=`http://testserver/media/images/test.width-800.png`(http로 시작하는 절대 URL). author={"@type":"Organization","name":"블로그"}(owner 미설정이므로 Organization 폴백, DEC-020 동작 확인) | PASS | |
| TC-009 | FAQPage 필드 (AC9) | TC-007, TC-005(FAQ 2문항 중 1개 답변 비움) | 파싱된 FAQPage.mainEntity 검사 | mainEntity 개수==답변이 채워진 질문 개수(1개), acceptedAnswer.text에 HTML 태그/미해석 엔티티 없음 | mainEntity 개수=1(빈 답변 항목 정상 제외). acceptedAnswer.text="RSS는 구독 방식의 하나입니다. & 확인."(원본 저장값 `<p>...&amp;...</p>`에서 태그 제거+엔티티 디코딩됨, `<`/`>`/`&amp;` 잔존 없음, 있는 그대로의 리터럴 `&`만 남음 — html.unescape 정상 동작) | PASS | |
| TC-010 | 특수문자 제목/FAQ 렌더링 (AC10) | 제목 `제목 <테스트> & "인용"`, FAQ 질문/답변에 `<b>`/`&`/`"` 포함하는 별도 게시물(`special-post`, 대표이미지 없음) | `GET /blog/special-post/` | 500 없이 200, `<script` 개수==`</script>` 개수 | 상태 200(500 아님). `<script` 개수=3, `</script>` 개수=3(정확히 일치, 조기 종료 없음). 해당 게시물의 JSON-LD도 `json.loads` 파싱 성공 | PASS | 대표이미지 없는 경계 케이스도 함께 확인(og:image 블록이 조용히 생략, 크래시 없음) |
| TC-011 | sitemap.xml (AC11) | TC-005 | `GET /sitemap.xml` | 200, 정규 URL(`/blog/<slug>/`) 포함·트리 URL(`/<slug>/`) 미포함, `<loc>` host가 요청 host와 일치 | 상태 200. `http://testserver/blog/test-post/` 포함. `<loc>http://testserver/test-post/</loc>`(트리 URL 형태) 없음. 전체 `<loc>`이 `http://testserver/` 기준이고 `http://localhost/`는 0건 | PASS | Wagtail 기본 `get_full_url()`(Site.hostname 기반)이 아니라 `core.seo.absolute_page_url`(요청 기반) 오버라이드가 실제로 적용됨을 실측 확인(DEC-021 유효성 재확인) |
| TC-012 | robots.txt (AC12) | - | `GET /robots.txt` | 200, `Content-Type: text/plain`, `Disallow: /cms-admin/`, `Sitemap: http(s)://<host>/sitemap.xml` | 상태 200. `Content-Type`="text/plain"(정확히 `text/plain`, 세미콜론/charset 없음). `Disallow: /cms-admin/` 포함. `Sitemap: http://testserver/sitemap.xml` 포함(TC-011과 동일 host) | PASS | |
| TC-013 | category/tag/home canonical (AC13) | TC-005, 태그 1건 부착 | `GET /category/test-category/`, `GET /tag/<한글슬러그>/`, `GET /` | 각 canonical이 실제 요청 경로와 일치 | category: canonical=`http://testserver/category/test-category/`(일치). home: canonical=`http://testserver/`(일치). tag(한글 slug "파이썬"): canonical=`http://testserver/tag/%ED%8C%8C%EC%9D%B4%EC%8D%AC/`(요청 시 사용한 percent-encoded 경로와 정확히 일치, 최초 비교 시 raw 한글 문자열과 비교해 FAIL로 오판했던 테스트 스크립트 자체 결함을 발견·수정 후 재검증 PASS) | PASS | §9 2차 검증에서 이 테스트 스크립트 자체 결함(한글 slug 미인코딩 비교)을 재점검 대상으로 다룸 |
| TC-014 | 페이지네이션 canonical (AC14) | 발행 게시물 12건 이상(TC-005에서 준비) | `GET /?page=2` | canonical이 `?page=2`를 포함하는 자기참조 URL | canonical=`http://testserver/?page=2`(1페이지 URL로 뭉개지지 않음, 쿼리스트링 보존 확인) | PASS | |
| TC-015 | production 유사(HTTPS) 환경 — canonical/sitemap/robots (AC15) | `config.settings.it_test_prodlike_wu05`(§3), `DJANGO_ALLOWED_HOSTS=example.com`, `Client(SERVER_NAME="example.com")` | (A) `secure=True` 요청으로 TC-006/011/012를 https 환경에서 재실행 | canonical/og:url/JSON-LD mainEntityOfPage.@id/sitemap `<loc>`/robots.txt `Sitemap:` 줄 전부 `https://example.com/...`, 무한 리다이렉트 없이 200, DEC-015 회귀 없음 | 게시물 상세 200(무한루프 없음). canonical=`https://example.com/blog/test-post/`. og:url 동일. JSON-LD mainEntityOfPage.@id=`https://example.com/blog/test-post/`(canonical과 일치). sitemap.xml 200, 모든 `<loc>`이 `https://example.com/...`(localhost 0건). robots.txt `Sitemap: https://example.com/sitemap.xml`. 8개 세부 항목 전부 확인 | PASS | 세부 로그는 `run_checks_prodlike.py` TC-015a~h 참고 |
| TC-016 | collectstatic 무오류 (AC16) | `config.settings.dev`(원 지시 그대로 dev로) | `python manage.py collectstatic --noinput` | 오류 없이 종료, 파일 수가 WU-04와 동일 | "216 static files copied to ...staticfiles"(오류 0건). WU-04 기준(unit-04-test.md TC-021 "216/632")과 파일 수 216 일치(dev는 매니페스트 후처리를 쓰지 않아 post-processed 카운트는 해당 없음 — STORAGES 설정상 정상) | PASS | prodlike(WhiteNoise 매니페스트) 설정에서도 별도로 "216 static files copied ... 632 post-processed"까지 동일 수치로 재확인(TC-015 준비 단계에서 수행) |
| TC-017 | 어드민 로그인 화면 회귀 (AC17) | 비로그인 상태 | `GET /cms-admin/login/` | 200 | 상태 200 | PASS | |
| TC-018 | 검증 산출물 정리 (AC18) | 전체 검증 종료 후 | venv 2개/`db*.sqlite3`/`media/`/`staticfiles/`/임시 설정 모듈/스크래치패드 스크립트/`__pycache__` 삭제 후 `git status --porcelain -- webapp docs/harness` 실행 | webapp/docs/harness diff에 검증 산출물 없음 | `git status --porcelain -- webapp docs/harness`가 검증 시작 전과 동일한 목록만 출력(신규 소스/문서 diff 외 venv/db/media/staticfiles/임시설정/`__pycache__` 0건) | PASS | |
| TC-019 | **[오케스트레이터 명시 지시] WU-04 `BlogPostPage.serve()`의 Site.hostname 의존 여부 실측** | production 유사 설정(TC-015와 동일), `SERVER_NAME=example.com` | (A) `secure=True`로 `GET /test-post/`(트리 URL) 요청 후 `Location` 헤더 확인 + 리다이렉트를 실제로 따라가 최종 200/URL 확인. (B) 실제 Render 트래픽 형태(HTTP로 도착 + `X-Forwarded-Proto: https` 헤더, `Host` 헤더 포함)로 동일 요청 재실행 | `Location`이 `localhost`나 잘못된 스킴/호스트가 아니어야 하고(상대경로 `/blog/test-post/` 또는 올바른 절대 URL), 리다이렉트를 따라가면 최종 200이 `example.com` 기준으로 나와야 함 | (A) `GET /test-post/` → 301, `Location: /blog/test-post/`(상대경로). `follow=True`로 리다이렉트 추적 시 최종 200, 최종 URL=`https://example.com/blog/test-post/`(localhost 없음). (B) `X-Forwarded-Proto: https` + `Host: example.com` 헤더 형태에서도 동일하게 301, `Location: /blog/test-post/`, localhost 없음. 코드 확인 결과 `BlogPostPage.serve()`(`blog/models.py`)는 `self.get_url(request=request)`를 호출하며, 이는 오버라이드된 `get_url_parts()`가 반환하는 `page_path`(`reverse('blog:post_detail', ...)`, 절대 경로 문자열)를 그대로 쓴다 — **현재 이 프로젝트에 등록된 Wagtail Site가 1개뿐이고 요청이 그 Site와 일치하므로 Wagtail이 `root_url`을 비우고 상대경로만 반환한다.** 그 결과 `Site.hostname="localhost"` 값 자체가 이 경로에서는 아예 사용되지 않아, 결함이 재현되지 않았다 | **PASS (결함 미재현)** | 아래 §7 "리스크" 및 본 절 하단 "규칙F 판단" 참고 — Site가 2개 이상으로 늘거나 요청 Site 판정이 어긋나는 경우의 이론적 위험은 여전히 미검증(현재 인프라로는 재현 불가능한 조건) |
| TC-020 | 회귀 — WU-01~04 화면/피드/마이그레이션 체인 | TC-002, TC-005 | `GET /feed.xml`(WU-04 RSS), `GET /nonexistent-page-xyz/`(404), `GET /category/does-not-exist/`(404), `GET /blog/does-not-exist/`(404) | 전부 정상(RSS 200, 존재하지 않는 리소스는 404) | `/feed.xml` 200. `/nonexistent-page-xyz/` 404. `/category/does-not-exist/` 404. `/blog/does-not-exist/` 404 | PASS | AC 범위 밖이지만 "빈 입력/존재하지 않는 리소스" 경계 케이스로 규칙에 따라 추가 확인 |
| TC-021 | 게이트1(정적분석/린트) 독립 재확인 | 저장소 루트 | `pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml` 존재 여부 검색, 변경된 Python 14개 파일 `python -m py_compile` | 린트 설정 없음(WU-05 §4 주장과 일치), py_compile 전부 오류 없음 | 저장소 루트에 해당 설정 파일 0건(검색 결과 없음, WU-05 §4 주장 독립 재확인됨). `core/*.py`(6개)·`blog/models.py`·`blog/views.py`·`blog/blocks.py`·`blog/urls.py`·`home/models.py`·`config/urls.py`·`config/settings/base.py` 총 14개 파일 `py_compile` 전부 exit 0(구문 오류 0건) | PASS | |
| TC-022 | 대표이미지 없는 게시물(경계) | TC-010의 `special-post`(featured_image=None) | `GET /blog/special-post/` 응답에서 `og:image`/`twitter:image` 메타 유무 확인 | og:image/twitter:image 블록이 조용히 생략되고 크래시 없음 | 200 응답, `property="og:image"` 없음(featured_image 없는 정상 분기), 500 없음 | PASS | AC10과 함께 실행되었으나 별도 경계 케이스로 명시적 기록(규칙에 따른 "명백히 위험한 케이스" 사전 점검 — null 이미지) |

### 테스트 스크립트 자체 결함 발견·수정 기록 (규칙 — "테스트 자체가 잘못 설계되어 결함을 놓칠 가능성 항상 의심")
검증 도중 **테스트 스크립트 자체의 결함 2건**을 발견하고 수정 후 재검증했다(애플리케이션 결함 아님, 아래 §6에는 포함하지 않음):
1. **TC-013(태그 canonical) 최초 비교 오류**: 최초 스크립트가 기대값을 `http://testserver/tag/파이썬/`(원본 한글 문자열)로 하드코딩해 FAIL로 오판했다. 실제로는 `request.build_absolute_uri()`가 RFC 3986에 따라 URL을 percent-encoding하는 것이 정상 동작이며(브라우저/봇이 동일하게 처리), 요청에 사용한 실제 경로(`/tag/%ED%8C%8C%EC%9D%B4%EC%8D%AC/`)와 canonical을 다시 비교하자 정확히 일치했다. → 코드 결함이 아니라 테스트 스크립트의 기대값 계산 오류였음을 `urllib.parse.quote`로 직접 인코딩해 재비교함으로써 규명했다.
2. **TC-019(B) 최초 시도의 `:80` 포트 아티팩트**: `X-Forwarded-Proto: https` 헤더만 주고 `Host` 헤더를 생략한 채 요청했더니 canonical이 `https://example.com:80/blog/test-post/`(포트 80이 잘못 붙음)로 나왔다. 원인을 추적한 결과, Django `HttpRequest.get_host()`는 `HTTP_HOST` 헤더가 있으면 그것을 최우선으로 쓰고, 없을 때만 `SERVER_NAME`+`SERVER_PORT` 조합으로 폴백하며 이때 `SERVER_PORT`(테스트 클라이언트 기본값 "80")와 `is_secure()`(헤더로 인해 True) 판정이 불일치해 포트가 강제로 붙는다는 것을 Django 소스로 확인했다. 그러나 **실제 HTTP/1.1 요청은 `Host` 헤더가 항상 필수**이고, `production.py`(DEC-015 IT-04)가 이미 "Render는 원본 Host 헤더를 변경 없이 그대로 전달한다"를 실측 확인해둔 상태이므로, 이 상황은 "`Host` 헤더가 아예 없는" 비현실적인 테스트 조건에서만 발생한다. `HTTP_HOST=example.com`을 명시적으로 포함해 재요청하자(TC-019(B)와 동일 조건 + Host 헤더) canonical이 정확히 `https://example.com/blog/test-post/`로 나왔다(포트 없음) — **애플리케이션 결함이 아니라 최초 테스트 시뮬레이션이 HTTP 스펙상 필수인 `Host` 헤더를 누락한 테스트 스크립트 결함**이었음을 대조군 실행으로 확정했다.

> 정상 경로(Happy Path)뿐 아니라 경계값(대표이미지 없음, 발행 게시물 12건 이상 페이지네이션), 예외 입력(존재하지 않는 slug, 빈 FAQ 답변, HTML/따옴표/앰퍼샌드가 섞인 제목·본문), 권한 경계(비로그인 어드민 로그인 화면 회귀)를 포함했다. 동시성/부하 테스트는 이번 WU의 인수조건에 해당 항목이 없고 단위 테스트 단계의 통상적 범위를 벗어나 제외했다(8단계 전체 풀테스트에서 다룰 사안).

## 5. 커버리지
- 커버리지 지표: `unit-05-note.md` §8 AC1~18 = 18/18(100%) 전부 최소 1개 이상의 TC로 1:1 매핑되어 독립 재현·PASS. 오케스트레이터가 이번에 추가로 명시한 4가지 핵심 확인 사항(sitemap.xml/robots.txt 실응답, 메타/JSON-LD 렌더링·파싱, production 유사 HTTPS 절대 URL, WU-04 serve() Site.hostname 의존성 실측)도 각각 TC-011/012, TC-006~010, TC-015, TC-019로 커버됨.
- 커버되지 않은 부분과 사유: §2 제외 범위에 명시한 3건(외부 도구 기반 OG/Twitter 실제 미리보기, Search Console 색인 반응, Render 실제 스핀다운 시 robots.txt 가로채기) — 전부 실제 외부 서비스/인프라가 있어야 재현 가능하며 10단계(배포테스트) 이후 실측이 필요함을 그대로 유지. Wagtail Site가 2개 이상으로 늘어나는 시나리오(TC-019 비고의 이론적 리스크)는 현재 인프라에 Site가 1개뿐이라 이번 단위테스트 범위에서 물리적으로 재현 불가능하다(§7에 잔존 리스크로 기록).

## 6. 결함(Defect) 목록
**결함 없음.** 아래 근거로 확인했다:
- AC1~18 전부(TC-001~018) 독립 재현 PASS, 예상 결과와 실제 결과를 문자열 단위로 직접 비교(단순 "에러 없음"이 아니라 canonical/JSON-LD 필드/sitemap host 등 구체적 값을 검증).
- 오케스트레이터가 이번에 특별히 우려한 WU-04 `BlogPostPage.serve()`의 Site.hostname 의존 문제(unit-05-note.md §7-1)를 production 유사 HTTPS 환경에서 두 가지 요청 형태(A: `secure=True`, B: 실제 Render 트래픽 형태인 `X-Forwarded-Proto`+`Host` 헤더)로 실제로 재현 시도했으나, **결함이 재현되지 않았다**(TC-019) — 근본 원인은 현재 프로젝트에 등록된 Site가 1개뿐이라 `get_url_parts()`가 상대경로만 반환하기 때문이며, 이는 추측이 아니라 코드(`get_url_parts` 오버라이드, `blog/models.py`)를 직접 읽고 실제 HTTP 응답의 `Location` 헤더 값으로 확인한 것이다.
- 검증 중 발견된 2건의 이상 징후(TC-013 최초 실패, TC-019(B) 최초 `:80` 아티팩트)는 모두 원인을 근본까지 추적한 결과 **테스트 스크립트 자체의 결함**으로 확정되었고(위 "테스트 스크립트 자체 결함" 절), 대조군 실행으로 애플리케이션 코드에는 문제가 없음을 재확인했다. "테스트가 실패하면 무조건 테스트 탓으로 돌리지 않는다"는 원칙에 따라, 두 경우 모두 Django 소스 코드(`get_host()`/`is_secure()`/`build_absolute_uri()`)를 직접 읽고 실제 요청 조건을 바꿔가며 원인을 검증한 뒤에만 "결함 아님"으로 결론 내렸다.
- 게이트1(정적분석/린트, §4)·게이트2(자체 코드 리뷰 체크리스트, §5)를 `unit-05-note.md`에서 그대로 베끼지 않고 TC-021로 독립 재확인했다(린트 설정 부재는 검색으로, py_compile은 직접 실행으로).

## 7. 리스크 및 잔존 이슈
- **Wagtail Site가 향후 2개 이상으로 늘어나는 경우의 이론적 리스크(unit-05-note.md §7-1과 동일 리스크, 이번 06단계가 실측으로 배제하지 못하고 그대로 승계)**: TC-019에서 확인했듯 `BlogPostPage.serve()`의 안전성은 "현재 Site가 1개뿐이라 상대경로가 반환된다"는 현재 상태에 암묵적으로 의존한다. Site가 늘거나 `Site.find_for_request()`의 판정이 요청과 어긋나는 상황이 되면 `get_url()`이 절대 URL(및 `Site.hostname="localhost"`)을 반환할 가능성이 이론적으로 남아 있다 — 이번 단위테스트는 이 조건을 물리적으로 재현할 수 없었다(현재 인프라에 Site가 1개만 존재). 10단계(배포테스트)/11단계(운영 Runbook)에서 "Site.hostname을 운영 도메인으로 갱신하는 절차"를 도입할 때 이 리다이렉트도 함께 재검증할 것을 권고(unit-05-note.md §7-1의 권고를 그대로 승계).
- robots.txt 스핀다운 가로채기(§2 제외 범위) — 10단계 실측 대상, 기존 리스크 그대로 유지.
- 외부 도구(Facebook/Twitter 디버거, Search Console) 기반 검증 미수행 — 10단계 이후 실제 배포 도메인 확보 시 수행 권고.
- NewsletterSubscribeForm/이메일 채널(REQ-016)은 WU-07 미구현 — `CONTENT_GUIDE.md`의 "준비 중" 안내는 WU-07 완료 시 갱신 필요(unit-05-note.md §7-4 승계).

## 8. 결론 및 판정
- [x] **PASS** — 다음 단계(07 업무단위 통합테스트) 진행 가능
- 판정 근거: AC1~18(18/18) 독립 재현 PASS, 오케스트레이터 지시 4대 핵심 확인 사항 전부 실측 PASS(특히 WU-04 `serve()`의 Site.hostname 의존 문제는 이번 production 유사 HTTPS 환경 재현 시도에서 **결함이 재현되지 않아 규칙F에 따른 WU-04 단계 회귀는 불필요**하다고 판단함 — 근거는 §6/TC-019), 결함 0건, 게이트1/2 독립 재확인 통과.
- **규칙F 판단 명시(오케스트레이터 요청 사항)**: WU-04 `BlogPostPage.serve()`에 대해 "동일한 Site.hostname 메커니즘에 의존하는지"와 "production 유사 HTTPS 환경에서 실제로 올바른 URL로 리다이렉트되는지"를 직접 코드 확인 + 실제 요청(2가지 트래픽 형태)으로 검증한 결과, **localhost나 잘못된 스킴/호스트로의 리다이렉트는 재현되지 않았다.** 따라서 이번 06단계 판단으로는 WU-04로의 재작업 요청(규칙F)이 **불필요**하다. 다만 그 안전성이 "Site가 1개뿐"이라는 현재 상태에 암묵적으로 의존하는 구조적 특성이라는 점은 결함이 아니라 잔존 리스크(§7)로 정직하게 남긴다 — unit-05-note.md §7-1이 이미 이 리스크를 문서화해 둔 것과 일치하며, 이번 06단계가 "실측으로 결함을 찾지 못했다"는 사실이 "리스크 자체가 사라졌다"는 뜻은 아니라는 점을 다음 단계(07단계, WU-01~04 조립 검증) 담당자가 오인하지 않도록 분명히 남긴다.

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자 관점 자가 재검토 — AC1~18과 TC-001~018의 1:1 매핑 완결성, 오케스트레이터 지시 4대 사항이 TC-006/007/011/012/015/019로 실제로 커버되는지, "실제 결과" 컬럼이 전부 이번 세션 실행 근거인지(05단계 보고 인용 없음) 확인. 결함 0건.
- 2차 검증 결과 요약: "07단계에 이 결과서를 그대로 넘겨도 되는가"를 의심하는 독립 심사자 관점 — TC-013/TC-019(B)의 최초 이상 징후를 테스트 결함으로 성급히 단정하지 않고 대조군(Host 헤더 유무)으로 재검증했는지, TC-019의 PASS 판정이 "결함이 없다"가 아니라 "이번 조건에서는 재현되지 않았다"로 정확히 좁혀 기술됐는지, §7 잔존 리스크가 §8 결론에서 축소·은폐되지 않았는지 재확인. 결함 0건.
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-05-test.md`
