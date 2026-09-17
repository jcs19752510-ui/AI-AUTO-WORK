# WU-03 — 오브젝트 스토리지 연동(미디어 업로드 파이프라인) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-03, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §2.3 R2/DEC-008, §3.2 CustomImage, §5.5), `docs/harness/04-ux-design.md`(v1.2, PASS, §6 반응형 이미지/srcset), `docs/harness/decisions.md`(DEC-001~015), `docs/harness/units/unit-01-note.md`(WU-01 STORAGES 골격), `docs/harness/units/unit-02-note.md`, `docs/harness/feature-WU-02-integration-test.md`(DEF-002 — 이미지 모델 교체 시 마이그레이션 필요)
- 작성일: 2026-09-16
- 대상 REQ-ID: REQ-006(이미지/미디어 업로드 — S3 호환 오브젝트 스토리지 연동)

---

## 1. 구현 범위

WU-01이 만든 R2/STORAGES 골격과 WU-02의 `blog` 앱 위에, 아래를 신규/수정했다.

```
webapp/
  custom_images/                     (신규)
    __init__.py
    apps.py                          CustomImagesConfig (label="custom_images")
    models.py                        CustomImage(AbstractImage), CustomRendition(AbstractRendition)
    migrations/
      __init__.py
      0001_initial.py                makemigrations로 생성, 로컬 SQLite에 실제 적용 검증
  blog/migrations/
    0002_alter_blogpostpage_featured_image.py   (신규) featured_image FK를
                                      wagtailimages.Image → custom_images.CustomImage로 변경
                                      (DEF-002가 예측한 AlterField, 실제로 발생함을 재확인)
  config/settings/base.py            (수정) INSTALLED_APPS에 "custom_images" 추가,
                                      WAGTAILIMAGES_IMAGE_MODEL, WAGTAILIMAGES_EXTENSIONS/
                                      MAX_UPLOAD_SIZE/MAX_IMAGE_PIXELS 신규 추가
  config/settings/production.py      (수정) STORAGES["backup"](backup-private 버킷) 별칭 신규 추가
  .env.example                       (수정) R2_BACKUP_BUCKET_NAME/ACCESS_KEY_ID/SECRET_ACCESS_KEY 추가
  render.yaml                        (수정) 동일 3개 env var를 sync:false로 등록(값은 비움)
docs/harness/decisions.md            DEC-016 추가(앱 명명/백업 자격증명 폴백 근거)
docs/harness/traceability.md         REQ-006 행 갱신
```

### 1.1 커스텀 이미지 모델 (지시사항 1)

