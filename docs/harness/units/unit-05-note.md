# WU-05 — SEO 기본 구현 + AI 검색 대응 콘텐츠 가이드라인 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-05, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §4 API/라우트 계약·REQ-005 JSON-LD 구현 방침), `docs/harness/04-ux-design.md`(PASS, §5 접근성), `docs/harness/decisions.md`(DEC-001~018, 특히 DEC-016 최소 앱 신설 선례·DEC-017 정규 URL 설계·DEC-018 WU-04/05 경계), `docs/harness/01-trend-analysis.md`(§2-3, §8 AI 검색 트래픽 감소 근거), `docs/harness/02-planning.md`(§4 REQ-005/017, §9 WU-05 정의), `docs/harness/units/unit-01~04-note.md`
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-005(SEO 기본요소), REQ-017(AI 검색 대응 콘텐츠/트래픽 전략)

---

## 1. 구현 범위

WU-01(골격)·WU-02(BlogPostPage/Category/Tag)·WU-03(CustomImage)·WU-04(공개 화면/RSS) 위에, SEO 기본 요소와 AI 검색 대응 가이드를 구현했다. `docs/harness/units/unit-04-note.md`(DEC-018)가 "REQ-005(JSON-LD 포함)는 WU-05로 이연"이라고 명시한 부분을 이번에 실제로 채웠다.

```
webapp/
  core/                             (신규 앱, DEC-019)
    apps.py                         CoreConfig
    context_processors.py           canonical_url (REQ-005)
    seo.py                          absolute_page_url (Site.hostname 비의존 절대 URL, DEC-021)
    views.py                        robots_txt (REQ-005)
    urls.py                         /robots.txt
    templatetags/seo_tags.py        jsonld 필터(JSON-LD 안전 직렬화)
  blog/
    urls.py                         (수정) /sitemap.xml (wagtail.contrib.sitemaps 표준 뷰)
    models.py                       (수정) BlogPostPage.get_json_ld/get_faq_json_ld/get_sitemap_urls
    views.py                        (수정) post_detail — json_ld/faq_json_ld/og_image 컨텍스트 추가
    blocks.py                       (수정) FAQItemBlock에 REQ-017 안내 help_text 추가
    templates/blog/blog_post_page.html (수정) og_type/twitter_card/og_image/extra_head(JSON-LD) 블록,
                                      다중 라인 주석을 {% comment %}로 교체(§3 발견·수정)
  home/
    models.py                       (수정) HomePage.get_sitemap_urls (DEC-021)
  config/
    settings/base.py                (수정) INSTALLED_APPS(core/wagtail.contrib.sitemaps/
                                      django.contrib.sitemaps), TEMPLATES context_processors
    urls.py                         (수정) core.urls include
    templates/base.html             (수정) canonical, RSS <link rel="alternate">,
                                      Open Graph/Twitter Card 메타태그, extra_head 블록
  CONTENT_GUIDE.md                  (신규) 운영자용 AI 검색 대응 콘텐츠 가이드(REQ-017)
docs/harness/decisions.md           DEC-019~021 추가
docs/harness/traceability.md        REQ-005/017 행 갱신
```

### 1.1 기본 SEO — REQ-005

