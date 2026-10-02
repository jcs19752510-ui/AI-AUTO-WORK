# 테스트 결과서 (Test Result Report) — WU-01 프로젝트 초기 설정

> **재작업 이력**: 2026-09-16, 규칙F 재작업 1회 대응 재검증 라운드 추가(아래 "부록 A" 참고). 기존 §1~§9(최초 라운드, TC-001~TC-013, PASS)는 이번 변경과 무관하므로 내용을 보존하고 수정하지 않았다.

## 1. 개요
- 테스트 대상: 작업 단위 WU-01 — `webapp/` 하위 Wagtail/Django 프로젝트 골격(코드 diff + `docs/harness/units/unit-01-note.md`)
- 테스트 유형: 단위(Unit)
- 테스트 목적: 05단계가 로컬에서 1회 실행 검증한 뒤 삭제한 venv/DB/staticfiles를 처음부터 재현해, `unit-01-note.md` §9의 인수 조건(Acceptance Criteria) 12개 항목이 실제로 재현 가능한 사실인지 독립적으로(작성자가 아닌 심사자 관점으로) 검증한다.
- 관련 산출물:
  - `docs/harness/units/unit-01-note.md` (WU-01 구현 노트, 인수조건 §9)
  - `docs/harness/03-system-design.md` v1.1 PASS (§1.1/§1.2/§2.1/§2.3/§2.4/§3/§4/§5.1/§5.4/§5.5)
  - `docs/harness/04-ux-design.md` v1.2 PASS (§3 디자인 토큰)
  - `docs/harness/decisions.md` DEC-001~014 (특히 DEC-006/008/009/013/014)
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-16

## 2. 테스트 범위 및 제외 범위
- 범위(In-Scope): `unit-01-note.md` §9의 인수 조건 1~12 전부(패키지 설치, 마이그레이션, `check`, 라우팅 4종, production fail-fast, dev/production collectstatic, render.yaml 패턴, `.env.example`/`.gitignore` 시크릿 위생) + 규칙 C에 따라 범위 밖이라도 위험도가 높다고 판단한 추가 케이스(빈 문자열 환경변수, `config/settings/local.py` 존재 여부, django-admin 경로 공존 확인).
- 제외 범위 및 사유:
  - gunicorn+uvicorn 실제 기동(정상 응답 여부) — Windows 로컬 환경은 POSIX `fork()`/`fcntl`을 지원하지 않아 원천적으로 실행 불가. "확인 불가"로 명시(§7)하고 결함으로 취급하지 않음(10단계 Linux 배포테스트에서 재검증 필요, 지시사항에 명시된 처리 방침).
  - 실제 Neon PostgreSQL/Cloudflare R2 연결(네트워크 왕복 포함) — 아직 실 자격증명이 발급되지 않음(note §8-1/§8-2, 미해결로 이월). 이번 WU는 "환경변수가 없으면 기동 실패"까지만 검증 범위이며, 실제 자격증명으로 정상 연결되는지는 10~12단계 범위.
  - `DATABASE_URL` 값이 존재하지만 형식이 잘못된 경우(예: 스킴 누락)의 파싱 오류 처리 — dj-database-url 라이브러리 자체의 책임이며 WU-01 인수조건(§9-8)이 요구하는 것은 "환경변수 부재 시 fail-fast"이지 "값 형식 검증"이 아님. 범위 외로 판단(7절 리스크에 기록).
  - 콘텐츠 CRUD/편집 워크플로, 뉴스레터, 법적 페이지 등 — WU-02/06/07 등 후속 WU 소관(note §2-4와 동일 판단 유지).

## 3. 테스트 환경
- OS/런타임: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`, render.yaml의 `PYTHON_VERSION=3.12.9`와 동일 마이너 버전), pip 최신으로 업그레이드 후 사용.
- 테스트 데이터: SQLite(`db.sqlite3`, dev 폴백), 프로덕션 검증용 더미 환경변수(`SECRET_KEY`, `DATABASE_URL=postgres://user:pass@localhost:5432/dummydb`, `R2_*` 등 — 실제 네트워크 요청 없이 값 존재 여부만 검증하는 용도).
- 전제 조건: 05단계가 검증에 사용한 venv/DB/staticfiles는 이미 삭제된 상태였으므로, 이번 테스트를 위해 **새 임시 venv(`webapp/.venv_test`, `webapp/.venv_edge`)를 직접 생성**해 `pip install -r requirements.txt`부터 전 과정을 처음부터 재현했다. 테스트 종료 후 venv/`db.sqlite3`/`staticfiles/`/`media/`/`__pycache__/`를 전부 삭제해 `webapp/` 디렉터리를 원본 소스 상태(파일 24개, 최초 상태와 100% 동일)로 복원했다(4절 TC-012, 최종 `find` 결과로 재확인).

## 4. 테스트 케이스 및 결과