- `custom_images.CustomImage(AbstractImage)` / `custom_images.CustomRendition(AbstractRendition)`을 Wagtail 공식 최소 패턴 그대로 구현했다(03 §3.2, DEC-008). 지금 시점에는 stock `Image` 대비 추가 필드가 없다 — 목적은 필드 확장이 아니라 "이미지 데이터가 0건인 지금" 교체 비용이 가장 쌀 때 모델을 미리 분리해 두는 것이다(근거: WU-02 07단계 IT-I5/DEF-002가 실측한 "나중에 교체하면 `AlterField` 마이그레이션이 필요하다"는 사실).
- `base.py`에 `WAGTAILIMAGES_IMAGE_MODEL = "custom_images.CustomImage"`를 추가했다.
- **DEF-002 인수조건을 직접 반영**: `custom_images` 앱을 먼저 만들고 `makemigrations custom_images`로 `0001_initial.py`를 생성한 뒤, `makemigrations blog`를 실행한 결과 **`blog/migrations/0002_alter_blogpostpage_featured_image.py`(AlterField, featured_image → custom_images.customimage)가 실제로 생성됨을 확인**했다(DEF-002가 임시 실험으로 예측한 것과 정확히 일치). "자동으로 될 것"이라고 가정하지 않고, 실제로 마이그레이션 파일을 만들고 로컬 SQLite에 `migrate`로 적용까지 완료했다(§3 참고). `blog`의 `ImageChooserBlock`(StreamField `image` 블록)은 IT-I5가 확인한 대로 모델명을 마이그레이션에 굽지 않으므로 별도 변경이 필요 없었다(실제로 `blog` 앱에는 위 AlterField 1건만 생성됨, 다른 앱 영향 없음).
- **Wagtail Group 권한("Choose") codename 정정**: stock `Image.Meta.permissions`는 리터럴 `("choose_image", ...)`를 쓰지만, Wagtail의 `CollectionOwnershipPermissionPolicy`는 `django.contrib.auth.get_permission_codename("choose", opts)`(= `f"choose_{opts.model_name}"`)로 codename을 동적으로 파생시킨다. `CustomImage`의 `model_name`은 `customimage`이므로 `("choose_customimage", "Can choose custom image")`로 선언해야 그룹별 "이미지 선택" 권한이 정상적으로 생성/부여 가능하다 — 이 부분은 03 설계서에 명시되어 있지 않았지만 Wagtail 프레임워크 자체의 구조적 요구사항이라 임의 해석 여지가 없어 질문으로 올리지 않았다. `python manage.py migrate` 후 `Permission.objects.filter(codename="choose_customimage")`로 실제 생성됨을 확인했다(§3).
- **알려진 한계(수동 확인 필요, §5-1)**: Wagtail 내장 `GroupImagePermissionFormSet`(`wagtail/images/forms.py`)은 `get_image_model()`이 아니라 **stock `Image` 모델을 하드코딩**해서 그룹 편집 화면의 "Images" 권한 패널을 구성한다. 즉 커스텀 이미지 모델로 교체해도 Wagtail 관리자 그룹 편집 화면(`/cms-admin/groups/<id>/edit/`)의 이미지 권한 패널은 여전히 stock `Image` content-type을 기준으로 표시된다(Wagtail 자체의 알려진 동작이며, 우리 구현의 결함이 아니다). 슈퍼유저는 이 패널과 무관하게 모든 권한을 자동으로 가지므로 이번 WU의 검증(§3)에는 영향이 없었다. 이 문제는 그룹 기반 세분화 권한을 실제로 도입하는 **WU-09(REQ-010) 범위**이므로 이번 WU에서 `wagtail_hooks`를 오버라이드하지 않았다(범위 외 변경 금지 원칙) — WU-09 착수 시 인수조건으로 명시적으로 인계한다.

### 1.2 R2 버킷 분리 (지시사항 2, DEC-008)

- `production.py`에 기존 `STORAGES["default"]`(media-public, WU-01이 이미 구성)는 그대로 두고, **`STORAGES["backup"]`(backup-private)을 신규 추가**했다. `R2_BACKUP_BUCKET_NAME` 환경변수가 설정된 경우에만 이 별칭이 활성화되고, 비어 있으면 `STORAGES`에 `"backup"` 키 자체가 생기지 않는다(§3에서 `InvalidStorageError`로 실측 확인) — "이번엔 설정만, 실사용은 WU-10"이라는 지시를 그대로 반영해, 아직 아무 코드도 쓰지 않는 별칭 때문에 production 기동이 막히지 않게 했다(다른 R2 값들처럼 `_require_env`로 강제하지 않음, 근거는 DEC-016(b)).
- 자격증명은 `R2_BACKUP_ACCESS_KEY_ID`/`R2_BACKUP_SECRET_ACCESS_KEY`가 있으면 그 값을, 없으면 media-public용 자격증명을 임시 재사용한다. 최소 권한 원칙상 바람직한 것은 버킷별로 범위가 분리된 전용 R2 API 토큰이며, 이를 WU-10 착수 시 인수조건으로 명시했다(§5-1).
- `.env.example`/`render.yaml`에 3개 신규 변수를 optional(`sync: false`, 값 비움)로 등록했다.

### 1.3 로컬 개발환경 폴백 (지시사항 3)

