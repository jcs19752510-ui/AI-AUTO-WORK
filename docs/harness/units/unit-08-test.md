# 테스트 결과서 (Test Result Report) — WU-08 (무료 티어 대응: 콜드스타트 UX 회귀 + 사용량 모니터링)

> **재시작 경위**: 이 WU-08의 6단계는 직전 세션에서 API 한도가 아니라 사용자의 명시적 "중지" 지시(TaskStop)로 강제 종료되었다. 종료 시점에 `unit-08-test.md`/`verify-log_unit-08-test.md`는 존재하지 않았고, 중단된 에이전트가 만들었던 임시 venv(`webapp/.venv_edge/`)와 임시 설정 모듈(`webapp/config/settings/it_test_prodlike_wu08_indep2.py`)은 이미 삭제되어 있었다. 즉 이번 6단계는 **완전히 처음부터** 수행한 것이며, 직전 세션의 어떤 부분 결과도 인용하지 않고 `unit-08-note.md` §8의 19개 인수조건(AC)을 전부 이번 세션에서 새로 만든 임시 venv(`webapp/.venv_wu08_verify`, 검증 후 삭제)로 독립 재현했다.

## 1. 개요
- 테스트 대상: WU-08(업무 단위) — REQ-011(콜드스타트 UX, 회귀 확인만)/REQ-012(사용량 모니터링·유료전환 기준). 신규 `webapp/core/middleware.py`(`RequestMetricsMiddleware`), `webapp/core/monitoring.py`(일자별 요청수/응답시간 집계 + `UPGRADE_CRITERIA`), `webapp/core/wagtail_hooks.py`(Wagtail 어드민 라우트/메뉴), `webapp/core/templates/core/usage_dashboard.html`(대시보드 화면). 수정된 `webapp/core/views.py`(`healthz`/`usage_dashboard` 추가), `webapp/core/urls.py`(`/healthz`), `webapp/core/apps.py`(docstring), `webapp/config/settings/base.py`(MIDDLEWARE 추가), `webapp/config/settings/production.py`(`ADMINS`/`MANAGERS`/`EMAIL_*`/`SERVER_EMAIL`), `webapp/render.yaml`(`--workers 1` 고정, `healthCheckPath: /healthz`, 이메일 env 자리).
- 테스트 유형: 단위(Unit)
- 테스트 목적: `docs/harness/units/unit-08-note.md` §8의 인수조건(AC) 19개를 처음부터 독립 재현해 PASS/FAIL을 판정하고, 5단계가 주장한 정적분석 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)가 실제로 근거가 있는지 재확인한다. 아울러 인수조건에 없지만 명백히 위험한 입력(캐시 백엔드 장애, 빈/이상 형식 `DJANGO_ADMIN_EMAIL`, 어드민 사이드바 등록 여부, "access_admin은 있으나 superuser는 아닌" 권한 경계)도 규칙C에 따라 추가 검증한다.
- 관련 산출물: `docs/harness/units/unit-08-note.md`(§8 AC1~19, §1~§7), `docs/harness/03-system-design.md`(v1.2, §4 `/healthz` 계약·§6.3 유료전환 4대 기준/킵얼라이브 미도입·§7.2 알림 채널·§7.4 Runbook), `docs/harness/decisions.md`(DEC-009/DEC-012/DEC-015/DEC-024/DEC-026/DEC-027), `docs/harness/04-ux-design.md`(§2 콜드스타트 UX), `docs/harness/units/unit-04-note.md`(§1.7, footer 카피 구현 근거), `docs/harness/feature-WU-07-integration-test.md`(IT-20, gunicorn 단일 워커 확인 근거), `docs/harness/traceability.md`(REQ-011/REQ-012)
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- 범위 (In-Scope): `unit-08-note.md` §8 AC1~19 전부 독립 재현(dev 환경 8건 + production 유사 환경 8건 + 정리 확인 1건 + 화면/데이터 흐름 3건 — AC 순서상 일부 중복 그룹). 추가로 (a) 정적분석/린트 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)가 실제로 검증 가능한 주장인지 재확인(린트 설정 부재 재확인 + `py_compile` 재실행), (b) `monitoring.record_request()`의 "예외를 상위로 전파하지 않는다"는 §5 주장을 캐시 백엔드 강제 장애 주입으로 직접 재현, (c) `DJANGO_ADMIN_EMAIL` 빈 값/쉼표+공백 혼재/쉼표만 있는 값 등 경계 입력에서 기동이 막히지 않는지, (d) Wagtail 어드민 사이드바에 실제로 메뉴가 등록되는지(§3-2 13번 주장 재검증), (e) "access_admin 권한은 있으나 superuser는 아닌" 사용자 시나리오(§2 편차 4번 주장) 재현.
- 제외 범위 및 사유:
  - **실제 SMTP 서버를 통한 이메일 발송(네트워크)** — `unit-08-note.md` §7-1이 이미 10단계(배포테스트) 대상으로 명시적으로 이월했다. 이번 6단계는 `EMAIL_BACKEND`를 `locmem`으로 일시 교체해(AC15 문언 그대로) Django `AdminEmailHandler`가 실제로 메일 객체를 만들어내는지까지만 검증한다.
  - **Render 실제 배포 환경에서의 `healthCheckPath`/gunicorn 프로세스 기동** — Windows 로컬 제약으로 WU-01~07과 동일 사유. `render.yaml` 문자열 대조(AC17)와 `--workers 1` 전제가 정확히 작동하는지는 `django.test.Client`/설정 로딩 수준까지만 검증했다.
  - **`--workers 1` 고정이 실제 동시 요청 처리량/메모리에 미치는 영향** — `unit-08-note.md` §7-3이 배포 후 실측 필요 항목으로 이월. 로컬에서 gunicorn 멀티워커 자체를 기동할 수 없다(Windows).
  - **브라우저 기반 E2E(Playwright 등)** — DEC-001(MCP 미연동)에 따라 `django.test.Client`로 대체(WU-01~07과 동일 방법론).

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`, WU-01~07과 동일 버전). `webapp/requirements.txt`(Django==5.2.17, wagtail==7.4.3 등, 신규 패키지 없음)를 새 venv(`webapp/.venv_wu08_verify`, 검증 후 삭제)에 clean install. `pip freeze`로 Django==5.2.17/wagtail==7.4.3/psycopg==3.2.10/django-storages==1.14.6/boto3==1.35.36/gunicorn==23.0.0/uvicorn==0.34.0/whitenoise==6.8.2/python-dotenv==1.0.1 전부 요구 버전과 일치 확인(신규 패키지 없음 재확인).
- 테스트 데이터: 픽스처 없는 인메모리/임시 데이터. dev 환경은 `DJANGO_SETTINGS_MODULE=config.settings.dev`, production 유사 환경은 신규 임시 모듈 `webapp/config/settings/it_test_prodlike_wu08_verify.py`(`production.py`를 그대로 상속하고 `DATABASES`만 SQLite로 재정의, WU-01~07과 동일 방법론)를 이번 세션에서 새로 만들어 사용하고 검증 후 삭제했다. 더미 환경변수: `SECRET_KEY`/`DJANGO_ALLOWED_HOSTS=blog-web.onrender.com`/`RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL`/`DATABASE_URL`(SQLite로 재정의되므로 형식만 채움)/`DJANGO_ADMIN_EMAIL=ops@example.com`.
- 전제 조건:
  - dev 환경 `manage.py migrate`가 빈 DB에서 오류 없이 전체 적용됨을 선행 확인.
  - production 유사 환경에서 `manage.py check`/`migrate`/`collectstatic --noinput`이 각각 별도 실행으로 전부 성공함을 선행 확인.
  - AC7/AC10 재현 전 매번 `cache.clear()`로 LocMemCache 상태를 통제했다(WU-08 자체 설계가 DEC-012 LocMemCache 공유를 전제하므로, WU-07 테스트가 쓴 동일 통제 패턴을 그대로 적용).
  - 검증에 사용한 venv(`.venv_wu08_verify`), `db.sqlite3`, `db_wu08_verify_prodlike.sqlite3`, `staticfiles/`, `media/`, 임시 설정 모듈(`config/settings/it_test_prodlike_wu08_verify.py`), 임시 검증 스크립트(스크래치패드에만 위치, 저장소 밖)는 검증 완료 후 전부 삭제했다(§8 근거).

## 4. 테스트 케이스 및 결과

### 4.1 인수조건(AC1~19) 1:1 매핑

| ID | 시나리오 (대응 AC) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | 신규 venv `pip install` (AC1) | 빈 venv(`py -3.12 -m venv .venv_wu08_verify`) | `pip install --upgrade pip` → `pip install -r requirements.txt` | 오류 없이 종료, 신규 패키지 없음 | 오류 없이 종료(무출력=성공). `pip freeze`로 요구 버전 전부 일치 확인, `django-filter`/`django-taggit` 등은 wagtail 종속 패키지로 requirements.txt에 명시된 목록과 별개(WU-01부터 동일) | PASS | |
| TC-002 | 빈 DB `migrate` (AC2) | dev 설정, 빈 SQLite | `DJANGO_SETTINGS_MODULE=config.settings.dev manage.py migrate` | 오류 없이 전체 마이그레이션 적용 | 전체 마이그레이션(`wagtailusers.0015` 등 최종 마이그레이션까지) 오류 없이 적용 완료 | PASS | |
| TC-003 | `manage.py check` (AC3) | TC-002 이후 | `manage.py check` | "System check identified no issues (0 silenced)." | 동일 문자열 그대로 출력 확인 | PASS | |
| TC-004 | `makemigrations --check --dry-run` (AC4) | TC-002 이후 | `manage.py makemigrations --check --dry-run` | "No changes detected" | 동일 문자열 그대로 출력 확인(모델 변경 없음, 신규 마이그레이션 없음) | PASS | |
| TC-005 | `GET /healthz` 계약 (AC5) | dev, `Client()` | `GET /healthz` | 200, `Content-Type` `text/plain`로 시작, 본문 정확히 `ok` | status=200, content_type=`text/plain`, body=`"ok"`(정확히 일치, 앞뒤 공백 없음) | PASS | |
| TC-006 | 콜드스타트 카피 회귀 (AC6) | dev, `Client()` | `GET /` | 응답 본문에 "무료 인프라로 운영 중" 포함 | 포함 확인(WU-04 구현 그대로, WU-08은 코드 미변경) | PASS | REQ-011 회귀 확인 |
| TC-007 | 익명 사용자 대시보드 접근 차단 (AC7) | `cache.clear()`, 익명 `Client()` | `GET /cms-admin/usage/` | 302, `Location`이 `/cms-admin/login/` 포함 | status=302, `Location=/cms-admin/login/?next=/cms-admin/usage/` | PASS | |
| TC-008 | staff이나 access_admin 권한 없는 사용자 (AC8) | `is_staff=True`, `is_superuser=False`, `wagtailadmin.access_admin` 권한 없음, 로그인 성공 | `GET /cms-admin/usage/` | 302(어드민 자체 접근 거부, 로그인 페이지로) | status=302, `Location=/cms-admin/login/?next=/cms-admin/usage/`. `user.has_perm("wagtailcore.access_admin")==False` 사전 확인 | PASS | Wagtail의 `require_admin_access`가 뷰 도달 전에 차단함을 직접 확인(`unit-08-note.md` §2-3/§2-4 주장과 일치) |
| TC-009 | superuser 대시보드 열람 (AC9) | `is_superuser=True`, 로그인 성공 | `GET /cms-admin/usage/` | 200, 본문에 "유료 전환"과 "요청 수" 표 포함 | status=200, `"유료 전환" in body == True`, `"요청 수" in body == True` | PASS | |
| TC-010 | 미들웨어 카운터 정확성 (AC10) | `cache.clear()` | 임의 경로(`/healthz`) 5회 호출 후 `core.monitoring.get_usage_snapshot()` 조회 | `daily[-1]["request_count"] == 5`, `avg_response_ms`가 `None` 아닌 숫자 | `request_count == 5`(정확히 일치), `avg_response_ms == 0.0`(숫자, `None` 아님 — `/healthz`가 매우 빠른 로컬 요청이라 반올림상 0.0, "숫자"라는 조건 자체는 충족) | PASS | §6-비고 참고(값이 0.0인 이유는 결함이 아니라 로컬 타이밍 특성) |
| TC-011 | 대시보드 실시간 반영 (AC11) | TC-010 직후, superuser 로그인 | `GET /cms-admin/usage/` 재요청 | 방금 기록된 요청 수(5)가 화면 표에도 동일 반영 | status=200, `"5" in body == True`(같은 날짜 행의 요청 수 셀에 5 포함, `get_usage_snapshot()` 재호출 결과와 일치) | PASS | 대시보드가 캐시된 스냅샷이 아니라 요청마다 `monitoring.get_usage_snapshot()`을 새로 호출함을 실증 |
| TC-012 | production 유사 설정 기동 3종 (AC12) | 임시 모듈 `it_test_prodlike_wu08_verify.py`(production.py 상속 + DATABASES만 SQLite), 더미 env 전체 | `manage.py check` → `migrate` → `collectstatic --noinput` | 전부 오류 없이 완료 | `check`: "System check identified no issues (0 silenced)." `migrate`: 오류 없이 완료. `collectstatic`: "218 static files copied ... 638 post-processed" — `feature-WU-07-integration-test.md` IT-04와 정확히 동일 수치(신규 정적자산 없음 재확인) | PASS | |
| TC-013 | MIDDLEWARE 순서 (AC13) | TC-012와 동일 설정 로드 | `settings.MIDDLEWARE[:2]` 조회 | `["config.middleware.XForwardedForMiddleware", "core.middleware.RequestMetricsMiddleware"]` | 정확히 동일 리스트(순서 포함 일치) | PASS | |
| TC-014 | ADMINS/EMAIL_BACKEND (AC14) | TC-012와 동일 설정, `DJANGO_ADMIN_EMAIL=ops@example.com` | `settings.ADMINS`, `settings.EMAIL_BACKEND` 조회 | `ADMINS == [("ops@example.com", "ops@example.com")]`, `EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"` | 정확히 일치 | PASS | |
| TC-015 | AdminEmailHandler 실동작 (AC15) | TC-012와 동일 설정, `override_settings(EMAIL_BACKEND="...locmem.EmailBackend")`, `DEBUG=False` 확인 | `logging.getLogger("django.request").error(...)` 직접 호출 | `mail.outbox`에 메일 1건, 수신자 `DJANGO_ADMIN_EMAIL` 값과 일치 | `len(mail.outbox) == 1`, `to == ["ops@example.com"]`, `subject == "[Django] ERROR: WU-08 6단계 검증용 강제 에러"`(제목에 에러 메시지 포함 확인, 한글 인코딩 깨짐 없음을 `PYTHONIOENCODING=utf-8`로 재확인) | PASS | 커스텀 LOGGING dict 없이 Django 기본 설정만으로 동작함을 실측 재확인(§1.2 "과설계 방지" 주장 근거 검증) |
| TC-016 | DEF-001 회귀(신규 라우트) (AC16) | TC-012와 동일 설정 | `GET /healthz`(`X-Forwarded-Proto` 없음, `Host: blog-web.onrender.com`) → `GET /healthz`(`X-Forwarded-Proto: https` 추가) | 첫 요청 301 + `Location`이 `https://`, 둘째 요청 200 + 본문 `ok` | 첫 요청: status=301, `Location=https://blog-web.onrender.com/healthz`. 둘째 요청: status=200, body=`ok` | PASS | DEC-015 회귀 방지가 신규 라우트(`/healthz`)에도 유효함을 확인 |
| TC-017 | `render.yaml` 문자열 대조 (AC17) | 없음 | `render.yaml`에서 `startCommand`/`healthCheckPath` grep | `--workers 1` 포함, `healthCheckPath: /healthz` 존재 | `startCommand: "gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 1"`, `healthCheckPath: /healthz` 둘 다 파일에 정확히 존재 | PASS | |
| TC-018 | 전체 회귀 테스트 (AC18) | dev 설정, 빈 DB | `manage.py test` | 기존 12개(subscribers) 포함 전부 OK | "Ran 12 tests in 0.203s\n\nOK"(WU-08은 신규 자동화 테스트를 추가하지 않았으므로 12개 그대로, `unit-08-note.md` §3-1-7 주장과 일치) | PASS | |
| TC-019 | 검증 산출물 정리 확인 (AC19) | TC-001~018 전부 종료 | `.venv_wu08_verify`/`db.sqlite3`/`db_wu08_verify_prodlike.sqlite3`/`staticfiles/`/`media/`/임시 설정 모듈/`__pycache__` 삭제 후 `git status --porcelain` | 삭제된 항목이 목록에서 사라지고, diff에 소스 코드(신규 4파일 + 수정 6파일)만 남음 | 삭제 후 `git status --porcelain` 결과: 수정 6파일(`decisions.md`/`traceability.md`는 6단계 갱신분, `webapp/config/settings/base.py`/`production.py`/`webapp/core/apps.py`/`urls.py`/`views.py`/`render.yaml`)과 신규 4파일(`webapp/core/middleware.py`/`monitoring.py`/`templates/`/`wagtail_hooks.py`) + WU-07의 기존 미커밋 산출물(무관, 손대지 않음)만 남음. 임시 venv/DB/staticfiles/설정 모듈 흔적 없음 | PASS | §8 "정리" 절 근거 |