- **`<title>`/meta description**: Wagtail `Page` 모델이 표준으로 제공하는 `seo_title`/`search_description`(promote_panels) 필드를 그대로 사용한다 — 이 필드들은 이미 WU-01의 `base.html`에 연결되어 있었으므로(코드 조사로 확인), 새로 만들 것은 없고 검증만 했다(§3). `search_description`이 비어 있으면 `BlogPostPage.intro`(WU-02가 만든 요약 필드)로 폴백하도록 보강했다.
- **Open Graph/Twitter Card**: `base.html`에 `og:type`/`og:title`/`og:description`/`og:url`/`og:site_name`/`og:image`(대표이미지가 있을 때만)와 `twitter:card`/`twitter:title`/`twitter:description`/`twitter:image`를 추가했다. title/description은 `<title>`/meta description과 같은 소스(page.seo_title/search_description)를 그대로 다시 읽어 값이 어긋나지 않게 했다(§2-1 참고 — 최초에는 `{% block title %}` 재사용을 시도했으나 Django가 허용하지 않아 직접 표현식 재사용으로 전환했다).
- **canonical URL**: `core/context_processors.py::canonical_url`이 모든 요청에 `request.build_absolute_uri()`(쿼리스트링 포함, 페이지네이션 자기참조 canonical)를 제공한다. DEC-017(트리 URL→정규 URL 301 리다이렉트)에 의해 템플릿이 렌더링되는 시점의 `request.path`는 항상 이미 정규 URL이므로, canonical이 항상 정식 URL을 가리킨다는 것을 로컬 검증(§3)으로 확인했다.
- **sitemap.xml**: `wagtail.contrib.sitemaps` 표준 뷰(03 §4 지시대로)를 `blog/urls.py`에 `/sitemap.xml`로 마운트했다. `INSTALLED_APPS`에 `wagtail.contrib.sitemaps`와 `django.contrib.sitemaps`를 추가해야 했다(추가하지 않으면 `TemplateDoesNotExist: sitemap.xml` — §3에서 실제로 재현·해결).
- **robots.txt**: `core/views.py::robots_txt`가 `Disallow: /cms-admin/`, `Disallow: /django-admin/`, `Allow: /`, `Sitemap: <절대 URL>`을 반환한다. 03 §6.3/§8이 이미 기록한 "Render 스핀다운 중 플랫폼이 robots.txt를 가로채 disallow-all로 응답"하는 리스크는 애플리케이션 코드로 해결할 수 없는 플랫폼 제약이라 그대로 유지하고(10단계 실측 대상), 이번 WU는 "정상 기동 중" 응답만 책임진다.

### 1.2 구조화 데이터(JSON-LD) — REQ-005

- `BlogPostPage.get_json_ld(request)`가 03 §4 필드 매핑(headline/datePublished/dateModified/image/author/mainEntityOfPage)을 그대로 구현한 `schema.org/BlogPosting` dict를 반환한다. `blog_post_page.html`의 `extra_head` 블록이 이를 `<script type="application/ld+json">`으로 렌더링한다.
- **JSON-LD 렌더링 안전성**: 03 §4는 "Django 템플릿의 기본 auto-escape만으로 충분하다"고 명시했지만, 이는 XSS 방지 관점(값 자체가 신뢰됨)이지 "HTML auto-escape를 JSON 문자열 안에 그대로 써도 된다"는 뜻은 아니다 — auto-escape가 `"`를 `&quot;`로 바꾸면 JSON 문자열 구분자 자체가 깨진다. `core/templatetags/seo_tags.py::jsonld` 필터가 `json.dumps` + 최소 이스케이프(`<`/`>`/`&`만, Django 내장 `json_script`와 동일 전략)로 안전하게 직렬화한다. 실제로 따옴표/HTML 태그/앰퍼샌드가 섞인 제목·FAQ 답변으로 렌더링해 `json.loads`로 파싱까지 성공함을 확인했다(§3).
- **FAQPage JSON-LD(REQ-017)**: `BlogPostPage.get_faq_json_ld()`가 본문 StreamField의 `faq` 블록에서 질문/답변을 모아 `schema.org/FAQPage`를 별도 `<script>` 태그로 반환한다(03 §4 "선택적으로 추가할 수 있도록 템플릿 블록을 분리"를 BlogPosting과 별개의 JSON-LD 객체로 구현). 답변은 `strip_tags` + `html.unescape`로 순수 텍스트화하고, 질문/답변 중 하나라도 비어 있으면 그 항목을 제외한다(모두 비면 스크립트 자체를 생략).
- **author 대체값(DEC-020)**: SiteSettings 모델이 아직 없어(§2-2), `owner` → `Site.site_name` → `settings.WAGTAIL_SITE_NAME` 순서로 대체한다.
- **canonical/sitemap의 Site.hostname 의존성 제거(DEC-021)**: Wagtail `get_full_url()`/기본 `get_sitemap_urls()`는 등록된 Wagtail `Site`의 hostname을 기준으로 절대 URL을 만드는데, 이 프로젝트의 기본 Site는 `hostname="localhost"`로 고정되어 있고 이를 운영 도메인으로 갱신하는 절차가 아직 없다(§2-3). 이 상태를 그대로 두면 `sitemap.xml`/JSON-LD `mainEntityOfPage`가 실제 도메인과 무관한 URL을 낼 수 있음을 로컬에서 직접 재현했다. `core/seo.py::absolute_page_url(page, request)`(요청 기반 절대 URL)로 대체해 `BlogPostPage`/`HomePage`의 `get_sitemap_urls()`를 오버라이드했다.

