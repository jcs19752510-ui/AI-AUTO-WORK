# WU-06 — 법적 페이지(개인정보처리방침/이용약관/쿠키 고지) + 콘텐츠 정책 + 쿠키배너 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-06, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §1.2 `legal` 앱 모듈 경계, §3.2 LegalPage 모델 옵션, §4 라우트 계약, §5.6 개인정보 처리 원칙), `docs/harness/04-ux-design.md`(v1.2, PASS, 화면 S-05~S-07, 전역 컴포넌트 CookieConsentBanner, §5 접근성), `docs/harness/decisions.md`(DEC-001~021), `docs/harness/01-trend-analysis.md`(§5 한국 개인정보/쿠키 법적 이슈, "확인 필요" 항목), `docs/harness/02-planning.md`(REQ-007/008/009/015, WU-06 정의, §11 Q1 미해결이 WU-06 착수를 막지 않음), `docs/harness/units/unit-04-note.md`(§1/§2-3 CookieConsentBanner "포함" 기록과 실제 코드 부재 확인)
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-007(개인정보처리방침), REQ-008(쿠키 사용 고지), REQ-009(이용약관), REQ-015(콘텐츠 정책)

---

## 1. 구현 범위

WU-01(골격)·WU-04(공개 화면/전역 컴포넌트 골격)·WU-05(SEO: canonical/sitemap/robots) 위에, 신규 `legal` 앱(03 §1.2가 이미 지정한 모듈 경계)과 사이트 전역 CookieConsentBanner를 구현했다.

```
webapp/
  legal/                              (신규 앱)
    apps.py
    constants.py                      VIEW_CACHE_SECONDS(10분, blog와 동일 정책, 앱 간 결합 방지 위해 독립 정의)
    models.py                         LegalPage(Page) — 공용 리치텍스트 모델(DEC-022), TOC 자동 생성, 뷰 캐시, get_sitemap_urls
    migrations/0001_initial.py        (makemigrations로 생성, Django 5.2.17/Wagtail 7.4.3 기준 자동 검증됨)
    migrations/0002_create_legal_pages.py   (신규) 개인정보처리방침/이용약관/쿠키고지 3개 페이지를 실제 콘텐츠로 live 게시하는 데이터 마이그레이션
    templates/legal/legal_page.html   (신규) S-05/S-06/S-07 공용 템플릿(Breadcrumb/최종업데이트/TOC/본문)
  config/
    settings/base.py                  (수정) INSTALLED_APPS에 "legal" 추가
    templates/base.html               (수정) CookieConsentBanner 마크업(전역) + 즉시-숨김 인라인 스크립트 + cookie-consent.js 로드
    static/js/cookie-consent.js       (신규) 배너 "확인"/ESC 처리, localStorage 저장
    static/css/components.css         (수정) `.legal-page*`, `.cookie-consent*` 스타일 추가
docs/harness/decisions.md             DEC-022(LegalPage 단일 모델 채택 근거) 추가
docs/harness/traceability.md          REQ-007/008/009/015 행 갱신
```

### 1.1 법적 페이지 3종 — REQ-007/008/009

03 §3.2는 "각각 별도 Page 서브클래스(**또는** 공통 RichTextPage 1개 모델을 재사용)"라는 두 옵션을 모두 승인했다. 세 페이지 모두 제목+리치텍스트 본문+최종수정일이라는 동일 구조이고 페이지별 차별화 로직이 없어, 서브클래스 3개는 불필요한 코드 중복이라고 판단해 **공용 `LegalPage` 모델**을 채택했다(DEC-022).

`LegalPage.parent_page_types = ["home.HomePage"]`로 지정하고, 데이터 마이그레이션에서 세 인스턴스를 `slug="privacy-policy"/"terms"/"cookies"`로 HomePage 직계 자식에 생성했다. HomePage가 사이트 루트라(blog.models.BlogPostPage.get_url_parts docstring이 이미 확인한 것과 동일한 이유로, 트리 URL에서 `/home/` 접두어가 제거됨) Wagtail 기본 트리 URL이 **접두어 없이 자동으로** 03 §4가 못박은 `/privacy-policy/`, `/terms/`, `/cookies/`와 정확히 일치한다. 따라서 blog 앱과 달리 `get_url_parts()`/`serve()` 오버라이드나 별도 `urls.py`가 전혀 필요 없다 — Wagtail의 기본 페이지 트리 서빙(`config/urls.py`의 `wagtail_urls` catch-all)이 그대로 처리한다.

### 1.2 실제 콘텐츠 게시(데이터 마이그레이션) — KPI #6 대응