### 4.2 위험입력/경계값/게이트 재확인 추가 검증 (규칙C — AC 범위 밖이라도 명백히 위험하면 검증, §4/§5 게이트 재확인 포함)

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| TC-020 | 정적분석 게이트 실재성 재확인 | 저장소 루트/`webapp/` 양쪽에서 `pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml` 존재 여부 확인 | `unit-08-note.md` §4 주장(설정 자체가 없음)과 일치 | 전부 미존재 확인(WU-01~07과 동일 결론) — "있는데 건너뛴 것"이 아니라 "설정 자체가 없다"는 5단계 주장이 사실임을 재확인 | PASS | 5단계 게이트1 주장 검증 |
| TC-021 | `py_compile` 재실행 | 신규/수정 Python 파일 8개(`core/middleware.py`, `core/monitoring.py`, `core/views.py`, `core/urls.py`, `core/wagtail_hooks.py`, `core/apps.py`, `config/settings/base.py`, `config/settings/production.py`)에 `python -m py_compile` | 전부 구문 오류 없음 | 전부 오류 없이 종료(`PY_COMPILE_OK`) | PASS | 5단계 게이트1 대체 수단 재확인 |
| TC-022 | `record_request` 캐시 백엔드 장애 시 예외 미전파(함수 단위) | `core.monitoring.cache`를 `get`/`set` 모두 `RuntimeError`를 던지는 더미 객체로 교체한 뒤 `record_request(12.3)` 직접 호출 | 예외가 호출자로 전파되지 않음(§5 "모니터링은 최선노력" 주장) | 예외 발생 없이 정상 반환(`try/except Exception: pass`가 실제로 동작) | PASS | §5 게이트2 "에러 처리 누락 없음" 주장의 근거를 코드 읽기가 아니라 실제 예외 주입으로 검증 |
| TC-023 | `record_request` 캐시 장애 시 예외 미전파(요청 경로 전체) | 같은 더미 캐시로 교체한 상태에서 `Client().get("/healthz")` 호출(미들웨어 전체 경로) | 요청이 500으로 죽지 않고 정상 응답 | status=200, body=`ok`(미들웨어가 뷰를 감싸는 상태에서도 모니터링 장애가 실제 응답에 영향 없음) | PASS | TC-022보다 상위 계층(미들웨어)에서 재현 — 함수 단위 테스트만으로는 놓칠 수 있는 통합 경로까지 확인 |
| TC-024 | 완전히 빈 캐시에서 스냅샷 안전성 | `cache.clear()` 직후(요청 0건) `get_usage_snapshot()` 호출 | 예외 없이 7일치 버킷 반환, 오늘 `request_count==0`, `avg_response_ms is None`(0으로 나누기 없음) | `len(daily)==7`, 오늘 `request_count==0`, `avg_response_ms is None`, `total_requests==0` | PASS | `avg_ms = round(total_ms / count, 1) if count else None` 분기가 0건일 때 ZeroDivisionError를 실제로 피하는지 실측(코드상 안전해 보여도 실행해 확인) |
| TC-025 | Wagtail 어드민 사이드바 메뉴 등록 실증 | superuser 로그인 후 `GET /cms-admin/` | 사이드바 JSON props(`sidebar_props`)에 라벨 유니코드 이스케이프(`사용량 모니터링` = "사용량 모니터링")와 URL(`/cms-admin/usage/`) 포함 | status=200, 이스케이프 문자열/URL 둘 다 응답 본문에 포함 확인 | PASS | `unit-08-note.md` §3-2 13번 주장을 코드 읽기가 아니라 실제 어드민 홈 응답으로 재현 |
| TC-026 | access_admin은 있으나 superuser는 아닌 사용자 (§2 편차 4번 검증) | `is_staff=True`, `is_superuser=False`, `wagtailadmin.access_admin` 권한만 부여, 로그인 성공 | `GET /cms-admin/usage/` (follow 없음) → `Location` 확인 → follow=True로 재요청해 플래시 메시지 존재 확인 | 302, `Location=/cms-admin/` (로그인 페이지 아님, 어드민 홈), follow 시 권한 관련 플래시 메시지 포함 | status=302, `Location=/cms-admin/`, follow 후 본문에 "권한이 없습니다" 포함 | PASS | `unit-08-note.md` §2 편차 4번("403 아니라 302+플래시")이 실제 동작과 일치함을 독립 재현 — AC8과는 다른 권한 조합(access_admin 있음)이라 커버리지 gap이었던 부분을 보강 |
| TC-027 | `DJANGO_ADMIN_EMAIL` 빈 문자열 | production 유사 설정, `DJANGO_ADMIN_EMAIL=""` | 설정 로드 후 `settings.ADMINS` 확인 | 예외 없이 로드, `ADMINS == []` | 예외 없음, `ADMINS == []` | PASS | §5 게이트2 "입력값 검증" 주장(빈 문자열도 안전하게 빈 리스트로 귀결) 실측 |
| TC-028 | `DJANGO_ADMIN_EMAIL` 공백/빈 항목 혼재 | `DJANGO_ADMIN_EMAIL="  ops@example.com , second@example.com ,,  "` | 설정 로드 후 `settings.ADMINS` 확인 | 공백 제거된 유효 이메일 2건만 남고 빈 항목 무시 | `ADMINS == [("ops@example.com","ops@example.com"), ("second@example.com","second@example.com")]` | PASS | |
| TC-029 | `DJANGO_ADMIN_EMAIL` 쉼표만 있는 값 | `DJANGO_ADMIN_EMAIL=",,,"` | 설정 로드 후 `settings.ADMINS` 확인 | 예외 없이 `ADMINS == []` | 예외 없음, `ADMINS == []` | PASS | |