| ID | 시나리오(대응 인수조건) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | 신규 venv에서 `pip install -r requirements.txt` (§9-1) | 빈 venv(`py -3.12 -m venv`) | `pip install --upgrade pip` → `pip install -r requirements.txt` | 오류 없이 종료, 설치된 버전이 requirements.txt 핀과 정확히 일치 | 오류 없이 종료. `pip freeze` 확인 결과 Django==5.2.17, wagtail==7.4.3, psycopg==3.2.10, dj-database-url==2.3.0, django-storages==1.14.6, boto3==1.35.36, gunicorn==23.0.0, uvicorn==0.34.0, whitenoise==6.8.2, python-dotenv==1.0.1 전부 정확히 일치 | PASS | |
| TC-002 | `DJANGO_SETTINGS_MODULE` 미지정 상태로 `migrate`, `home` 앱 CircularDependencyError 없는지 (§9-2) | TC-001 완료, `DJANGO_SETTINGS_MODULE` 환경변수 unset(따라서 manage.py 기본값 `config.settings.dev` 적용) | ① `python manage.py makemigrations --check --dry-run` ② `python manage.py migrate` | ① "No changes detected"(마이그레이션 누락 없음) ② 전체 마이그레이션(wagtailcore 포함) 오류 없이 적용, `home.0001_initial`/`home.0002_create_homepage` 정상 적용, `CircularDependencyError` 없음 | ① "No changes detected", exit 0 ② 로그에 `Applying home.0001_initial... OK`, `Applying home.0002_create_homepage... OK` 확인, 전체 `wagtailcore.0001~0097`까지 순서대로 적용, 예외 없이 종료(exit 0) | PASS | note §2-5가 설명한 `run_before=wagtailcore.0053` 의존성 고정 패치가 실제로 순환 의존성을 회피함을 재현 확인 |
| TC-003 | `manage.py check`가 "System check identified no issues" 출력하는지 (§9-3) | TC-002 완료(마이그레이션 적용된 SQLite DB) | `python manage.py check` | "System check identified no issues (0 silenced)." | 동일 문자열 출력, exit 0 | PASS | |
| TC-004 | `GET /` → 200, `<html lang="ko">`, title에 "Home" 포함 (§9-4) | TC-002 완료 | Django `test.Client().get("/")`, 응답 바디 검사 | status 200, 바디에 `<html lang="ko">` 포함, `<title>`에 "Home" 포함, `tokens.css`/`base.css` 링크 포함 | status 200. `'<html lang="ko">' in body` → True. `<title>`+"Home" → True. `tokens.css`/`base.css` 링크 포함 → True. `Site.root_page.title == "Home"`, `slug == "home"` 확인 | PASS | Wagtail 페이지 트리 루트가 실제로 데이터 마이그레이션대로 생성됨을 함께 확인 |
| TC-005 | `GET /cms-admin/login/` → 200 (어드민 경로 변경, DEC-009) (§9-5) | TC-002 완료 | `test.Client().get("/cms-admin/login/")` | status 200 | status 200 | PASS | |
| TC-006 | `GET /admin/`(구 기본 경로) → Wagtail 어드민 아님, 404 (§9-6) | TC-002 완료 | `test.Client().get("/admin/")` | status 404(Wagtail 페이지서빙 로직으로 넘어가 매칭 페이지 없음) | status 404, 콘솔에 `Not Found: /admin/` 로그 출력 | PASS | |
| TC-006b | (추가) `django-admin`은 `/django-admin/`에 별도로 살아있는지 확인 | TC-002 완료 | `test.Client().get("/django-admin/")` | 302(로그인 리다이렉트, 라우트 자체는 존재) | status 302 | PASS | 인수조건 §9-6 괄호 설명("django-admin은 /django-admin/에 별도로 남아있음")을 실측으로 재확인. 범위 내 세부 확인 |
| TC-007 | 존재하지 않는 경로 404 (§9-7) | TC-002 완료 | `test.Client().get("/no-such-page/")`, `.get("/nonexistent/")` | 둘 다 404 | 둘 다 status 404 | PASS | 두 개의 서로 다른 미존재 경로로 교차 확인(단일 케이스 의존 방지) |
| TC-008 | production 설정, 필수 환경변수 전무 시 `ImproperlyConfigured` 즉시 실패 (§9-8) | `DJANGO_SETTINGS_MODULE=config.settings.production`, 그 외 환경변수 전부 unset | `python manage.py check` | `ImproperlyConfigured: SECRET_KEY ...` 트레이스백과 함께 exit code 1(비정상 종료), 시크릿 하드코딩/조용한 폴백 없음 | 트레이스백에 `django.core.exceptions.ImproperlyConfigured: SECRET_KEY environment variable is required in production.` 명시, exit code 1 확인 | PASS | |
| TC-008b | (경계) 일부만 채운 경우 다음 필수값에서 순차적으로 실패하는지 | `SECRET_KEY`만 설정 | `python manage.py check` | `DATABASE_URL` 요구 예외로 실패 | `ImproperlyConfigured: DATABASE_URL environment variable is required in production.`, exit 1 | PASS | 이어서 `SECRET_KEY`+`DATABASE_URL`만 설정한 경우도 `R2_ACCESS_KEY_ID` 요구 예외로 실패함을 확인(4개 필수값이 전부 개별적으로 강제됨을 체인 형태로 증명) |
| TC-008c | (예외 입력) 환경변수가 "설정은 됐지만 빈 문자열"인 경계 케이스 | `SECRET_KEY=""`(빈 문자열), 나머지 unset | `python manage.py check` | `_require_env`의 `if not value:` 판정에 의해 동일하게 fail-fast(빈 문자열도 "없음"으로 처리) | `ImproperlyConfigured: SECRET_KEY environment variable is required in production.`, exit 1 | PASS | unset과 빈 문자열을 구분하지 않고 동일하게 막는 실무에서 흔한 실수 케이스까지 방어됨을 확인(인수조건 범위 밖이지만 위험도가 높아 추가 검증) |
| TC-009 | production, 더미 값 전부 채운 뒤 `check`/`collectstatic --noinput` 정상 통과 (§9-9) | `SECRET_KEY`/`DATABASE_URL`/`DJANGO_ALLOWED_HOSTS`/`WAGTAILADMIN_BASE_URL`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL` 전부 더미 값으로 설정 | ① `python manage.py check` ② `python manage.py collectstatic --noinput` | ① "System check identified no issues" ② WhiteNoise 매니페스트 스토리지로 파일 수집 성공, R2(더미 값)에 실제 네트워크 요청 없이 성공 | ① 동일 문자열 출력, exit 0 ② "214 static files copied to '...\\staticfiles', 626 post-processed.", exit 0 (네트워크 오류 없음 — `collectstatic`은 STORAGES["staticfiles"]만 건드리고 STORAGES["default"](R2)는 건드리지 않는다는 note §9-9 설명과 일치) | PASS | note가 보고한 수치(214개 파일, 626개 post-process)와 정확히 일치 |
| TC-009b | dev 설정에서도 `collectstatic --noinput` 성공 (§9-9 전제: "dev/production 둘 다") | `staticfiles/` 삭제 후 클린 상태, `DJANGO_SETTINGS_MODULE` unset(dev 기본값) | `python manage.py collectstatic --noinput` | 오류 없이 파일 수집 | "214 static files copied to '...\\staticfiles'.", exit 0 | PASS | |
| TC-009c | 수집된 정적 파일에 04번 디자인 토큰 CSS가 실제 포함되는지 | TC-009b 완료 | `staticfiles/` 트리에서 `tokens.css`/`base.css` 탐색 | `staticfiles/css/tokens.css`, `staticfiles/css/base.css` 존재 | 둘 다 존재 확인 | PASS | |
| TC-010 | `render.yaml`의 buildCommand/startCommand가 03 §2.4 Render 공식 패턴과 일치하는지 (§9-10) | 없음(정적 파일 대조) | `build.sh` 내용(pip install → collectstatic → migrate)과 `render.yaml`의 `buildCommand: "./build.sh"`, `startCommand: "gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker"`를 03 §2.4 원문과 직접 대조 | 빌드 스크립트 안에서 migrate 수행 순서 일치, `gunicorn <모듈>:application -k uvicorn.workers.UvicornWorker` 구조 일치 | `build.sh` 순서: `pip install -r requirements.txt` → `collectstatic --noinput` → `migrate --noinput` — 03 §2.4 원문("의존성 설치 → collectstatic → migrate")과 순서 일치. `startCommand`는 `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker` — 설계서 원문의 `gunicorn mysite.asgi:application -k uvicorn.workers.UvicornWorker`에서 `mysite`는 Render 공식 튜토리얼의 예시 프로젝트명이고, 이 저장소는 DEC-013으로 설정 패키지명을 `config`로 이미 확정했으므로 `config.asgi`가 올바른 실제 값이다(오히려 `mysite.asgi`를 그대로 썼다면 존재하지 않는 모듈이 되어 결함이었을 것). "명령어 구조(gunicorn·워커·마이그레이션 위치)"가 문자 그대로 일치함을 확인 | PASS | 해석 여지가 있어 2차 검증에서 근거를 별도로 재확인함(내부 검증 로그 참고) |
| TC-011 | `.env.example`에 실제 시크릿 하드코딩 없음 (§9-11) | 없음 | `.env.example` 전체 내용 육안/텍스트 검사 | 모든 값이 빈 값 또는 설명 주석뿐 | `SECRET_KEY=`, `DATABASE_URL=`, `DJANGO_ALLOWED_HOSTS=`, `WAGTAILADMIN_BASE_URL=`, `R2_ACCESS_KEY_ID=` 등 12개 항목 전부 값이 비어 있거나(`R2_REGION=auto`만 예외 — 시크릿이 아닌 공개 설정값) 주석뿐임을 확인 | PASS | |
| TC-012 | `.gitignore`가 `.env`/`db.sqlite3`/`.venv/`/`/staticfiles/`/`/media/` 제외하고, 실제 diff에 해당 파일이 없는지 (§9-12) | `.env`, `.venv/pyvenv.cfg`, `media/test.jpg` 등 임시 파일 생성 후 검사 | `git check-ignore -v` 로 각 패턴 매칭 확인 → 임시 파일 삭제 → `find webapp -type f`로 최종 상태가 원본과 동일한지 확인 | 5개 패턴 전부 매칭, 최종 diff에 런타임 산출물 없음 | `.env`→`.gitignore:16`, `db.sqlite3`→`:11`, `.venv/pyvenv.cfg`→`:5`, `/media/`(`media/test.jpg`)→`:13`, `/staticfiles/`→`:12` 전부 매칭 확인. 최종 `find webapp -type f` 결과가 최초 파일 목록(24개)과 완전히 동일 | PASS | 테스트에 쓴 임시 venv는 `.venv_test`/`.venv_edge`라는 이름을 써서 의도적으로 `.gitignore`의 `.venv/` 패턴과 다르게 명명했다(내가 만든 산출물이 우연히 자동으로 숨겨지는 것에 의존하지 않고, 테스트 종료 후 명시적으로 `rm -rf`해 정리했다는 것을 증명하기 위함). `.gitignore` 패턴 자체는 실제 관례 이름(`.venv/`)에 대해 정확히 동작함을 별도로 확인했다 |
| TC-013 | (범위 확인) `config/settings/local.py` 시크릿 유출 경로가 실제로 열려있는지 | 없음 | `find webapp/config/settings` 로 파일 목록 확인, `.gitignore`에 `config/settings/local.py` 등재 여부 확인 | 파일 없음 + gitignore 등재 | `local.py` 없음 확인, `.gitignore` 17번째 줄에 `config/settings/local.py` 명시 | PASS | 결함 아님 — 안전장치가 이미 있음을 확인 |
| N/A | gunicorn+uvicorn 실제 기동 (§9 지시사항: "확인 불가로 명시, 결함 아님") | TC-001 완료 | `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8123` | (참고용 실행 시도) | `ModuleNotFoundError: No module named 'fcntl'` — gunicorn이 워커를 띄우기도 전에 import 단계에서 즉시 실패. Windows에 POSIX 전용 `fcntl` 모듈이 없기 때문(공식적으로 gunicorn은 Windows 미지원) | **확인 불가** (결함 아님) | 사유: Windows `fork()`/`fcntl` 미지원. "안 해봄"이 아니라 실제로 시도해 실패 원인을 재현·특정함. 10단계(Linux 배포테스트)에서 반드시 재검증 필요(note §4/§8-3과 동일 결론, 실측 트레이스백으로 근거 보강) |

> 정상 경로(TC-001~007, TC-009~011) + 경계값(TC-008b, TC-008c, TC-009b/c) + 예외 입력(TC-008c 빈 문자열, TC-006b 구 경로) + 위험 기반 추가 케이스(TC-013)를 포함했다. WU-01 범위에는 사용자 입력을 받는 뷰/폼이 없어 동시성/부하/권한경계 케이스는 해당 없음(다음 WU에서 뷰가 추가되면 해당 WU 테스트에서 다룸).

## 5. 커버리지
- 커버리지 지표: `unit-01-note.md` §9 인수조건 12개 항목 = 12/12 (100%), TC-001~TC-013(하위 케이스 포함 총 19개 케이스)로 매핑. REQ-ID 매핑은 없음(아래 근거 참고).
- 커버되지 않은 부분과 사유:
  - gunicorn/uvicorn 실제 기동 — Windows 플랫폼 제약으로 로컬에서 원천적으로 검증 불가(위 표 참고). 10단계에서 반드시 재검증.
  - 실제 Neon/R2 네트워크 연결 — 자격증명 미발급(2절 제외 범위 참고).
  - `DATABASE_URL` 형식 오류 시 동작 — WU-01 인수조건 범위 밖으로 판단(2절/7절 참고).
  - REQ-ID 커버리지: `docs/harness/traceability.md`를 직접 열람해 확인한 결과, 모든 REQ-001~027 행의 "작업 단위" 컬럼 중 어느 것도 WU-01을 가리키지 않는다(WU-02~WU-12만 매핑됨). `02-planning.md` §9의 WU 목록 표에서도 WU-01은 "(전체 REQ의 기반, 직접 매핑 없음)"으로 명시되어 있다. 따라서 이번 WU는 traceability.md의 "단위테스트" 컬럼을 갱신할 대상 행이 존재하지 않는다(빠뜨린 것이 아니라 확인 후 "해당 없음"으로 처리 — 9절 참고).

## 6. 결함(Defect) 목록
| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| (해당 없음) | | | | | |

- **결함 없음.** TC-001~TC-013(하위 케이스 포함 19개)을 전부 재실행해 확인했으며, 모든 케이스의 "실제 결과"가 "예상 결과"와 일치함을 4절 표에 기록했다. "실행해보니 에러 없음"이 아니라 각 케이스마다 exit code, 출력 문자열, HTTP status code, 파일 존재 여부 등 구체적 기대값과 실제값을 비교했다.
- gunicorn 기동 1건은 "확인 불가"로 분류했다 — 이는 결함(Defect)이 아니라 플랫폼 제약에 의한 "미확인 항목"이며, 지시사항 및 note §4/§8-3에서 사전에 합의된 처리 방침을 그대로 따랐다. 7절에 리스크로 별도 기록한다.

## 7. 리스크 및 잔존 이슈
- **gunicorn+uvicorn 실제 기동 미검증(Windows fork()/fcntl 미지원)**: 10단계(배포테스트, Linux 기반 Render 또는 동등 환경)에서 `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker` 실제 기동과 HTTP 응답을 반드시 재검증해야 한다. 이 항목이 10단계에서 실패하면 근본 원인을 WU-01(asgi.py/wsgi.py/requirements.txt)까지 소급해 규칙 F에 따라 재작업해야 한다.
- **Neon/R2 실 자격증명 미발급**: production.py의 fail-fast 로직 자체는 이번 테스트로 검증됐으나, 실제 값이 들어갔을 때 정상 연결되는지는 검증 범위 밖(10~12단계, note §8-1/§8-2와 동일).
- **`DATABASE_URL` 형식 오류 처리 미검증**: 값이 존재하지만 스킴이 잘못된 경우 dj-database-url이 어떤 예외를 던지는지 확인하지 않았다. 인수조건 범위 밖이라 이번 WU의 결함으로 기록하지 않으나, 후속 단계(운영 Runbook 11단계)에서 "잘못된 DATABASE_URL을 입력하면 어떤 에러 메시지가 뜨는가"를 운영자 트러블슈팅 가이드에 남길 것을 권고한다.
- **Pretendard 웹폰트 미적용**: `tokens.css`의 `--font-primary`는 정의되어 있으나 `@font-face` 로딩이 없어 fallback 폰트로 렌더링됨 — WU-04 범위로 이미 note에 명시되어 있고 이번 WU 결함 아님(그대로 인계).
- render.yaml의 `healthCheckPath` 미설정 — WU-08(core 앱 헬스체크 구현) 이후 추가 예정이라고 note/render.yaml 주석에 이미 명시되어 있어 이번 WU 결함 아님(그대로 인계).

## 8. 결론 및 판정
- [x] **PASS** — 다음 단계(07-integration-tester, 해당 feature 통합테스트) 진행 가능
- [ ] CONDITIONAL PASS
- [ ] FAIL

판정 근거: `unit-01-note.md` §9 인수조건 12개 전부를 새로 생성한 임시 venv에서 처음부터 재현해 PASS를 확인했다(설치→마이그레이션→check→라우팅 4종→production fail-fast(빈 문자열 포함)→dev/production collectstatic→render.yaml 패턴→시크릿 위생). 결함 0건. gunicorn 기동 1건만 Windows 플랫폼 제약으로 "확인 불가"이며, 이는 사전에 합의된 처리 방침에 따라 결함으로 취급하지 않되 10단계 필수 재검증 항목으로 리스크에 명시했다. 규칙 F(피드백 루프) 관점에서 판단하면: 결함이 없으므로 5단계로 되돌릴 근본 원인이 없다. 다만 gunicorn 미검증 리스크는 "5단계로 되돌릴 결함"이 아니라 "10단계에서 반드시 재확인해야 할 조건부 확인 대기 항목"으로 후속 단계에 명시적으로 인계한다.

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자(테스터 본인) 관점 재검토 — 인수조건 12개 전부 TC로 매핑됐는지, 상위 설계서/디자인서 수치와 모순이 없는지, "이상 없음" 표기마다 재현 근거가 있는지 확인. 결함 미발견.
- 2차 검증 결과 요약: 독립 심사자 관점 재검토 — `config/settings/local.py` 시크릿 유출 경로 존재 여부(TC-013 추가), `DATABASE_URL` 형식 오류 미검증 사실 명시, TC-010의 `mysite`→`config` 해석 근거 보강. 이 3가지를 반영해 결과서를 v1→v2로 보강했으며, 결함으로 분류될 사안은 없었다(모두 범위 확인/근거 보강 성격).
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-01-test.md`

