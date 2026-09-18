# WU-04 — 공개 열람 화면(목록/상세/카테고리/태그/RSS/반응형 레이아웃) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-04, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §4 API/라우트 계약), `docs/harness/04-ux-design.md`(v1.2, PASS, 화면 S-01~S-04/S-08/S-09, §3 디자인 토큰, §4 컴포넌트, §5 접근성, §6 반응형, §7 정합성 체크), `docs/harness/decisions.md`(DEC-001~016), `docs/harness/units/unit-01-note.md`(base.html/tokens.css/base.css/404·500 골격), `docs/harness/units/unit-02-note.md`(BlogPostPage/blocks.py, 템플릿 미작성 명시), `docs/harness/units/unit-03-note.md`(CustomImage 렌디션), `docs/harness/feature-WU-03-integration-test.md`(IT-E2E7, srcset 데이터 흐름 검증 완료·WU-04로 인계)
- 작성일: 2026-09-16
- 대상 REQ-ID: REQ-003(콘텐츠 공개 목록/상세 뷰), REQ-004(RSS 피드), REQ-014(반응형 기본 레이아웃/접근성)

---

## 1. 구현 범위

WU-01(골격)·WU-02(BlogPostPage/Category/Tag)·WU-03(CustomImage 렌디션) 위에, 방문자용 공개 화면(S-01/S-02/S-03/S-04/S-08/S-09)과 그 전역 컴포넌트(Header/Footer/Pagination/Breadcrumb/PostCard/CategoryBadge/TagChip/EmptyState/Button/SkipLink/ArticleBody/RSSIconLink/CookieConsentBanner)를 구현했다. S-05~S-07(법적 페이지, WU-06)과 NewsletterSubscribeForm(REQ-016, WU-07)·JSON-LD(REQ-005, WU-05)는 지시받은 범위 밖이라 만들지 않았다(§2-2, DEC-018).

```
webapp/
  blog/
    constants.py                     (신규) POSTS_PER_PAGE, VIEW_CACHE_SECONDS
    pagination.py                    (신규) 목록 공용 페이지네이션 헬퍼
    context_processors.py            (신규) 헤더 nav_categories 전역 컨텍스트
    views.py                         (신규) post_detail/category_list/tag_list (S-02~S-04)
    feeds.py                         (신규) LatestPostsFeed (REQ-004, /feed.xml)
    urls.py                          (신규) /blog/<slug>/, /category/<slug>/, /tag/<slug>/, /feed.xml
    models.py                        (수정) BlogPostPage.published()/get_url_parts()/serve() 추가
    blocks.py                        (수정) ImageBlock/QuoteBlock/FAQBlock에 template Meta 추가
    templates/blog/
      blog_post_page.html            (신규) S-02 상세 (정규 뷰 + Wagtail 미리보기 공용)
      category_list.html             (신규) S-03
      tag_list.html                  (신규) S-04
      blocks/image_block.html        (신규) ArticleBody 이미지 블록(srcset)
      blocks/quote_block.html        (신규) ArticleBody 인용 블록
      blocks/faq_block.html          (신규) ArticleBody FAQ 블록
      partials/_post_list.html       (신규) 목록+페이지네이션+빈상태 공용(S-01/S-03/S-04가 재사용)
      partials/_post_card.html       (신규) PostCard(srcset, 이미지 없음 플레이스홀더)
      partials/_pagination.html      (신규) Pagination 컴포넌트
  home/
    models.py                        (수정) HomePage.get_context()(S-01 목록) + serve() 뷰 캐시
    templates/home/home_page.html    (재작성) S-01 홈
  config/
    urls.py                          (수정) blog.urls를 wagtail_urls catch-all보다 먼저 include
    settings/base.py                 (수정) TEMPLATES context_processors에 nav_categories 추가
    templates/
      base.html                      (수정) components.css/nav.js 연결, header/footer 블록 기본값을 partials include로
      partials/header.html           (신규) Header/Nav(카테고리, RSS, 모바일 드로어)
      partials/footer.html           (신규) Footer(법적 링크 3종, RSS, 콜드스타트 안내, 저작권)
      404.html                       (수정) 토큰 기반 스타일 적용, 홈 CTA (S-08)
      500.html                       (수정) 토큰 기반 인라인 스타일 정교화, 새로고침/홈 CTA (S-09, base.html 미상속 유지)
    static/
      css/components.css             (신규) 04 §4 컴포넌트 17종 중 이 화면 대상 스타일
      js/nav.js                      (신규) 모바일 내비 드로어 포커스 관리(점진적 향상)
docs/harness/decisions.md            DEC-017(URL 라우팅 설계), DEC-018(컴포넌트 범위 경계) 추가
docs/harness/traceability.md         REQ-003/004/014 행 갱신
```

### 1.1 목록/상세 뷰 — S-01(REQ-003)

`GET /`는 Wagtail이 이미 사이트 루트로 서빙하므로(03 §4), 별도 URLconf 라우트 없이 **`HomePage.get_context()`**(Wagtail 표준 패턴)로 구현했다. 목록 조회 자체(`BlogPostPage.published()` — `.live().order_by("-first_published_at")`)는 03 §1.2가 "공개 목록/상세 뷰"의 소유 앱으로 지정한 `blog`에 두고, `HomePage.get_context()`는 그 결과를 페이지네이션(`blog.pagination.paginate`)해 템플릿에 연결하는 얇은 어댑터 역할만 한다. `HomePage.serve()`에 `@cache_page(VIEW_CACHE_SECONDS)`를 적용해 03 §2.5(DEC-012) 뷰 캐시(5~15분)를 반영했다(10분 채택).

### 1.2 상세/카테고리/태그 뷰 — S-02/S-03/S-04(REQ-003) 및 URL 라우팅 설계(DEC-017)

