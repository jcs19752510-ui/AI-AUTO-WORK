# WU-09 — 관리자 인증/권한(Django/Wagtail 어드민 커스터마이징) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-09, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §2.6/§4/§5.1), `docs/harness/04-ux-design.md`(v1.2, PASS, §0 "Wagtail 어드민 UI 자체는 벤더 기본 제공 화면"), `docs/harness/decisions.md`(DEC-001~027, 특히 DEC-009/DEC-011/DEC-024/DEC-026), `docs/harness/units/unit-08-note.md`(§8 `superuser_required` 패턴), `docs/harness/feature-WU-08-integration-test.md`
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-010(관리자 인증 — Django/Wagtail 어드민 권한관리)

---

## 0. 실행 환경 메모

이번 세션의 작업 지시는 프로젝트 루트를 `C:\big21\vibe-coding\AI-AUTO-WORK`로 명시했으나, 에이전트 환경변수의 기본 작업 디렉터리는 `C:\big21\vibe-coding\STOCK-ANALYZER-KR`(별개 프로젝트)로 설정되어 있었다. `docs/harness/units/`에 WU-01~08 산출물이 실제로 존재하는 쪽이 `AI-AUTO-WORK`임을 확인한 뒤, 이하 모든 작업은 절대경로로 `AI-AUTO-WORK`에서 수행했다.

---

## 1. 구현 범위

작업 지시가 제시한 4개 항목(그룹/권한 체계, 로그인 레이트리밋, 슈퍼유저 계정 절차, 접근 로그/감사)을 03-system-design.md §5.1(DEC-009)과 대조해 아래와 같이 구현/판단했다.

### 1.1 Wagtail 그룹/권한 체계 정비 — 결함 발견 및 수정 (신규)

DEC-009는 "Wagtail 그룹 기반 페이지 권한(Editor/Moderator 등 **Wagtail 표준 그룹** 활용)"을 이미 확정했으므로, 새 커스텀 그룹(예: 한글 "편집자"/"운영자")을 만들지 않고 Wagtail 표준 그룹(Editors/Moderators)을 그대로 썼다.

권한 범위를 실제로 조사한 결과 **결함을 발견**했다: `blog.Category`(REQ-002, `@register_snippet`)의 기본 권한 정책은 Django 표준 모델 권한(`blog.add_category`/`change_category`/`delete_category`, Wagtail 소스 `wagtail/snippets/views/snippets.py`의 `permission_policy` 프로퍼티로 직접 확인)인데, 이 권한을 Editors/Moderators 그룹에 부여하는 마이그레이션이 어디에도 없었다. Wagtail 코어(`wagtailcore 0002_initial_data`)가 자동으로 주는 것은 **페이지** 권한뿐이고, 스니펫 모델 권한은 그 스니펫을 도입하는 쪽이 직접 부여해야 하는 Wagtail 표준 패턴이다(이미지 스니펫류가 `wagtail/images/migrations/0002_initial_data.py`로 직접 부여하는 것과 동일 패턴). 이 결함이 있으면 슈퍼유저가 아닌 그룹 사용자는 카테고리를 CRUD할 수 없다.

`webapp/core/migrations/0001_setup_editor_permissions.py`(신규)를 추가해 Editors/Moderators 그룹에 카테고리 add/change/delete 권한을 명시적으로 부여했다(DEC-028).

**이미지(`custom_images.CustomImage`) 권한은 손대지 않았다** — 조사 결과 문제가 없었다. Wagtail이 `WAGTAILIMAGES_IMAGE_MODEL`을 스왑해도 권한 코드네임은 항상 원본 `wagtailimages.Image`에 고정된다(`wagtail/images/permissions.py`의 `CollectionOwnershipPermissionPolicy(get_image_model(), auth_model=Image, ...)` 소스로 직접 확인 — `auth_model`이 실제 권한 판정 기준). 기존 Wagtail 마이그레이션이 이미 Editors/Moderators에 이미지 add/change 권한(`wagtailimages 0002_initial_data`/`0012_copy_image_permissions_to_collections`)을 올바르게 부여해 두었으므로 WU-03의 이미지 모델 스왑과 무관하게 정상 동작함을 `core/tests.py`로 확인했다(§3).

페이지 권한(BlogPostPage/LegalPage/HomePage)은 전부 Wagtail 코어가 루트 페이지에 부여한 것이 트리 전체에 자동 상속되므로 이미 정상이다(Editors: add/edit, Moderators: add/edit/publish).

### 1.2 로그인 무차별대입 방어(레이트리밋) — 신규 구현

03 §2.6은 로그인 레이트리밋 수단으로 django-axes/django-ratelimit을 후보로 들며 "라이선스 확인 후 5단계에서 도입"이라고 위임했다. 이번 작업 지시가 "WU-07(DEC-024)이 이미 LocMemCache 기반 레이트리밋 패턴을 사용했으니 일관성 있게 재사용 검토, 새 패키지 도입은 근거 필요"라고 명시적으로 위임했으므로, **새 패키지를 도입하지 않고** `subscribers/views.py`(WU-07)와 동일한 `cache.incr` 기반 카운터 패턴을 `webapp/core/admin_auth.py`(신규)에 재구현했다(DEC-029). 03 §2.6의 "확인 필요"(라이선스 재확인) 자체를 회피하는 효과도 있다.

