# WU-01 — 프로젝트 초기 설정 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-01, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.1, PASS), `docs/harness/04-ux-design.md`(v1.2, PASS), `docs/harness/decisions.md`(DEC-001~014)
- 작성일: 2026-09-16
- **재작업 이력**: 2026-09-16, 규칙F 재작업 1회 — 아래 §0 참고

---

## 0. 재작업 이력 (규칙 F 피드백 루프)

- **근거**: `docs/harness/feature-WU-01-integration-test.md`(07단계 통합테스트) FAIL 판정 — DEF-001(Critical). production 배포 시 `SECURE_PROXY_SSL_HEADER` 미설정으로 `SECURE_SSL_REDIRECT=True`와 결합해 무한 HTTPS 리다이렉트 루프가 발생, 사이트 100% 접근 불가. 07단계는 근본 원인을 구현 실수가 아니라 **설계 단계의 누락**(Render의 TLS 종료 아키텍처 전제 자체가 03-system-design.md §5.5에 없었음)으로 지목했다(규칙F-1, 근본 원인 단계까지 소급).
- **선행 조치**: 03-system-design.md가 §5.5를 v1.1 → v1.2로 갱신(내부검증 규칙B 2회 재수행 완료, `verify-log_03-system-design.md` "재작업 라운드" 참고)하고 DEC-015로 기록됨. 이 노트는 그 v1.2 §5.5를 입력으로 받아 **WU-01 코드(`webapp/config/settings/production.py`, 신규 `webapp/config/middleware.py`)를 수정**하는 규칙F-3(하위 단계 재실행) 작업이다.
- **무엇을 왜 고쳤는지** (03 §5.5.2~§5.5.4 기준):
  1. `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`를 `production.py`에 신규 추가(Critical, DEF-001 직접 해소). Render 엣지가 TLS를 종료하고 앱에는 평문 HTTP로 전달하므로, 이 설정이 없으면 `request.is_secure()`가 항상 `False`로 판정되어 무한 리다이렉트 루프가 발생한다.
  2. `CSRF_TRUSTED_ORIGINS`(기존 구현, `ALLOWED_HOSTS`에서만 파생)는 03 §5.5.3이 정식 요구사항으로 격상한 것을 코드가 이미 만족하고 있음을 재확인하고, 왜 이렇게(하드코딩 오리진 없이 `ALLOWED_HOSTS` 기반 파생만) 구성했는지 근거 주석을 추가했다.
  3. `USE_X_FORWARDED_HOST`는 03 §5.5.3 점검 결과(조치 불필요)를 그대로 유지하되, 켜지 않는 근거(Render는 원본 Host 헤더를 그대로 전달하는 단일 홉 투명 프록시이며, 불필요하게 켜면 `X-Forwarded-Host`가 새 스푸핑 경로가 될 수 있음)를 주석으로 명시했다.
  4. 03 §5.5.4(신규 식별, Medium)에 따라 `X-Forwarded-For`의 rightmost 값을 `REMOTE_ADDR`로 재설정하는 `XForwardedForMiddleware`를 `webapp/config/middleware.py`에 신규 작성하고, `production.py`의 `MIDDLEWARE` 최상단에만 추가했다(dev에는 추가하지 않음 — "Render 엣지만이 유일한 진입 경로"라는 신뢰 전제가 dev 로컬 실행에는 성립하지 않기 때문). WU-07/WU-09가 실제 레이트리밋 로직을 구현할 때 이 값을 그대로 신뢰해 쓸 수 있도록 재사용 가능한 유틸 수준으로만 만들었다 — 레이트리밋/스팸 방지 로직 자체는 이번 범위 밖(지시사항과 동일).