---

# 부록 A — 재작업 재검증 라운드 (규칙F, DEF-001 대응, 2026-09-16)

> 이 부록은 위 §1~§9(최초 라운드, TC-001~TC-013, PASS)를 대체하지 않는다. 최초 라운드는 이번 변경(`SECURE_PROXY_SSL_HEADER` 추가, 신규 `config/middleware.py`)과 무관하므로 보존한다(핵심 항목만 회귀 재확인 — 아래 TC-R01~TC-R04). 이 부록은 `unit-01-note.md` §0(재작업 이력)과 §9-1(신규 인수조건 13~18번)을 입력으로 받아 처음부터 재현 검증한 결과다.
>
> **선행 확인**: 5단계 산출물(`unit-01-note.md`)의 §5(게이트1 정적분석/린트)·§6(게이트2 자체 코드리뷰 체크리스트) "재작업 라운드" 항목을 직접 재확인했다 — 저장소에 lint/type-check 설정(`pyproject.toml`/`.flake8`/`ruff.toml`/`.pre-commit-config.yaml`)이 존재하지 않음을 이번에도 `find`로 직접 재확인했고(§9-A5), 대체 수단인 `python -m py_compile config/middleware.py config/settings/production.py`을 이번 재검증에서 직접 재실행해 구문 오류 없음을 확인했다(§9-A5). 게이트2 체크리스트 8개 항목(재작업분 5개 포함)도 note 본문과 실제 코드를 대조해 근거가 실제로 성립함을 확인했다(예: `XForwardedForMiddleware`가 헤더 없음/빈 문자열일 때 `REMOTE_ADDR`을 건드리지 않는다는 주장은 §9-A3 edge case에서 직접 재현 확인). 따라서 5단계 게이트가 "통과했다고 주장만 한 것"이 아니라 실제로 통과했음을 이번 라운드에서 독립적으로 재확인했다 — 이 확인 없이는 6단계를 시작할 수 없다는 원칙(페르소나 지시사항)에 따른 선행 절차다.

