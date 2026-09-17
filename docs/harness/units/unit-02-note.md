# WU-02 — 콘텐츠 모델 및 CRUD 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-02, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §3 데이터 모델/DEC-007), `docs/harness/04-ux-design.md`(v1.2, PASS, 특히 §5 접근성/§7 정합성 체크), `docs/harness/decisions.md`(DEC-001~015), `docs/harness/units/unit-01-note.md`(WU-01이 만든 `webapp/` 골격)
- 작성일: 2026-09-16
- 대상 REQ-ID: REQ-001(콘텐츠 CRUD/편집 워크플로), REQ-002(카테고리/태그 분류체계)

---

## 1. 구현 범위

WU-01이 만든 `webapp/`(Wagtail 7.4 LTS + Django 5.2 LTS, `home` 앱, `config/settings`) 위에 신규 `blog` 앱을 추가했다.

```
webapp/
  blog/                              (신규)
    __init__.py
    apps.py                          BlogConfig
    blocks.py                        StreamField 블록 정의(문단/이미지/인용/FAQ)
    models.py                        Category(Snippet), BlogPageTag(taggit), BlogPostPage(Page)
    migrations/
      __init__.py
      0001_initial.py                makemigrations로 생성, 로컬 SQLite에 실제 적용/검증
  config/settings/base.py            (수정) INSTALLED_APPS에 "blog" 추가
```

### 1.1 BlogPostPage (REQ-001)

- `wagtail.models.Page`를 상속한다(DEC-007 그대로 따름). `title`/`slug`는 Wagtail `Page`가 기본 제공.
- `intro`(CharField, 목록 카드용 짧은 요약), `body`(StreamField), `category`(FK, 필수), `featured_image`(FK, nullable), `tags`(django-taggit).
- **임시저장/예약발행/리비전은 커스텀 재구현하지 않았다.** `go_live_at`/`expire_at`/`live`/`has_unpublished_changes`/`first_published_at`/`last_published_at`/`owner`/`PageRevision`(`save_revision()`/`.publish()`)은 Wagtail 코어가 제공하는 것을 그대로 사용한다(03 §3.2, DEC-007).
- `content_panels = Page.content_panels + [intro, featured_image, category, tags, body]`로 어드민 편집 인터페이스를 구성했다. 별도 `PageChooserPanel`은 필요하지 않았다 — 이 모델에 다른 Page를 참조하는 필드가 없기 때문이다(태그/카테고리 선택은 표준 `FieldPanel`이 자동으로 적절한 위젯(오토컴플리트/셀렉트)을 제공한다, Wagtail 표준 동작).
- `parent_page_types = ["home.HomePage"]`, `subpage_types = []`로 페이지 트리 위치를 제한했다(홈 바로 하위에만 생성 가능, 게시물 자신은 하위 페이지를 갖지 않음) — 03 §3.1 ERD가 암시하는 트리 구조를 명시적 제약으로 옮긴 것이며 새로운 기능 추가가 아니다.

### 1.2 body(StreamField) 블록 — 접근성 요구사항 반영 (04 §5, §7)

`blog/blocks.py`에 03 §3.2가 명시한 "문단/이미지/인용/FAQ블록"을 그대로 구현했다.

- `paragraph`: `RichTextBlock`
- `image`(`ImageBlock`, StructBlock): `image`(`ImageChooserBlock`) + **`alt_text`(`CharBlock`, `required=True`)** + `caption`(선택). 04-ux-design.md §5/§7이 "StreamField 이미지 블록에는 전용 alt 입력 필드가 03 설계서에 명시되어 있지 않으므로 WU-02 구현 시 반드시 포함해야 한다"고 지적한 접근성 요구사항을 이 필드로 충족한다. `alt_text`를 필수로 지정했으므로, 어드민에서 alt 텍스트 없이 이미지 블록을 저장하려 하면 Wagtail의 StructBlock 검증(`required=True`)이 막는다.
- `quote`(`QuoteBlock`): `quote` + `attribution`(선택)
- `faq`(`FAQBlock`): `items`(`ListBlock(FAQItemBlock)`, 각 항목은 `question`/`answer`) — REQ-017(AI 검색 대응 질문-답변형 콘텐츠, WU-05)이 사용할 데이터 구조. FAQPage JSON-LD 렌더링 자체는 이번 WU 범위가 아니다(03 §4가 WU-05로 귀속).

### 1.3 Category / Tag (REQ-002)