- `base.py`의 `STORAGES["default"] = FileSystemStorage`(WU-01이 이미 구성)를 그대로 유지했다 — 이번 WU에서 `base.py`의 이 부분을 변경하지 않았다. `production.py`만 R2로 덮어쓴다는 WU-01 원칙이 이번에도 그대로 유지됨을 §3에서 재확인했다(R2 자격증명 없이 dev에서 업로드/렌디션 왕복 정상 동작).

### 1.4 업로드 경로/네이밍, 렌디션(반응형 이미지) 동작 확인 (지시사항 4)

- Wagtail의 기본 `get_upload_to()`(`original_images/<ASCII 정규화된 파일명>`, 100자 제한 처리 포함)를 그대로 사용한다 — 별도 커스터마이징을 하지 않았다(Wagtail이 이미 파일명 새니타이즈/경로 규칙을 제공하므로 재구현은 과설계).
- `CustomRendition`은 `AbstractRendition`을 상속해 Wagtail의 표준 렌디션 파이프라인(`get_rendition()`, `unique_together=(image, filter_spec, focal_point_key)`)을 그대로 사용한다. §3에서 `width-800`/`width-400`/`fill-100x100` 3가지 filter spec으로 실제 렌디션 파일이 생성됨을 확인했다 — 04-ux-design.md §6(`srcset`로 화면 폭별 이미지 제공)이 요구하는 다중 렌디션 메커니즘이 CustomImage 교체 후에도 정상 동작함을 실측했다.

### 1.5 업로드 파일 검증 (지시사항 5)

- `base.py`에 `WAGTAILIMAGES_EXTENSIONS`(`avif/gif/jpg/jpeg/png/webp` 화이트리스트, **svg 제외로 XSS 방지**), `WAGTAILIMAGES_MAX_UPLOAD_SIZE`(10MB), `WAGTAILIMAGES_MAX_IMAGE_PIXELS`(1.28억 픽셀, 디컴프레션 폭탄 방지)를 명시적으로 선언했다. 값 자체는 Wagtail 기본값과 동일하지만, `WAGTAILDOCS_*`와 동일한 패턴으로 보안 의도를 코드에 명문화했다(임의로 끄거나 낮추지 않았다는 근거를 남기기 위함).
- Wagtail의 `WagtailImageField`(`wagtail/images/fields.py`)가 이 값들을 자동으로 사용해 (a) 확장자 화이트리스트, (b) 실제 이미지 콘텐츠와 확장자 일치 여부(Willow로 파일을 실제로 열어 검증 — 확장자만 바꾼 위장 파일 차단), (c) 파일 크기, (d) 픽셀 수를 검증한다. 이 검증은 CustomImage로 교체해도 동일하게 적용됨을 §3에서 실제 HTTP 관리자 폼 제출로 확인했다(`.exe`를 `.exe` 그대로 업로드 시도 → 거부, SVG 업로드 시도 → 거부, 11MB 파일 → 거부, 정상 JPEG → 성공).

---

## 2. 설계서 대비 편차 (사유 포함)