- **범위 외로 명시적으로 하지 않은 것**: `base.py`는 수정하지 않았다 — 이번 변경은 모두 production 전용 관심사(리버스프록시 배포 환경 전제)이고, dev에는 해당 전제가 없어 `base.py`의 공통 `MIDDLEWARE`/설정을 건드릴 이유가 없었다.
- **재검증 결과**: 아래 §4-1 "재작업 로컬 검증" 참고. 07단계(`feature-WU-01-integration-test.md`)는 이 코드 변경을 입력으로 IT-02/IT-03을 재실행해 PASS로 갱신해야 한다(이번 05단계 산출물 완료 후 06 → 07 순서로 재트리거).
- **별도 DEC 필요 여부**: 없음. 설계 결정 자체는 이미 DEC-015(decisions.md)로 기록되어 있고, 이번 구현 중 새로운 비가역적 판단은 발생하지 않았다(미들웨어를 dev에 넣지 않기로 한 판단은 03 §5.5.4의 "신뢰할 수 있는 단일 홉" 전제를 그대로 따른 것이지, 새로운 아키텍처 결정이 아니므로 별도 DEC 미기록).

## 1. 구현 범위

Wagtail/Django 프로젝트 코드 기반 골격 전체(다른 모든 WU의 선행 조건)를 `webapp/` 하위에 신규 생성했다. 실제로 만든 파일:

```
webapp/
  manage.py
  build.sh                      Render 빌드 커맨드(pip install → collectstatic → migrate)
  render.yaml                   Render Blueprint 골격(시크릿은 전부 sync:false)
  requirements.txt              정확한 버전 핀(아래 §3 참고)
  .env.example
  .gitignore
  config/
    __init__.py
    middleware.py              (재작업 신규) XForwardedForMiddleware — X-Forwarded-For rightmost 값을 REMOTE_ADDR로 재설정(03 §5.5.4)
    settings/
      __init__.py
      base.py                   공통 설정(INSTALLED_APPS, TEMPLATES, CACHES=LocMemCache, STORAGES 기본값 등)
      dev.py                    DEBUG=True, SQLite 기본(DATABASE_URL로 로컬 Postgres 전환 가능)
      production.py             필수 환경변수 미설정 시 기동 실패(ImproperlyConfigured), R2 STORAGES, HTTPS 강제. (재작업) SECURE_PROXY_SSL_HEADER 추가, XForwardedForMiddleware 등록, CSRF_TRUSTED_ORIGINS/USE_X_FORWARDED_HOST 근거 주석 보강
    urls.py                     Wagtail 어드민 경로를 /cms-admin/으로 변경(DEC-009)
    wsgi.py / asgi.py           asgi.py 신규 작성(gunicorn+uvicorn 워커용, 03 §1.1/§2.4)
    templates/base.html, 404.html, 500.html
    static/css/tokens.css       04-ux-design.md §3 디자인 토큰을 CSS 커스텀 프로퍼티로 그대로 반영
    static/css/base.css         토큰을 적용하는 최소 리셋 + 스킵링크 스타일만(컴포넌트 스타일은 WU-04)
  home/
    models.py                   HomePage(Page) — Wagtail 페이지 트리 루트
    apps.py, migrations/0001_initial.py, migrations/0002_create_homepage.py
    templates/home/home_page.html
docs/harness/decisions.md       DEC-013(디렉터리 배치), DEC-014(Django 5.2 LTS 호환 재확인) 추가
```

## 2. 설계서 대비 편차 (사유 포함)