### 1.3 AI 검색 시대 대응 — REQ-017

- **질문-답변형 콘텐츠 가이드**: `webapp/CONTENT_GUIDE.md`(신규) — 소제목을 질문형으로 쓰기, 답을 먼저 제시하기, FAQ 블록 활용법, SEO 필드(Promote 탭) 작성법, RSS/이메일 채널 이중화 안내를 담았다. 전부 권장 사항이며 강제하지 않는다(문서 자체가 그렇게 명시).
- **템플릿 수준 지원**: `blog/blocks.py`의 `FAQItemBlock.question`/`answer`에 안내형 `help_text`를 추가해, Wagtail 어드민 편집 화면에서 직접 가이드를 보여준다(가이드 문서를 열지 않아도 최소한의 방향은 화면에서 안내됨).
- **RSS/이메일 채널 이중화**: RSS는 WU-04가 이미 구현했으므로, 이번 WU는 SEO/디스커버리 관점에서 `<link rel="alternate" type="application/rss+xml">`을 모든 페이지의 `<head>`에 명시적으로 노출했다(`base.html`). 이메일(REQ-016)은 WU-07 미구현이라 가이드 문서에 "준비 중" 안내만 포함했다(실제 폼을 만들지 않음 — DEC-018과 동일한 경계 원칙 유지).

### 1.4 접근성/시맨틱 HTML 재확인 — 요청 항목 4

WU-04가 구현한 `header`/`nav`/`main`/`footer` 랜드마크와 페이지당 단일 H1 구조(`base.html`/`blog_post_page.html`/`home_page.html`)를 코드로 다시 확인했다. 이번 WU는 `<head>` 영역(메타태그/JSON-LD)만 추가했고 `<body>` 마크업은 건드리지 않았으므로, 접근성 구조에 변경이 없다 — 재확인만 하고 별도 조치는 하지 않았다.

---

## 2. 설계서 대비 편차 (사유 포함)

