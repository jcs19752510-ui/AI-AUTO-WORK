# 테스트 결과서 (Test Result Report) — WU-01 프로젝트 초기 설정

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