1. **프로젝트 배치 경로**: 03/04번 설계서는 정확한 디렉터리 경로를 지정하지 않았다. `wagtail start`의 표준 산출물은 프로젝트 루트에 `templates/`를 만드는데, 이 하네스가 이미 저장소 루트에서 `templates/`(decision-log-template.md 등 공통 양식)를 쓰고 있어 충돌한다. `webapp/` 하위 디렉터리에 전체 프로젝트를 배치해 충돌을 피했다 — DEC-013으로 기록.
2. **`search` 앱 제외**: `wagtail start` 표준 스캐폴딩은 `home` 외에 기본 검색 뷰를 제공하는 `search` 앱도 함께 생성한다. 03 §1.2 모듈 경계 표에는 `search` 앱이 없고, REQ-018(내부 검색)은 Could-have로 v1 미구현이 명시되어 있어(WU-11, 자리만 마련) `search` 앱은 생성하지 않았다(범위 외 기능 추가 금지 원칙).
3. **`home` 앱은 유지**: 03 §1.2 모듈 표에는 `home` 앱이 명시적으로 나열되어 있지 않지만, Wagtail 아키텍처상 페이지 트리의 루트 역할을 할 최소 Page 모델이 반드시 있어야 하므로(그렇지 않으면 사이트 자체가 기동하지 않음) 표준 `wagtail start` 관례대로 유지했다. `BlogPostPage`/`LegalPage` 등 실제 콘텐츠 모델은 만들지 않았다(WU-02/WU-06 범위).
4. **blog/subscribers/legal/core 앱 미생성**: 03 §1.2가 언급하는 도메인 앱들은 각각 WU-02(콘텐츠), WU-03(스토리지 연동은 설정만 이번 WU에서 처리), WU-06(법적 페이지), WU-07(뉴스레터), WU-08/WU-09(core: 헬스체크/어드민 등)에서 만들 대상이다. 이번 WU는 "골격"만 지시받았으므로(작업 지시 §1~§7) 앱 디렉터리를 미리 만들지 않았다 — 빈 껍데기 앱을 먼저 만들어두는 것도 각 WU가 실제로 무엇을 새로 추가했는지 흐리게 하는 것이라 판단했다.
5. **Django 마이그레이션 의존성 수정(설계 편차 아님, 구현 중 발견한 버그 회피)**: `manage.py makemigrations`가 자동 생성한 `home/migrations/0001_initial.py`는 기본적으로 `wagtailcore`의 최신 마이그레이션(0097)에 의존하게 되는데, Wagtail 공식 프로젝트 템플릿의 `0002_create_homepage.py`는 `run_before=[("wagtailcore","0053_locale_model")]` 제약을 갖고 있어 그대로 두면 `CircularDependencyError`가 실제로 발생했다(로컬 검증 중 재현). Wagtail 공식 `project_template`(설치된 패키지 안의 `wagtail/project_template/home/migrations/0001_initial.py`)을 직접 열어 확인한 뒤, 의존성을 `("wagtailcore", "0040_page_draft_title")`로 고정해 해결했다. 이는 Wagtail 자체가 공식적으로 검증한 패턴을 그대로 따른 것이다.
6. **STORAGES["default"] 클래스 경로**: 03 §2.3은 "`django-storages` + `boto3`의 `S3Boto3Storage`"라고 표현하지만, 실제로 `django-storages==1.14.6` 패키지를 설치해 확인한 결과 최신 클래스 경로는 `storages.backends.s3.S3Storage`다(`S3Boto3Storage`는 과거 버전의 이름이며 1.14.x에서도 하위호환 별칭이 존재하긴 하나, 패키지가 실제로 노출하는 표준 이름을 그대로 썼다). 기능은 설계서가 의도한 것과 동일(S3 호환 엔드포인트로 R2 연결).

## 3. 버전 고정 근거 (게이트2 체크리스트 — 실존 패키지 확인)

아래 전부 `pip index versions <pkg>`로 PyPI에 실제 존재하는지 직접 조회했다(그럴듯하지만 실존하지 않는 버전을 임의로 지어내지 않았음을 확인):

| 패키지 | 버전 | 비고 |
|---|---|---|
| Django | 5.2.17 | DEC-006 LTS 고정. Wagtail 7.4.3 메타데이터(`Requires-Dist: Django>=5.2`)로 호환 재확인 — DEC-014 |
| wagtail | 7.4.3 | DEC-006 |
| psycopg[binary] | 3.2.10 | psycopg3, Django 5.2 공식 지원 드라이버 |
| dj-database-url | 2.3.0 | |
| django-storages[s3] | 1.14.6 | DEC-008. `storages.backends.s3.S3Storage` 클래스 실존 확인(§2-6 참고) |
| boto3 | 1.35.36 | |
| gunicorn | 23.0.0 | 03 §2.4 |
| uvicorn[standard] | 0.34.0 | 03 §1.1 ASGI 워커 |
| whitenoise | 6.8.2 | 03 §2.4 |
| python-dotenv | 1.0.1 | 로컬 `.env` 로딩 편의 |

## 4. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv`, 검증 후 삭제)에서 `pip install -r requirements.txt` 후 아래를 직접 실행해 확인했다:

- `python manage.py makemigrations home` → `home/migrations/0001_initial.py` 생성
- `python manage.py migrate`(dev, SQLite) → 전체 마이그레이션(Wagtail 코어 포함) 오류 없이 적용
- Wagtail 페이지 트리 확인: `HomePage` 인스턴스(id=3, slug=home)가 Site의 root_page로 정상 생성됨(공식 데이터 마이그레이션 패턴대로 기본 "Welcome to..." placeholder 페이지가 삭제되고 교체됨)
- `python manage.py check` → "System check identified no issues (0 silenced)"
- Django `test.Client`로 `GET /` → 200, `<html lang="ko">` 및 `tokens.css`/`base.css` 링크 포함 확인
- `GET /cms-admin/login/` → 200 (관리자 경로가 `/cms-admin/`으로 변경되었음을 실측 확인, DEC-009)
- `GET /nonexistent-page/` → 404
- `python manage.py collectstatic --noinput`(dev) → 214개 파일 정상 수집
- production 설정: `SECRET_KEY` 등 필수 환경변수 없이 `manage.py check` 실행 시 `ImproperlyConfigured` 예외로 **의도한 대로 즉시 실패**함을 확인. 더미 값(`SECRET_KEY`, `DATABASE_URL`, `R2_*`)을 전부 채운 뒤에는 `manage.py check`와 `collectstatic --noinput`(WhiteNoise 매니페스트 스토리지, 626개 파일 post-process) 모두 정상 통과
- 검증에 사용한 venv/`db.sqlite3`/`staticfiles/`는 전부 삭제하고 마쳤다(diff에는 소스 코드만 남음)

**로컬에서 확인하지 못한 것(플랫폼 제약)**: `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker` 실제 기동은 로컬에서 검증하지 못했다 — gunicorn은 POSIX `fork()`에 의존해 Windows에서 동작하지 않는다(현재 개발 환경이 Windows). 이 커맨드가 실제로 뜨는지는 10단계(배포테스트, Linux 기반 Render 환경)에서 반드시 확인해야 한다.

### 4-1. 재작업(규칙F) 로컬 검증 (2026-09-16, DEF-001 해소 확인)

06/07단계가 사용한 검증용 venv/DB/staticfiles는 이미 삭제된 상태였으므로, 새 임시 venv(`webapp/.venv_it2`)를 처음부터 만들어 `pip install -r requirements.txt`부터 재현했다. 07단계 IT-02/IT-03과 동일한 방식(Render의 TLS 종료 아키텍처를 로컬에서 재현)으로 아래를 `django.test.Client`로 직접 실행해 확인했다:

- **재현 전제**: production 더미 환경변수 전체(`SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=www.example.com`, `RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`, `R2_*`) + `collectstatic --noinput`(214개 복사/626개 post-process, 07단계와 동일 결과) 완료. DB 접근이 필요한 라우트는 07단계와 동일한 사유(SQLite+`ssl_require=True` 조합이 `TypeError: 'sslmode' is an invalid keyword argument`로 즉시 크래시, production은 Neon 전용 설계이므로 결함 아님)로 WhiteNoise 정적자산 경로(`/static/css/tokens.<hash>.css`)를 사용해 SSL 리다이렉트 경계만 분리 검증했다.
- **Case A (헤더 없음, `Host: blog-web.onrender.com`만 설정)**: `GET /static/css/tokens.dce349c89221.css` → **301**, `Location: https://blog-web.onrender.com/...` — 프록시 헤더가 없으면 여전히 정상적으로 HTTPS로 리다이렉트됨을 확인(회귀 없음, 의도된 동작).
- **Case B (`X-Forwarded-Proto: https` 헤더 추가)**: 동일 요청 → **200**. 같은 요청을 반복(브라우저가 리다이렉트를 따라간 뒤 재요청하는 상황 시뮬레이션)해도 **200이 유지**되고 다시 301로 튕기지 않음을 확인 — 07단계 IT-02/IT-03이 재현했던 무한 리다이렉트 루프가 해소됨.
- **Case C (`XForwardedForMiddleware` 단위 동작)**: `RequestFactory`로 `X-Forwarded-For: 1.2.3.4, 10.0.0.5` 헤더를 가진 요청을 만들어 미들웨어에 직접 통과시킨 결과, `REMOTE_ADDR`이 rightmost 값인 `10.0.0.5`로 정확히 재설정됨을 확인(03 §5.5.4가 요구한 rightmost 채택 방식과 일치).
- **회귀 확인**: `DJANGO_SETTINGS_MODULE=config.settings.production manage.py check` → "System check identified no issues". `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `manage.py check`/`makemigrations --check --dry-run` → 이상 없음, "No changes detected"(dev 경로에 회귀 없음 확인 — `base.py`를 건드리지 않았으므로 예상된 결과).
- **정리**: 검증 후 `.venv_it2`, `db.sqlite3`, `staticfiles/`, `media/`, `__pycache__/`를 전부 삭제해 `webapp/`를 소스 코드만 남긴 상태로 복원했다(`find webapp -type f`로 25개 파일 — 기존 24개 + 신규 `config/middleware.py` 1개 — 확인).

## 5. 게이트 1 — 정적 분석/린트

저장소 전체(`AI-AUTO-WORK` 루트 포함)에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 **존재하지 않는다** — 직접 검색해 확인했으며, 있는데 건너뛴 것이 아니라 애초에 설정 자체가 없다. 대체 수단으로 `python -m py_compile`을 모든 신규 `.py` 파일에 대해 실행했고 전부 구문 오류 없이 통과했다.

**(재작업 라운드, 2026-09-16)**: 이번 재작업에서 수정/신규 작성한 `config/middleware.py`, `config/settings/production.py`에 대해 다시 `python -m py_compile`을 실행했고(설정 자체가 없다는 사실은 이번에도 동일하게 재확인) 구문 오류 없이 통과했다.

## 6. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] 설계서/디자인서 명세와 실제 구현이 일치하는가 — 일치(§2 편차 항목은 전부 사유와 함께 명시)
- [x] 에러 처리가 누락된 경로가 없는가 — production.py의 필수 환경변수 누락은 조용히 넘어가지 않고 `ImproperlyConfigured`를 즉시 발생시킴(예외를 삼키는 코드 없음)
- [x] 입력값 검증이 시스템 경계에서 이루어지는가 — 이 WU 범위에는 사용자 입력을 받는 뷰가 없음(뉴스레터 폼 등은 WU-07). 유일한 "경계"는 환경변수이며, production.py가 필수 값 존재를 기동 시점에 검증함
- [x] 하드코딩된 시크릿/자격증명이 없는가 — 없음. dev.py의 기본 SECRET_KEY는 `django-insecure-dev-only-...`로 명확히 표시된 개발 전용 더미 값이며 프로덕션에서는 강제로 무시되고 환경변수가 필수임
- [x] 새로 추가한 외부 의존성이 실제 PyPI 패키지인지 확인 — §3 표 전체를 `pip index versions`로 직접 조회해 확인함
- [x] 범위를 벗어난 변경이 섞여 있지 않은가 — blog/subscribers/legal/core 등 다른 WU 소관 앱/모델은 만들지 않았고, `docs/harness` 문서 중 이번 WU와 무관한 파일은 건드리지 않음(`decisions.md`에 DEC-013/014 추가만 함)

**(재작업 라운드, 2026-09-16, DEF-001 대응 범위)**

- [x] 설계서/디자인서 명세와 실제 구현이 일치하는가 — 03 §5.5.2~§5.5.4의 코드 예시(`SECURE_PROXY_SSL_HEADER` 값, rightmost XFF 채택 방식)를 문자 그대로 반영
- [x] 에러 처리가 누락된 경로가 없는가 — `XForwardedForMiddleware`는 `X-Forwarded-For` 헤더가 없거나 빈 값이면 `REMOTE_ADDR`을 건드리지 않고 그대로 통과시킴(예외적 형식을 조용히 잘못 처리하지 않음). 헤더 파싱 실패로 인한 예외 경로는 없음(단순 `split`/`strip`만 사용, 빈 문자열 방어 포함)
- [x] 입력값 검증이 시스템 경계에서 이루어지는가 — `X-Forwarded-For`는 외부(리버스프록시)에서 오는 값이므로 신뢰 경계를 rightmost 값(단일 신뢰 홉이 실제로 추가한 값)으로 명확히 한정했고, leftmost(클라이언트가 임의 조작 가능한 값)는 신뢰하지 않음(03 §5.5.4)
- [x] 하드코딩된 시크릿/자격증명이 없는가 — 이번 변경분에 시크릿 없음(설정값·미들웨어 로직만)
- [x] 범위를 벗어난 변경이 섞여 있지 않은가 — `webapp/config/settings/base.py`는 건드리지 않았고(변경 불필요, §0 참고), `dev.py`도 무변경. WU-07/09의 실제 레이트리밋/스팸방지 로직은 구현하지 않음(지시사항 범위 외로 명시)

## 7. traceability.md 갱신 여부

**변경 없음.** `docs/harness/02-planning.md` §9에 WU-01은 "(전체 REQ의 기반, 직접 매핑 없음)"으로 명시되어 있고, `docs/harness/traceability.md`의 어떤 REQ-ID 행도 작업 단위 컬럼에 WU-01을 참조하지 않는다. 따라서 이번 WU에서 갱신할 REQ-ID 행이 없다(사실 확인 완료, 빠뜨린 것이 아님).

**(재작업 라운드, 2026-09-16) 재확인**: `docs/harness/traceability.md` 27개 REQ 행을 이번에도 다시 직접 열람해, DEF-001/DEC-015 대응(리버스프록시 보안 설정)과 관련된 REQ-ID 행이 있는지 재확인했다 — 없음. 가장 근접한 후보인 REQ-010(관리자 인증/로그인 레이트리밋)·REQ-016(뉴스레터)도 "작업 단위" 컬럼이 각각 WU-09/WU-07로 이미 지정되어 있고, 이번 WU-01 변경은 그 두 WU가 나중에 쓸 `REMOTE_ADDR` 유틸을 준비해 둔 것일 뿐 REQ-010/016 자체를 구현한 것이 아니므로(§0/§8-9 참고) 이번 라운드에도 WU-01을 참조하도록 traceability.md를 갱신할 행이 없다. `feature-WU-01-integration-test.md` §5(07단계 커버리지)의 동일 결론과 일치한다.

## 8. 수동 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **Neon 실제 연결**: `DATABASE_URL`은 아직 실제 Neon 프로젝트가 없어 값이 없다(사용자 지시사항 원문: "연결 정보는 아직 실제 발급 안 됨"). 로컬 검증은 SQLite로 수행했다. 10~12단계에서 Neon 프로젝트를 실제로 만들 때, pooled connection string(`-pooler` 호스트) 제공 여부를 반드시 재확인할 것(03 §6.4, 아직 미해결로 이월 — `.env.example`에 주석으로 남겨둠).
2. **Cloudflare R2 실제 버킷/키**: 마찬가지로 아직 발급 전. `production.py`는 값이 없으면 기동 자체가 실패하도록 만들어져 있어, 실제 배포 시 이 값들을 채우지 않으면 바로 드러난다(조용히 로컬 파일시스템으로 폴백하지 않음 — 의도된 안전장치).
3. **gunicorn+uvicorn 실제 기동**: 위 §4에서 설명한 대로 Windows 로컬 환경 제약으로 검증 못함. 10단계에서 Linux 기반 Render(또는 동등 리눅스 환경)에서 `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker` 기동을 반드시 실측할 것.
4. **Pretendard 웹폰트**: `tokens.css`에 `--font-primary` 토큰은 정의했지만 실제 `@font-face`(자체 호스팅 또는 CDN) 로딩은 넣지 않았다 — WU-04(공개 화면 UX 구현)에서 처리 예정. 지금은 시스템 폰트 fallback으로 렌더링된다.
5. **HSTS max-age**: `production.py`에 `SECURE_HSTS_SECONDS`를 1주일(604800초)로 보수적으로 잡아뒀다. 배포 후 HTTPS가 안정적으로 동작함을 실측 확인한 뒤 값을 늘리는 것을 운영 Runbook(11단계)에 반영할 것을 권고한다.
6. **django-taggit / django-axes(or ratelimit) 라이선스 재확인**: 03 §2.6에서 "확인 필요"로 남긴 항목이며, 이번 WU에서는 두 패키지 모두 실제로 설치/사용하지 않았다(taggit은 Wagtail의 전이 의존성으로만 설치됨, axes/ratelimit은 WU-09 소관). 아직 미해결로 이월.
7. **git 커밋 여부**: 이번 프로젝트(`AI-AUTO-WORK`)는 이미 git 저장소이고 `origin` 리모트도 연결되어 있어(`git remote -v` 확인함), 작업 지시 §7의 "저장소가 아직 없으면 git init"은 해당하지 않는다. 이번 WU 산출물은 **아직 커밋하지 않았다** — 일반 원칙("사용자가 명시적으로 요청할 때만 커밋")에 따라 오케스트레이터/사용자의 커밋 지시를 기다린다. 원격 push는 어떤 경우에도 수행하지 않았다.
8. **(재작업 신규) 10단계 실측 검증 필수**: 03 §7.2 (3)항이 명시한 대로, Uvicorn/Gunicorn 레벨에서 별도의 프록시 헤더 처리가 존재해 `SECURE_PROXY_SSL_HEADER` 판정과 충돌하지 않는지는 이번 재작업에서도 `test.Client()`로만 검증했다(§4-1) — 실제 gunicorn+uvicorn 프로세스가 Render 환경에서 Render 엣지가 보내는 실제 `X-Forwarded-Proto`/`X-Forwarded-For` 헤더로 무한루프 없이 동작하는지는 10단계에서 반드시 실측할 것.
9. **(재작업 신규) `X-Forwarded-For` 신뢰 방식 확인 필요 이월**: 03 §5.5.4가 "확인 필요"로 남긴 항목 — Render가 `X-Forwarded-For`를 자체적으로 관리(덮어쓰기/신뢰 보증)하는지 공식 문서로 아직 확정하지 못했다. 이번 WU는 설계서가 지시한 보수적 기본값(rightmost 채택)으로 구현했으며, 이후 단계(10단계 또는 실제 레이트리밋을 구현하는 WU-07/09)에서 Render 공식 문서로 재확인이 필요하다.

## 9. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

아래는 6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다.

1. `webapp/` 디렉터리에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가.
2. `DJANGO_SETTINGS_MODULE` 미지정 상태(즉 `manage.py` 기본값 `config.settings.dev`)로 `python manage.py migrate`를 실행하면, SQLite(`db.sqlite3`)에 오류 없이 전체 마이그레이션이 적용되는가. 특히 `home` 앱의 `0001_initial`/`0002_create_homepage`가 `CircularDependencyError` 없이 적용되는가.
3. `python manage.py check`가 "System check identified no issues"를 출력하는가.
4. `python manage.py runserver`(또는 `test.Client`)로 `GET /`를 호출하면 200과 함께 `<html lang="ko">`, `<title>`에 "Home"이 포함된 HTML이 오는가.
5. `GET /cms-admin/login/`이 200을 반환하는가(어드민 경로가 `/admin/`이 아니라 `/cms-admin/`으로 변경되었는지, DEC-009/03 §5.1 요건).
6. `GET /admin/`(변경 전 기본 경로)을 호출했을 때 Wagtail 어드민이 아니라 Wagtail의 일반 페이지 서빙 로직으로 넘어가 404가 나는가(즉 구 경로가 실수로 남아있지 않은지 — django-admin은 `/django-admin/`에 별도로 남아있음, 의도된 동작).
7. 존재하지 않는 경로(`GET /no-such-page/`)가 404를 반환하는가.
8. `DJANGO_SETTINGS_MODULE=config.settings.production`으로 `SECRET_KEY`/`DATABASE_URL`/`R2_*` 환경변수 없이 아무 `manage.py` 커맨드나 실행하면 `ImproperlyConfigured` 예외로 즉시 실패하는가(시크릿 하드코딩/조용한 폴백이 없는지 확인).
9. 위 8번의 환경변수를 전부(더미 값이라도) 채운 뒤 `python manage.py check`와 `python manage.py collectstatic --noinput`이 정상 통과하는가(단, 이 상태에서는 실제 R2/Neon에 네트워크 요청을 시도하지 않으므로 더미 값으로도 통과해야 정상 — `collectstatic`은 "staticfiles" 스토리지만 건드리고 "default"(R2) 스토리지는 건드리지 않기 때문).
10. `render.yaml`의 `buildCommand`(`./build.sh`)와 `startCommand`가 03-system-design.md §2.4가 명시한 Render 공식 패턴(빌드 스크립트 안에서 migrate, `gunicorn ...:application -k uvicorn.workers.UvicornWorker` 기동)과 문자 그대로 일치하는가.
11. `.env.example`에 실제 시크릿 값이 하드코딩되어 있지 않은가(전부 빈 값 또는 설명 주석뿐인지).
12. `webapp/.gitignore`가 `.env`, `db.sqlite3`, `.venv/`, `/staticfiles/`, `/media/`를 제외하는지, 그리고 실제로 이번 diff에 이 파일들이 포함되어 있지 않은지.

### 9-1. (재작업, DEF-001 대응) 신규 인수 조건 — 6단계가 반드시 추가로 확인해야 함

13. `DJANGO_SETTINGS_MODULE=config.settings.production`으로 필수 환경변수(더미 값 포함, R2/DATABASE_URL 포함)를 전부 채운 뒤 `python -c "import django; django.setup(); from django.conf import settings; print(settings.SECURE_PROXY_SSL_HEADER)"`가 `("HTTP_X_FORWARDED_PROTO", "https")`를 출력하는가.
14. 위와 같은 production 설정에서, DB를 거치지 않는 정적자산 경로(`collectstatic` 후 생성된 `/static/css/tokens.<hash>.css` 등)에 `test.Client().get(path, HTTP_HOST=<ALLOWED_HOSTS 중 하나>)`를 **`X-Forwarded-Proto` 헤더 없이** 호출하면 301/302로 정상 리다이렉트되는가(무조건 200이 아니라, "헤더 없을 때는 정상적으로 리다이렉트"가 맞는지 확인 — 회귀 검증).
15. 같은 요청에 `HTTP_X_FORWARDED_PROTO="https"`를 추가하면 **200**을 반환하는가, 그리고 같은 요청을 반복해도 다시 301로 튕기지 않고 200이 유지되는가(무한 루프 해소 확인, DEF-001 재발 방지 회귀 케이스로 자산화).
16. `config/middleware.py`의 `XForwardedForMiddleware`에 `RequestFactory`로 `X-Forwarded-For: 1.2.3.4, 10.0.0.5` 헤더가 있는 요청을 직접 통과시키면 `request.META["REMOTE_ADDR"]`이 rightmost 값인 `10.0.0.5`로 재설정되는가.
17. `python -c "...; from django.conf import settings; print(settings.MIDDLEWARE)"`(production 설정)로 확인했을 때 `config.middleware.XForwardedForMiddleware`가 `MIDDLEWARE` 리스트의 **맨 앞**에 있는가(뒤 단계 미들웨어가 정규화된 `REMOTE_ADDR`을 보도록).
18. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `manage.py check`/`makemigrations --check --dry-run`을 실행했을 때 이번 재작업으로 인한 회귀가 없는가(dev의 `MIDDLEWARE`에는 `XForwardedForMiddleware`가 포함되지 않아야 함 — `base.py` 무변경 확인).

## 10. 다음 단계

**재작업 이전**: 이 노트 작성 완료 후 6단계(`06-unit-tester`) 호출을 트리거했었다.

**재작업 이후(이번 라운드)**: 이번 05단계 코드 수정 완료 후, 규칙F-3(하위 단계 재실행 의무)에 따라 아래 순서로 재트리거해야 한다.
1. 6단계(`06-unit-tester`) — 위 §9-1(13~18번)을 신규 인수 조건으로 포함해 재검증(기존 §9의 1~12번은 이번 변경으로 영향받지 않으므로 회귀만 확인).
2. 7단계(`07-integration-tester`) — `feature-WU-01-integration-test.md`의 IT-02/IT-03을 재실행해 200으로 해소되는지 확정한 뒤 문서를 PASS로 갱신.
3. 8단계(전체 풀테스트)는 위 1~2가 PASS로 완료되기 전까지 시작할 수 없다(규칙 D, 단계 게이트 — `feature-WU-01-integration-test.md` §8 4항과 동일).