03 §4는 `GET /blog/<slug>/`·`/category/<slug>/`·`/tag/<slug>/`라는 평면 경로를 못박았지만, `BlogPostPage`는 `parent_page_types = ["home.HomePage"]`(WU-02)이고 HomePage가 사이트 루트라, Wagtail 기본 트리 URL 규칙을 그대로 따르면 게시물 URL은 `/<slug>/`가 되어 03 §4 계약과 어긋난다. 이를 "표가 최소 계약"이라는 03 §4 서술을 근거로 문자 그대로 지키기로 하고(DEC-017), 세 라우트를 Wagtail 페이지 트리 서빙이 아니라 **`blog/urls.py`의 일반 Django 뷰**로 구현했다. `config/urls.py`는 이 모듈을 `wagtail_urls` catch-all보다 먼저 `include()`한다.

- `post_detail`: `BlogPostPage.published()`에서 slug로 조회(`get_object_or_404`) → 404(미공개/예약전/만료/존재하지 않음, 03 §4).
- `category_list`/`tag_list`: `Category`/`Tag` 객체 자체가 없으면 404, 있지만 소속 발행 게시물이 0건이면 빈 상태(04 §2 S-03/S-04 — "카테고리/태그 자체가 없음"과 "있지만 게시물 0건"을 명확히 구분).
- 세 뷰 모두 `@cache_page(VIEW_CACHE_SECONDS)`(10분) 적용.

**트리 URL과 정규 URL의 중복 접근 문제**: `BlogPostPage`가 여전히 페이지 트리에 있으므로 `/<slug>/`(트리 URL)로도 이론상 접근 가능하다. Wagtail 공식 문서가 커스텀 라우팅 페이지에 권장하는 패턴(`get_url_parts()` 오버라이드, "pages with custom URL routing should override this method")을 그대로 따라, `BlogPostPage.get_url_parts()`가 `reverse("blog:post_detail", ...)`를 반환하도록 오버라이드했고, `BlogPostPage.serve()`는 트리 URL 접근을 정규 URL로 **301 리다이렉트**하도록 오버라이드했다. Wagtail 소스(`wagtail/models/preview.py`)를 직접 확인한 결과 `serve_preview()`는 `serve()`를 호출하지 않고 `get_preview_template`/`get_preview_context`로 독립 렌더링하므로, 이 리다이렉트가 **OP-03(어드민 미리보기)을 막지 않음**을 실제 HTTP 요청으로 재현·확인했다(§3).

**한글 slug 라우팅**: Wagtail 기본값(`WAGTAIL_ALLOW_UNICODE_SLUGS=True`, Wagtail 소스 직접 확인)과 django-taggit 기본 `slugify(allow_unicode=True)`가 한글 slug("기술", "파이썬" 등)를 그대로 생성한다. Django 기본 `slug:` 경로 컨버터(ASCII 전용 정규식)로는 한글 slug가 매칭되지 않는 것을 로컬 실행에서 실제로 재현했고(`TemplateSyntaxError`가 아니라 `NoReverseMatch`로 나타남), `blog/urls.py`의 세 라우트 모두 `str:slug`(슬래시 제외 임의 문자열) 컨버터로 교체했다. 조회는 뷰의 `get_object_or_404`가 정확히 일치하는 slug만 통과시키므로 안전하다.

### 1.3 RSS 피드 — REQ-004

Django 표준 `django.contrib.syndication.views.Feed`로 `LatestPostsFeed`를 구현하고 `/feed.xml`에 마운트했다(`blog/feeds.py`). `items()`는 `BlogPostPage.published()`(발행분만, 미공개 자동 제외)를 최신순 20건으로 제한한다. `item_link()`는 `item.get_url()`(§1.2의 `get_url_parts` 오버라이드 덕에 정규 URL `/blog/<slug>/`를 반환)을 쓰므로 RSS 링크도 트리 URL이 아닌 정규 URL을 가리킨다. `django.contrib.sites`를 `INSTALLED_APPS`에 추가하지 않았다 — Django의 `get_current_site()`가 요청 객체가 있으면 `RequestSite` 폴백으로 동작함을 실제 HTTP 요청으로 확인했다(§3).

### 1.4 반응형 이미지(srcset) — REQ-014, 04 §6

WU-03이 검증해 둔 `CustomImage` 렌디션 메커니즘(`width-800`/`width-400`/`fill-100x100`)을 실제 템플릿에서 사용했다. 대표이미지(S-02 히어로, S-01/S-03/S-04 PostCard 썸네일)와 ArticleBody 이미지 블록에 `{% image ... width-400 as img_400 %}`/`{% image ... width-800 as img_800 %}`를 각각 로드해 `srcset="{{ img_400.url }} 400w, {{ img_800.url }} 800w"` + `sizes`를 명시했고, `width`/`height` 속성을 명시적으로 채워 레이아웃 시프트를 방지했다(04 §2 S-02 "명시적 width/height" 요구). `fill-100x100`은 이번 WU의 어떤 화면 명세에도 정사각형 고정 크롭이 필요한 용도가 없어 사용하지 않았다 — `srcset`은 동일 종횡비의 해상도 변형만 담아야 의미가 있는데(`width-400`/`width-800`은 원본 종횡비를 유지, `fill-100x100`은 강제 정사각형 크롭이라 종횡비가 다름), 이를 `width-400`/`width-800`과 같은 `srcset`에 섞는 것은 기술적으로 부정확하다. 대표이미지 alt는 Wagtail 표준 동작대로 `Image.title`을 사용했고(04 §5), ArticleBody 이미지 블록은 WU-02가 만든 필수 `alt_text` 필드를 사용했다(누락 없음, §3에서 실측 확인).