02-planning.md §5 KPI 6("법적 페이지가 배포 전 100% 게시·최신화되어 있어야 함")을 충족하기 위해, 페이지 골격만 만들지 않고 **`legal/migrations/0002_create_legal_pages.py`가 실제 콘텐츠를 담아 `live=True`로 게시**한다(home/migrations/0002_create_homepage.py와 동일한 "historical 모델 + 수동 path/depth/numchild/url_path 계산" 패턴). 본문 내용은 03 §5.6이 명시한 항목을 반영했다:

- **개인정보처리방침**: 수집 항목(뉴스레터 이메일뿐 — REQ-016은 WU-07 미구현이므로 아직 실제로 수집되지는 않음, 접속 로그), 수집/이용 목적, 보유기간(탈퇴 요청 전까지), 파기절차(수동 하드 삭제, 03 §5.6과 동일), **제3자 처리위탁 및 국외이전**(Render/Neon/Cloudflare/GitHub, 전부 미국 소재 — 03 §5.6이 "반드시 방침에 명시" 요구한 항목), 이용자 권리, 쿠키 고지 페이지 링크, 문의처.
- **이용약관**: 목적, 게시물 저작권, 이용자 제공 정보 처리(개인정보처리방침 링크), **콘텐츠 정책**(아래 1.3), 약관 변경.
- **쿠키 사용 고지**: 쿠키란, 이 사이트가 실제로 사용하는 쿠키 2종(`sessionid`/`csrftoken`)을 목적/보관기간과 함께 나열, localStorage 기반 배너 상태 저장 사실 고지(쿠키 아님을 명시해 혼동 방지), 쿠키 설정 변경 방법.

**법률 자문 관련 명시적 한계**: 01/02/03 단계가 일관되게 밝힌 대로("에이전트가 법률 자문을 대신하지 않음"), 개인정보처리방침 본문 끝에 "이 문서는 서비스 운영 원칙을 안내하기 위한 초안이며, 실제 공개 서비스 운영 전 관련 법률 전문가의 자문을 받아 최종 검토할 것을 권고합니다"라는 문구를 명시적으로 포함했다. 이 문구는 이 WU가 임의로 발명한 것이 아니라 03 §5.6/01 §5/02 §7-4가 반복적으로 요구한 "법률 자문 필요 고지"를 실제 화면에 반영한 것이다.

**"쿠키 목적/보관기간 표" 관련 기술적 제약**: 04 §2 S-07은 "리치텍스트 본문(쿠키 목적/보관기간 **표**)"이라고 서술했지만, 이 프로젝트의 Wagtail 리치텍스트 에디터는 기본 기능 세트만 활성화되어 있고(`WAGTAILADMIN_RICH_TEXT_EDITORS` 커스터마이징 없음, `wagtail.contrib.table_block` 미설치) `<table>`은 기본 허용 태그가 아니다. 지원되지 않는 리치텍스트 기능을 임의로 사용하는 대신, 동일한 정보(쿠키명/목적/보관기간)를 `<ul>` 목록의 굵은 라벨로 표현했다 — 방문자에게 전달되는 정보 내용은 동일하고, 04가 요구한 "목적/보관기간 안내"라는 목적을 충족한다.

### 1.3 콘텐츠 정책(REQ-015) — `/terms/` 하위 섹션

04-ux-design.md §2 S-06(v1.1 변경이력, DEC-018 재확인)이 이미 "새 라우트를 만들지 않고 `/terms/` 안에 콘텐츠 정책을 하위 섹션으로 통합"하기로 확정해 두었으므로, 이 WU는 그 결정을 그대로 따랐다(새로운 판단이 아니라 이미 승인된 설계를 실제 콘텐츠로 채움). `/terms/` 본문의 "콘텐츠 정책" 섹션에 요청받은 문구를 정확히 반영했다: **"본 사이트는 금융/투자, 의료/건강, 법률, 보험 등 전문적인 자격이나 인허가가 필요한 분야에 대해 전문가의 조언이나 추천을 제공하지 않습니다."** 이어서 콘텐츠가 일반 정보 제공 목적이며 전문 자문으로 해석하면 안 된다는 설명과, 03 §5.6이 명시한 "카테고리는 운영자만 생성/관리"하는 화이트리스트 운영 정책을 함께 서술했다.

### 1.4 목차(TOC) — 04 §2 S-06 요구, 04 §7의 편차/일반화