## 5. 커버리지
- `unit-08-note.md` §8 AC1~19: 19/19 전부 독립 재현(TC-001~019), 커버리지 100%.
- 추가 위험/경계 케이스 10건(TC-020~TC-029) 전부 실행.
- 커버되지 않은 부분과 사유: §2 제외 범위에 명시한 4항목(실제 SMTP 네트워크 발송, Render 실배포 헬스체크, `--workers 1`의 실제 처리량 영향, 브라우저 E2E) — 전부 Windows 로컬/MCP 미연동 제약으로 10단계(배포테스트) 또는 이후 단계 이월 대상이며, `unit-08-note.md` §7이 이미 동일하게 인계 사항으로 명시했다.

## 6. 결함(Defect) 목록
**결함 없음.** AC1~19(TC-001~019) 전부 PASS, 추가 위험/경계 케이스(TC-020~029) 전부 PASS. 근거: 위 §4.1/§4.2 표의 "실제 결과" 컬럼이 전부 코드 읽기가 아닌 실행 결과(HTTP status/body/설정값/예외 발생 여부)를 직접 관측한 것이며, 예상 결과와 일치했다.

- **비고(결함 아님, 관찰 사항)**: TC-010에서 `avg_response_ms`가 `0.0`으로 나온 것은 로컬 `/healthz` 요청이 DB 접근 없이 수 밀리초 이내에 끝나 `round(total_ms/count, 1)`이 0.0으로 반올림된 것이며, AC10의 조건("`None`이 아닌 숫자")을 문자 그대로 충족한다. 결함이 아니다.
- **비고(결함 아님, 문서 정합성 관찰 사항)**: `webapp/core/wagtail_hooks.py`의 모듈 docstring은 "Wagtail 공식 문서: `register_admin_urls`로 추가한 URL에는 로그인/권한 검사가 자동으로 걸리지 않는다"는 문서 인용만 남아 있고, `unit-08-note.md` §2 편차 3번이 실측으로 확인한 "실제로 설치된 wagtail==7.4.3에서는 `decorate_urlpatterns(urlpatterns, require_admin_access)`가 이미 적용되고 있다"는 반증 사실은 코드 docstring에는 반영되지 않았다. TC-008/TC-026이 실제 동작(자동 차단됨)을 재확인했고, `superuser_required`는 방어 계층 중복으로 여전히 유효하므로 기능적 결함은 아니다(안전한 방향의 오차 — 향후 개발자가 이 docstring만 보고 "보호가 필요하다"고 오해해도 실제로 이중 방어가 이미 되어 있어 위험하지 않음). 코드를 임의로 고치지 않고 §7에 관찰 사항으로만 기록한다(오탈자 수준이 아니라 설계 판단에 대한 서술 차이이므로 6단계 테스터가 직접 수정하지 않음).