- `Category`: 별도 Django 모델을 `@register_snippet`으로 Wagtail Snippet 등록(03 §3.2 지시대로). `name`(unique), `slug`(unique, blank 허용 — 비워두면 `save()`에서 `slugify(name, allow_unicode=True)`로 자동 생성). 어드민에서 스니펫 목록(`/cms-admin/snippets/blog/category/`)으로 CRUD 가능.
- `Tag`: 커스텀 모델을 새로 만들지 않고 **django-taggit 표준 through 모델 패턴**을 사용했다 — `BlogPageTag(TaggedItemBase)` + `BlogPostPage.tags = ClusterTaggableManager(through="blog.BlogPageTag")`. 이는 Wagtail 공식 튜토리얼이 권장하는 정확한 패턴이며(03 §3.2 "django-taggit의 TaggedItemBase 표준 패턴"과 문자 그대로 일치), `taggit`/`modelcluster`는 이미 WU-01의 `INSTALLED_APPS`에 존재하고 Wagtail 자체의 전이 의존성으로 설치되어 있어 `requirements.txt`에 새 패키지를 추가하지 않았다.

### 1.4 마이그레이션 (REQ-001/002)

- `python manage.py makemigrations blog` → `blog/migrations/0001_initial.py` 1개 생성(Category/BlogPageTag/BlogPostPage 생성 + BlogPageTag.content_object 필드 추가).
- 로컬 SQLite(`config.settings.dev`)에 `python manage.py migrate` 실제 적용 확인(§4 참고). `makemigrations --check --dry-run` → "No changes detected"(모델과 마이그레이션이 정확히 일치).

---

## 2. 설계서 대비 편차 (사유 포함)