04 §2는 TOC를 S-06(이용약관)에만 명시했다. 페이지 종류별로 분기 로직을 추가하는 대신, `legal/models.py`의 `_add_heading_anchors()`가 **"본문에 `<h2>` 제목이 있으면 자동으로 목차를 생성한다"는 일반 규칙**으로 구현했다 — 새로운 데이터/라우트 요구 없이 세 페이지 모두 동일한 컴포넌트를 재사용하는 가역적 판단이다(unit-06-note.md 이 절 참고, decisions.md에 별도 등재하지 않음 — 04-ux-design.md §2 "콜드스타트 UX 설계"가 채택한 것과 동일한 성격의 "근거를 남긴 자체 판단, 되돌리기 쉬움" 기준). 결과적으로 개인정보처리방침(h2 8개)과 쿠키 고지(h2 3개)에도 TOC가 함께 노출되는데, 이는 04가 금지한 사항이 아니라 단지 요구하지 않았을 뿐이며 접근성(04 §5 "헤딩 레벨 순차 사용")과 가독성에 도움이 된다.

TOC 앵커는 `slugify(text, allow_unicode=True)`로 한글 제목을 그대로 슬러그화한다(blog 앱이 한글 slug에 적용한 것과 동일한 함수). 중복 텍스트가 있으면 `-1`, `-2` 접미사로 구분한다. `expand_db_html()`로 리치텍스트 내부 링크 placeholder를 실제 HTML로 확장한 뒤, 정규식으로 `<h2>` 태그에만 `id` 속성을 주입해 `mark_safe`로 렌더링한다 — 03 §5.1(에디터가 곧 운영자)/§5.2(JSON-LD 필드에 적용한 것과 동일한 신뢰 경계 논리)에 따라 방문자 입력이 아닌 운영자 리치텍스트 콘텐츠에만 적용되는 처리이며, 새 태그를 추가하지 않고 기존 `<h2>` 태그에 슬러그화된(영숫자+하이픈만 남는) `id` 값만 주입한다.

### 1.5 CookieConsentBanner(REQ-008) — 실제 구현

`docs/harness/units/unit-04-note.md` §1과 §2-3은 CookieConsentBanner를 "이번 WU(WU-04)에 포함했다"고 기록했지만, 실제 코드베이스를 전수 검색(`grep -ril cookie`)한 결과 배너 마크업/JS/CSS가 어디에도 존재하지 않았다 — WU-04의 기록과 실제 구현 사이에 공백이 있었다. `docs/harness/traceability.md`도 REQ-008을 줄곧 "Not Started"로 정확히 반영하고 있었다(WU-04가 REQ-008 자체를 자신의 구현 상태로 갱신하지는 않았음). REQ-008(쿠키 사용 고지)은 02-planning.md §9/traceability.md가 처음부터 **WU-06 소유**로 배정한 요구사항이고, 이번 작업 지시("쿠키 고지 배너: ... 실제로 구현")도 명시적으로 이 구현을 요구했으므로, WU-04 기록의 정정이 아니라 **WU-06 자신의 REQ-008 산출물**로 지금 실제로 구현했다(WU-04 소유 파일을 리팩터링하지 않고, `config/templates/base.html`의 신규 블록 추가와 신규 `cookie-consent.js` 파일 추가로만 구현 — 범위 외 변경 없음).

**구현 방식(04 §2/§4/§5 명세 반영)**:
- 배너 마크업은 `base.html`에 **항상 서버 렌더링**된다(04 §0 "모든 화면은 JS 없이도 동작해야 한다" 원칙 — JS가 없으면 배너는 계속 노출되지만 비모달이라 콘텐츠 열람을 막지 않는다. "동의를 기억하는" 향상 기능만 JS에 의존한다).
- 재방문 시 재노출 방지: `cookie-consent.js`가 `localStorage.getItem("cookie_consent_ack")`를 확인해 있으면 배너를 숨기고, "확인" 클릭 시 값을 저장한다. base.html에 배치한 짧은 인라인 스크립트가 배너 마크업 바로 뒤에서 **동기적으로(defer 아님)** 먼저 실행되어, 재방문자에게 배너가 잠깐 보였다 사라지는 플래시를 방지한다.
- 키보드 접근성(04 §5): "확인" 버튼은 일반 `<button>`으로 Tab 순서에 포함되고, 포커스 트랩 없음(비모달), **Escape 키로 닫기 지원**(04 §5 "Should" 요구 충족).
- `prefers-reduced-motion: reduce`에서 등장 애니메이션 비활성화(04 §5 모션 원칙 — `@media (prefers-reduced-motion: no-preference)`로 감싸 reduce일 때 자동 미적용).
- localStorage 접근 실패(프라이빗 모드 등)는 `try/catch`로 흡수하고 배너가 계속 노출되는 것으로 안전하게 폴백한다(조용히 죽지 않고, 실패해도 페이지 자체는 정상 동작).

---

## 2. 설계서 대비 편차 (사유 포함)