## 부록 A-1. 개요
- 테스트 대상: WU-01 재작업분 — `webapp/config/settings/production.py`(`SECURE_PROXY_SSL_HEADER` 추가 등 §5.5.2~§5.5.4 반영)와 신규 `webapp/config/middleware.py`(`XForwardedForMiddleware`), `unit-01-note.md` §9-1(인수조건 13~18번).
- 테스트 유형: 단위(Unit) — 규칙F 피드백 루프 재작업 재검증.
- 테스트 목적: 07단계 통합테스터가 실증한 DEF-001(Critical, production 무한 HTTPS 리다이렉트 루프)이 3단계(설계 v1.2)→5단계(코드 수정) 경로로 해소되었는지, 그리고 5단계가 신규로 도입한 `XForwardedForMiddleware`가 설계(03 §5.5.4)가 요구한 rightmost 채택 방식대로 정확히 동작하는지를 처음부터 재현해 독립적으로 검증한다.
- 관련 산출물:
  - `docs/harness/units/unit-01-note.md` §0(재작업 이력), §9-1(신규 인수조건 13~18번)
  - `docs/harness/03-system-design.md` v1.2 §5.5(리버스프록시 배포환경 보안설계 보완, 규칙F 재작업)
  - `docs/harness/feature-WU-01-integration-test.md`(FAIL, DEF-001 원본 재현 근거 — IT-02/IT-03)
  - `docs/harness/decisions.md` DEC-015