1. **`custom_images`라는 신규 앱 생성 — 03 §1.2 "media_storage(설정 모듈, 별도 앱은 아님)"과 표면적으로 배치**: §1.2 모듈 경계 표는 "별도 앱은 아니다"라고 썼지만, 같은 문서 §3.2(DEC-008)는 `CustomImage`/`CustomRendition`이라는 모델을 요구하며, Django/Wagtail 구조상 모델은 반드시 `INSTALLED_APPS`에 속한 앱에 있어야 마이그레이션을 가질 수 있다 — "모델은 있는데 앱은 없음"은 기술적으로 불가능하다. §1.2의 서술은 "blog/subscribers/legal/core 같은 별도 도메인 앱을 새로 만들 필요는 없다"는 취지로 해석했고(모델을 담을 최소 앱 자체는 프레임워크의 구조적 요구사항), 두 서술이 실질적으로 모순되지 않는 단일 해석이 가능하다고 판단해 규칙A-③ 질문으로 올리지 않았다(WU-01이 `home` 앱을 §1.2 표에 없어도 유지한 것과 동일한 성격의 판단). DEC-016(a)로 기록.
2. **앱 이름을 `images`가 아니라 `custom_images`로 명명**: `wagtail.images` 패키지(앱 라벨 `wagtailimages`)와 이름이 겹쳐 혼동을 줄 여지를 없애기 위한 순수 명명 판단이며, 03 설계서가 정확한 앱 이름을 지정하지 않았으므로 임의 추측이 아니라 합리적 단일 선택으로 처리했다.
3. **CustomImage에 추가 필드를 넣지 않음**: 03 §3.2는 "Wagtail 기본 Image 모델을 상속해... 저장 경로를 연결"이라고만 서술하고 구체적 추가 필드를 요구하지 않는다. 임의로 필드를 추가하는 것은 범위 외 기능 추가이므로 하지 않았다(Wagtail 공식 최소 패턴 그대로).
4. **CustomDocument는 만들지 않음**: 지시사항 1번은 `WAGTAILIMAGES_IMAGE_MODEL`(이미지)만 명시했고, 03 §3.2도 CustomImage/CustomRendition만 언급한다(CustomDocument 없음). Wagtail의 `Document` 모델은 커스텀 서브클래스 없이도 이미 `default_storage`(R2)를 그대로 쓰므로(WU-01이 이미 구성), 이번 WU에서 Document 모델 교체는 필요하지도, 지시받지도 않아 하지 않았다.
5. **`STORAGES["backup"]`을 `_require_env`로 강제하지 않음**: 작업 지시 §2가 "이번엔 설정만, 실사용은 WU-10"이라고 명시했으므로, 아직 아무 코드도 쓰지 않는 별칭 때문에 production 기동을 막는 것은 불필요한 운영 마찰이라고 판단했다(DEC-016(b)). `R2_BUCKET_NAME`(media-public, 실제 사용 중)과는 달리 optional로 처리했다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

### 3-1. 마이그레이션 (임시 venv, 검증 후 삭제)

1. 신규 임시 venv(`webapp/.venv_wu03`)에서 `pip install -r requirements.txt`(신규 패키지 없음, WU-01/02와 동일 버전) 완료.
2. `python manage.py makemigrations custom_images` → `custom_images/migrations/0001_initial.py` 생성(CustomImage/CustomRendition).
3. `python manage.py makemigrations blog` → **`blog/migrations/0002_alter_blogpostpage_featured_image.py`가 실제로 생성됨을 확인**(DEF-002 예측과 일치, `featured_image` FK가 `wagtailimages.image` → `custom_images.customimage`로 변경).
4. `python manage.py migrate`(dev, SQLite) → wagtailcore/wagtailimages/taggit 포함 전체 마이그레이션 + `custom_images.0001_initial` + `blog.0002_...` 전부 오류 없이 적용(순환 의존성 없음, `custom_images` 앱이 `blog`보다 먼저 적용됨을 마이그레이션 그래프가 자동으로 정렬).
5. `python manage.py check` → "System check identified no issues (0 silenced)".
6. `python manage.py makemigrations --check --dry-run` → "No changes detected"(모델=마이그레이션 일치).

### 3-2. 실제 이미지 업로드 → 렌디션 → FK 왕복 (ORM + 실제 관리자 HTTP 폼)

동일 venv에서 슈퍼유저 1명을 만들고 임시 스크립트(검증 후 삭제)로 아래를 확인했다.