1. **category FK를 필수(non-nullable)로 구현**: 03 §3.2 본문은 "category(FK)"라고만 쓰고 nullable 여부를 명시하지 않았지만(반면 `featured_image`는 "FK, nullable"이라고 명시적으로 구분), 같은 문서 §3.1 ERD의 `BLOGPOSTPAGE }o--|| CATEGORY : belongs_to` 표기(카테고리 쪽 카디널리티 `||` = 정확히 1)는 "게시물은 반드시 하나의 카테고리에 속한다"는 것을 명확히 나타낸다. 두 서술이 실질적으로 모순되지 않고(하나는 생략, 하나는 명시) 단일하게 해석 가능하다고 판단해 규칙A-③ 질문으로 올리지 않고 ERD를 따라 필수 FK(`on_delete=PROTECT`, 카테고리가 게시물에 쓰이는 동안은 삭제 불가)로 구현했다.
2. **`featured_image`/`ImageChooserBlock`에 `get_image_model_string()` 간접 참조 사용**: 03 §3.2는 WU-03에서 Wagtail 기본 `Image`를 상속한 `CustomImage`로 교체할 계획을 이미 명시했다(DEC-008, R2 연동). Wagtail 공식 문서가 권장하는 대로 지금부터 `wagtail.images.get_image_model_string()`을 FK 대상으로 쓰고 `ImageChooserBlock`은 기본적으로 "현재 활성 이미지 모델"을 참조하도록 했다 — 이렇게 하면 WU-03이 `CustomImage`로 교체할 때 이번 WU의 마이그레이션을 다시 손댈 필요가 없다. 새로운 아키텍처 결정이 아니라 이미 확정된 DEC-008의 자연스러운 구현 디테일이라 별도 decisions.md 항목을 추가하지 않았다.
3. **BlogPostPage 공개(프런트엔드) 템플릿 미작성**: `blog/templates/blog/blog_post_page.html`을 만들지 않았다. 04-ux-design.md는 "공개 열람 화면(목록/상세/카테고리/태그/RSS/반응형 레이아웃)"을 WU-04로 명시적으로 분리했고, ArticleBody 컴포넌트(블록별 렌더링/접근성 마크업)도 04 §4가 WU-04 몫으로 정의한다. 이번 WU는 지시사항 1~5번(모델/Category-Tag/어드민 편집/REQ 대조/마이그레이션)에 템플릿 작성이 포함되어 있지 않으므로 범위를 지키기 위해 만들지 않았다. **영향**: 지금 상태로 `live=True`인 게시물의 공개 URL(`/blog/<slug>/`)에 접속하면 `TemplateDoesNotExist`(500)가 발생하고, 어드민의 "Preview" 버튼도 같은 이유로 실패한다 — 편집/저장/리비전/예약발행 자체(이번 WU의 인수 대상)는 전혀 영향받지 않는다. §5(수동 확인 필요)에 다시 명시.
4. **`blog/blocks.py`에 StreamField 블록의 프런트엔드 `template` Meta 옵션을 지정하지 않음**: 위 3번과 같은 이유(WU-04가 ArticleBody 마크업을 설계·구현). 블록 데이터 구조(`ImageBlock.alt_text` 등)만 이번 WU 책임이다.
5. **범위 외로 명시적으로 만들지 않은 것**: `LegalPage`(WU-06), `NewsletterSubscriber`(WU-07), `SiteSettings`(WU-05/06과 연계) — 03 §3.2가 정의하지만 이번 WU-02 지시사항(REQ-001/002만 대상)에는 없으므로 만들지 않았다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv_wu02`, 검증 후 삭제)에서 `pip install -r requirements.txt`(WU-01과 동일 버전, 신규 패키지 추가 없음) 후 아래를 직접 실행해 확인했다.

1. `python manage.py makemigrations blog` → `blog/migrations/0001_initial.py` 생성(위 §1.4).
2. `python manage.py migrate`(dev, SQLite) → Wagtail 코어 포함 전체 마이그레이션 및 `blog.0001_initial` 오류 없이 적용.
3. `python manage.py makemigrations --check --dry-run` → "No changes detected".
4. `python manage.py check` → "System check identified no issues (0 silenced)".
5. **ORM으로 직접 CRUD 왕복 + 어드민 HTTP 스모크 테스트**(`django.test.Client`, 임시 스크립트로 실행 후 삭제) — 총 25건 전부 PASS:
   - Category 생성 시 `slug` 미입력이면 자동 생성됨.
   - `HomePage.add_child(instance=post)`로 `BlogPostPage` 생성(CREATE), `category`/`tags`/`body`(문단·이미지·인용·FAQ 4개 블록 전부 포함) 정상 저장. 이미지 블록의 `alt_text`가 실제로 저장됨을 확인.
   - slug로 조회(READ) 성공.
   - `live=False`(초안) 상태에서 `save_revision()`만 호출 → `PageRevision` 생성되지만 `live`는 여전히 `False`(임시저장 동작 확인, REQ-001).
   - `go_live_at`을 미래 시각으로 설정 후 `save_revision().publish()` → **예약발행**: `live`는 여전히 `False`이고 `go_live_at`/`expire_at` 값이 정확히 저장됨(REQ-001).
   - `go_live_at`을 제거하고 다시 `save_revision().publish()` → `live=True`로 전환(즉시 게시).
   - `BlogPostPage.revisions.count()`가 누적되어 리비전 이력이 실제로 쌓임을 확인(REQ-001).
   - `title`/`category` 수정 후 재발행(UPDATE) → 변경사항이 조회 결과에 반영됨.
   - `delete()` 호출 후 더 이상 조회되지 않음(DELETE).
   - 어드민 HTTP 경로(모두 `force_login`된 슈퍼유저로 요청):
     - `GET /cms-admin/pages/<home.pk>/add_subpage/` → 200, 응답에 `blogpostpage`가 추가 가능한 타입으로 노출됨.
     - `GET /cms-admin/snippets/blog/category/` → 200(스니펫 목록).
     - `GET /cms-admin/snippets/blog/category/add/` → 200(스니펫 추가 폼).
     - 신규 페이지 생성 후 `GET /cms-admin/pages/<post.pk>/edit/` → 200, 응답 HTML에 `category`/`tags`/`body` 필드가 모두 렌더링됨(`FieldPanel` 구성이 실제로 동작함을 확인).
6. 회귀 확인: `GET /`(홈) → 200, `GET /cms-admin/login/` → 200 — WU-01이 만든 기존 경로가 `blog` 앱 추가로 깨지지 않음을 확인.
7. 검증에 사용한 `.venv_wu02`, `db.sqlite3`, `staticfiles/`, `media/`, `__pycache__/`, 임시 검증 스크립트는 전부 삭제하고 마쳤다(diff에는 소스 코드만 남음, `find webapp -type f` 재확인 완료).

**로컬에서 확인하지 못한 것**: 실제 이미지 업로드(파일 첨부를 통한 `ImageChooserBlock`/`featured_image` 선택)는 WU-03(R2 연동)이 아직 없어 R2 자격증명 없이는 의미 있게 검증할 수 없다 — 이번 검증은 이미지 FK/블록 값을 `None`으로 둔 채(또는 값 없이) 데이터 구조/필수값 검증(`alt_text`)만 확인했다. 실제 이미지 첨부 CRUD는 WU-03 완료 후 재검증이 필요하다.

---

## 4. 게이트 1 — 정적 분석/린트

WU-01 노트와 동일하게, 저장소(`AI-AUTO-WORK` 루트 및 `webapp/`)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 재확인**했다(직접 검색). 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 파일 전체(`blog/__init__.py`, `blog/apps.py`, `blog/blocks.py`, `blog/models.py`, `blog/migrations/__init__.py`, `blog/migrations/0001_initial.py`, `config/settings/base.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] 설계서/디자인서 명세와 실제 구현이 일치하는가 — 일치(§2 편차 항목 5건은 전부 사유와 함께 명시했고, 모두 "WU-02 범위 밖으로 명시적으로 미룬 것" 또는 "ERD 근거로 단일 해석한 것"이지 임의 추측이 아니다).
- [x] 에러 처리가 누락된 경로가 없는가 — `category`는 `null=False`이므로 값 없이 저장을 시도하면 Django ORM/DB 제약(NOT NULL)이 막는다(조용히 통과하지 않음). `Category.save()`의 slug 자동생성은 예외를 삼키지 않는다(단순 조건부 대입). `on_delete=PROTECT`로 사용 중인 카테고리를 실수로 삭제하지 못하게 막는다.
- [x] 입력값 검증이 시스템 경계(사용자 입력)에서 이루어지는가 — 이 WU의 유일한 "사용자 입력 경계"는 Wagtail 어드민 폼이며, `alt_text`를 `required=True`로 선언해 Wagtail의 표준 `StructBlock`/폼 검증이 비어있는 값을 거부하게 했다(접근성 요구사항을 시스템 경계에서 강제). 공개 사용자 입력(방문자 폼 등)은 이번 WU에 없음(뉴스레터는 WU-07).
- [x] 하드코딩된 시크릿/자격증명이 없는가 — 없음. 이번 변경분에는 설정값/모델 정의만 있고 시크릿이 필요한 코드가 없음.
- [x] 범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가 — `home` 앱, `config/settings/dev.py`, `config/settings/production.py`, `config/urls.py`, `config/middleware.py` 등 WU-01 산출물은 건드리지 않았다. `config/settings/base.py`는 `INSTALLED_APPS`에 `"blog"` 한 줄만 추가했다(그 외 무변경). `requirements.txt`에 새 패키지를 추가하지 않았다(taggit/modelcluster는 이미 Wagtail 의존성으로 설치되어 있었음, §1.3 확인).

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-001, REQ-002 행을 갱신했다: "구현 상태" 컬럼을 "Not Started" → "구현 완료(`unit-02-note.md`, ...)"로, "단위테스트" 컬럼을 "대기(6단계)"로 채웠다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다(사실을 그대로 반영, 빠뜨린 것이 아님).

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **공개 프런트엔드 템플릿 부재(§2-3)**: `live=True`인 `BlogPostPage`의 공개 URL(`/blog/<slug>/`)과 어드민 "Preview" 버튼은 WU-04가 `blog/templates/blog/blog_post_page.html`(및 블록별 템플릿)을 추가하기 전까지 `TemplateDoesNotExist`로 실패한다. 6단계는 이것이 이번 WU의 결함이 아니라 의도된 범위 경계임을 확인하고, 실패 원인이 정확히 `TemplateDoesNotExist`(다른 예외가 아님)인지만 확인하면 된다.
2. **실제 이미지 첨부 미검증(§3 로컬 확인 못한 것)**: R2 연동(WU-03) 전이라 `featured_image`/이미지 블록에 실제 파일을 업로드해 첨부하는 과정은 검증하지 못했다. WU-03 완료 후 재검증 권고.
3. **Category `on_delete=PROTECT` 운영 정책 확인**: 게시물이 하나라도 딸려 있는 카테고리는 어드민에서 삭제가 막힌다(예외를 던지는 대신 Wagtail이 삭제 확인 화면에서 이를 알려줌). 03/04번 설계서에 이 구체적 동작이 명시되어 있지 않아 에이전트 판단(§2-1)으로 정했다 — 운영자가 이 제약이 불편하다고 판단하면 이후 WU에서 재검토 대상이다(낮은 위험, 언제든 `on_delete` 값만 바꾸는 가역적 변경).
4. **FAQ 블록의 JSON-LD 미구현**: `FAQBlock` 데이터 구조는 이번 WU가 만들었지만, `schema.org/FAQPage` 구조화 데이터 렌더링은 03 §4가 WU-05로 귀속한 범위이므로 만들지 않았다.
5. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다림). 원격 push는 수행하지 않았다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일).

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, WU-01과 동일 버전).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `python manage.py migrate`가 오류 없이 끝나는가(특히 `blog.0001_initial`이 `wagtailcore`/`wagtailimages`/`taggit` 마이그레이션에 대한 의존성 문제 없이 적용되는지).
3. `python manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가(모델=마이그레이션 일치 확인).
4. `python manage.py check`가 "System check identified no issues"를 출력하는가.
5. ORM으로 `Category.objects.create(name="테스트", slug="")`를 호출하면 `slug`가 `"테스트"`(또는 그 slugify 결과)로 자동 채워지는가.
6. `HomePage` 인스턴스(`Page.objects.get(slug="home").specific`)에 `add_child(instance=BlogPostPage(...))`로 게시물을 생성할 수 있는가 — 이때 `category`를 지정하지 않으면 DB 제약으로 저장이 실패하는가(필수 FK 확인).
7. 생성한 `BlogPostPage.body`에 `paragraph`/`image`/`quote`/`faq` 4개 타입 블록을 각각 최소 1개 포함시켜 저장할 수 있고, 저장 후 다시 읽었을 때 `image` 블록의 `value["alt_text"]`가 그대로 보존되는가.
8. `django-taggit` 기반 `tags`(예: `post.tags.add("a", "b")`)가 정상 저장/조회되는가.
9. 새로 만든 페이지가 `live=False`(초안) 상태에서 `save_revision(user=...)`만 호출하면(publish 호출 없이) `PageRevision`은 생성되지만 재조회한 페이지의 `live`는 여전히 `False`인가(임시저장 동작, REQ-001).
10. `go_live_at`을 미래 시각으로 설정하고 `save_revision(user=...).publish()`를 호출하면, 재조회한 페이지의 `live`가 여전히 `False`이고 `go_live_at`/`expire_at` 값이 저장되어 있는가(예약발행 동작, REQ-001).
11. `go_live_at`을 `None`으로 되돌리고 다시 `save_revision(user=...).publish()`를 호출하면 `live=True`로 전환되는가(즉시 게시).
12. 위 8~11번 과정을 거치며 `BlogPostPage.revisions.count()`가 누적되어 2건 이상인가(리비전 이력, REQ-001).
13. 게시된 페이지의 `title`/`category`를 수정하고 다시 `save_revision().publish()`하면, 재조회 결과에 변경사항이 반영되는가(UPDATE).
14. 페이지를 `delete()`한 뒤 같은 id로 더 이상 조회되지 않는가(DELETE).
15. Wagtail 관리자 계정(`force_login` 또는 실제 로그인)으로 `GET /cms-admin/pages/<home.pk>/add_subpage/`를 호출하면 200이 오고, 응답에 `blogpostpage`가 추가 가능한 페이지 타입으로 노출되는가.
16. `GET /cms-admin/snippets/blog/category/`(목록)와 `GET /cms-admin/snippets/blog/category/add/`(추가 폼)가 각각 200을 반환하는가(Category 스니펫 어드민 CRUD 인터페이스 확인).
17. 임의의 `BlogPostPage`에 대해 `GET /cms-admin/pages/<pk>/edit/`가 200을 반환하고, 응답 HTML에 `category`/`tags`/`body` 필드가 실제로 렌더링되어 있는가(편집 인터페이스 구성 확인).
18. (회귀) `GET /`(홈)이 200을, `GET /cms-admin/login/`이 200을 계속 반환하는가(`blog` 앱 추가로 WU-01 기존 경로가 깨지지 않았는지).
19. (접근성 회귀) `blog/blocks.py`의 `ImageBlock.alt_text`가 `required=True`로 선언되어 있는지 코드로 확인하고, 어드민에서 이미지 블록에 alt 텍스트 없이 저장을 시도하면 폼 검증 에러가 발생하는지 확인(04 §5/§7 접근성 요구사항 충족 여부).
20. 검증 후 사용한 venv/DB/staticfiles/media를 정리했는지, diff에 포함되지 않았는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~20번 인수 조건을 입력으로 `docs/harness/units/unit-02-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 이 하나의 작업 단위(WU-02)에 대한 7단계(통합테스트) 착수 여부는 02-planning.md §9의 남은 작업 단위(WU-03 등) 진행 계획에 따라 오케스트레이터가 판단한다.