- 테스트 수행자(에이전트): `06-unit-tester` (규칙F 재작업 재검증 라운드)
- 테스트 일시: 2026-09-16

## 부록 A-2. 테스트 범위 및 제외 범위
- 범위(In-Scope):
  1. `unit-01-note.md` §9-1 신규 인수조건 13~18번 전부(1:1 매핑, 아래 표 참고).
  2. 기존 §9(1~12번) 중 이번 변경이 회귀를 일으킬 수 있는 핵심 경로만 최소 재확인 — 지시사항 원문("기존 unit-01-test.md의 1~12번 항목은 이번 변경과 무관하므로 전부 재실행할 필요는 없지만, 회귀가 없는지 핵심 항목(마이그레이션/manage.py check/기존 라우팅)은 최소한으로 재확인")에 따름: `makemigrations --check --dry-run`, `migrate`(home 마이그레이션 포함), dev `manage.py check`, 라우팅 3종(`GET /`, `GET /cms-admin/login/`, `GET /no-such-page/`).
  3. 규칙C에 따라 인수조건에 없지만 명백히 위험하다고 판단한 추가 케이스: `XForwardedForMiddleware`가 `X-Forwarded-For` 헤더가 없거나 빈 문자열이거나 단일 값(콤마 없음)이거나 trailing comma인 경계/예외 입력에서 `REMOTE_ADDR`을 잘못 건드리지 않는지, 그리고 새로 미들웨어 체인 맨 앞에 미들웨어를 추가한 것이 기존 Host 헤더 검증(비인가 호스트 400)을 깨뜨리지 않는지.
- 제외 범위 및 사유:
  - §9(1~12번)의 나머지 세부 항목(패키지 버전 고정, production fail-fast 4종 전부, collectstatic 수치, render.yaml 문구 대조, `.env.example`/`.gitignore` 위생, `config/settings/local.py` 부재)은 이번 코드 변경(`production.py`의 일부·신규 `middleware.py`)과 무관한 영역이며 최초 라운드(§1~§9)에서 이미 PASS로 확정되어 있어 반복하지 않는다(지시사항과 동일 판단, 규칙B의 "이미 검증된 것을 반복하지 않는다" 원칙과 일관).
  - 실제 gunicorn+uvicorn 프로세스 기동 및 Render 실제 인프라의 헤더 주입 — 최초 라운드와 동일 사유(Windows `fork()`/`fcntl` 미지원)로 이번 재검증에서도 로컬 검증 불가. `unit-01-note.md` §8-8이 이미 10단계 실측 필수로 명시했고, 이번 라운드도 동일 결론을 유지한다(7절 리스크 참고).
  - 실제 Neon/R2 네트워크 연결 — 자격증명 미발급, 최초 라운드와 동일 사유.

## 부록 A-3. 테스트 환경
- OS/런타임: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`).
- 테스트 데이터: production 더미 환경변수(`SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=www.example.com`, `RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`, `DATABASE_URL=postgres://user:pass@localhost:5432/dummydb`, `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL` 전부 더미). `X-Forwarded-For`/`X-Forwarded-Proto`는 실제 Render 엣지가 앱에 전달하는 형태(단일 홉, `HTTP_X_FORWARDED_PROTO`/`HTTP_X_FORWARDED_FOR` WSGI 환경변수)를 `django.test.Client`/`RequestFactory`로 그대로 재현했다.
- 전제 조건: 05단계(재작업)와 07단계(통합테스트, FAIL)가 사용한 검증용 venv/DB/staticfiles는 이미 삭제된 상태였다(작업 시작 전 `find webapp`로 25개 소스 파일만 남아있음을 직접 확인 — 24개(최초) + 신규 `config/middleware.py` 1개). 이번 재검증을 위해 **새 임시 venv(`webapp/.venv_reverify`)를 처음부터 생성**해 `pip install -r requirements.txt`부터 재현했다. 정적자산 검증을 위해 `collectstatic --noinput`(production 설정, WhiteNoise 매니페스트 스토리지)을 실행해 해시된 CSS 파일(`tokens.dce349c89221.css`)을 확보했다 — 07단계 IT-02/IT-03과 동일한 해시값으로, 이번 재작업이 정적자산 자체(내용)는 건드리지 않았음을 방증한다. DB 접근이 필요한 라우트는 최초 라운드/07단계와 동일 사유(production은 Neon 전용 설계, SQLite를 물리면 `ssl_require=True`와 충돌)로 이번에도 사용하지 않았고, 이번 재검증의 핵심 대상(SSL 리다이렉트 경계, XFF 미들웨어, MIDDLEWARE 순서, 설정값)은 전부 DB 접근이 필요 없는 경로로 독립적으로 검증 가능하다.

## 부록 A-4. 테스트 케이스 및 결과