- `wagtail.images.get_image_model_string()` → `"custom_images.CustomImage"` (활성 모델 확인).
- PNG 400x300 이미지를 `CustomImage`에 실제 저장(FileSystemStorage) → `original_images/test-image.png` 경로에 실제 파일 생성 확인(`os.path.exists` True).
- `image.get_rendition("width-800")`, `("width-400")`, `("fill-100x100")` 3가지 filter spec 전부 `CustomRendition` 인스턴스 생성 + 실제 파일 생성 확인(반응형 이미지 다중 렌디션, 04 §6). `img.renditions.count() == 3`.
- `BlogPostPage(featured_image=<CustomImage 인스턴스>)`로 게시물 생성·발행 → 재조회 시 `featured_image_id`가 정확히 일치(WU-02의 `get_image_model_string()` 간접참조 FK가 실제로 CustomImage를 정상 참조함을 재확인, WU-02 §3 "로컬에서 확인하지 못한 것"이었던 실제 이미지 첨부를 이번에 완료).
- **실제 Wagtail 관리자 HTML 폼 제출**(`django.test.Client`, `force_login`)로 `/cms-admin/images/add/`에 업로드 시도:
  - `.exe` 파일(가짜 이미지) → 200(저장 거부), 응답 HTML에 "올바른 이미지를 업로드하세요..." 오류 메시지 존재, `CustomImage` 미생성.
  - `.svg` 파일 → 200(저장 거부), "지원하지 않는 이미지 포맷입니다. 지원 포맷은 AVIF, GIF, JPG, JPEG, PNG, WEBP 입니다." 오류 메시지 존재, 미생성.
  - 11MB PNG(상한 10MB 초과) → 200(저장 거부), "이 파일 사이즈는 너무 큽니다(11.0 MB). 최대 허용 가능한 파일 사이즈는 10.0 MB 입니다." 오류 메시지 존재, 미생성.
  - 정상 JPEG(200x150) → **302**(성공), `CustomImage` 실제 생성 확인.
- `Permission.objects.filter(codename="choose_customimage")` → 1건 존재, `content_type`이 `custom_images.customimage`를 정확히 가리킴(§1.1 권한 codename 정정이 실제로 반영됨을 확인).

### 3-3. R2(S3Storage) 구조적 정합성 + 버킷 분리 (production 유사 설정, 네트워크 호출 없음)

WU-01/02와 동일한 방법론(`config/settings/it_test_prodlike.py` — `production.py`를 그대로 상속하되 `DATABASES`만 SQLite로 재정의, 검증 후 삭제)으로 더미 R2 환경변수를 채운 뒤 확인했다.

- `default_storage`가 `storages.backends.s3.S3Storage`로 정상 인스턴스화(`isinstance` True), `bucket_name="media-public-dummy"`, `endpoint_url`이 더미 값과 일치.
- `R2_BACKUP_BUCKET_NAME="backup-private-dummy"`를 채운 경우: `storages["backup"]`이 별도의 `S3Storage` 인스턴스로 정상 로드되고, `bucket_name="backup-private-dummy"`로 `default_storage`의 버킷과 **서로 다름**을 확인(버킷 물리적 분리 실측).
- `R2_BACKUP_BUCKET_NAME`을 설정하지 않은 경우: `settings.STORAGES`에 `"backup"` 키 자체가 없고(`["default", "staticfiles"]`만 존재), `storages["backup"]` 접근 시 `InvalidStorageError`가 발생함 — 즉 이 값이 없어도 `manage.py check`가 여전히 "System check identified no issues"로 정상 통과함을 별도로 재확인했다(§2-5의 optional 처리 의도가 실제로 지켜짐).
- `get_image_model_string()` → `"custom_images.CustomImage"`, `BlogPostPage.featured_image` FK target → `custom_images.models.CustomImage` (production 유사 설정에서도 dev와 동일하게 확인).

### 3-4. 완전히 새로운 venv로 전체 파이프라인 재현(최종 확인)

위 개별 검증들과 별개로, **모든 임시 스크립트/venv를 삭제한 뒤 처음부터 새 venv(`webapp/.venv_final`)를 만들어** `pip install -r requirements.txt` → `migrate`(dev, SQLite) → `check` → `makemigrations --check --dry-run` 전 과정을 다시 실행해 동일한 결과(오류 없음, "No changes detected")를 재확인했다 — 6단계 테스터가 그대로 재현할 절차와 동일하다.

### 3-5. 정리

검증에 사용한 `.venv_wu03`, `.venv_final`, `db.sqlite3`, `media/`, `staticfiles/`, `__pycache__/`, 임시 스크립트(`it_wu03_*.py`), 임시 설정 모듈(`config/settings/it_test_prodlike.py`), 임시 응답 덤프(`it_wu03_resp.html`, `it_wu03_errs.txt`)를 전부 삭제했다. `git status --porcelain webapp/`으로 diff에 소스 코드(`custom_images/`, `blog/migrations/0002_...`, 수정된 4개 설정/골격 파일)만 남았음을 최종 확인했다.