1. **`SiteSettings` 모델을 만들지 않음(DEC-020)** — 03 §4가 JSON-LD author 대체값으로 언급한 필드이지만, 그 모델은 03 §1.2가 REQ-011/012 담당 `core` 앱 몫으로 지정했다. 이번 WU가 REQ-005만 구현하면서 아직 필요 없는 모델을 앞서 만드는 것은 범위 확장이라 판단해, `Site.site_name`→`WAGTAIL_SITE_NAME` 2단계 대체로 충족했다.
2. **`core` 앱을 이번 WU가 먼저 신설함(DEC-019)** — DEC-016(WU-03의 `custom_images` 신설 선례)을 그대로 따랐다. 헬스체크/SiteSettings/콜드스타트 뷰(REQ-011/012)는 담당 WU가 같은 앱에 이어서 채우도록 앱 docstring에 명시했다.
3. **`sitemap.xml`/JSON-LD의 절대 URL을 Wagtail 기본 `get_full_url()`이 아닌 요청 기반으로 오버라이드함(DEC-021)** — 로컬 검증 중 실제로 `http://localhost/...` URL이 sitemap에 나오는 결함을 재현했다(§3). 03 §4는 "표준 프레임워크 활용"만 명시했으므로 프레임워크 자체(`wagtail.contrib.sitemaps`)는 그대로 쓰되, 그 URL 계산 방식만 페이지 모델 오버라이드로 보정했다 — 이는 "REQ-005가 실제로 올바르게 동작하는가"를 검증하다 발견한 결함의 근본 원인 수정이지, 설계를 재해석한 것이 아니다.
4. **WU-04의 `BlogPostPage.serve()`(DEC-017 트리 URL 리다이렉트)는 손대지 않음** — 이 메서드도 이론상 같은 Site.hostname 의존 메서드(`get_url()`)를 쓰고 있어 잠재적으로 같은 위험군에 속하지만, 그 코드는 WU-04 소유이고 이번 작업 지시(REQ-005/017)에 포함되지 않는다. 범위 외 변경 금지 원칙에 따라 수정하지 않고, 아래 §7(수동 확인 필요)에 후속 확인 사항으로 남겼다.
5. **템플릿 `{% block %}` 이름 재사용 시도를 철회함** — og:title/twitter:title을 `<title>`과 같은 값으로 자동 동기화하려고 `{% block title %}`을 base.html에서 두 번 썼는데, Django가 "같은 이름의 block은 한 템플릿에 한 번만 정의 가능"이라는 것을 로컬 검증에서 `TemplateSyntaxError`로 직접 확인했다(§3). 블록 재사용 대신 동일한 표현식(`page.seo_title`/`page.title` 폴백)을 필요한 곳마다 직접 반복하는 방식으로 전환했다 — category/tag 목록처럼 `page` 객체가 없는 화면은 og:title/twitter:title이 비지만, 대부분의 OG/Twitter 파서가 `<title>` 태그로 자동 폴백하므로 기능적으로 문제가 없다고 판단했다(기능상 가장 중요한 게시물 상세/홈은 정상적으로 채워짐).

---

## 3. 로컬 동작 확인 (실제 실행 결과, 발견·수정한 결함 포함)

임시 venv(`webapp/.venv_wu05`, 검증 후 삭제)에서 `pip install -r requirements.txt`(WU-01~04와 동일 버전, 신규 패키지 없음) 후 실행했다. **검증 과정에서 4건의 실제 결함을 발견·수정했다** (아래 순서대로) — 모두 "만들고 나서 실행해보지 않았다면 놓쳤을" 종류다.

### 3-1. 발견·수정한 결함

1. **`TemplateSyntaxError`(WU-04 DEF-001과 동일 계열)**: `blog_post_page.html` 상단에 쓴 다중 라인 `{# ... #}` 주석 안에 예시로 적은 리터럴 `{% if %}` 문구가 실제 블록 태그로 파싱되어 렌더링이 깨졌다. `{% comment %}...{% endcomment %}`로 교체하고, 그 설명 안에서도 리터럴 중괄호 태그 문법(`{% endcomment %}` 등)을 다시 쓰지 않도록 재작성했다(처음 수정에서 또 같은 함정에 걸려 두 번째로 고쳤다 — 재현 로그는 아래 3-2 참고).
2. **`django.contrib.sitemaps`/`wagtail.contrib.sitemaps` 미등록으로 `TemplateDoesNotExist: sitemap.xml`**: `INSTALLED_APPS`에 두 앱을 추가해 해소.
3. **Django `{% block %}` 이름 중복 정의로 `TemplateSyntaxError`**: og:title/twitter:title에 `{% block title %}`을 재사용하려다 발생. §2-5 편차 참고, 직접 표현식으로 전환.
4. **sitemap.xml/JSON-LD가 `http://localhost/...`를 반환(Site.hostname 의존)**: production 유사 설정 + `Client(SERVER_NAME="example.com")` HTTPS 요청으로 재현. `core/seo.py::absolute_page_url` 도입으로 해소(DEC-021).

### 3-2. 재현 로그 요약 (스크래치패드 임시 스크립트로 실행 후 삭제)