1. **LegalPage를 단일 재사용 모델로 구현(3개 서브클래스 아님)** — §1.1, DEC-022에 근거와 함께 기록. 03 §3.2가 "또는"으로 명시적으로 승인한 두 옵션 중 하나를 선택한 것이며, 두 옵션 모두 결과(라우트/화면)가 동일해 규칙A 질문 대상이 아니라고 판단했다.
2. **TOC를 S-06 전용이 아니라 "h2가 있으면 자동 생성"하는 일반 규칙으로 구현** — §1.4 참고. 04가 금지하지 않은 확장이며 새 데이터/라우트 요구가 없다.
3. **쿠키 목적/보관기간을 `<table>`이 아닌 `<ul>` 목록으로 표현** — §1.2 참고. 이 프로젝트의 Wagtail 리치텍스트 기본 기능 세트에 표 기능이 없어(설정 변경은 범위 외) 동등한 정보를 지원되는 태그로 표현했다.
4. **CookieConsentBanner를 WU-06에서 실제로 구현(unit-04-note.md의 "포함" 기록은 실제 코드가 없었음)** — §1.5 참고. WU-04 소유 파일을 고치는 리팩터링이 아니라, REQ-008 소유 WU(WU-06)가 REQ-008 산출물을 만드는 정상적인 작업으로 처리했다. WU-04의 기록 자체를 수정하지는 않았다(과거 기록은 과거 판단 시점의 기록으로 그대로 두고, 이 노트에 공백과 조치를 명시하는 쪽을 택함 — 규칙 F의 "재작업 이력을 남긴다"는 취지와 일관).
5. **개인정보처리방침 "문의처"에 실제 이메일 주소를 기재하지 않음** — `SiteSettings.contact_email` 모델이 아직 어떤 WU도 만들지 않았고(03 §3.1 ERD에 정의만 있고 구현 WU 미배정), 가짜 이메일 주소를 지어내는 것은 오히려 방문자를 오도하므로, "사이트 운영자에게 연락"이라는 일반적 안내로 남기고 실제 연락 채널이 생기면(예: SiteSettings 구현 WU) 갱신하도록 §7에 인계 사항으로 남긴다.
6. **legal 앱 전용 `VIEW_CACHE_SECONDS` 상수를 독립 정의(blog.constants 재사용 안 함)** — 03 §1.2 "경계 원칙"(도메인 간 격리)을 따른 판단. blog와 값은 동일(10분)하지만 import 의존을 만들지 않았다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv_wu06`, 검증 후 삭제)에서 `pip install -r requirements.txt`(WU-01~05와 동일 버전, 신규 패키지 없음) 후 아래를 직접 실행해 확인했다.

### 3-1. 마이그레이션/시스템 체크 (dev, SQLite)

1. `python manage.py makemigrations legal` → `legal/migrations/0001_initial.py` 자동 생성(스키마 오류 없음).
2. **데이터 마이그레이션 최초 시도 시 실제 결함을 발견·수정**: `python manage.py migrate`(빈 SQLite에서 처음부터)를 처음 실행했을 때 `legal.0002_create_legal_pages` 단계에서 `IntegrityError: NOT NULL constraint failed: wagtailcore_page.locale_id`가 실제로 발생했다. 원인은 `home/migrations/0002_create_homepage.py`(이 프로젝트의 유일한 선례)가 `wagtailcore.0053_locale_model`(Locale 모델 도입) **이전**에 실행되어 `locale` 필드 자체가 없었던 반면, `legal.0001_initial`은 최신 wagtailcore 마이그레이션에 의존해 `locale`이 NOT NULL FK로 이미 존재하는 시점에 실행되기 때문이었다(`Migration.atomic = False`로 임시 전환해 원인을 특정한 뒤 제거). `wagtail.coreutils.get_supported_content_language_variant(settings.LANGUAGE_CODE)`로 wagtailcore의 기본 Locale 초기화 마이그레이션(`0054_initial_locale.py`)과 동일한 방식으로 Locale을 조회해 명시적으로 채워 해결했다(`legal/migrations/0002_create_legal_pages.py` 참고 주석). 수정 후 재실행하여 정상 동작을 확인했다.
3. `python manage.py migrate`(빈 SQLite, 수정 후 재실행) → 오류 없이 전체 적용, `legal.0001_initial`/`legal.0002_create_legal_pages` 모두 OK.
4. `python manage.py check` → "System check identified no issues (0 silenced)".
5. `python manage.py makemigrations --check --dry-run` → "No changes detected".
6. `home.0002_create_homepage`(run_before wagtailcore.0053)와 `legal.0001_initial`(wagtailcore 최신 의존) 사이에 순환 의존성(CircularDependencyError)이 발생하지 않는지 직접 재현해 확인했다 — home의 자체 앱 내 순서 제약(0001→0002, 0002가 wagtailcore.0053 이전이어야 함)과 legal의 별도 앱 의존(legal.0002가 legal.0001과 home.0002 둘 다에 의존)이 서로 다른 제약 축이라 충돌하지 않음을 실제 `migrate` 성공으로 실증했다.

### 3-2. HTTP 스모크 테스트 (`django.test.Client`, 임시 스크립트로 실행 후 삭제)

**dev 설정, 9건 전부 PASS**:
1. `GET /privacy-policy/` → 200, "개인정보처리방침"/"최종 업데이트"/"Render"/"Neon"/"Cloudflare"/"GitHub"/"목차"/`id="` 전부 포함(TOC 앵커 실제 생성 확인).
2. `GET /terms/` → 200, "이용약관"/"콘텐츠 정책"/"금융/투자, 의료/건강, 법률, 보험" 문구 정확히 포함(REQ-015 면책 문구 실사용자 화면 노출 확인).
3. `GET /cookies/` → 200, "쿠키 사용 고지"/"sessionid"/"csrftoken"/"localStorage" 포함.
4. `GET /`(홈) → 200, `id="cookie-consent"`/`id="cookie-consent-accept"`/"쿠키 사용 안내" 포함(배너가 전역으로 렌더링됨을 확인 — S-01뿐 아니라 모든 화면 공통).
5. `GET /`(홈) → Footer 법적 링크 3종(`href="/privacy-policy/"`/`href="/terms/"`/`href="/cookies/"`)이 더 이상 존재하지 않는 페이지를 가리키지 않음(WU-04가 남긴 "일시적 404" 상태가 이번 WU로 자동 해소됨, unit-04-note.md §7-4가 예고한 대로).
6. `GET /terms/` → `<link rel="canonical"` 존재(WU-05 SEO 체계에 legal 페이지도 자동 편입됨 확인 — canonical_url 컨텍스트 프로세서는 페이지 종류에 무관하게 전역 적용되므로 별도 코드 없이 자동 동작).
7. `GET /not-a-real-page/` → 404(회귀 없음).
8. `GET /sitemap.xml` → 200, `/privacy-policy/`·`/terms/`·`/cookies/` 전부 포함(LegalPage.get_sitemap_urls가 정상 동작 확인).
9. `GET /robots.txt` → 200(회귀 없음).