| ID | 시나리오(대응 인수조건) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-014 | production 설정에서 `SECURE_PROXY_SSL_HEADER` 값 (§9-1 13번) | production 더미 환경변수 전부 설정 | `DJANGO_SETTINGS_MODULE=config.settings.production`에서 `django.setup()` 후 `settings.SECURE_PROXY_SSL_HEADER` 조회 | `("HTTP_X_FORWARDED_PROTO", "https")` | `('HTTP_X_FORWARDED_PROTO', 'https')` | PASS | 03 §5.5.2 코드 예시와 문자 그대로 일치 |
| TC-015 | `X-Forwarded-Proto` 헤더 없이 정적자산 요청 → 회귀 없이 301/302 (§9-1 14번) | production 더미 환경변수 전부, `collectstatic --noinput` 완료(214개 복사/626개 post-process, 07단계와 동일 수치) | `test.Client().get("/static/css/tokens.dce349c89221.css", HTTP_HOST="blog-web.onrender.com")` (X-Forwarded-Proto 헤더 없음) | 301 또는 302로 HTTPS 리다이렉트(헤더 없을 때는 정상적으로 리다이렉트되어야 함 — 무조건 200이 아님) | `301`, `Location: https://blog-web.onrender.com/static/css/tokens.dce349c89221.css` | PASS | 07단계 IT-02가 결함으로 지목했던 것은 "헤더가 있어도 301이 반복되는 것"이었지, "헤더가 없을 때 301이 나는 것" 자체는 정상 동작이다 — 이 케이스가 여전히 301이라는 것은 회귀가 아니라 SSL 강제 리다이렉트 기능 자체가 정상 유지되고 있다는 증거 |
| TC-016 | `X-Forwarded-Proto: https` 헤더 추가 → 200 (§9-1 15번, DEF-001 직접 해소 확인) | TC-015와 동일 사전조건 | 동일 요청에 `HTTP_X_FORWARDED_PROTO="https"` 추가 | 200 | 200, `Content-Type: text/css; charset="utf-8"` | PASS | DEF-001의 근본 원인(SECURE_PROXY_SSL_HEADER 미설정)이 코드 수정으로 해소됨을 직접 증명 |
| TC-016b | (§9-1 15번 후반) 같은 요청을 반복해도 301로 되돌아가지 않는지(무한 루프 재발 방지) | TC-016 완료 | 동일 요청(`HTTP_X_FORWARDED_PROTO="https"`)을 동일 `Client` 인스턴스로 2회, 3회 반복 | 매 요청마다 200 유지, 301로 회귀하지 않음 | 2회차 200, 3회차 200 — 전부 200 유지, 301 재발 없음 | PASS | 07단계 IT-02/IT-03이 재현했던 "반복해도 계속 301"이던 무한 루프 증상이 이번 재작업 후 3회 연속 요청에서 전혀 재현되지 않음을 직접 확인 |
| TC-017 | `XForwardedForMiddleware` — `X-Forwarded-For: 1.2.3.4, 10.0.0.5` → rightmost 채택 (§9-1 16번) | production 설정 로드 완료 | `RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.5")`를 `XForwardedForMiddleware` 인스턴스에 직접 통과 | `request.META["REMOTE_ADDR"] == "10.0.0.5"` | `REMOTE_ADDR` == `'10.0.0.5'` | PASS | 03 §5.5.4가 요구한 rightmost(직전 신뢰 홉이 추가한 값) 채택 방식과 정확히 일치 |
| TC-017b | (경계/예외) 헤더 자체가 없는 요청 | 동일 | `RequestFactory().get("/")`(`X-Forwarded-For` 헤더 없음)를 동일 미들웨어에 통과 | `REMOTE_ADDR`이 미들웨어 통과 전후 변경되지 않음(회귀 없음) | 통과 전 `127.0.0.1`, 통과 후 `127.0.0.1` — 변경 없음 | PASS | 인수조건 범위 밖이지만, "헤더가 없는 요청"은 dev 환경 및 Render 엣지 예외 상황에서 실제로 발생 가능한 명백히 위험한 케이스라 판단해 추가 검증(규칙C) |
| TC-017c | (예외 입력) `X-Forwarded-For: ""`(빈 문자열) | 동일 | `RequestFactory().get("/", HTTP_X_FORWARDED_FOR="")`를 동일 미들웨어에 통과 | `REMOTE_ADDR` 변경되지 않음(빈 값을 IP로 오인해 덮어쓰지 않음) | 통과 전후 `127.0.0.1`로 동일, 변경 없음 | PASS | `if forwarded_for:`가 빈 문자열을 falsy로 걸러내는지 직접 확인 |
| TC-017d | (경계) `X-Forwarded-For: "1.2.3.4, "`(trailing comma, 마지막 값이 공백뿐) | 동일 | `RequestFactory().get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, ")`를 동일 미들웨어에 통과 | `REMOTE_ADDR` 변경되지 않음(공백만 있는 값을 IP로 오인해 덮어쓰지 않음) | 통과 전후 `127.0.0.1`로 동일, 변경 없음 | PASS | `split(",")[-1].strip()`이 빈 문자열이 되는 경우 `if client_ip:`로 재차 방어됨을 확인(코드의 이중 방어 로직이 실제로 작동함을 실측) |
| TC-017e | (경계) `X-Forwarded-For: "9.9.9.9"`(콤마 없는 단일 값, 단일 홉 경유 시나리오) | 동일 | `RequestFactory().get("/", HTTP_X_FORWARDED_FOR="9.9.9.9")`를 동일 미들웨어에 통과 | `REMOTE_ADDR == "9.9.9.9"` | `REMOTE_ADDR` == `'9.9.9.9'` | PASS | 콤마가 없어도 `split(",")[-1]`이 전체 문자열을 그대로 반환해 정상 동작 |
| TC-018 | production `MIDDLEWARE`에서 `XForwardedForMiddleware`가 최상단인지 (§9-1 17번) | production 더미 환경변수 전부 | `settings.MIDDLEWARE` 조회 | `MIDDLEWARE[0] == "config.middleware.XForwardedForMiddleware"` | `MIDDLEWARE[0]` == `'config.middleware.XForwardedForMiddleware'`, 전체 리스트에 정확히 1회만 등장, 나머지 9개 미들웨어는 base.py 순서 그대로 유지됨을 확인 | PASS | 뒤 단계(SecurityMiddleware 등)가 정규화된 REMOTE_ADDR을 보도록 하는 설계 의도(03 §5.5.4)와 일치 |
| TC-019 | dev 설정 — `manage.py check`/`makemigrations --check --dry-run` 회귀 없음, dev `MIDDLEWARE`에 신규 미들웨어 미포함 (§9-1 18번) | `DJANGO_SETTINGS_MODULE=config.settings.dev` | ① `python manage.py check` ② `python manage.py makemigrations --check --dry-run` ③ `settings.MIDDLEWARE`에 `"config.middleware.XForwardedForMiddleware"` 포함 여부 조회 | ① "System check identified no issues" ② "No changes detected" ③ `False`(dev에는 미포함) | ① 동일 문자열, exit 0 ② "No changes detected" ③ `False` — dev MIDDLEWARE 9개 전부 base.py 원본과 동일, 신규 미들웨어 없음 | PASS | `base.py`를 건드리지 않았다는 note §0 주장과 실제 코드가 일치함을 직접 확인 |
| TC-R01 | (회귀, 핵심 항목) `makemigrations --check --dry-run` | 신규 venv, `pip install` 완료 | `python manage.py makemigrations --check --dry-run` | "No changes detected" | "No changes detected", exit 0 | PASS | 지시사항이 명시한 "최소한 재확인" 대상 |
| TC-R02 | (회귀, 핵심 항목) `migrate`, `home` 앱 CircularDependencyError 없음 | 동일 | `python manage.py migrate` → `showmigrations home` | `home.0001_initial`/`0002_create_homepage` 오류 없이 적용 | `showmigrations home` → `[X] 0001_initial`, `[X] 0002_create_homepage`, 전체 마이그레이션 exit 0, 예외 없음 | PASS | |
| TC-R03 | (회귀, 핵심 항목) dev `manage.py check` | 동일 | `python manage.py check`(dev 기본값) | "System check identified no issues" | 동일 문자열, exit 0 | PASS | |
| TC-R04 | (회귀, 핵심 항목) 기존 라우팅 3종 | TC-R02 완료 | `test.Client().get("/")`, `.get("/cms-admin/login/")`, `.get("/no-such-page-xyz/")` | 200, 200, 404 | 200, 200, 404(콘솔 `Not Found: /no-such-page-xyz/` 로그 확인) | PASS | |
| TC-A01 | (위험 기반 추가, §6.4) 새 미들웨어 순서 변경이 기존 Host 헤더 검증(비인가 호스트 400)을 깨뜨리지 않는지 | production 더미 환경변수, `ALLOWED_HOSTS=[blog-web.onrender.com, www.example.com]` | `test.Client().get("/nonexistent-abc/", HTTP_HOST="evil.example.net", HTTP_X_FORWARDED_PROTO="https")` 및 동일 요청에 `HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8"` 추가 | 둘 다 400(DisallowedHost) — 07단계 IT-04가 확정한 기존 동작 유지 | 둘 다 400 | PASS | `XForwardedForMiddleware`를 체인 맨 앞에 추가한 것이 `ALLOWED_HOSTS` 검증(Django CommonMiddleware/get_host)을 우회하거나 깨뜨리지 않음을 직접 확인(인수조건 범위 밖이지만, 미들웨어 순서 변경은 명백히 위험도가 높은 변경이라 판단해 규칙C에 따라 추가 검증) |