**Wagtail 이미지 태그 문법 주의(구현 중 발견/정정)**: `{% image obj "width-400" as x %}`처럼 필터 스펙을 따옴표로 감싸면 `TemplateSyntaxError`가 난다(Wagtail의 `image` 태그 파서는 필터 스펙을 따옴표 없는 bareword로만 받는다 — `wagtail/images/templatetags/wagtailimages_tags.py` 소스로 직접 확인). 모든 템플릿에서 `{% image obj width-400 as x %}`(따옴표 없음)로 통일했다.

### 1.5 ArticleBody(StreamField 블록 렌더링) — REQ-001/017 데이터의 WU-04 몫

WU-02가 데이터 구조만 만들고 프런트엔드 렌더링을 명시적으로 WU-04로 미룬 대로(`unit-02-note.md` §2-4), `blog/blocks.py`의 `ImageBlock`/`QuoteBlock`/`FAQBlock`에 `template` Meta를 추가하고 각 템플릿을 작성했다. `paragraph`(`RichTextBlock`)는 커스텀 템플릿 없이 Wagtail 기본 렌더링(이미 새니타이즈된 리치텍스트 HTML)을 그대로 썼다.

### 1.6 접근성(REQ-014, 04 §5)

- **스킵 링크**: WU-01이 만든 `.skip-link`(base.css)를 그대로 사용(변경 없음).
- **키보드 내비게이션/포커스 관리**: 모바일 내비 드로어(`nav.js`)가 열림 시 첫 링크로, Esc/토글 재클릭 시 토글 버튼으로 포커스를 이동한다(WCAG 2.4.3). JS 없이도 `#nav-menu`는 `[hidden]` 속성이 없는 일반 목록으로 렌더링되어 전체 메뉴가 그대로 노출/사용 가능하다(04 §0 "모든 화면은 JS 없이도 동작" 원칙).
- **시맨틱 마크업**: `header`/`nav`/`main`/`footer` 랜드마크(WU-01 base.html 골격 유지), 브레드크럼 `aria-label="브레드크럼"`, 페이지네이션 `aria-label="페이지 내비게이션"`, 헤딩 레벨 순차 사용(S-02는 게시물 제목이 H1, S-01은 시각적으로는 숨기되 `sr-only` H1 유지).
- **이미지 alt**: §1.4에서 설명한 대로 대표이미지/ArticleBody 이미지 블록 모두 alt를 실제로 출력한다(플레이스홀더 아이콘과 PostCard 썸네일은 제목 링크가 접근 가능한 이름을 제공하므로 `alt=""` + `aria-hidden="true"`로 중복 안내를 피했다 — 일반적인 "장식적 링크 이미지" 패턴).
- **폼 접근성**: 이번 WU에는 실제 폼이 없다(뉴스레터는 WU-07, §2-2).
- **터치 타겟**: Pagination 링크/Button 컴포넌트에 `min-height/min-width: 44px` 적용(04 §5).
- **포커스 스타일**: WU-01의 `:focus-visible` 전역 규칙(base.css)을 그대로 활용, 500.html은 별도 인라인 규칙으로 동일 효과 재현.
- **언어**: `<html lang="ko">`(WU-01 골격, 변경 없음).

### 1.7 콜드스타트 안내(REQ-011/DEC-011 연계, 04 §2)

전역 Footer에 04-ux-design.md §2가 제시한 정적 카피("⚡ 무료 인프라로 운영 중이라...")를 그대로 반영하고, `<details>/<summary>`로 1~2문장 추가 설명을 넣었다(새 라우트/DB 필드 없이, 04 §2가 명시한 방식 그대로).

---

## 2. 설계서 대비 편차 (사유 포함)