## 7. 리스크 및 잔존 이슈
- `unit-08-note.md` §7이 이미 명시한 4개 인계 사항(SMTP 실발송 미검증/Render healthCheckPath 실배포 미검증/`--workers 1` 실측 미검증/대시보드 수치가 재시작마다 초기화되는 특성)을 그대로 승계한다 — 전부 10단계(배포테스트) 대상이며 이번 6단계 범위 밖이다.
- `core/wagtail_hooks.py` docstring이 `unit-08-note.md`가 실측으로 확인한 최신 동작(Wagtail이 자동으로 권한 검사를 적용함)을 반영하지 않고 있다(§6 비고). 기능적 위험은 없으나, 7단계 통합테스터 또는 이후 유지보수자가 참고할 수 있도록 인계한다. 6단계 테스터가 임의로 코드/주석을 고치지 않았다(규칙F 원칙 — 판단이 필요한 서술 변경은 원 작성자/5단계 재작업 대상으로 남긴다).
- LocMemCache 기반 카운터는 워커 2개 이상으로 늘어나면 워커별로 값이 갈라진다(DEC-026이 `--workers 1` 고정으로 이 전제를 명시적으로 보호하고 있음, `render.yaml`에서 재확인 완료 — TC-017). 향후 워커 증설 시 공유 저장소(Redis 등) 전환이 선행되어야 한다는 조건이 `unit-08-note.md`/DEC-026에 이미 기록되어 있다.