**TOC 앵커 실제 데이터 검증**: `/privacy-policy/` 응답에서 `<h2 id="...">` 8개를 추출해 UTF-8로 파일에 기록·직접 확인한 결과, 한글 제목이 `slugify(allow_unicode=True)`로 정확히 슬러그화됨을 확인했다(예: "수집하는 개인정보 항목" → `id="수집하는-개인정보-항목"`, "쿠키(Cookie)의 사용" → `id="쿠키cookie의-사용"`). 터미널에 직접 출력했을 때는 콘솔 코드페이지 문제로 글자가 깨져 보였으나, 파일로 UTF-8 기록 후 확인해 실제 데이터는 정상임을 재확인했다(인코딩 표시 문제와 실제 데이터 결함을 혼동하지 않도록 별도로 검증).

**Wagtail 어드민 회귀/신규 기능 확인**: 임시 슈퍼유저로 로그인 후 (a) `LegalPage` 인스턴스(예: `/terms/`)의 `/cms-admin/pages/<pk>/edit/` → 200(공용 모델도 정상적으로 어드민 편집 폼이 렌더링됨 확인), (b) HomePage 페이지 탐색기(`/cms-admin/pages/<homepage_pk>/`) 응답에 "개인정보처리방침"/"이용약관"/"쿠키 사용 고지" 3개 자식 페이지가 모두 노출됨을 확인(데이터 마이그레이션이 만든 페이지가 어드민에서도 정상적으로 보이고 향후 운영자가 직접 수정 가능함을 실증).

**회귀 스모크**: `GET /`, `/feed.xml`, `/sitemap.xml`, `/robots.txt`, `/cms-admin/login/`, 존재하지 않는 경로(404) 전부 재확인해 WU-01~05 기존 기능에 영향이 없음을 확인했다.

### 3-3. production 유사 설정 (WU-01~05와 동일 방법론)