1. **URL 라우팅을 Wagtail 페이지 트리 서빙이 아닌 일반 Django 뷰로 구현하고, `get_url_parts()`/`serve()`를 오버라이드함** — §1.2, DEC-017에 근거와 함께 기록. 03 §4 문언을 그대로 지키기 위한 기술적 선택이며, 두 갈래 해석 문제가 아니라 "명시된 계약을 어떻게 만족시킬 것인가"의 구현 문제로 판단해 질문으로 올리지 않았다.
2. **NewsletterSubscribeForm/JSON-LD(BlogPosting) 미구현** — 04 §2/§4는 S-01/S-02 구성요소로 나열하지만, 02-planning.md §9는 REQ-016을 WU-07로, REQ-005(JSON-LD 포함)를 WU-05로 각각 배정했고 이번 WU 작업 지시도 두 기능을 언급하지 않았다. REQ-ID 소유권을 경계 기준으로 채택해 미구현으로 남겼다(DEC-018). NewsletterSubscribeForm은 백엔드(`POST /newsletter/subscribe/`)가 아직 없어 폼을 렌더링해도 제출 시 항상 실패하므로, 만들지 않는 쪽이 "동작하지 않는 UI를 노출"하는 것보다 낫다고 판단했다.
3. **CookieConsentBanner는 포함** — 위 2번과 달리 서버 API 의존이 없는(순수 `localStorage` + 정적 링크) 컴포넌트이고 S-01의 필수 전역 컴포넌트로 명시되어 있어 이번 WU에 포함했다(DEC-018). "자세히 보기" 링크(`/cookies/`)는 WU-06 전까지 일시적으로 404이며, Footer 법적 링크 3종과 동일한 성격의 정상적인 점진적-완성 상태로 판단했다(둘 다 `{% url %}`이 아니라 하드코딩 `<a href>`를 써서, 아직 없는 URL name을 reverse하다 `NoReverseMatch`로 전체 렌더링이 깨지는 것을 피했다).
4. **Pretendard 웹폰트(@font-face) 미구현, 시스템 폰트 fallback 유지** — WU-01이 "WU-04에서 처리"로 명시했던 항목이지만, 실제 폰트 바이너리 자산을 내려받아 저장소에 포함하는 것은 이번 도구 환경에서 검증 가능한 방식으로 수행하기 어렵고(라이선스/파일 무결성을 실제로 확인할 방법이 없음), 검증되지 않은 CDN URL을 추측해 넣는 것도 무책임하다고 판단해 보류했다. `tokens.css`의 `--font-primary` 토큰(fallback 체인 포함)은 이미 정의되어 있으므로 시각적으로는 시스템 폰트로 정상 렌더링된다. 후속 WU 또는 별도 작업에서 실제 폰트 자산을 검증된 경로로 추가할 것을 권고한다(§7-1).
5. **페이지네이션을 번호 목록이 아닌 "이전/다음 + N/전체" 형태로 구현** — 04 §4는 "기본, 비활성(첫/끝 페이지), 현재 페이지 표시"만 요구하고 구체적인 번호 링크 윈도우 알고리즘(몇 개를 보여줄지, 생략 표기 등)을 명시하지 않았다. 임의의 윈도우 규칙을 발명하는 대신 더 단순하고 명세를 충족하는 형태(현재 페이지 표시 포함)를 택했다 — 가역적 UI 세부사항.
6. **헤더 카테고리 "5~6개 초과 시 드롭다운"을 6개 기준 `<details>` "더보기"로 구현** — 04 §2 Header 설명 문구를 그대로(6개 초과 시 `<details>`로 분리) 구현했다. 정렬 기준(Category.Meta.ordering=["name"], WU-02)을 그대로 따랐다.
7. **캐시 TTL 10분, 페이지당 10건 채택** — 03 §2.5(DEC-012)는 "5~15분"만 못박고 정확한 값은 5단계 재량이라, 각각 10분/10건을 채택했다(`blog/constants.py`에 근거 주석과 함께 정의).
8. **Wagtail 예약발행(`go_live_at`/`expire_at`) 자동 반영을 위한 cron(`publish_scheduled_pages`) 설정은 이번 WU 범위에 포함하지 않음** — `BlogPostPage.published()`는 `live` 플래그만 필터링하는데, `go_live_at`이 실제로 `live=True`로 전환되려면 Wagtail의 `publish_scheduled_pages` 관리 명령이 주기적으로(cron 등) 실행되어야 한다. 이 운영 스케줄러 설정은 배포 파이프라인 구성이며 03/04 어디에도 담당 WU가 명시되어 있지 않다 — WU-04는 뷰 구현만 담당하므로 범위 밖으로 남기고 §7-2에 인계 사항으로 남긴다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv_wu04`, 검증 후 삭제)에서 `pip install -r requirements.txt`(WU-01~03과 동일 버전, 신규 패키지 없음) 후 아래를 직접 실행해 확인했다.

### 3-1. 마이그레이션/시스템 체크 (dev, SQLite)

1. `python manage.py migrate`(빈 SQLite에서 처음부터) → 오류 없이 전체 적용.
2. `python manage.py check` → "System check identified no issues (0 silenced)".
3. `python manage.py makemigrations --check --dry-run` → "No changes detected"(이번 WU는 모델 스키마를 변경하지 않았으므로 신규 마이그레이션 없음 — 실제로 없음을 확인).

### 3-2. HTTP 스모크 테스트 (`django.test.Client`, 임시 스크립트로 실행 후 삭제) — 43건 전부 PASS

1. **S-01 빈 상태**: 게시물 0건일 때 `GET /` → 200, "아직 게시된 글이 없습니다..." 문구 노출, 스킵링크/카테고리 컨텍스트 프로세서 정상 동작.
2. **데이터 준비**: Category 2종(기술/일상) + 6종 추가(헤더 "더보기" 테스트용, 총 8종), `CustomImage` 실제 업로드(PNG), `BlogPostPage`에 문단/이미지(alt_text/caption)/인용(quote/attribution)/FAQ(질문×2) 블록을 모두 포함해 생성·발행.
3. **S-02 상세**: `GET /blog/first-post/` → 200. 제목/카테고리 배지/태그 칩/문단/이미지 블록(alt_text·caption)/인용(quote·attribution)/FAQ(질문·답변)/대표이미지 `srcset`(400w·800w)/대표이미지 `alt`=이미지 title/`loading="lazy"`/브레드크럼 `aria-label` 전부 렌더링 확인.
4. **트리 URL 리다이렉트**: `GET /first-post/`(Wagtail 기본 트리 URL) → **301**, `Location: /blog/first-post/`(중복 URL 방지, DEC-017 실증).
5. **404 케이스**: 미공개(`live=False`) 게시물 상세 → 404. 존재하지 않는 slug → 404. 존재하지 않는 카테고리 → 404. 존재하지 않는 태그 → 404.
6. **S-03 카테고리**: 게시물 있는 카테고리 → 200 + 카드 노출. 게시물 0건인 카테고리(카테고리 자체는 존재) → 200 + 빈 상태 문구("이 카테고리에는 아직 게시된 글이 없습니다.").
7. **S-04 태그**: 게시물 있는 태그(`#파이썬`, 한글 slug) → 200 + 카드 노출.
8. **RSS(`/feed.xml`)**: 200, `Content-Type: application/rss+xml; charset=utf-8`, 발행 게시물 제목/정규 URL(`/blog/first-post/`, 트리 URL 아님) 포함, 미공개("초안") 게시물 미포함.
9. **페이지네이션**: 총 13건(발행 12 + 초안 1) 중 발행 12건, 10건/페이지로 `page=1`(nav 노출 확인)/`page=2` 정상, `page=9999`(범위 밖) → 마지막 페이지로 보정(200), `page=abc`(비정상 값) → 1페이지로 보정(200). 어느 경우도 500/예외 없음.
10. **헤더 카테고리 "더보기"**: 8개 카테고리 중 6개 초과분이 `<details><summary>더보기</summary>`로 분리 노출됨을 확인.
11. **회귀**: `GET /cms-admin/login/`(비로그인) → 200.
12. **OP-03 미리보기 비영향 확인**: 로그인 후 `GET /cms-admin/pages/<pk>/edit/` → 200(정정 응답에 편집 폼 정상 렌더 — `BlogPostPage.serve()`의 301 리다이렉트가 어드민 미리보기/편집 흐름에 영향을 주지 않음을 확인. `serve_preview()`가 `serve()`를 호출하지 않는다는 Wagtail 소스 확인과 일치).
13. **뷰 캐시로 인한 스테일(stale) 응답**: 테스트 중 "빈 상태" 요청이 캐시(10분 TTL)에 적재된 뒤 게시물을 추가로 만들고 재요청하면 과거 캐시가 그대로 반환되는 것을 실제로 재현했다 — 애플리케이션 결함이 아니라 03 §2.5(DEC-012)가 의도한 뷰 캐시의 정상 동작이며, 6단계 테스터가 동일한 순서로 재현할 때 반드시 인지해야 할 사항(§7-3)으로 남긴다.