- `RateLimitedLoginView`(`wagtail.admin.views.account.LoginView`를 상속)가 `dispatch()`에서 IP당 15분/10회를 넘는 POST를 `429`로 즉시 차단하고, 넘지 않으면 원래 Wagtail 로그인 뷰로 그대로 위임한다.
- `webapp/config/urls.py`에 `cms-admin/login/` 라우트를 wagtailadmin_urls include보다 먼저 등록하되 URL 이름(`wagtailadmin_login`)은 그대로 유지해, 어드민 내부의 다른 `reverse("wagtailadmin_login")` 호출(예: `core/views.py`의 `superuser_required`)과 충돌 없이 자연스럽게 이 뷰로 연결된다.
- **IP 기준으로만 제한**하고 계정(사용자명) 기준 잠금은 두지 않았다 — 1인 운영(가정 A1) 전제에서 계정 잠금은 공격자가 알려진 관리자 계정명으로 고의 실패를 반복해 정당한 운영자 본인을 잠그는 자기서비스거부(self-DoS) 경로가 되기 때문이다(DEC-029에 상세 근거).
- IP는 `config.middleware.XForwardedForMiddleware`(WU-01, production 전용)가 이미 정규화한 `REMOTE_ADDR`을 그대로 신뢰한다(03 §5.5.4) — production.py의 기존 주석("WU-09(로그인 레이트리밋)가 이 값을 신뢰해 쓸 수 있도록...")이 이번 구현으로 실현됐다.

### 1.3 슈퍼유저 계정 생성/운영 절차 문서화 — 문서화 + 최소 구현 (신규)

**문서화만으로는 끝낼 수 없었다.** Render 공식 문서(render.com/docs/free "Other limitations", 2026-09-17 직접 curl 조회)를 확인한 결과 **Free 웹 서비스는 Shell 접속(SSH/대시보드 Shell)과 one-off Job 실행을 지원하지 않는다**는 사실을 발견했다. DEC-011이 v1을 Render 무료 티어로 유지하기로 이미 확정했으므로, "Render Shell에서 `manage.py createsuperuser`를 대화형으로 실행하라"는 절차를 문서화하는 것은 실행 불가능한 허위 절차를 남기는 것과 같다(DEC-030).

대신 **`build.sh`(모든 요금제에서 배포마다 실행되는 빌드 단계 — 이미 `migrate --noinput`이 이 방식으로 동작함을 WU-01부터 증명)에 새 관리 명령 `manage.py ensure_superuser`를 추가**했다:

- `webapp/core/management/commands/ensure_superuser.py`(신규): 환경변수(`DJANGO_SUPERUSER_USERNAME`/`EMAIL`/`PASSWORD`)로 최초 슈퍼유저를 **멱등하게**(이미 슈퍼유저가 하나라도 있으면 아무 것도 하지 않음) 생성한다. `AUTH_PASSWORD_VALIDATORS`(03 §5.1 비밀번호 정책)를 `validate_password()`로 재사용해, 정책을 통과하지 못하는 값이면 배포를 막지 않고 경고만 남긴 채 건너뛴다.
- `webapp/build.sh`: 마지막 단계에 `python manage.py ensure_superuser` 추가.
- `webapp/render.yaml`: `DJANGO_SUPERUSER_USERNAME`/`EMAIL`/`PASSWORD` 환경변수 자리(`sync: false`) 추가.
- `webapp/ADMIN_ACCESS_GUIDE.md`(신규): 운영자용 가이드 — 로그인 경로, 최초 계정 생성 절차(위 부트스트랩 사용법 + 생성 후 환경변수 삭제 권고), 비밀번호 정책, 레이트리밋 동작, 그룹 권한 범위 표.

### 1.4 어드민 접근 로그/감사 — 신규 구현하지 않음(과설계 방지 판단)

WU-08이 이미 구현한 `core/middleware.py`(`RequestMetricsMiddleware`)와 `core/monitoring.py`가 모든 요청(어드민 포함)의 요청량/응답시간을 집계하고, `/cms-admin/usage/` 대시보드(superuser 전용)로 노출하고 있다. REQ-010이 요구하는 수준의 "접근 로그/감사"가 이미 이 장치로 커버된다고 판단해 별도의 감사로그 테이블/미들웨어를 신설하지 않았다 — 03 §6.3이 이미 "배치 잡을 두지 않는다"는 과설계 방지 원칙을 명시했고, DEC-027이 그 원칙을 유지한 채 모니터링을 구현한 선례를 그대로 따른 것이다. 다만 WU-08의 미들웨어는 "누가"(사용자)가 아니라 "얼마나"(요청량/응답시간)만 집계하므로, 향후 "누가 어떤 페이지를 언제 발행/삭제했는가" 수준의 감사가 필요해지면 이는 Wagtail이 이미 내장한 `PageLogEntry`(발행/리비전 이력, DEC-007이 이미 재사용을 확정한 기능)로 커버 가능하다는 점을 확인해 이 노트에 기록해 둔다(신규 코드 없이 기존 기능 활용 가능 — 실제 화면 노출이 필요해지면 별도 WU로 검토).

### 1.5 파일 변경 목록

```
webapp/
  core/
    admin_auth.py                          (신규) RateLimitedLoginView, is_rate_limited() — IP 기준 15분/10회
    tests.py                                (신규) 카테고리 권한/로그인 레이트리밋/ensure_superuser 자동화 테스트 15건
    migrations/
      __init__.py                           (신규)
      0001_setup_editor_permissions.py      (신규) Editors/Moderators에 카테고리 스니펫 권한 부여(DEC-028)
    management/
      __init__.py                           (신규)
      commands/__init__.py                  (신규)
      commands/ensure_superuser.py          (신규) 멱등 슈퍼유저 부트스트랩(DEC-030)
  config/
    urls.py                                  (수정) cms-admin/login/ 라우트를 RateLimitedLoginView로 교체
  build.sh                                   (수정) ensure_superuser 호출 추가
  render.yaml                                (수정) DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD env 자리 추가
  ADMIN_ACCESS_GUIDE.md                      (신규) 운영자용 계정/접근 가이드
docs/harness/decisions.md                    DEC-028(카테고리 권한 결함/수정), DEC-029(레이트리밋 설계), DEC-030(Free 티어 Shell 부재/부트스트랩) 추가
docs/harness/traceability.md                 REQ-010 행 갱신
```