- `manage.py check`/`migrate`(빈 SQLite, 처음부터)/`makemigrations --check --dry-run`("No changes detected" — 이번 WU는 모델 스키마를 바꾸지 않음, `core` 앱은 모델이 없어 마이그레이션 없음) 전부 정상.
- `django.test.Client` 기반 스모크 테스트 41건 작성 후 전부 PASS(위 결함 4건을 고치는 과정에서 여러 차례 재실행):
  - `GET /sitemap.xml` → 200, 발행 게시물의 정규 URL(`/blog/<slug>/`) 포함, 트리 URL 미포함.
  - `GET /robots.txt` → 200, `Content-Type: text/plain`, `Disallow: /cms-admin/` 포함, `Sitemap: http://testserver/sitemap.xml` 포함.
  - `GET /blog/<slug>/`: `<title>`에 게시물 제목, `<meta name="description">`에 intro, `<link rel="canonical" href="http://testserver/blog/<slug>/" />`, `og:type=article`, `og:url`이 canonical과 일치, `og:image`(대표이미지 있을 때), `twitter:card=summary_large_image`(이미지 있을 때), `<link rel="alternate" type="application/rss+xml">` 전부 확인.
  - JSON-LD `<script type="application/ld+json">` 정확히 2개(BlogPosting/FAQPage), 둘 다 `json.loads`로 파싱 성공(구문 오류 없음). `headline`이 제목(`<`/`>`/`&`/`"` 포함)과 정확히 일치, `mainEntityOfPage.@id`가 canonical_url과 정확히 일치, `image`가 절대 URL, `author`가 owner 없을 때 Organization(`site_name` 폴백)으로 채워짐. FAQPage는 빈 답변 항목이 제외되고, 답변 텍스트가 태그 제거+HTML 엔티티 디코딩까지 된 순수 텍스트임을 확인.
  - 제목/따옴표/HTML 태그가 섞인 문자열로도 `</script>` 조기 종료 없음(`html.count("<script") == html.count("</script>")`) 확인 — WU-04의 500.html 사고를 반면교사 삼아 명시적으로 검증한 항목.
  - `/category/<slug>/`, `/tag/<slug>/`, `/`(홈): 200, canonical 정상, category/tag는 og:title이 `{% block title %}` 오버라이드 값과 일치.
  - 페이지네이션: 게시물 12건 생성 후 `GET /?page=2` → canonical이 `?page=2`를 포함(자기참조 canonical, 1페이지로 뭉개지지 않음).
  - 회귀: `GET /cms-admin/login/` → 200.
- **production 유사 설정 검증**(`config/settings/it_test_prodlike_wu05.py` — WU-01~04와 동일 방법론, `production.py` 상속 + `DATABASES`만 SQLite, 더미 R2/`SECRET_KEY`/`DJANGO_ALLOWED_HOSTS` 환경변수, 검증 후 삭제): `manage.py check`/`migrate`/`makemigrations --check --dry-run`/`collectstatic --noinput`("216 static files copied ... 632 post-processed" — WU-04와 동일 수치, 회귀 없음) 전부 정상. `Client(SERVER_NAME="example.com")`로 HTTPS 요청 8건 전부 PASS: 게시물 상세 200(무한 리다이렉트 회귀 없음, DEC-015 재확인), canonical/og:url이 `https://example.com/...`, `sitemap.xml`이 `https://example.com/...` URL(결함 4 수정 후 정상), `robots.txt`의 Sitemap 줄도 `https://`, `X-Forwarded-Proto: https` 헤더 형태(실제 Render 트래픽 형태) 요청도 200(무한루프 없음).

### 3-3. 정리

검증에 쓴 `.venv_wu05`, `db.sqlite3`, `db_prodlike_wu05.sqlite3`, `media/`, `staticfiles/`, `config/settings/it_test_prodlike_wu05.py`, 임시 검증 스크립트(스크래치패드 경로 2개) 전부 삭제했다. 추가로 재확인용 `.venv_wu05_final`(clean 재설치 검증)도 삭제했다. `git status --porcelain -- webapp docs/harness`로 소스/문서 diff만 남았음을 최종 확인했다(venv/db/media/staticfiles/`__pycache__` 없음).