**R2 실연동(네트워크가 필요한 부분)은 로컬에서 검증하지 못했다** — 실제 Cloudflare R2 계정/버킷/API 토큰이 아직 발급되지 않았고(WU-01부터 이월된 사항), 이번 WU도 "구성은 맞으나 실측은 10단계에서 필요"로 명시적으로 이월한다. 구체적으로 10단계가 확인해야 할 것: (a) 실제 `media-public`/`backup-private` 두 버킷 생성 및 버킷 정책(공개/비공개)이 설계 의도대로 적용됐는지, (b) 실제 R2 자격증명으로 이미지 업로드 시 R2에 실제 오브젝트가 생성되고 공개 URL로 접근 가능한지, (c) `AWS_S3_CUSTOM_DOMAIN`(R2_PUBLIC_BASE_URL) 설정 여부에 따라 렌디션 URL이 올바르게 생성되는지.

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체(및 `webapp/`)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않음을 이번에도 재확인**했다(직접 검색, WU-01/02와 동일 결론) — 있는데 건너뛴 것이 아니라 설정 자체가 없다. 대체 수단으로 신규/수정 파일 전체(`custom_images/__init__.py`, `apps.py`, `models.py`, `migrations/__init__.py`, `migrations/0001_initial.py`, `blog/migrations/0002_alter_blogpostpage_featured_image.py`, `config/settings/base.py`, `config/settings/production.py`)에 `py_compile`을 실행했고 전부 구문 오류 없이 통과했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 항목(5건)은 전부 사유와 함께 명시했고, 대부분 "프레임워크의 구조적 요구사항에 따른 단일 해석" 또는 "지시사항이 명시한 범위 축소(설정만, 실사용은 WU-10)"이지 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — 이미지 업로드 검증은 Wagtail의 표준 `WagtailImageField` 예외 처리(파일 형식/크기/픽셀수 불일치 시 `ValidationError`, 사용자에게 그대로 노출되는 폼 오류)를 그대로 활용하며, 예외를 삼키는 코드를 추가하지 않았다. `STORAGES["backup"]`은 값이 없으면 키 자체를 만들지 않는 명시적 조건문(`if R2_BACKUP_BUCKET_NAME:`)이며, 조용히 잘못된 기본값으로 폴백하지 않는다(값이 없으면 없는 대로 명확히 드러남 — `InvalidStorageError`, §3-3 확인).
- [x] **입력값 검증이 시스템 경계(사용자 입력)에서 이루어지는가** — 이 WU의 시스템 경계는 "운영자가 Wagtail 어드민에서 업로드하는 이미지 파일"이다. `WAGTAILIMAGES_EXTENSIONS`(화이트리스트, svg 제외로 XSS 방지)/`MAX_UPLOAD_SIZE`(10MB)/`MAX_IMAGE_PIXELS`(디컴프레션 폭탄 방지)를 명시적으로 선언했고, Wagtail이 실제 파일 내용을 Willow로 열어 확장자-콘텐츠 일치까지 검증함을 §3-2에서 실측 확인했다(임의 파일 업로드 방지 기본기, 20년차 보안 관점 요구사항 충족).
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. `.env.example`/`render.yaml`에 추가한 백업 버킷 관련 값은 전부 빈 값 또는 `sync: false`(Render 대시보드에서 직접 입력)이다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `blog/models.py`, `blog/blocks.py`(WU-02 산출물)는 건드리지 않았다(FK가 `get_image_model_string()` 간접참조라 코드 변경 없이 마이그레이션만 추가되면 충분했음, WU-02 §2-2가 이미 의도한 대로). `base.py`의 STORAGES 주석 오탈자(`S3Boto3Storage` → `S3Storage`, WU-01 §2-6이 이미 지적한 것과 동일한 종류의 오기)를 이번에 함께 바로잡았다 — 이것은 곁다리 리팩터링이 아니라 이번 WU가 실제로 구현하는 대상(R2 스토리지 클래스)에 대한 주석 오류를 그 코드를 만지는 김에 정정한 것이며, 로직 변경은 없다. `WAGTAILDOCS_*` 등 기존 설정은 변경하지 않았고, `home`/`config/urls.py`/`config/middleware.py` 등 WU-01/02 산출물도 손대지 않았다.

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-006 행을 갱신했다: "구현 상태" 컬럼을 "Not Started" → "구현 완료"로 채우고 구현 근거(파일 경로)를 명시했다. "단위테스트" 컬럼은 "대기(6단계)"로 표시했다. "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다. 비고란에 "R2 실연동(네트워크)은 10단계에서 실측 필요"를 추가했다.

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **R2 실연동 미검증**: §3 결론 참고. 10단계에서 실제 버킷 2개(`media-public`/`backup-private`) 생성, 버킷 공개/비공개 정책 설정, 실제 자격증명으로 업로드/공개 URL 접근을 반드시 실측해야 한다.
2. **Wagtail Group 권한 패널의 알려진 한계**: §1.1 참고. `GroupImagePermissionFormSet`이 stock `Image` 모델을 하드코딩해, 그룹 편집 화면의 이미지 권한 패널이 `CustomImage`가 아니라 stock `Image` content-type을 기준으로 표시된다. 슈퍼유저에는 영향 없으나, 그룹 기반 세분화 권한을 실제로 쓸 WU-09 착수 시 이 문제를 명시적으로 처리해야 한다(Wagtail의 `register_group_permission_panel` 훅을 `CustomImage` 기준으로 재등록하는 방식 검토 권고).
3. **백업 버킷 자격증명 분리 권고**: §1.2/DEC-016(b) 참고. 현재는 `R2_BACKUP_ACCESS_KEY_ID`/`SECRET`이 없으면 media-public 자격증명을 재사용하도록 폴백되어 있다. WU-10(실제 백업 파이프라인) 착수 시, 버킷 범위가 분리된 전용 R2 API 토큰을 발급해 최소 권한 원칙을 완성할 것을 강력 권고한다.
4. **Document 모델은 이번에 손대지 않음**: §2-4 참고. `wagtail.documents.Document`는 커스텀 서브클래스 없이 이미 `default_storage`(R2)를 사용 중이며, 이번 WU 지시사항/설계서 어디에도 CustomDocument 요구가 없어 변경하지 않았다.
5. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다림). 원격 push는 수행하지 않았다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일).

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, WU-01/02와 동일 버전).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `python manage.py migrate`가 처음부터(빈 SQLite) 오류 없이 끝나는가 — 특히 `custom_images.0001_initial`과 `blog.0002_alter_blogpostpage_featured_image`가 마이그레이션 의존성 오류(순환 의존 등) 없이 순서대로 적용되는가.
3. `python manage.py check`가 "System check identified no issues"를 출력하는가.
4. `python manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가(모델=마이그레이션 일치, DEF-002 대응이 완결됐는지 확인).
5. `python -c "..."`로 `wagtail.images.get_image_model_string()`을 호출하면 `"custom_images.CustomImage"`를 반환하는가.
6. `BlogPostPage._meta.get_field("featured_image").remote_field.model`이 `custom_images.models.CustomImage`를 가리키는가(WU-02가 `get_image_model_string()`으로 미리 구현해 둔 FK가 실제로 스왑된 모델을 정확히 참조하는지).
7. 슈퍼유저로 ORM에서 실제 이미지 파일(PNG 등)을 `CustomImage`에 저장하면 `MEDIA_ROOT/original_images/<파일명>`에 실제 파일이 생성되는가(FileSystemStorage, dev).
8. 저장된 `CustomImage`에 대해 `get_rendition("width-800")`(또는 임의의 filter spec)을 호출하면 `CustomRendition` 인스턴스가 생성되고 실제 렌디션 파일이 디스크에 존재하는가(반응형 이미지 다중 렌디션 동작 확인, 04 §6).
9. Wagtail 관리자 로그인 후 `POST /cms-admin/images/add/`로 **실제 이미지가 아닌 파일**(예: 확장자만 바꾼 실행파일)을 업로드하면 200(폼 재표시, 저장 거부)과 함께 오류 메시지가 응답에 포함되고, `CustomImage`가 생성되지 않는가.
10. 동일한 방식으로 `.svg` 파일을 업로드하면 확장자 미허용으로 거부되는가(`WAGTAILIMAGES_EXTENSIONS`에 svg가 없음을 코드로도 확인).
11. `WAGTAILIMAGES_MAX_UPLOAD_SIZE`(10MB)를 초과하는 파일을 업로드하면 거부되는가(예: 11MB 더미 PNG).
12. 위 9~11과 동일한 방식으로 **정상적인 JPEG/PNG 파일**을 업로드하면 302(성공)와 함께 `CustomImage`가 실제로 생성되는가(정상 경로 회귀 확인, 과도하게 막지 않는지).
13. `Permission.objects.filter(codename="choose_customimage")`가 1건 존재하고 그 `content_type`이 `custom_images`/`customimage`를 가리키는가(그룹 "이미지 선택" 권한이 올바른 모델에 연결됐는지).
14. `DJANGO_SETTINGS_MODULE=config.settings.production`으로 R2 관련 환경변수(더미 값 포함, `R2_BACKUP_BUCKET_NAME` 제외)를 채운 뒤 `manage.py check`가 정상 통과하는가(백업 버킷 미설정이 production 기동을 막지 않는지 확인, §2-5/DEC-016(b)).
15. 위 14에 `R2_BACKUP_BUCKET_NAME`(+선택적으로 `R2_BACKUP_ACCESS_KEY_ID`/`SECRET`) 더미 값을 추가하면 `django.core.files.storage.storages["backup"]`이 `storages.backends.s3.S3Storage` 인스턴스로 로드되고, `bucket_name`이 `default_storage`(media-public)와 다른가(버킷 물리적 분리 확인).
16. 위 14(백업 변수 없음) 상태에서 `django.core.files.storage.storages["backup"]`에 접근하면 `InvalidStorageError`가 발생하는가(설정 안 된 별칭이 조용히 잘못된 값으로 폴백하지 않는지).
17. `.env.example`/`render.yaml`에 실제 시크릿 값이 하드코딩되어 있지 않은가(전부 빈 값 또는 `sync: false`인지).
18. (회귀) `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `GET /`(홈), `GET /cms-admin/login/`이 여전히 200을 반환하는가 — `custom_images` 앱 추가로 WU-01/02 기존 경로가 깨지지 않았는지.
19. (회귀) WU-02가 만든 `BlogPostPage`의 초안/발행/리비전 워크플로(ORM 레벨)가 이번 이미지 모델 스왑 이후에도 정상 동작하는가(임의의 category로 생성 → `save_revision()` → `.publish()` → `live=True`).
20. 검증 후 사용한 venv/DB/staticfiles/media/임시 스크립트/임시 설정 모듈을 정리했는지, diff에 포함되지 않았는지 확인.

### 8-1. R2 실연동 관련 (10단계로 명시적으로 이월 — 6단계 범위 아님, 참고용)

- 실제 R2 자격증명으로 이미지 업로드 시 R2 콘솔에 오브젝트가 실제로 생성되는지.
- `media-public` 버킷의 공개 읽기 정책과 `backup-private` 버킷의 비공개 정책이 각각 의도대로 적용됐는지.
- `R2_PUBLIC_BASE_URL`(`AWS_S3_CUSTOM_DOMAIN`) 설정 시 이미지/렌디션 URL이 올바른 공개 도메인으로 생성되는지.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~20번 인수 조건을 입력으로 `docs/harness/units/unit-03-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-03)의 7단계(통합테스트, WU-02와의 조립 검증 포함) 착수 여부를 오케스트레이터가 판단한다.