### 3-3. 정적 파일 (dev + production 유사)

14. `python manage.py collectstatic --noinput`(dev, 로컬 파일시스템 스토리지) → 216개 파일 정상 수집(오류 없음).
15. `config/settings/it_test_prodlike.py`(WU-01~03과 동일 방법론: `production.py` 상속 + `DATABASES`만 SQLite로 재정의, 검증 후 삭제)로 **production 유사 설정**에서:
    - `python manage.py check` → "System check identified no issues".
    - `python manage.py migrate`(처음부터) → 오류 없이 전체 적용.
    - `python manage.py collectstatic --noinput`(WhiteNoise `CompressedManifestStaticFilesStorage`) → "0 static files copied, 216 unmodified, 632 post-processed" — 신규 CSS/JS(`components.css`, `nav.js`)를 포함한 매니페스트 생성에 문제 없음을 확인(더미 R2 환경변수 사용, 네트워크 호출 없음).

### 3-4. 정리

검증에 사용한 `.venv_wu04`, `db.sqlite3`, `db_prodlike.sqlite3`, `media/`, `staticfiles/`, `config/settings/it_test_prodlike.py`, 임시 검증 스크립트(스크래치패드 경로)는 전부 삭제했다. `git status --porcelain`으로 diff에 소스 코드만 남았음을 최종 확인했다(신규 `blog`/`custom_images` 등 이전 WU 산출물 포함 — 여전히 커밋 전 상태, WU-02/03과 동일하게 이번 WU도 아직 커밋하지 않음).