## 8. 결론 및 판정
- [x] **PASS** — 다음 단계(7단계, 통합테스트) 진행 가능. `unit-08-note.md` §8 AC1~19 전부(TC-001~019) PASS, 추가 위험/경계 케이스(TC-020~029) 전부 PASS, 결함 0건. 5단계가 주장한 정적분석 게이트(§4)와 자체 코드 리뷰 체크리스트(§5)의 핵심 주장(린트 설정 부재, `py_compile` 통과, 예외 미전파, 입력값 안전 처리)을 전부 코드 읽기가 아닌 실행으로 재확인했다.
- 검증에 사용한 `webapp/.venv_wu08_verify`, `webapp/db.sqlite3`, `webapp/db_wu08_verify_prodlike.sqlite3`, `webapp/staticfiles/`, `webapp/media/`, `webapp/config/settings/it_test_prodlike_wu08_verify.py`, `__pycache__`는 전부 삭제했다. `git status --porcelain` 최종 확인 결과 소스 diff(WU-08 신규 4파일 + 수정 6파일, `decisions.md`/`traceability.md` 갱신분)와 WU-07의 기존 미커밋 산출물(이번 WU와 무관, 손대지 않음)만 남아 있음을 확인했다(§4.1 TC-019).

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: AC1~19 커버리지 100% 확인, 예상 결과가 모두 `unit-08-note.md` §8 원문 및 03-system-design.md §4/§6.3/§7.2 명세에 근거함을 재확인. 결함 0건.
- 2차 검증 결과 요약: "이 테스트를 통과했다고 7단계에 넘겨도 되는가"를 의심하며 재검토 — 권한 경계(access_admin 있음/없음 조합, TC-026 보강), 캐시 백엔드 장애(TC-022/023), 스냅샷 0건 상태(TC-024), 관리자 이메일 파싱 경계값(TC-027~029), 사이드바 등록 실측(TC-025) 등 AC에 없던 경계 조건을 추가 발굴해 검증. 전부 PASS, 결함 0건.
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-08-test.md`

---

## 부록 — 재작업 라운드 2 (규칙F, `SiteSettings.contact_email` 신설, 2026-09-25)

- **신규 AC**: `unit-08-note.md` §10 참고 — (1) `makemigrations core`가 정확히 1개 마이그레이션(`0002_initial.py`, `CreateModel SiteSettings`)만 생성하는가, (2) `makemigrations --check --dry-run` → "No changes detected", (3) dev/production 유사 설정 양쪽 `manage.py check` 이상 없음, (4) 전체 회귀 `manage.py test`(기존 38 + legal 신규 4 = 42) OK.
- **실행 결과**: 전부 PASS(`unit-08-note.md` §10 로컬 검증 인용). 신규 결함 0건.
- **회귀 판단**: `contact_email` 기본값이 빈 문자열이라 이 필드가 존재하기 전과 렌더링 결과가 100% 동일함을 `legal.tests.PrivacyPolicyContactEmailTests.test_no_contact_block_when_unset`으로 직접 확인 — 기존 AC1~19를 반복 재실행하지 않고 이 대표 케이스로 회귀 없음을 판정(규칙B 레이어별 책임 분리).
- **판정**: PASS — 다음 단계는 7단계(`feature-WU-08-integration-test.md`) addendum. 8/9단계 재실행 불필요 판단 근거는 `unit-08-note.md` §10 참고.