`config/settings/it_test_prodlike.py`(`production.py` 상속 + `DATABASES`만 SQLite로 재정의, 검증 후 삭제)로:
- `python manage.py check` → "System check identified no issues".
- `python manage.py migrate`(처음부터) → 오류 없이 전체 적용(legal 포함).
- `python manage.py collectstatic --noinput`(WhiteNoise `CompressedManifestStaticFilesStorage`) → "0 static files copied, 217 unmodified, 635 post-processed"(신규 `cookie-consent.js`/`components.css` 변경분 포함 매니페스트 정상 생성).
- `HTTP_X_FORWARDED_PROTO: https` 헤더를 실은 요청으로 `/privacy-policy/`·`/terms/`·`/cookies/` 전부 200 확인, `SECURE_SSL_REDIRECT`/`SECURE_PROXY_SSL_HEADER` 조합에서 무한 리다이렉트(DEF-001 계열) 재발 없음을 확인(헤더 없이 요청 시 301 한 번만 발생, 루프 아님).
- `sitemap.xml`/canonical에 legal 페이지의 절대 URL이 실제 요청 도메인(`example.com`) 기준으로 나옴을 확인(DEC-021 로직이 legal 페이지에도 그대로 적용됨).

**로컬 검증 중 발견했으나 WU-06이 직접 수정하지 않은 사전 존재 이슈(범위 외, 정보 공유 목적으로 기록)**: 위 HTTPS 시뮬레이션에서 canonical/sitemap URL에 `:80`이 그대로 붙어 나오는 현상(`https://example.com:80/...`)을 관찰했다. **이 문제가 legal 페이지 고유의 결함이 아님을 홈페이지(`/`)에 대해 동일한 요청으로 재현해 확인**했다 — WU-05가 만든 `core/seo.py`/`core/context_processors.py`(DEC-020/DEC-021)의 기존 로직이 모든 페이지 종류에 동일하게 적용되는 것이며, `django.test.Client`가 `SERVER_PORT`를 명시적으로 443으로 맞추지 않고 `X-Forwarded-Proto`만 흉내 내는 로컬 테스트 환경의 한계인지, 실제 Render 배포 환경(Gunicorn이 바인딩하는 내부 포트가 443이 아님)에서도 재현되는 실질적 결함인지는 이번 WU의 범위(REQ-007/008/009/015)를 벗어난 WU-05 소유 코드 영역이라 직접 조사·수정하지 않았다. WU-05 소유 파일(`core/seo.py`, `core/context_processors.py`)에 대한 변경은 "범위를 벗어난 변경"에 해당하므로 손대지 않았으며, 이 관찰 사실만 다음 단계(6단계 또는 담당 WU 재작업)가 판단할 수 있도록 기록으로 남긴다.

### 3-4. 정리