**로컬에서 확인하지 못한 것**: 실제 브라우저에서 OG/Twitter 카드 미리보기 렌더링(Facebook/Twitter 디버거 등 외부 도구), 실제 Google Search Console에 sitemap.xml 제출 후 색인 반응은 MCP 미연동(DEC-001)과 실제 배포 도메인 부재로 이번 WU에서 수행하지 못했다 — 10단계(배포테스트) 이후 실측 권고.

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 이번에도 재확인**했다(직접 검색, WU-01~04와 동일 결론) — 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 Python 파일 전체(`core/__init__.py`, `core/apps.py`, `core/context_processors.py`, `core/views.py`, `core/urls.py`, `core/seo.py`, `core/templatetags/__init__.py`, `core/templatetags/seo_tags.py`, `blog/models.py`, `blog/views.py`, `blog/blocks.py`, `blog/urls.py`, `home/models.py`, `config/urls.py`, `config/settings/base.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다(clean venv로 재설치 후 마지막에 한 번 더 재확인, §3-3). Django/HTML 템플릿 린터도 저장소에 없어, `manage.py check`/실제 렌더링(§3)으로 구문·참조 오류가 없음을 실행 기반으로 확인했다 — 특히 이 과정에서 실제 `TemplateSyntaxError` 2건을 찾아 고쳤다(§3-1).

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 5건은 전부 사유와 함께 명시했고, 모두 "설계서가 구체 방법을 명시하지 않은 부분에 대한 합리적 구현 선택" 또는 "실제로 검증하다 발견한 결함의 근본 원인 수정"이지 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — `get_json_ld`/`get_faq_json_ld`는 `first_published_at`/`last_published_at`/`featured_image`/`owner`가 없을 수 있는 상황을 전부 `if`로 분기해 처리한다(예외를 삼키는 `try/except`가 아니라 애초에 예외가 나지 않게 값 존재를 확인). FAQ 블록의 빈 질문/답변은 조용히 건너뛰되(스팸이 아니라 데이터 불완전 상태이므로 결과에서 제외하는 것이 맞는 처리), 로그를 남기거나 예외를 숨기지 않는다. `robots_txt` 뷰는 사용자 입력을 받지 않아 검증할 입력이 없다.
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 이번 WU가 새로 여는 시스템 경계는 없다(sitemap.xml/robots.txt는 GET 전용, 파라미터 없음). JSON-LD에 들어가는 값은 전부 운영자가 Wagtail 어드민에서 입력한 신뢰된 콘텐츠(제목/FAQ/이미지)이며, 03 §4가 명시한 대로 별도 새니타이즈 라이브러리 없이 안전 직렬화(§1.2)로 처리한다.
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 이번 변경분은 뷰/템플릿/모델 메서드/설정 등록만 다루고 시크릿이 필요한 코드가 없다. 검증용 production 유사 설정 모듈은 전부 환경변수로만 값을 주입했고 삭제까지 완료했다(§3-3).
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — WU-04의 `BlogPostPage.serve()`/`get_url_parts()`(DEC-017)는 같은 파일(`blog/models.py`) 안에 있지만 손대지 않았다(§2-4에 후속 확인 사항으로만 기록). `custom_images/`(WU-03), `home/models.py`의 `get_context`/`serve`(WU-04)도 그대로 유지했다. `500.html`/`404.html`(WU-04 소유)은 건드리지 않았다.

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-005/REQ-017 행을 갱신했다: "작업 단위"는 이미 WU-05로 채워져 있었고, "구현 상태"를 "Not Started" → "구현 완료"(구현 근거 파일 경로 포함)로, "단위테스트"를 "대기(6단계)"로 채웠다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다.

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **Wagtail `Site.hostname` 운영 도메인 미설정(구조적 리스크, DEC-021)**: 이 프로젝트의 초기 마이그레이션이 만드는 기본 Wagtail Site는 `hostname="localhost"`로 고정되어 있고, 이를 실제 운영 도메인으로 갱신하는 절차가 어떤 WU에도 없다. 이번 WU는 `sitemap.xml`/JSON-LD의 URL 계산을 요청 기반으로 바꿔 이 문제를 우회했지만(`core/seo.py`), **WU-04의 `BlogPostPage.serve()`(DEC-017 트리 URL→정규 URL 301 리다이렉트)는 여전히 `get_url()`(Site.hostname 의존 가능)을 쓴다** — Site가 여러 개로 늘거나 hostname 불일치가 실제로 발생하는 상황이면 그 리다이렉트도 잘못된 도메인으로 나갈 이론적 가능성이 있다(이번 WU의 로컬 검증 범위에서는 재현되지 않음 — 단일 사이트에서는 `get_url()`이 상대 경로를 반환하기 때문). 배포 전(10단계) 또는 운영자 인수인계(11단계) 시 Wagtail 어드민에서 Site의 hostname/포트를 실제 운영 도메인으로 갱신하는 절차를 Runbook에 추가할 것을 권고한다.
2. **robots.txt 스핀다운 가로채기(기존 리스크, 03 §6.3 — 이번 WU 신규 아님)**: Render가 스핀다운 상태일 때 애플리케이션 코드가 실행되기 전에 플랫폼이 robots.txt를 "disallow all"로 가로챈다. 애플리케이션 코드로 해결 불가능하며, 10단계(배포테스트)에서 실측 확인이 필요하다.
3. **외부 도구 기반 검증 미수행**: Facebook 공유 디버거/Twitter Card Validator로 실제 OG/Twitter 카드 미리보기 확인, Google Search Console에 sitemap.xml 제출 후 실제 색인 반응 확인은 MCP 미연동(DEC-001) + 실제 공개 도메인 부재로 이번 WU에서 수행하지 못했다. 10단계 이후 실제 배포 도메인이 생기면 수행 권고.
4. **NewsletterSubscribeForm 미구현 상태에서의 가이드 문서 내용**: `CONTENT_GUIDE.md` §5는 이메일 채널을 "준비 중"으로 안내한다 — WU-07이 실제로 구현되면 이 문서도 함께 갱신할 것을 권고(이번 WU 범위 밖이라 트리거만 남김).
5. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(WU-01~04와 동일하게, 사용자/오케스트레이터의 명시적 커밋 지시를 기다림). 원격 push는 수행하지 않았다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일). **주의**: 공개 목록/상세 뷰는 WU-04부터 `@cache_page(10분)`로 캐시되므로(unit-04-note.md §7-3과 동일), 데이터를 바꾼 뒤 즉시 재요청해 검증하려면 매 시나리오 전에 `from django.core.cache import cache; cache.clear()`를 실행하거나 프로세스를 재시작할 것.

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, WU-01~04와 동일 버전).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `python manage.py migrate`가 빈 DB에서 처음부터 오류 없이 끝나는가.
3. `python manage.py check`가 "System check identified no issues"를 출력하는가.
4. `python manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가(이번 WU는 모델 스키마를 바꾸지 않음, `core` 앱은 모델이 없음).
5. Category·`CustomImage`를 준비하고 `HomePage.add_child()`로 대표이미지 포함 `BlogPostPage`를 생성해 본문에 FAQ 블록(질문/답변 2개 이상, 그중 하나는 답변을 비워둠)을 포함한 뒤 `save_revision().publish()`한다.
6. `GET /blog/<slug>/` → 200이고 응답 HTML에 다음이 전부 포함되는가:
   - `<title>`에 게시물 제목
   - `<meta name="description" content="...">`(search_description 또는 intro)
   - `<link rel="canonical" href="http://<host>/blog/<slug>/" />`(요청에 사용한 host와 정확히 일치)
   - `<meta property="og:type" content="article">`
   - `<meta property="og:url" content="...">`가 canonical과 정확히 같은 값
   - `<meta property="og:image" ...>`/`<meta name="twitter:image" ...>`(대표이미지 등록 시)
   - `<meta name="twitter:card" content="summary_large_image">`(대표이미지 등록 시)
   - `<link rel="alternate" type="application/rss+xml" ... href="/feed.xml">`
7. 위 응답에서 `<script type="application/ld+json">` 태그가 정확히 2개(BlogPosting, FAQPage) 존재하고, **각각을 정규식 등으로 추출해 `json.loads()`로 파싱했을 때 예외 없이 성공**하는가(구문 오류 없음이 핵심 인수 조건 — WU-04 500.html 사고 반면교사).
8. 파싱한 BlogPosting JSON-LD에 대해: `headline`이 게시물 제목과 정확히 일치, `datePublished`/`dateModified`가 ISO 8601 형식으로 존재, `mainEntityOfPage.@id`가 6번의 canonical 값과 정확히 일치, `image`가 `http(s)://`로 시작하는 절대 URL, `author`가 존재하는가(owner 미설정 시 `@type: Organization`).
9. 파싱한 FAQPage JSON-LD에 대해: `mainEntity` 배열의 개수가 "답변을 채운 질문" 개수와 일치(빈 답변 항목은 제외되는가), 각 `acceptedAnswer.text`에 HTML 태그(`<`, `>`)나 `&amp;` 같은 미해석 엔티티가 남아있지 않은가(순수 텍스트).
10. 게시물 제목이나 FAQ 답변에 `<`, `>`, `&`, `"` 같은 특수문자를 포함시켜도(예: `제목 <테스트> & "인용"`) 페이지가 500 없이 200으로 렌더링되고, `<script` 개수와 `</script>` 개수가 정확히 같은가(스크립트 태그가 중간에 깨지지 않음).
11. `GET /sitemap.xml` → 200이고, 응답 본문에 6번 게시물의 정규 URL(`/blog/<slug>/`)이 포함되며 트리 URL(`/<slug>/`) 형태는 포함되지 않는가. **요청 시 사용한 host(예: `SERVER_NAME`)와 일치하는 도메인**으로 `<loc>`이 나오는가(`localhost`로 고정되어 나오면 결함).
12. `GET /robots.txt` → 200, `Content-Type`이 `text/plain`로 시작, 본문에 `Disallow: /cms-admin/`과 `Sitemap: http(s)://<host>/sitemap.xml`(11번과 같은 host)이 포함되는가.
13. `GET /category/<slug>/`, `GET /tag/<slug>/`, `GET /`(홈) 각각에서 `<link rel="canonical" ...>`이 해당 페이지의 실제 요청 경로와 일치하는가.
14. 발행된 게시물을 11건 이상 만들고 `GET /?page=2`로 요청하면 canonical이 `?page=2`를 포함하는 자기 자신의 URL을 가리키는가(1페이지 URL로 뭉개지지 않음).
15. (production 유사) `production.py`를 상속하고 `DATABASES`만 SQLite로 재정의한 설정 모듈로 더미 R2 환경변수를 채운 뒤, `Client(SERVER_NAME="example.com")`로 `secure=True` 요청을 보내 6·11·12번을 다시 확인 — 이번엔 canonical/sitemap/robots.txt의 Sitemap 줄이 전부 `https://example.com/...`로 나오는가(무한 리다이렉트 없이 200, DEC-015 회귀 없음도 함께 확인).
16. `python manage.py collectstatic --noinput`(dev)이 오류 없이 끝나는가(이번 WU는 신규 정적 자산을 추가하지 않았으므로 파일 수는 WU-04와 동일해야 함).
17. `GET /cms-admin/login/`(비로그인) → 200인가(회귀).
18. 검증 후 사용한 venv/DB(`db.sqlite3` 등)/staticfiles/media/임시 설정 모듈/임시 스크립트를 정리했는지, diff에 포함되지 않았는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~18번 인수 조건을 입력으로 `docs/harness/units/unit-05-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-05)의 7단계(통합테스트, WU-01~04와의 조립 검증 포함 — 특히 §7-1의 Site.hostname 리스크가 DEC-017 리다이렉트에 실제로 영향을 주는지 재확인 권고)와 다음 WU(WU-06) 착수 여부를 오케스트레이터가 판단한다.