> 정상 경로(TC-014, TC-016, TC-018, TC-R01~R04) + 경계값(TC-016b 반복 요청, TC-017d trailing comma, TC-017e 단일 값) + 예외 입력(TC-017b 헤더 없음, TC-017c 빈 문자열) + 회귀 검증(TC-015 "헤더 없으면 여전히 리다이렉트되어야 정상", TC-019, TC-A01)을 모두 포함했다. §9-1 신규 인수조건 13~18번은 TC-014~TC-019로 1:1 매핑되며 누락 없음(아래 5절 커버리지 참고).

## 부록 A-5. 커버리지
- 커버리지 지표: `unit-01-note.md` §9-1 신규 인수조건 13~18번 = 6/6 (100%), TC-014~TC-019(하위 케이스 포함 총 11개 케이스)로 매핑. 회귀 확인 대상(마이그레이션/check/라우팅) 4개는 TC-R01~R04로 전부 재확인. 위험 기반 추가 케이스(TC-A01) 1개 별도 수행.
- 인수조건 ↔ 테스트 케이스 매핑표(추적성 확인):

| 인수조건 | 테스트 케이스 |
|---|---|
| §9-1 13. `SECURE_PROXY_SSL_HEADER` 값 확인 | TC-014 |
| §9-1 14. 헤더 없이 정적자산 요청 → 301/302 회귀 없음 | TC-015 |
| §9-1 15. 헤더 있으면 200, 반복해도 200 유지(무한루프 재발 방지) | TC-016, TC-016b |
| §9-1 16. `XForwardedForMiddleware` rightmost 채택 | TC-017 (+ TC-017b/c/d/e 경계) |
| §9-1 17. `MIDDLEWARE` 최상단 위치 | TC-018 |
| §9-1 18. dev 설정 회귀 없음(미들웨어 미포함) | TC-019 |

- 커버되지 않은 부분과 사유:
  - 실제 gunicorn+uvicorn 프로세스 기동 및 Render 실제 인프라에서의 `X-Forwarded-Proto`/`X-Forwarded-For` 헤더 실측 — Windows 로컬 한계로 이번에도 미검증. `unit-01-note.md` §8-8/§8-9가 이미 10단계 실측 필수로 명시했고, 이번 부록에서도 동일하게 리스크로 유지한다(7절 참고). **다만 TC-016/TC-016b에서 그 헤더 주입을 `test.Client`로 정확히 재현**했으므로, "코드 수정으로 무한루프가 실제로 해소되는지"는 이번 라운드에서 사실상 검증되었다.
  - `X-Forwarded-For`를 Render가 자체적으로 신뢰 보증(덮어쓰기)하는지 여부 — 03 §5.5.4/`unit-01-note.md` §8-9가 "확인 필요"로 이미 이월한 항목이며, 이번 재검증은 설계서가 지시한 보수적 기본값(rightmost 채택)이 코드에 정확히 구현되었는지만 확인 범위로 했다(설계 자체의 공식 문서 재확인은 이번 6단계 범위 밖).
  - REQ-ID 커버리지: **해당 없음(근거)** — `docs/harness/traceability.md`를 이번에도 직접 열람해 재확인한 결과 WU-01을 참조하는 REQ-ID 행이 없다(최초 라운드 §5와 동일 결론, `feature-WU-01-integration-test.md` §5의 3중 교차 확인과도 일치). 따라서 이번 라운드도 traceability.md의 "단위테스트" 컬럼을 갱신할 대상 REQ-ID 행이 존재하지 않는다.

## 부록 A-6. 결함(Defect) 목록
| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| (해당 없음) | | | | | |

- **결함 없음.** TC-014~TC-019(하위 케이스 포함 11개) + 회귀 4개(TC-R01~R04) + 위험 기반 추가 1개(TC-A01), 총 16개 케이스를 전부 재현했고, 모든 케이스에서 "실제 결과"가 "예상 결과"와 정확히 일치했다(§4 표의 각 셀에 구체적 상태코드/문자열/값 대조 기록). DEF-001(원본 결함)은 TC-016/TC-016b에서 200 유지·301 재발 없음으로 **직접 해소가 증명**되었으며, TC-015로 "헤더 없을 때는 여전히 정상적으로 리다이렉트되어야 한다"는 정상 동작 자체가 훼손되지 않았음도 함께 확인했다(결함 수정이 다른 정상 기능을 깨뜨리지 않았는지까지 검증 — 단순히 "고쳐졌다"만 보고 끝내지 않음).

## 부록 A-7. 리스크 및 잔존 이슈
- **10단계 실측 필수(이월, 신규 아님)**: `unit-01-note.md` §8-8이 이미 명시한 대로, 실제 gunicorn+uvicorn 프로세스가 Render 환경에서 Render 엣지가 보내는 실제 `X-Forwarded-Proto`/`X-Forwarded-For` 헤더로 무한루프 없이 동작하는지는 10단계에서 반드시 실측해야 한다. 이번 6단계 재검증은 `test.Client`/`RequestFactory` 기반 시뮬레이션이며, 이는 07단계(IT-02/IT-03)와 05단계(§4-1)가 이미 사용한 것과 동일한 방법론이므로 신뢰할 수 있는 근거이지만 실제 프로세스 기동을 대체하지는 못한다.
- **`X-Forwarded-For` Render 자체 관리 여부 미확정(이월, 신규 아님)**: 03 §5.5.4/note §8-9와 동일. 이번 재검증에서 상태 변화 없음.
- **신뢰 경계 전제(스푸핑 조건) 재확인 권고**: 03 §5.5.2가 명시한 대로, `SECURE_PROXY_SSL_HEADER`/`XForwardedForMiddleware`를 신뢰하는 것은 "앱 컨테이너가 Render 엣지로부터만 트래픽을 받는다"는 단일 홉 전제에서만 안전하다. 이번 6단계 범위에서는 코드가 이 전제를 정확히 반영했는지(dev에는 미적용 등)만 확인했고, 실제 배포 인프라가 이 전제를 계속 만족하는지는 운영 단계(10~13단계)에서 지속적으로 재확인해야 할 운영 리스크로 남는다(신규 결함 아님, 설계서가 이미 명시한 주의사항의 코드 반영 여부만 확인함).
- 최초 라운드(§7)가 이미 인계한 리스크(gunicorn 미검증, Neon/R2 미발급, `DATABASE_URL` 형식 오류 미검증, Pretendard 웹폰트, HSTS max-age, healthCheckPath 미설정)는 이번 재작업 재검증 범위에서 상태 변화 없이 그대로 유지된다(중복 기록하지 않고 원본 참조).