검증에 사용한 `.venv_wu06`, `db.sqlite3`, `db_prodlike.sqlite3`, `media/`, `staticfiles/`, `config/settings/it_test_prodlike.py`, 임시 검증 스크립트(스크래치패드 경로), 전 앱의 `__pycache__/`는 전부 삭제했다. `git status --porcelain`으로 diff에 소스만 남았음을 최종 확인했다(신규 `webapp/legal/`, 수정된 `webapp/config/settings/base.py`/`config/templates/base.html`/`config/static/css/components.css`, 신규 `webapp/config/static/js/cookie-consent.js`). 이전 WU들과 동일하게 이번 WU 산출물도 아직 커밋하지 않았다(사용자/오케스트레이터의 명시적 커밋 지시를 기다림).

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체(및 `webapp/`)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 이번에도 재확인**했다(직접 검색, WU-01~05와 동일 결론) — 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 Python 파일 전체(`legal/apps.py`, `legal/constants.py`, `legal/models.py`, `legal/migrations/0001_initial.py`, `legal/migrations/0002_create_legal_pages.py`, `config/settings/base.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다(§3의 `manage.py check`/`makemigrations --check`/실제 마이그레이션·렌더링 실행이 이를 실행 기반으로 재확인). CSS/JS/HTML 템플릿 린터도 설정되어 있지 않아, `collectstatic`과 실제 렌더링(§3)으로 구문·참조 오류가 없음을 실행 기반으로 확인했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 6건은 전부 사유와 함께 명시했고, 모두 "설계서가 명시적으로 승인한 선택지 중 하나 선택" 또는 "지원되지 않는 리치텍스트 기능에 대한 동등한 대체 표현" 수준이지 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — 존재하지 않는 legal 페이지 slug는 Wagtail 표준 페이지 트리 서빙이 자동으로 404 처리한다(별도 뷰 코드가 없으므로 우리가 예외를 삼킬 지점 자체가 없음). `cookie-consent.js`의 `localStorage` 접근은 `try/catch`로 감싸 실패 시 조용히 무시하되 배너는 계속 노출되는 안전한 폴백으로 처리했다(예외를 삼키고 "성공한 척"하지 않음 — 저장 실패 시 다음 방문에 배너가 다시 뜨는 것이 정직한 동작).
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 이 WU에는 사용자 입력을 받는 경계가 없다(법적 페이지는 정적 콘텐츠, 쿠키 배너는 버튼 클릭/ESC 키 이벤트일 뿐 데이터 입력이 아님). TOC 앵커 생성 정규식은 운영자(에디터) 리치텍스트 입력만 다루며(03 §5.1 신뢰 경계), 슬러그화 함수(`slugify`)가 결과를 영숫자+하이픈으로 제한해 안전하게 처리한다.
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 이번 변경분은 정적 콘텐츠(마이그레이션 데이터)/템플릿/정적 자산/설정 등록만 다루며 시크릿이 필요한 코드가 없다. 검증용 production 유사 설정(`it_test_prodlike.py`)은 환경변수로만 값을 주입했고 삭제까지 완료했다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `blog/`, `custom_images/`, `core/`(WU-04/03/05 소유)는 건드리지 않았다. `config/templates/partials/header.html`/`footer.html`(WU-04 소유)도 변경하지 않았다(footer의 법적 링크 3종은 WU-04가 이미 올바른 경로로 만들어 뒀으므로 그대로 유효해짐). `config/templates/base.html`은 CookieConsentBanner를 위한 블록 추가만 했고 기존 블록/구조는 그대로 유지했다. §3-3에서 발견한 WU-05 소유 `core/seo.py`/`core/context_processors.py`의 잠재 이슈는 기록만 남기고 코드를 수정하지 않았다(범위 외 변경 금지 원칙 준수).

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-007/REQ-008/REQ-009/REQ-015 행을 갱신했다: "구현 상태"를 "Not Started" → "구현 완료(`unit-06-note.md`, 구현 근거 파일 경로)"로, "단위테스트"를 "대기(6단계)"로 채웠다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다(사실을 그대로 반영).

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **법적 문구는 실제 법률 검토 전 초안**: §1.2 참고. 개인정보처리방침/이용약관/쿠키고지 본문은 03 §5.6이 요구한 항목을 모두 반영했지만, 실제 공개 서비스로 나가기 전에는 법률 전문가의 검토가 필요하다(페이지 본문에도 이 사실을 명시했다). 6단계 테스터는 "문구가 실제로 화면에 렌더링되는가"만 검증하면 되고, 법률적 정확성 검증은 이 하네스의 범위가 아니다.
2. **개인정보처리방침 "문의처"에 구체적 연락 채널 없음**: §2-5 참고. `SiteSettings` 모델이 아직 구현되지 않아 실제 연락처(이메일 등)를 채울 수 없었다. 담당 WU가 `SiteSettings`를 구현하면 이 페이지 본문도 함께 갱신해야 한다(자동으로 해소되지 않음 — 콘텐츠는 리치텍스트라 운영자가 어드민에서 직접 수정 가능).
3. **`core/seo.py`/`core/context_processors.py`의 포트 표기 이슈(§3-3)**: WU-06이 발견했지만 WU-05 소유 코드라 직접 수정하지 않았다. 실제 Render 배포 환경에서 canonical/sitemap URL에 내부 포트가 노출되는지는 10단계(배포테스트) 또는 WU-05 재작업에서 실측 확인이 필요하다.
4. **REQ-016(뉴스레터) 미구현 상태와의 정합성**: 개인정보처리방침이 "뉴스레터 구독 시 수집"을 설명하지만, 실제 구독 폼(WU-07)은 아직 없다. 이는 모순이 아니라 정책을 먼저 명시하고 기능이 뒤따르는 정상적인 점진적-완성 상태다(WU-04가 남긴 법적 링크 3종의 "일시적 404"와 반대 방향의 동일한 성격 — 이번엔 정책이 기능보다 먼저 존재).
5. **뷰 캐시(10분 TTL)로 인한 지연 반영**: LegalPage.serve()에도 blog/home과 동일한 10분 캐시를 적용했다(§1.5 아님, §1.1 뷰 캐시 설명 참고). 운영자가 어드민에서 법적 페이지 내용을 수정해도 최대 10분간 이전 내용이 보일 수 있다 — unit-04-note.md §7-3이 이미 기록한 것과 동일한 트레이드오프이며, 6단계 테스터는 캐시를 고려해 테스트 순서를 설계하거나(`cache.clear()`) 캐시 우회가 필요하다.
6. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다림). 원격 push는 수행하지 않았다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일). **주의**: 모든 legal 뷰가 `@method_decorator(cache_page(10분))`으로 캐시되므로, 데이터를 바꾼 뒤 즉시 재요청해 검증하려면 매 시나리오 전에 캐시를 비우거나(`from django.core.cache import cache; cache.clear()`) 프로세스를 재시작할 것.

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, WU-01~05와 동일 버전).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `python manage.py migrate`가 **빈 DB에서 처음부터** 오류 없이 끝나는가(특히 `legal.0002_create_legal_pages` 데이터 마이그레이션이 `IntegrityError` 없이 성공하는가 — §3-1의 locale 결함이 재발하지 않는지 확인).
3. `python manage.py check`가 "System check identified no issues"를 출력하는가.
4. `python manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가.
5. `GET /privacy-policy/` → 200이고, 응답 본문에 "개인정보처리방침"·"최종 업데이트"·"Render"·"Neon"·"Cloudflare"·"GitHub"·목차 링크(`<a href="#...">`)가 포함되는가.
6. `GET /terms/` → 200이고, 응답 본문에 "이용약관"과 "**금융/투자, 의료/건강, 법률, 보험**" 문구(REQ-015 면책 문구, 정확한 문자열)가 포함되는가.
7. `GET /cookies/` → 200이고, 응답 본문에 "쿠키 사용 고지"·"sessionid"·"csrftoken"이 포함되는가.
8. `GET /`(홈) → 200이고, 응답 본문에 `id="cookie-consent"`와 `id="cookie-consent-accept"`가 포함되는가(배너가 홈뿐 아니라 임의의 다른 화면, 예: `GET /privacy-policy/`에서도 동일하게 포함되는지 최소 1개 추가 화면에서 교차 확인).
9. `GET /`(홈) 응답에 `href="/privacy-policy/"`, `href="/terms/"`, `href="/cookies/"`가 포함되고, 그 세 URL을 실제로 요청하면 전부 200이 오는가(WU-04가 남긴 "일시적 404" 해소 확인).
10. `/privacy-policy/` 응답에서 `<h2 id="...">` 개수를 세어 8개 이상인지, 그중 하나 이상이 한글 슬러그(예: `id="수집하는-개인정보-항목"`류)로 생성되는지 확인하는가.
11. 브라우저(또는 headless 브라우저 MCP가 있다면 그것을 활용, 없으면 수동 조작) 기준: 첫 방문 시 쿠키 배너가 보이고, "확인" 버튼을 클릭하면 배너가 사라지며, 같은 브라우저로 재방문(새 요청)해도 배너가 다시 나타나지 않는가(`localStorage.getItem("cookie_consent_ack")`가 설정돼 있는지로 판별 가능). `localStorage.clear()` 후 재방문하면 다시 나타나는가.
12. 배너가 노출된 상태에서 Tab 키로 "확인" 버튼에 포커스가 가고, Escape 키를 누르면 배너가 닫히는가(포커스 트랩 없음 — Tab을 계속 눌러도 배너 밖 요소로 자유롭게 이동 가능한지 확인).
13. `prefers-reduced-motion: reduce`가 설정된 환경(브라우저 개발자도구 에뮬레이션)에서 배너 등장 애니메이션이 비활성화되는가.
14. `GET /sitemap.xml` → 200이고, `/privacy-policy/`·`/terms/`·`/cookies/` 세 URL이 모두 포함되는가.
15. `GET /terms/` 응답에 `<link rel="canonical"`이 포함되는가(WU-05 SEO 체계 자동 편입 확인).
16. Wagtail 어드민에 로그인해 `/cms-admin/pages/<legalpage_pk>/edit/`(임의의 legal 페이지 pk)에 접근하면 200이고 편집 폼이 정상 렌더링되는가(운영자가 실제로 문구를 수정할 수 있는지 확인).
17. 회귀: `GET /`, `/feed.xml`, `/sitemap.xml`, `/robots.txt`, `/cms-admin/login/`이 이전 WU와 동일하게 정상 동작하는가.
18. (production 유사) `config/settings/production.py`를 상속하되 `DATABASES`만 SQLite로 재정의한 설정 모듈로 더미 R2 환경변수를 채운 뒤 `python manage.py check`/`migrate`/`collectstatic --noinput`이 모두 오류 없이 끝나는가. `HTTP_X_FORWARDED_PROTO: https` 헤더로 `/privacy-policy/`·`/terms/`·`/cookies/`를 요청하면 200이 오고, 헤더 없이 요청하면 무한루프가 아닌 301 한 번만 오는가(DEF-001 계열 회귀 없음 확인).
19. 검증 후 사용한 venv/DB(`db.sqlite3`, `db_prodlike.sqlite3` 등)/staticfiles/media/임시 설정 모듈/임시 스크립트/`__pycache__`를 정리했는지, diff에 포함되지 않았는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~19번 인수 조건을 입력으로 `docs/harness/units/unit-06-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-06)의 7단계(통합테스트, WU-01/04/05와의 조립 검증 포함) 착수 여부를 오케스트레이터가 판단한다.