**로컬에서 확인하지 못한 것**: 실제 브라우저 렌더링(키보드 전용 수동 통과, 스크린리더 스팟 체크, 실제 뷰포트별 반응형 레이아웃 시각 확인)은 MCP 미연동(DEC-001)으로 이번 WU에서 수행하지 못했다 — 04 §5가 권고한 axe-core/Lighthouse/NVDA 등 검증은 6단계(또는 이후 단계)에서 별도 도구로 수행해야 한다. Pretendard 실제 폰트 로딩도 마찬가지로 미검증(§2-4).

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체(및 `webapp/`)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 이번에도 재확인**했다(직접 검색, WU-01~03과 동일 결론) — 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 Python 파일 전체(`blog/constants.py`, `pagination.py`, `context_processors.py`, `views.py`, `feeds.py`, `urls.py`, `models.py`, `blocks.py`, `home/models.py`, `config/urls.py`, `config/settings/base.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다. CSS/JS/HTML 템플릿에 대한 별도 린터(stylelint/eslint 등)도 저장소에 설정되어 있지 않아, `manage.py check`/`collectstatic`/실제 렌더링(§3)으로 구문·참조 오류(예: `{% static %}` 경로, `{% url %}` 참조명)가 없음을 실행 기반으로 확인했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 8건은 전부 사유와 함께 명시했고, 대부분 "설계서가 구체 값/알고리즘을 명시하지 않은 부분에 대한 합리적 단일 선택" 또는 "REQ-ID 소유권에 따른 명시적 범위 경계"이지 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — 존재하지 않는/미공개 리소스는 전부 `get_object_or_404`로 404 처리(예외를 삼키지 않고 Django 표준 경로로 위임). `BlogPostPage.serve()`는 `get_url()`이 `None`을 반환하는 예외적 상황(사이트 설정 오류 등)에 조용히 실패하지 않고 프레임워크 기본 처리로 폴백하도록 명시적으로 분기했다. `_post_list.html`은 빈 목록/페이지네이션 없음 상태를 `{% if %}`로 명확히 분기해 인덱스 에러 없이 렌더링한다.
- [x] **입력값 검증이 시스템 경계(사용자 입력)에서 이루어지는가** — 이 WU의 시스템 경계는 URL 경로 파라미터(`slug`, `page`)뿐이다(폼 입력 없음, §2-2). `slug`는 ORM `get_object_or_404`가 DB에 실재하는 값만 통과시키고, `page`는 `Paginator.get_page()`가 비정상 값(문자열이 아님/범위 밖)을 예외 없이 안전한 값으로 보정한다(§3-2 AC9 실측 확인) — 사용자 입력이 서버 오류로 이어지지 않는다.
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 이번 변경분은 뷰/템플릿/정적 자산/설정 연결(컨텍스트 프로세서 등록)만 다루고 시크릿이 필요한 코드가 없다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `custom_images/`(WU-03), `blog/models.py`의 기존 필드/`Category`/`BlogPageTag`(WU-02)는 건드리지 않았다(신규 메서드만 추가). WU-01의 `middleware.py`, `settings/dev.py`, `settings/production.py`(보안 설정 부분)는 변경하지 않았다. `500.html`이 `base.html`을 extends하지 않는다는 WU-01의 안전 설계 결정(DB 장애 시 500 페이지 자체가 실패하는 것을 막기 위함)은 그대로 유지했다(스타일/카피만 04번 토큰 기준으로 다듬음, 지시사항 그대로).

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-003/REQ-004/REQ-014 행을 갱신했다: "설계 매핑"에 실제 사용한 라우트(카테고리/태그 포함)를 보강하고, "작업 단위"는 이미 WU-04로 채워져 있었으며, "구현 상태"를 "Not Started" → "구현 완료(`unit-04-note.md`, 구현 근거 파일 경로)"로, "단위테스트"를 "대기(6단계)"로 채웠다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다(사실을 그대로 반영).

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **Pretendard 웹폰트 미구현**: §2-4 참고. 실제 폰트 자산(자체 호스팅 또는 검증된 CDN)을 추가하는 작업이 별도로 필요하다 — 현재는 시스템 폰트 fallback으로 렌더링된다(기능/접근성에는 영향 없음, 시각 디자인 완성도 항목).
2. **Wagtail 예약발행 cron 미설정**: §2-8 참고. `go_live_at`/`expire_at`이 실제 `live` 플래그에 반영되려면 `python manage.py publish_scheduled_pages`를 주기적으로 실행하는 배포 파이프라인 설정(예: Render Cron 또는 GitHub Actions)이 필요하다 — 이번 WU는 뷰 구현만 담당하므로 이 설정을 하지 않았다. 담당 WU가 명시되어 있지 않으므로 다음 단계(운영 관련 WU 또는 배포 단계)에서 명시적으로 인계받아야 한다.
3. **뷰 캐시(10분 TTL)로 인한 지연 반영**: §3-2의 13번 참고. 운영자가 새 글을 발행해도 직전까지 캐시된 응답이 최대 10분간 그대로 보일 수 있다(03 §2.5/DEC-012가 의도한 트레이드오프). 6단계 테스터가 "발행 직후 즉시 반영"을 기대하고 테스트하면 거짓 결함으로 오인할 수 있으니, 캐시를 고려해 테스트 순서를 설계하거나(예: 매 시나리오마다 새 프로세스로 서버 재기동, 또는 `django.core.cache.cache.clear()`) 캐시 우회 방법을 사용해야 한다.
4. **NewsletterSubscribeForm/CookieConsentBanner "자세히 보기"/Footer 법적 링크 3종이 아직 가리키는 페이지가 없음**: §2-2/2-3 참고. `/privacy-policy/`, `/terms/`, `/cookies/`는 WU-06이 실제 페이지를 만들기 전까지 404를 반환한다 — 링크 자체(`<a href>`)는 정상이며 존재하지 않는 목적지로 인한 일시적 상태다. WU-06 완료 시 별도 조치 없이 자동으로 해소된다(하드코딩 경로가 03 §4 라우트 표와 정확히 일치하므로).
5. **접근성 실기기/실브라우저 검증 미수행**: §3-4 참고. axe-core/Lighthouse 자동 검사, 키보드 전용 수동 통과, 스크린리더(NVDA/VoiceOver) 스팟 체크는 MCP 미연동(DEC-001)으로 이번 WU에서 도구 기반으로 수행하지 못했다 — 04 §5 권고에 따라 6단계(또는 이후 단계)에서 별도로 수행 필요.
6. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다림). 원격 push는 수행하지 않았다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일). **주의**: 모든 공개 목록/상세 뷰가 `@cache_page(10분)`으로 캐시되므로(§7-3), 데이터를 바꾼 뒤 즉시 재요청해 검증하려면 매 시나리오 전에 캐시를 비우거나(`from django.core.cache import cache; cache.clear()`) 프로세스를 재시작할 것.

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, WU-01~03과 동일 버전).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `python manage.py migrate`가 빈 DB에서 처음부터 오류 없이 끝나는가.
3. `python manage.py check`가 "System check identified no issues"를 출력하는가.
4. `python manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가(이번 WU는 모델을 바꾸지 않았으므로 신규 마이그레이션이 없어야 함).
5. 게시물이 0건인 상태에서 `GET /` → 200이고, 응답 본문에 "아직 게시된 글이 없습니다"가 포함되는가(S-01 빈 상태).
6. Category(예: 이름 "기술")와 `CustomImage`(WU-03 참고)를 준비하고, `HomePage.add_child()`로 `BlogPostPage`를 생성해 문단/이미지(alt_text/caption)/인용(quote/attribution)/FAQ(질문/답변) 블록을 모두 포함한 뒤 `save_revision().publish()`하면, `GET /blog/<slug>/` → 200이고 응답에 제목/카테고리 배지/태그 칩/각 블록 내용이 전부 렌더링되는가.
7. 위 게시물 상세 응답에 대표이미지 `srcset`(`400w`/`800w` 토큰 포함), `alt="<이미지 title>"`, `loading="lazy"`가 포함되는가(REQ-014 반응형 이미지).
8. 같은 게시물의 **Wagtail 기본 트리 URL**(예: `/<slug>/`, HomePage가 루트이므로 부모 slug 없이 자신의 slug만)로 요청하면 **301**이 오고 `Location` 헤더가 `/blog/<slug>/`(정규 URL)를 가리키는가(중복 URL 방지, DEC-017).
9. 게시물을 `live=False`로 만들거나(초안) 존재하지 않는 slug로 `/blog/<slug>/`를 요청하면 404가 오는가.
10. 게시물이 있는 카테고리로 `GET /category/<slug>/` → 200이고 게시물 카드가 노출되는가. 같은 카테고리이지만 소속 게시물이 없는 경우 → 200 + "이 카테고리에는 아직 게시된 글이 없습니다." 빈 상태 문구가 노출되는가(404가 아님을 확인).
11. 존재하지 않는 카테고리 slug로 `/category/<slug>/`를 요청하면 404가 오는가.
12. 게시물에 태그(예: 한글 "파이썬")를 추가하고 `GET /tag/<slug>/`(한글 slug 그대로)로 요청하면 200과 함께 게시물 카드가 노출되는가(한글 slug 라우팅 확인, §1.2).
13. 존재하지 않는 태그 slug로 `/tag/<slug>/`를 요청하면 404가 오는가.
14. `GET /feed.xml` → 200, `Content-Type`이 `application/rss+xml`로 시작하는가. 응답에 발행된 게시물의 제목과 정규 URL(`/blog/<slug>/`)이 포함되고, 미공개 게시물은 포함되지 않는가.
15. 발행된 게시물을 11건 이상 만들고(페이지당 10건, `blog/constants.py`) `GET /` → 200이고 응답에 `class="pagination"` 페이지네이션 내비게이션이 노출되는가. `?page=2` → 200. `?page=9999`(범위 밖) → 200(예외 없이 마지막 페이지로 보정). `?page=abc`(비정상 값) → 200(예외 없이 1페이지로 보정).
16. Category를 7개 이상 만들면(정렬은 이름순) `GET /`(또는 임의 페이지) 응답의 헤더에 `<details><summary>더보기</summary>`가 노출되고 그 안에 7번째 이후 카테고리가 포함되는가.
17. 로그인하지 않은 상태로 `GET /cms-admin/login/` → 200인가(회귀, WU-01).
18. 관리자로 로그인한 뒤 `GET /cms-admin/pages/<blogpostpage_pk>/edit/` → 200이고 정상적으로 편집 화면이 렌더링되는가 — 즉 `BlogPostPage.serve()`의 301 리다이렉트가 어드민 편집/미리보기 흐름을 방해하지 않는가(OP-03 비영향 확인, §3-2 AC12).
19. `python manage.py collectstatic --noinput`(dev)이 오류 없이 끝나고 `components.css`/`nav.js`가 수집되는가.
20. (production 유사) `config/settings/production.py`를 상속하되 `DATABASES`만 SQLite로 재정의한 설정 모듈로 더미 R2 환경변수를 채운 뒤 `python manage.py check`/`migrate`/`collectstatic --noinput`이 모두 오류 없이 끝나는가(WhiteNoise 매니페스트 스토리지 포함).
21. 검증 후 사용한 venv/DB(`db.sqlite3`, `db_prodlike.sqlite3` 등)/staticfiles/media/임시 설정 모듈/임시 스크립트를 정리했는지, diff에 포함되지 않았는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~21번 인수 조건을 입력으로 `docs/harness/units/unit-04-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-04)의 7단계(통합테스트, WU-01~03과의 조립 검증 포함)와 WU-05 착수 여부를 오케스트레이터가 판단한다.

---

## 10. 재작업 이력 (규칙 F, 피드백 루프 — 1라운드)

- **반려 근거**: `docs/harness/units/unit-04-test.md` §6 DEF-001(Critical). 6단계가 `django.views.defaults.server_error()`를 `RequestFactory` 요청으로 직접 호출해(Django가 미처리 예외를 500으로 변환할 때 실제로 호출하는 것과 동일한 경로) `config/templates/500.html`이 `TemplateSyntaxError: Invalid block tag on line 4: 'static'`로 컴파일 자체가 되지 않음을 dev/production 유사 설정 양쪽에서 재현했다. 6단계 결론(unit-04-test.md §8)은 "근본 원인이 WU-04 자신의 구현 세부사항(Django 템플릿 주석 문법)에 있고 설계/디자인 계약과는 무관"하다고 판단해 3/4단계까지 소급하지 않고 5단계(WU-04)로 직접 반려했다.
- **원인**: `500.html` 최상단의 `{# ... #}` 주석이 여러 줄(1~6행)에 걸쳐 있었는데, Django의 `{# #}` 주석 태그는 한 줄을 넘어가면 안 된다(공식 문서: "This comment tag can not span multiple lines"). 그 결과 주석 설명 문장 중 "`{% static %}`도 마찬가지 이유로 쓰지 않고"라는 문구(실제 태그 호출 의도가 아니라 설명 텍스트의 일부)가 파서에 의해 실제 블록 태그로 오인되어 "Invalid block tag" 오류가 발생했다.
- **수정 내용**: `webapp/config/templates/500.html` 1~6행의 `{# ... #}` 다중 라인 주석을 `{% comment %}...{% endcomment %}`(Django가 공식 지원하는 유일한 다중 라인 주석 방법, DEF-001 6절 조치안 (a))로 교체했다. 아울러 주석 본문에서 "`{% static %}`"이라는 중괄호 리터럴 표기 자체도 "static 태그"(중괄호 없는 표현, 조치안 (c))로 함께 고쳐, 향후 같은 주석을 다시 여러 줄로 늘려 쓰더라도 같은 함정에 재차 걸릴 여지를 줄였다. 이 파일 안의 `<style>` 인라인 CSS/본문 마크업(브랜드명, 문구, 버튼 2개, `line-height`/`.brand`/`.actions` 등 이전 WU-04 라운드에서 이미 작성된 내용)은 이번 재작업 대상이 아니므로 손대지 않았다.
- **범위 최소화**: DEF-001 6절이 Low 권고로 남긴 "`blog/templates/blog/blog_post_page.html`(4~9행)의 동일 계열 다중 라인 `{# #}` 주석"은 이번 재작업 지시(사용자 지시 "다른 파일/기능은 건드리지 말 것")에 따라 손대지 않았다. 6단계 스스로도 그 주석 안에는 `{%`/`{{` 리터럴이 없어 현재 무해함을 TC-006/007로 실측 확인했으므로(unit-04-test.md §6), 이번 재작업의 블로킹 대상이 아니다 — 별도 결함으로 제기되면 그때 다룬다.
- **재현 검증(직접 실행, 임시 venv `webapp/.venv_wu04_fix`에서 수행 후 삭제)**:
  1. dev 설정(`config.settings.dev`): `RequestFactory().get("/anything")`으로 만든 요청을 `django.views.defaults.server_error(request)`에 직접 전달 → 수정 전에는 `TemplateSyntaxError`, 수정 후에는 `TemplateSyntaxError` 없이 정상 렌더링(`status_code=500`, 본문에 "일시적인 오류가 발생했습니다" 포함) 확인.
  2. production 유사 설정: WU-01~03·05·06단계와 동일 방법론으로 `config/settings/it_test_prodlike_fix.py`(이번 재작업이 신규 생성 — `production.py` 상속 + `DATABASES`만 SQLite로 재정의, 더미 `SECRET_KEY`/`DATABASE_URL`/`R2_*`/`DJANGO_ALLOWED_HOSTS` 환경변수, 실제 네트워크 호출 없음, 검증 후 삭제)에서 동일한 `server_error()` 직접 호출 → 동일하게 `TemplateSyntaxError` 없이 정상 렌더링 확인.
  3. 회귀 스모크: `manage.py migrate` 후 `django.test.Client`로 `GET /`(200), 존재하지 않는 slug(404), `GET /cms-admin/login/`(200) 확인 — 500.html 수정이 다른 라우트에 부작용을 주지 않음을 확인.
  4. **`server_error()`의 실제 반환 상태코드는 500이다**(Django `HttpResponseServerError`가 `status_code=500`을 고정). `unit-04-test.md` TC-031의 "예상 결과" 서술("200, `500.html` 렌더...")은 상태코드 표기에 오탈자가 있는 것으로 보이며, 이번 재작업 검증의 판정 기준은 "TemplateSyntaxError 없이 500.html이 정상 렌더링되고 기대 문구가 포함되는가"로 삼았다(6단계가 TC-031을 재실행할 때 상태코드 자체는 500이 정상임에 유의할 것 — 서술 오탈자이지 결함이 아님).
  5. 검증에 사용한 `.venv_wu04_fix`, `db.sqlite3`(dev migrate로 생성), `config/settings/it_test_prodlike_fix.py`, 임시 스크립트(스크래치패드 경로)는 전부 삭제했다. `git status --porcelain -- webapp`로 소스만 남았음을 최종 확인(변경분은 `webapp/config/templates/500.html` 한 파일).
- **게이트 1(정적 분석/린트) 재확인**: 이번 재작업은 Python 파일을 변경하지 않았다(Django HTML 템플릿 1개만 수정). 저장소에 Python lint/type-check/formatter 설정(`pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml`)이 여전히 존재하지 않음을 재확인했다(WU-01~06과 동일 결론, 있는데 건너뛴 것이 아님). HTML/템플릿 린터도 저장소에 없어, 위 재현 검증(실제 렌더링 성공)으로 구문 정확성을 실행 기반으로 확인했다.
- **게이트 2(자체 코드 리뷰 체크리스트)**:
  - [x] 설계서/디자인서 명세와 실제 구현이 일치하는가 — 04-ux-design.md S-09(500 페이지) 요구사항(브랜드 카피, 새로고침/홈 CTA, 토큰 기반 스타일)은 이번 재작업으로 변경되지 않았다(이미 이전 라운드에서 반영됨). 이번 수정은 그 내용을 그대로 유지한 채 주석 문법만 고쳤다.
  - [x] 에러 처리가 누락된 경로가 없는가 — 해당 없음(이번 변경은 정적 템플릿 주석/문구 수정이며 새로운 실행 경로를 추가하지 않았다).
  - [x] 입력값 검증이 시스템 경계에서 이루어지는가 — 해당 없음(사용자 입력을 받는 코드 변경 없음).
  - [x] 하드코딩된 시크릿/자격증명이 없는가 — 없음. 검증용 프로덕션 유사 설정 모듈(`it_test_prodlike_fix.py`)은 환경변수로만 값을 주입했고 삭제까지 완료했다.
  - [x] 범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가 — `webapp/config/templates/500.html` 한 파일의 주석 블록만 수정했다. `blog_post_page.html`의 동일 계열 Low 권고, CSS/문구/버튼 등 이 파일의 나머지 부분, 다른 어떤 파일도 건드리지 않았다(사용자 지시 "다른 파일/기능은 건드리지 말 것" 준수).
- **traceability.md 갱신**: REQ-003/REQ-004/REQ-014 행의 "단위테스트" 컬럼을 "**FAIL**(DEF-001)"에서 "재작업 완료, 재확인 대기(6단계)"로 갱신했다(6단계가 §5절 재확인 절차대로 TC-031을 포함해 전체를 재실행해 PASS로 전환하기 전까지는 이 노트가 스스로 PASS를 선언하지 않는다 — unit-04-test.md §8의 재확인 절차를 그대로 존중).
- **6단계에 인계하는 인수 조건(재현 절차, 그대로 재실행 가능)**:
  1. `webapp/`에 새 venv를 만들고 `pip install -r requirements.txt`.
  2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 Django 초기화 후, `RequestFactory().get(아무 경로)`로 만든 요청을 `django.views.defaults.server_error(request)`에 전달 → `TemplateSyntaxError`가 발생하지 않고, 응답 본문에 "일시적인 오류가 발생했습니다"가 포함되는가(상태코드는 500이 정상).
  3. `production.py`를 상속하고 `DATABASES`만 SQLite로 재정의한 설정 모듈(더미 `SECRET_KEY`/`DATABASE_URL`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL`/`DJANGO_ALLOWED_HOSTS` 환경변수)에서 2번과 동일하게 재현했을 때도 동일하게 통과하는가.
  4. unit-04-test.md 4절의 나머지 TC(특히 TC-005~TC-021, TC-032)를 전부 재실행해 이번 수정이 회귀를 일으키지 않았는가.
  5. 검증에 사용한 venv/DB/임시 설정 모듈/임시 스크립트가 모두 삭제되어 `git status`에 소스 diff만 남는가.