---

## 2. 설계서 대비 편차 (사유 포함)

1. **커스텀 한글 그룹("편집자"/"운영자") 대신 Wagtail 표준 그룹(Editors/Moderators)을 그대로 사용** — 작업 지시 예시 문구("예: 편집자/운영자 등")는 예시일 뿐이고, DEC-009가 이미 "Wagtail 표준 그룹 활용"을 명시적으로 확정했다(PASS 상태 설계서의 기존 결정). 임의로 새 그룹 체계를 만드는 것은 이미 확정된 비가역적(High) 결정을 뒤집는 범위 확장이라 판단해 하지 않았다.
2. **DEC-009 "IP/계정 기준 레이트리밋"에서 계정 기준을 채택하지 않음** — DEC-029에 근거를 상세히 기록했다(§1.2 요약, 1인 운영 self-DoS 리스크).
3. **REQ-010 범위에서 "접근 로그/감사"를 신규 구현하지 않음** — §1.4에 근거를 기록했다. 작업 지시 자체가 "과설계 방지 원칙에 따라 이번 WU-08 모니터링 미들웨어로 충분한지... 설계서 근거로 판단하라"고 이미 재량을 위임했다.
4. **`core/migrations/0001_...`를 core 앱에 배치** — 03 §1.2 모듈 경계 표는 REQ-010을 "Wagtail 내장" 소유로 지정해 특정 앱을 배정하지 않았다. `blog/migrations/`에 넣는 대신 `core`(WU-05/08이 이미 관리자/사이트 전역 관심사의 자리로 써 온 앱, DEC-019 선례)에 넣었다 — Category 모델 자체를 건드리지 않고 데이터 마이그레이션만 추가하는 것이므로 blog 앱 소유 코드에 대한 곁다리 변경이 아니다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv_wu09`, 검증 후 삭제) + 임시 production 유사 설정 모듈(`config/settings/it_test_prodlike_wu09.py`, 검증 후 삭제)로 아래를 직접 실행했다(WU-01~08과 동일 방법론).

### 3-1. 기본 동작(dev, SQLite)

1. `pip install -r requirements.txt` — 오류 없음(신규 패키지 없음).
2. `manage.py makemigrations --check --dry-run` → "No changes detected"(모델 변경 없음, 데이터 마이그레이션만 추가했으므로 정상).
3. `manage.py migrate`(빈 DB) → `core.0001_setup_editor_permissions` 포함 전체 오류 없이 적용, `showmigrations core` → `[X] 0001_setup_editor_permissions` 확인.
4. `manage.py check` → "System check identified no issues (0 silenced)".
5. `manage.py test`(전체) → "Ran 27 tests ... OK"(subscribers 12개 + core 15개, 회귀 없음).

### 3-2. 권한/레이트리밋/슈퍼유저 부트스트랩 자동화 테스트 (`core/tests.py`, 15건 전부 PASS)

- **`CategoryEditorPermissionTests`(4건)**: 마이그레이션 적용 후 Editors/Moderators 그룹이 정확히 `{add_category, change_category, delete_category}` 권한을 갖는지 직접 조회로 확인. 그룹에 속하지 않은 일반 스태프 사용자는 `has_perm("blog.add_category")`가 `False`임을 대조 확인(권한이 슈퍼유저/그룹에만 한정됨을 검증). Editors 그룹에 배정한 사용자는 `has_perm`이 전부 `True`임을 확인 — DEC-028이 고친 결함이 실제로 해소됐음을 실측으로 증명.
- **`AdminLoginRateLimitTests`(7건)**: GET은 카운트되지 않음(11회 반복 GET 모두 200), 임계값(10회) 이내 POST는 정상 응답(200, CSRF 체크가 비활성인 기본 테스트 Client 기준), 11번째 POST는 429, 올바른 비밀번호면 임계값 이내에서 302 성공, 서로 다른 IP는 독립적으로 카운트됨을 확인. **`Client(enforce_csrf_checks=True)`로 GET에서 실제 CSRF 쿠키/토큰을 받아 POST에 그대로 실어 보내는 end-to-end 시나리오**로 로그인 성공(302)까지 확인해, 레이트리밋 도입이 실제 로그인 흐름을 깨지 않았음을 증명했다. `RequestFactory` + `XForwardedForMiddleware`를 뷰에 직접 감싸는 방식(subscribers/tests.py와 동일 방법론)으로 X-Forwarded-For의 **rightmost** 값만 카운터 키로 채택됨을 확인(leftmost를 매번 바꿔도 같은 rightmost면 같은 카운터로 취급).
  - **테스트 중 실제로 재현·수정한 결함**: 최초 구현은 `post()`를 오버라이드했는데, Django `auth_views.LoginView.dispatch()`에 걸린 `csrf_protect` 데코레이터가 `post()` 호출보다 먼저 실행되어, CSRF 검증에 실패하는 요청은 내 레이트리밋 카운터를 아예 거치지 않고 403으로 먼저 응답을 끝내버리는 것을 `RequestFactory` 기반 테스트로 실제로 재현했다(§3-2 XFF 테스트가 처음엔 11번째 요청에서 429가 아니라 403을 받아 실패했다). IP 기준 요청 수 자체를 제한하는 것이 목적이므로 CSRF 통과 여부와 무관하게 카운트해야 한다고 판단해, `post()`가 아니라 `dispatch()`에서 확인하도록 수정했다(수정 근거는 `core/admin_auth.py` 클래스 docstring에도 기록).
- **`EnsureSuperuserCommandTests`(4건)**: 환경변수로 슈퍼유저 생성, 이미 슈퍼유저가 있으면 건너뜀(멱등성), 환경변수가 비어 있으면 건너뜀, 비밀번호가 정책(`AUTH_PASSWORD_VALIDATORS`)을 통과하지 못하면 건너뜀(계정 생성 안 됨)을 각각 확인.
  - **테스트 중 실제로 재현·수정한 결함**: 최초 구현의 안내 메시지에 em-dash(`—`, U+2014)를 썼는데, 이 검증 환경(Windows, cp949 콘솔)에서 `self.stdout.write()`가 `UnicodeEncodeError`로 커맨드 자체를 크래시시키는 것을 실제로 재현했다. Render 배포 환경(Linux, UTF-8 로케일)에서는 발생하지 않을 문제이지만, 로케일에 따라 크래시할 수 있는 문자를 CLI 출력 문자열에서 제거하는 것이 방어적으로 옳다고 판단해 해당 메시지의 em-dash를 마침표로 교체했다.

### 3-3. production 유사 설정(HTTPS 강제, `it_test_prodlike_wu09.py` = `production.py` 상속 + `DATABASES`만 SQLite로 재정의)

6. 더미 환경변수(`SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`/`RENDER_EXTERNAL_HOSTNAME`/`R2_*`/`DATABASE_URL`/`DJANGO_ADMIN_EMAIL`) 전체 채운 뒤 `manage.py check`/`migrate`/`collectstatic --noinput` 전부 오류 없음("218 static files copied ... 638 post-processed" — WU-08과 동일 수치로, 이번 WU가 새 정적자산을 추가하지 않았음을 재확인).
7. `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD`를 추가로 채운 뒤 `manage.py ensure_superuser` 실행 → 슈퍼유저 생성 성공 메시지 출력, `get_user_model().objects.filter(is_superuser=True)`에 실제로 반영됨을 확인.
8. 같은 상태에서 `manage.py ensure_superuser`를 **재실행** → "이미 존재합니다. 건너뜁니다" 메시지만 출력되고 두 번째 계정이 생성되지 않음을 확인(멱등성, production 유사 환경에서도 재확인).

### 3-4. 정리

검증에 사용한 `.venv_wu09`, `db.sqlite3`, `db_it_test_wu09.sqlite3`, `staticfiles/`, `media/`, `config/settings/it_test_prodlike_wu09.py`, `__pycache__`는 전부 삭제했다. `git status --porcelain`으로 diff에 소스 코드(신규 8개 파일 + 수정 3개 파일 + `docs/harness/` 갱신)만 남았음을 최종 확인했다 — WU-07/WU-08의 기존 미커밋 산출물은 이번 WU와 무관한 기존 상태이며 건드리지 않았다.

**로컬에서 확인하지 못한 것**: 실제 Render Free 티어 배포에서 `ensure_superuser`가 빌드 로그에 정상 출력되는지(Windows 로컬 제약, WU-01~08과 동일 사유), 15분 레이트리밋 윈도우가 실제 운영 트래픽 패턴에서 정당한 관리자를 과도하게 막지는 않는지(운영 데이터 필요).

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 여전히 **존재하지 않음을 재확인**했다(WU-01~08과 동일 결론 — 있는데 건너뛴 것이 아니라 설정 자체가 없다). 대체 수단으로 신규/수정 Python 파일 전체(`core/admin_auth.py`, `core/tests.py`, `core/migrations/0001_setup_editor_permissions.py`, `core/management/commands/ensure_superuser.py`, `config/urls.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다. `build.sh`/`render.yaml`은 YAML/셸 전용 린터가 없어 §3-3에서 실제로 실행(및 collectstatic/migrate 성공)해 형식 오류가 없음을 확인했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 4건은 전부 사유(기존 PASS 결정 존중, 작업 지시가 위임한 재량, 설계서가 소유 앱을 지정하지 않은 항목의 합리적 배치)와 함께 명시했으며 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — `ensure_superuser`는 환경변수 누락/비밀번호 정책 위반을 각각 명시적으로 감지해 안내 메시지와 함께 건너뛰고(예외를 삼키고 무시하지 않음 — 원인을 stdout에 남김), 예상치 못한 DB 오류 등은 그대로 전파시켜 빌드를 실패시킨다(migrate와 동일한 실패 전파 원칙 — 조용히 삼키지 않음). `RateLimitedLoginView`는 캐시 접근 실패 시 `cache.incr`의 `ValueError`만 명시적으로 잡아 카운터를 재설정하고, 그 외 예외는 그대로 전파한다(subscribers의 `_is_rate_limited`와 동일 패턴).
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 로그인 폼 자체의 검증은 Wagtail/Django 표준 `AuthenticationForm`이 그대로 수행한다(재구현하지 않음, §1.2). `ensure_superuser`의 환경변수 입력은 `validate_password()`(Django 표준)로 비밀번호 정책을 검증하고, 빈 값은 명시적으로 걸러낸다.
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. `DJANGO_SUPERUSER_*`는 전부 환경변수(`render.yaml`에서 `sync: false`)로만 주입되고, 코드 어디에도 기본 비밀번호/계정명을 하드코딩하지 않았다(값이 없으면 조용히 생성을 건너뛸 뿐).
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `blog/`, `legal/`, `subscribers/`, `custom_images/`, `home/`, `core/middleware.py`, `core/monitoring.py`, `core/wagtail_hooks.py`, `core/views.py`(WU-08 소유) 등 다른 WU 소유 코드는 전혀 건드리지 않았다. `config/urls.py`는 로그인 라우트 한 줄만 추가했고 기존 라우트 순서/구조는 그대로 유지했다.

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-010 행을 "Not Started"에서 "구현 완료"로 갱신하고 구현 근거 파일 경로를 명시했다. "단위테스트" 컬럼은 "6단계 대기"로 표기했고, "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다(WU-04~08 선례와 동일 패턴, 허위로 PASS를 채우지 않음).

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **Render 실제 배포에서 `ensure_superuser` 빌드 로그 미검증**: Windows 로컬 제약으로 실제 Render 빌드 환경(Linux, UTF-8)에서의 출력은 확인하지 못했다. 10단계(배포테스트)에서 실제 배포 시 빌드 로그에 "슈퍼유저 '...' 계정을 생성했습니다" 메시지가 나타나는지, 이후 `/cms-admin/login/`으로 실제 로그인이 되는지 반드시 실측해야 한다.
2. **15분/10회 임계값의 운영 적정성 미검증**: 실제 운영자의 로그인 습관(예: 여러 기기에서 동시 로그인 시도)에서 이 임계값이 과도하게 자주 걸리는지는 운영 데이터가 쌓여야 판단 가능하다. 문제가 되면 `core/admin_auth.py`의 상수(`RATE_LIMIT_MAX_ATTEMPTS`/`RATE_LIMIT_WINDOW_SECONDS`)만 조정하면 된다.
3. **LocMemCache 단일 프로세스 전제**: DEC-026(gunicorn `--workers 1` 고정)이 이미 이 전제를 명시적으로 유지하고 있으므로 현재는 문제가 없으나, 워커를 늘리게 되면 이 레이트리밋도 DEC-024/026과 같은 이유로 Redis 등 공유 저장소 전환이 선행돼야 한다 — `ADMIN_ACCESS_GUIDE.md` §4에 이미 명시했다.
4. **`ensure_superuser`가 매 배포마다 실행되므로, 첫 배포 이후 `DJANGO_SUPERUSER_PASSWORD` 환경변수를 대시보드에서 지우는 절차를 운영자가 실제로 수행했는지**는 코드로 강제할 수 없다(문서 권고만 가능). 11단계 운영 Runbook에 "최초 배포 후 슈퍼유저 부트스트랩 환경변수 삭제 확인"을 체크리스트 항목으로 반영 권고.
5. **어드민 접근 로그/감사(§1.4)를 "구현하지 않음"으로 판단한 것에 대한 재검토 여지**: 향후 다중 운영자 체제로 전환되면(REQ-026이 Out-of-Scope인 현재는 해당 없음), "누가" 발행/삭제했는지에 대한 화면 수준 감사가 필요해질 수 있다. 이 경우 Wagtail 내장 `PageLogEntry`를 노출하는 신규 화면을 별도 WU로 검토할 것을 권고(신규 데이터 모델은 필요 없음, §1.4 참고).
6. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다린다). 원격 push는 수행하지 않았다. WU-07/WU-08의 기존 미커밋 산출물도 이번 세션에서 건드리지 않고 그대로 두었다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일).

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가.
3. `manage.py migrate`가 빈 DB에서 오류 없이 끝나고, `manage.py showmigrations core`에 `[X] 0001_setup_editor_permissions`가 표시되는가.
4. `manage.py check`가 "System check identified no issues"를 출력하는가.
5. `manage.py test`(전체)가 27개 테스트(subscribers 12 + core 15) 전부 OK로 통과하는가(회귀 확인 포함).
6. 마이그레이션 적용 후 `Group.objects.get(name="Editors").permissions.filter(content_type__app_label="blog").values_list("codename", flat=True)`가 정확히 `{"add_category", "change_category", "delete_category"}`인가. `Moderators`도 동일한가.
7. Editors 그룹에 배정된 스태프 사용자가 `has_perm("blog.add_category")`/`change_category`/`delete_category` 전부 `True`이고, 그룹에 속하지 않은 일반 스태프 사용자는 `False`인가.
8. `reverse("wagtailadmin_login")`으로 얻은 URL에 GET을 11회 반복해도 매번 200이 오는가(GET은 카운트되지 않음).
9. 동일 IP(`REMOTE_ADDR`)로 해당 URL에 POST를 10회 보내면 매번 429가 아니고, 11번째 POST에서 429(본문 `text/plain`)가 오는가.
10. 올바른 사용자명/비밀번호로 임계값 이내에 POST하면 302(로그인 성공)가 오는가(레이트리밋이 정상 로그인을 막지 않음).
11. 서로 다른 `REMOTE_ADDR`은 카운터가 독립적인가(한 IP가 429여도 다른 IP는 429가 아님).
12. `RequestFactory` + `config.middleware.XForwardedForMiddleware`로 뷰를 감싼 뒤, `X-Forwarded-For` 헤더의 leftmost 값을 매번 바꾸고 rightmost 값을 고정해 10회 POST하면, 11번째 POST에서 429가 오는가(rightmost만 신뢰, 03 §5.5.4).
13. `Client(enforce_csrf_checks=True)`로 GET에서 CSRF 쿠키를 받아 POST에 그대로 실어 올바른 자격증명으로 로그인하면 302가 오는가(레이트리밋이 실제 CSRF 보호 로그인 흐름을 깨지 않음).
14. `manage.py ensure_superuser`를 `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD`(정책을 통과하는 값)와 함께 실행하면 해당 슈퍼유저가 생성되는가.
15. 슈퍼유저가 이미 존재하는 상태에서 다시 실행하면 새 계정이 생성되지 않고 "이미 존재" 메시지만 출력되는가(멱등성).
16. `DJANGO_SUPERUSER_USERNAME/PASSWORD`가 비어 있으면 계정이 생성되지 않고 안내 메시지만 출력되는가.
17. `DJANGO_SUPERUSER_PASSWORD`에 `AUTH_PASSWORD_VALIDATORS`를 통과하지 못하는 값(예: `"12345678"`)을 주면 계정이 생성되지 않고 비밀번호 정책 관련 경고 메시지가 출력되는가.
18. `config/settings/production.py`를 상속하고 `DATABASES`만 SQLite로 재정의한 설정 모듈(더미 `SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`/`RENDER_EXTERNAL_HOSTNAME`/`R2_*`/`DATABASE_URL` 환경변수)에서 `manage.py check`/`migrate`/`collectstatic --noinput`이 전부 오류 없이 끝나는가.
19. 위 production 유사 설정에서 `DJANGO_SUPERUSER_*` 환경변수를 채운 뒤 `manage.py ensure_superuser`를 실행하면 계정이 생성되고, 재실행하면 멱등하게 건너뛰는가.
20. `render.yaml`에 `DJANGO_SUPERUSER_USERNAME`/`DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` 키가 `sync: false`로 존재하는가(값이 커밋되지 않았는지 육안 확인).
21. `webapp/build.sh`에 `python manage.py ensure_superuser`가 `migrate --noinput` 이후에 위치하는가.
22. 검증에 사용한 venv/DB/staticfiles/media/임시 설정 모듈을 정리했는지, `git status --porcelain`에 소스 diff만 남는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~22번 인수 조건을 입력으로 `docs/harness/units/unit-09-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-09)의 7단계(통합테스트, WU-01~08과의 조립 검증 포함) 착수 여부를 오케스트레이터가 판단한다. 이번 세션 범위는 WU-09까지이며 WU-10/11은 착수하지 않았다.

---

## 재작업 라운드 2 (DEF-09-01 해소, 규칙F 재작업)

- 작성 에이전트: `05-unit-developer` (WU-09 타겟 재작업)
- 트리거: `docs/harness/09-security-audit.md`(FAIL) SEC-02가 실측 재현한 **DEF-09-01(High)** — `/cms-admin/login/`(Wagtail)만 레이트리밋이 걸려 있고 `/django-admin/login/`(Django 기본 관리자, 동일 `auth_user` 슈퍼유저 계정 공유)은 방어가 전혀 없어 11회 연속 로그인 실패에도 200이 반복됨을 `django.test.Client`로 직접 확인.
- 입력: `docs/harness/decisions.md` DEC-039(결함 발견/재작업 트리거)·DEC-040(3단계 재작업 채택안, 옵션2), `docs/harness/03-system-design.md` §5.1(v1.3, 구현 지침 1~5), `docs/harness/09-security-audit.md`(DEF-09-01 재현 절차), 기존 `webapp/core/admin_auth.py`/`webapp/config/urls.py`
- 작성일: 2026-09-17

### R2-1. 구현 범위

03 §5.1(v1.3)의 구현 지침 1~4를 그대로 따랐다(문자 그대로 따를 수 있을 만큼 구체적이어서, 두 갈래로 해석이 갈리는 지점은 없었다):

1. **`webapp/core/admin_auth.py`에 `RateLimitedAdminLoginView` 신설** — `django.views.View`를 상속(설계서 예시 그대로)하고, `dispatch()`에서 기존 `is_rate_limited(ip)`를 새로 만들지 않고 그대로 재사용해 POST가 임계값(IP당 15분/10회, DEC-029)을 넘으면 429를, 넘지 않으면 `django.contrib.admin.site.login(request, *args, **kwargs)`에 위임한다. `WagtailLoginView`를 상속하는 기존 `RateLimitedLoginView`와 달리, Django 기본 관리자 로그인은 상속할 뷰 클래스가 없다(`AdminSite.login()`은 바운드 메서드이며 내부에서 즉석으로 `LoginView.as_view()`를 만들어 호출) — 그래서 `View` 상속 + 위임 패턴을 썼다.
2. **카운터 공유** — `is_rate_limited(ip)`는 원래부터 IP만을 캐시 키(`core:admin_login:ratelimit:{ip}`)로 쓰고 URL을 구분하지 않으므로, 두 뷰가 이 함수를 그대로 호출하는 것만으로 자동으로 카운터가 공유된다. 별도 조치를 하지 않았다(설계서가 명시적으로 "새로 설계하지 않는다"고 지시한 부분).
3. **`webapp/config/urls.py`에 `path("django-admin/login/", RateLimitedAdminLoginView.as_view(), name="admin_login")`를 `path("django-admin/", admin.site.urls)`보다 먼저 추가** — 기존 `cms-admin/login/` 오버라이드와 동일한 배치 원칙. `admin.site.urls`가 내부적으로 등록하는 `login/`(namespace 내 이름 `admin:login`)은 그대로 남아 있어 `reverse("admin:login")`은 깨지지 않고(로컬 검증으로 실측 확인, R2-3), 실제 HTTP 요청만 먼저 배치된 우리 뷰가 가로챈다.
4. **기존 `/cms-admin/login/` 레이트리밋(WU-09 원본, DEC-028~031)은 코드 변경 없이 그대로 유지** — `RateLimitedLoginView`/카테고리 권한 마이그레이션/`ensure_superuser` 등은 이번 라운드에서 건드리지 않았다.

추가로(03 §5.1 지침 5, 이번 결함 수정과 직접 결부된 문서 정합성 조치로 판단 — DEC-041 참고) `webapp/ADMIN_ACCESS_GUIDE.md` §1/§4를 갱신해 "두 로그인 경로 모두 공유 레이트리밋으로 보호됨"을 반영했다.

**건드리지 않은 것(범위 외 변경 금지)**: Category 권한 마이그레이션(`core/migrations/0001_...`), `ensure_superuser` 커맨드, 로그인 뷰 자체의 그룹 권한 로직 — 전부 라운드 1 그대로다.

### R2-2. 파일 변경 목록

```
webapp/
  core/
    admin_auth.py       (수정) RateLimitedAdminLoginView 신설(신규 클래스), 모듈 docstring 갱신
    tests.py             (수정) DjangoAdminLoginRateLimitTests(6건) + SharedAdminRateLimitCounterTests(1건) 신규 추가
  config/
    urls.py               (수정) django-admin/login/ 을 admin.site.urls보다 먼저 오버라이드
  ADMIN_ACCESS_GUIDE.md    (수정) §1/§4 — 두 로그인 경로 공유 레이트리밋 반영