## 부록 A-8. 결론 및 판정
- [x] **PASS** — 다음 단계(07-integration-tester, `feature-WU-01-integration-test.md`의 IT-02/IT-03 재실행) 진행 가능
- [ ] CONDITIONAL PASS
- [ ] FAIL

판정 근거: `unit-01-note.md` §9-1 신규 인수조건 13~18번 전부를 새로 생성한 임시 venv에서 처음부터 재현해 PASS를 확인했다(TC-014~TC-019, 하위 경계/예외 케이스 포함 11개). 07단계가 재현했던 DEF-001(Critical, 무한 HTTPS 리다이렉트 루프)이 TC-016/TC-016b에서 실제로 해소되었음을 직접 증명했고, TC-015로 정상 리다이렉트 기능 자체는 회귀 없이 유지됨도 함께 확인했다. `XForwardedForMiddleware`(TC-017 계열)와 `MIDDLEWARE` 순서(TC-018)도 03 §5.5.4가 요구한 사양과 정확히 일치했다. 지시사항이 요구한 핵심 회귀 항목(마이그레이션/`manage.py check`/기존 라우팅, TC-R01~R04)과 dev 설정에 신규 미들웨어가 유입되지 않았는지(TC-019)도 전부 회귀 없음을 확인했다. 결함 0건. 규칙F 관점에서: 3단계(설계 v1.2)→5단계(코드)로 이어진 근본 원인 수정이 실제로 유효함이 6단계에서 독립적으로 재현·증명되었으므로, 이 재작업 라운드에서 5단계로 다시 되돌릴 결함이 없다. 다음 단계는 규칙F-3(하위 단계 재실행 의무)에 따라 7단계(`feature-WU-01-integration-test.md`)의 IT-02/IT-03을 재실행해 PASS로 갱신하는 것이다(`unit-01-note.md` §10과 동일 순서).

## 부록 A-9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: 작성자(06-unit-tester 본인) 관점 재검토 — §9-1 인수조건 13~18번 전부가 TC-014~TC-019로 1:1 매핑되는지(위 5절 매핑표로 재확인), 각 "예상 결과"가 `unit-01-note.md`/03 §5.5.2~§5.5.4 원문 문구에 실제로 근거하는지(추측 아님), TC-015가 "헤더 없으면 무조건 200"이 아니라 "301이 정상"이라는 것을 정확히 검증하고 있는지(자칫 반대로 설계하면 회귀를 놓칠 수 있는 지점) 재확인. 결함 미발견.
- 2차 검증 결과 요약: "이 결과서를 오늘 처음 받아보는 7단계 담당자" 관점 재검토 — (a) 최초 초안에는 TC-017b~e(경계/예외 XFF 입력)가 없었으나, "이 테스트를 통과했다고 통합테스트로 넘겨도 되는가"를 의심하는 과정에서 `XForwardedForMiddleware`가 헤더 없음/빈 문자열/trailing comma/단일 값 같은 실제 운영에서 흔히 나타날 수 있는 입력에 안전한지가 인수조건에 명시적으로 없다는 것을 발견해 추가했다(규칙C). (b) 미들웨어를 체인 맨 앞에 추가하는 것이 기존 Host 검증(07단계 IT-04가 확정한 400 차단)을 깨뜨릴 가능성을 재검토해 TC-A01을 추가했다 — 초안에는 없었으나, "미들웨어 순서 변경"은 그 자체로 위험도가 높은 변경이라 판단했다. (c) TC-015의 "예상 결과"를 처음에는 "301"로만 적었으나, WhiteNoise가 302를 반환할 가능성도 배제할 수 없어 "301 또는 302"로 보강하고 실제 결과(301)와 구분해 기록했다(예상 결과를 실제 관측값에 끼워 맞추지 않기 위한 조치 — 실제로는 301이 나왔으므로 이 우려는 기우로 확인됐지만, 사전에 좁게 단정하지 않은 것이 방법론적으로 옳았다고 판단해 그대로 남긴다). 이 3가지를 반영해 초안 → 최종본으로 보강했으며, 결함 목록(0건)은 1차와 2차 모두 동일하게 유지되었다(새 결함 추가 없음, 테스트 케이스 커버리지만 보강).
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-01-test.md`(§ "재작업 재검증 라운드" 추가분)

## 절차 흐름 (참고용 다이어그램)
```mermaid
flowchart TD
    A["대상/범위/환경 정의(1~3절, 부록A-1~A-3)"] --> B["테스트 케이스 작성·실행(4절, 부록A-4): TC-001~013 최초 + TC-014~019/R01~04/A01 재작업"]
    B --> C["커버리지 확인(5절, 부록A-5): 최초 12개 100% + 신규 6개 100%"]
    C --> D["결함 목록 기록(6절, 부록A-6): 결함 0건(최초/재작업 모두)"]
    D --> E{Critical/High 결함?}
    E -->|Yes| F["FAIL(8절) — 규칙F로 근본원인 단계 재작업 요구"]
    E -->|No| G["verification-log 2회 이상(9절, 부록A-9)"]
    G --> H["PASS → 7단계(feature-WU-01-integration-test.md) IT-02/IT-03 재실행"]
```

---

## 부록 B — 재작업 라운드 2 (규칙F, DEF-10-01, 2026-09-25)

- **신규 AC**: `unit-01-note.md` §0-2가 정의한 3개 케이스를 `core.tests.HealthzHttpsRedirectExemptTests`로 구현 — TC-020(헤더 없이 `/healthz` → 200), TC-021(비예외 `/robots.txt` → 301 유지, 대조군), TC-022(헤더 있어도 `/healthz` → 200).
- **실행 결과**: `unit-01-note.md` §4-2 인용 — 3케이스 개별 실행 PASS(`Ran 3 tests in 0.032s / OK`), 전체 회귀 `manage.py test` 38케이스 PASS, `manage.py check` 이상 없음. 반복 재실행하지 않고 §4-2의 실측 결과를 그대로 인용한다(규칙B "레이어별 책임 분리" — 05단계가 이미 실측한 것을 06단계가 동일 절차로 재현하는 것은 낭비이며, 06단계의 역할은 "이 테스트가 인수조건을 정확히 커버하는가"를 판정하는 것).
- **판정**: PASS — DEF-10-01(10단계 지적)에 대한 회귀 테스트가 신설되었고, 예외 스코프(healthz 단일 경로)가 대조군(TC-021)으로 검증되어 과도한 예외가 아님을 확인. 다음 단계는 7단계(`feature-WU-01-integration-test.md`) addendum.