docs/harness/decisions.md  DEC-041(이번 라운드의 구현 세부 판단) 추가
docs/harness/traceability.md  REQ-010 행 갱신(v1.3 재작업 반영, 6/7/9단계 재검증 대기 명시)
```

### R2-3. 로컬 동작 확인 (실제 실행 결과)

`webapp/.harness-tmp/venv_09_wu09_r2/`(Python 3.13, `requirements.txt` clean install, 규칙K 준수 — 검증 후 즉시 삭제)로 실행했다.

1. `pip install -r requirements.txt` — 오류 없음(신규 패키지 없음).
2. `manage.py check`(dev 설정) → "System check identified no issues (0 silenced)".
3. `manage.py migrate --noinput`(빈 SQLite DB) → 오류 없음.
4. `manage.py test`(전체, dev 설정) → **재작업 전 29개 → 재작업 후 35개 전부 OK**(신규 6건 = `DjangoAdminLoginRateLimitTests` 5 + `SharedAdminRateLimitCounterTests` 1, 기존 29건 회귀 없음 — 6단계 DEC-031이 추가한 CSRF 경계 테스트 2건 포함).
5. **DEF-09-01 재현 시나리오를 09단계와 동일한 방법(`django.test.Client`, 동일 IP 11회 연속 POST)으로 `/django-admin/login/`에 직접 재실행** → `[200×10, 429]` — 11번째에 정확히 429가 나와 결함이 해소됨을 실측 확인(수정 전에는 09단계가 `[200×11]`로 재현했던 것과 대조).
6. **카운터 공유 계약 실측**: 동일 IP로 `/cms-admin/login/`에 5회 + `/django-admin/login/`에 6회(합산 11회) POST → 마지막(11번째, `/django-admin/login/`) 요청에서 429, 이어서 같은 IP로 `/cms-admin/login/`에 보낸 요청도 429(카운터가 URL과 무관하게 공유됨을 양방향으로 확인).
7. 올바른 자격증명으로 `/django-admin/login/`에 로그인하면 임계값 이내에서 302(로그인 성공)가 옴을 확인(레이트리밋이 정상 로그인 흐름을 깨지 않음).
8. GET 요청은 카운트되지 않음(11회 반복 GET 모두 200, 단 이미 인증된 세션으로 GET하면 Django 관리자 자체 동작으로 302 리다이렉트되는 것은 정상이며 레이트리밋과 무관 — 최초 조사에서 혼동했다가 신선한 미인증 `Client`로 재확인해 바로잡음).
9. `reverse("admin:login")`과 `reverse("admin_login")`이 둘 다 `/django-admin/login/`로 정확히 일치함을 확인(내부 `reverse("admin:login")` 호출 경로가 깨지지 않음, 03 §5.1 지침 3의 근거 재확인).
10. production 유사 설정(`production.py` 상속 + `DATABASES`만 SQLite, 더미 필수 환경변수 전체)에서 `manage.py check`/`migrate`/`collectstatic --noinput` 전부 오류 없이 끝남(`collectstatic` 결과 "218 static files copied ... 638 post-processed" — 라운드 1과 동일 수치로, 이번 라운드가 정적자산을 추가하지 않았음을 재확인).

**정리(규칙K)**: 검증에 사용한 `.harness-tmp/venv_09_wu09_r2/`, 임시 production 유사 설정 모듈(`config/settings/it_test_prodlike_wu09r2.py`), `db.sqlite3`/`db_it_test_wu09r2.sqlite3`, `staticfiles/`, `media/`, `__pycache__` 전부 삭제 확인. `git status --porcelain`으로 diff에 소스/문서 변경만 남았음을 최종 확인했다(기존에 미커밋 상태였던 03-system-design.md/decisions.md/traceability.md/09-security-audit.md 등은 이번 라운드 이전 세션(3단계 v1.3, 9단계 보안검증)이 만든 것이며 그대로 유지했다).

### R2-4. 게이트 1 — 정적 분석/린트

저장소 전체에 Python용 lint/type-check/formatter 설정이 여전히 존재하지 않음을 재확인했다(라운드 1과 동일 결론 — 있는데 건너뛴 것이 아니라 설정 자체가 없다). 대체 수단으로 수정된 `core/admin_auth.py`/`core/tests.py`/`config/urls.py`에 `python -m py_compile`을 실행해 구문 오류 없음을 확인했다.

### R2-5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 03 §5.1(v1.3) 구현 지침 1~4를 문자 그대로 구현했다(클래스명, 카운터 공유 방식, urls.py 배치 순서 전부 설계서 예시 코드와 일치).
- [x] **에러 처리가 누락된 경로가 없는가** — `RateLimitedAdminLoginView.dispatch()`는 기존 `RateLimitedLoginView`와 동일하게 `is_rate_limited()`의 예외를 삼키지 않고(그 함수 내부에서만 `ValueError`를 명시적으로 처리), 레이트리밋을 통과한 요청은 `admin.site.login()`에 그대로 위임해 Django 표준 에러 처리(폼 검증 실패 등)를 그대로 따른다.
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 로그인 폼 자체의 검증은 Django 표준 `AdminAuthenticationForm`이 수행(재구현하지 않음). 이번 라운드가 새로 받는 입력은 없다(기존 `REMOTE_ADDR` 신뢰 경계 그대로 재사용).
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 이번 라운드는 시크릿을 다루지 않는다.
- [x] **새로 추가한 외부 의존성이 있다면 실존 여부를 확인했는가** — 신규 패키지 없음(설계서 지침이 "기존 `is_rate_limited()`를 재사용"하도록 명시적으로 지시했고 그대로 따름). `requirements.txt` 변경 없음.
- [x] **범위를 벗어난 변경이 섞여 있지 않은가** — Category 권한 마이그레이션/`ensure_superuser`/`RateLimitedLoginView` 자체 로직 등 라운드 1의 다른 부분은 전혀 건드리지 않았다. `config/urls.py`는 신규 라우트 1줄 + import 1줄만 추가했다.

### R2-6. 수동으로 확인이 필요한 부분 (6단계 테스터 인계)

1. **09단계가 로컬 재현에 썼던 정확한 venv/스크립트(`webapp/.harness-tmp/venv_09_sec`)는 이미 삭제된 상태**이므로, 6단계는 이 노트의 §R2-3 절차(신규 venv + `Client()` 11회 연속 POST)를 자신의 검증 환경에서 처음부터 다시 실행해 독립 재현해야 한다(기존 원칙과 동일 — 5단계 보고를 신뢰하지 않고 재현).
2. **7단계(통합테스트) 재실행 필요**: DEC-039가 요구한 재검증 체인은 5→6→7→9다. 이번 라운드는 5단계 몫만 수행했으므로, 6단계 PASS 이후 7단계가 WU-01(XFF 미들웨어)/WU-08(모니터링 미들웨어) 등과의 조립 상태에서 `/django-admin/login/` 레이트리밋이 실제로 정상 동작하는지 재확인해야 한다.
3. **9단계 재검증 필요**: `09-security-audit.md` §6 SEC-02와 동일한 방법(신규 venv, `Client()` 11회 연속 POST)으로 DEF-09-01이 Fixed로 전환되었는지 최종 확인이 남아 있다(§R2-3의 5번 항목이 그 절차를 이미 한 번 로컬로 재현했지만, 9단계는 독립적으로 재실행해야 한다).
4. **워커 수 전제(DEC-026, `--workers 1`)는 이번 라운드로 변경되지 않았다** — 두 뷰가 공유하는 `LocMemCache` 카운터도 여전히 단일 프로세스 전제 위에서만 정확하다(라운드 1과 동일한 기존 리스크, 신규 아님).

### R2-7. 6단계(단위테스트) 인수 조건 (Acceptance Criteria) — 재작업 라운드 2분

기존 §8의 AC1~22(라운드 1, 여전히 유효 — 회귀 확인 대상)에 더해, 아래 AC23~29를 이번 라운드의 신규 인수 조건으로 추가한다.

23. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음, requirements.txt 변경 없음을 `git diff`로 확인).
24. `reverse("admin_login")`과 `reverse("admin:login")`이 둘 다 `/django-admin/login/`을 반환하는가(URL 이름 충돌 없음).
25. **(DEF-09-01 재현 절차 그대로)** 동일 `REMOTE_ADDR`로 `/django-admin/login/`에 POST를 10회 보내면 매번 429가 아니고, 11번째 POST에서 429(본문 `text/plain`)가 오는가.
26. 올바른 사용자명/비밀번호로 `/django-admin/login/`에 임계값 이내에 POST하면 302(로그인 성공)가 오는가.
27. `/django-admin/login/`에 대한 GET은 11회 반복해도 매번 200(미인증 상태 기준)이고 카운트되지 않는가.
28. **(카운터 공유 계약)** 동일 IP로 `/cms-admin/login/`에 5회 + `/django-admin/login/`에 6회(합산 11회) POST하면, 11번째 요청에서 429가 오는가. 그 직후 같은 IP로 반대쪽 URL(`/cms-admin/login/`)에 보낸 요청도 429가 오는가(카운터가 양방향으로 공유됨을 확인).
29. 라운드 1의 AC5(`manage.py test` 전체 통과)를 재실행하면 총 35개 테스트(기존 29 + 신규 6)가 전부 OK인가.
30. 검증에 사용한 venv/DB/staticfiles/media/임시 설정 모듈을 정리했는지, `git status --porcelain`에 소스/문서 diff만 남는지 확인.

---

이 절 작성 완료 후 **6단계(`06-unit-tester`) 재호출을 트리거한다** — 위 AC1~22(회귀) + AC23~30(신규)을 입력으로 `unit-09-test.md`를 갱신(재검증 라운드 추가)하도록 한다. 6단계 PASS 이후 DEC-039가 정한 순서(7→9)로 이어진다.
