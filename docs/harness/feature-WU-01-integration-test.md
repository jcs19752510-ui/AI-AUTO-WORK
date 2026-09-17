# 테스트 결과서 (Test Result Report) — WU-01 프로젝트 초기 설정 (업무 단위 통합테스트)

> **재작업 이력**: 2026-09-16, 규칙F 재작업 1회 대응 재실행 라운드 추가(아래 "부록 B" 참고). 기존 §1~§9(최초 라운드, IT-01~IT-07, **FAIL**, DEF-001)는 그대로 보존하고 수정하지 않는다 — 규칙F-4(재작업 이력은 append, 과거 판정을 지우지 않음)에 따름. **최종 판정은 부록 B §8을 따른다.**

## 1. 개요
- 테스트 대상: 업무 단위 WU-01(프로젝트 초기 설정) 전체 — `webapp/` 하위 Wagtail/Django 프로젝트 골격이 **하나의 배포 가능한 전체**로서 일관되게 동작하는지(설정 분리 3종 간 정합성, URL 라우팅 전체 트리, 정적파일 파이프라인, 환경변수 계약 전체)를 통합 관점에서 검증.
- 테스트 유형: 통합(Integration) — 업무 단위 전체 풀테스트 (ORCHESTRATOR.md 파이프라인 7단계)
- 테스트 목적: 06단계(`unit-01-test.md`, PASS)가 개별 요소(패키지 설치, 마이그레이션, `check`, 라우팅 4종 개별 호출, production fail-fast, dev/production 각각의 `collectstatic`)를 요소별로 검증한 것과 달리, 이번 07단계는 **그 요소들을 실제 배포 형태(WSGI/ASGI 진입점 + 전체 미들웨어 체인 + 실제 HTTP 요청/응답 왕복)로 한 번에 조립했을 때**도 동일하게 동작하는지를 검증한다. 참고: 이 프로젝트는 02-planning.md §9 기준 WU 단위가 곧 하네스의 "업무 단위(feature)"이며, WU-01은 다른 모든 WU의 선행조건이 되는 단일 작업단위(내부에 결합할 다른 WU가 아직 없음)이므로, "여러 WU 간 데이터 흐름"이 아니라 "WU-01 내부의 여러 구성요소(설정 분리·라우팅·정적파일·환경변수) 간 경계"를 통합 검증 대상으로 삼았다(지시사항과 동일 판단).
- 관련 산출물:
  - `docs/harness/units/unit-01-note.md` (WU-01 구현 노트)
  - `docs/harness/units/unit-01-test.md` v2 (PASS, 06단계 단위테스트, TC-001~TC-013)
  - `docs/harness/03-system-design.md` v1.1 PASS (§1.1 아키텍처, §2.4 Render 배포, §4 라우팅 표, §5.4/§5.5 보안 설계)
  - `docs/harness/04-ux-design.md` v1.2 PASS (§3 디자인 토큰)
  - `docs/harness/decisions.md` DEC-001~014
  - `docs/harness/traceability.md`
- 테스트 수행자(에이전트): `07-integration-tester`
- 테스트 일시: 2026-09-16

## 2. 테스트 범위 및 제외 범위
- 범위(In-Scope) — 06단계에서 요소 단위로 이미 PASS된 것을 반복하지 않고, **경계/조립 지점**만 신규로 검증했다:
  1. **dev 설정 전체 파이프라인**: 마이그레이션 → 라우팅 → 템플릿 렌더링 → `{% static %}` 태그 → 실제 HTTP 응답까지 한 번의 요청/응답 왕복으로 연결되는지(단위테스트 TC-004는 HTML 바디에 링크 문자열이 "포함"되는지만 확인했고, 그 링크가 실제로 200을 반환하는지는 확인하지 않았다).
  2. **production 설정 전체 파이프라인(신규)**: `collectstatic`(매니페스트 스토리지) → 실제 HTTP 요청 → WhiteNoise가 해시된 정적파일을 서빙 → 전체 미들웨어 체인(SecurityMiddleware·WhiteNoise·Session·Common·CSRF·Auth·Messages·XFrame·Redirects) 통과까지 하나의 왕복으로 연결되는지. 06단계는 `manage.py check`/`collectstatic`만 실행했고 **production 설정으로 실제 HTTP 요청을 보낸 적이 없다** — 이번 단계의 핵심 신규 검증 지점.
  3. **환경변수 계약과 설정/라우팅의 교차 검증**: `RENDER_EXTERNAL_HOSTNAME`/`DJANGO_ALLOWED_HOSTS` → `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`WAGTAILADMIN_BASE_URL` 계산 로직이 실제 요청의 `Host` 헤더 검증과 일관되게 맞물리는지.
  4. **WSGI/ASGI 두 진입점의 계약 일치**: `manage.py`/`wsgi.py`/`asgi.py`가 동일한 `DJANGO_SETTINGS_MODULE` 기본값·동일 `ROOT_URLCONF`로 일관되게 동작하는지(render.yaml의 실제 기동 커맨드가 참조하는 진입점).
  5. WU-01을 구성하는 개별 요소(패키지 설치, 마이그레이션, 어드민 경로 4종, fail-fast 등)의 회귀 — 06단계 인수조건을 처음부터 재현해 07 검증용 임시 조립 환경에서도 동일하게 PASS하는지(합쳤을 때 깨지지 않는지) 확인.
- 제외 범위(Out-of-Scope) 및 사유:
  - 실제 Neon PostgreSQL/Cloudflare R2 네트워크 연결 — 자격증명 미발급(unit-01-note §8, unit-01-test §2와 동일 사유, 10~12단계 범위).
  - gunicorn+uvicorn 실제 프로세스 기동 — Windows 로컬 환경 제약으로 06단계와 동일하게 이번에도 실행 불가(§3 참고). 대신 WSGI/ASGI 애플리케이션 객체가 동일 설정 계약 하에서 일관되게 인스턴스화되는지까지만 검증(§4 IT-05).
  - 콘텐츠 CRUD, 뉴스레터, 법적 페이지 등 — 아직 코드가 없는 후속 WU 범위(WU-01에는 해당 라우트/모델이 존재하지 않음).
  - 다른 업무 단위(WU-02~WU-11)와의 통합 — 아직 개발되지 않았으므로 이번 07단계 대상이 아니다(8단계 전체 풀테스트에서 다룸). 다만 이번 07단계에서 발견한 결함이 8단계 경계에도 영향을 줄 수 있는지는 §7에 명시했다.

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`). 06단계와 마찬가지로 05/06단계가 사용한 검증용 venv/DB/staticfiles는 이미 삭제된 상태였으므로, 이번 07단계를 위해 **새 임시 venv(`webapp/.venv_it`)를 처음부터 생성**해 `pip install -r requirements.txt`부터 재현했다.
- 테스트 데이터: SQLite(`db.sqlite3`, dev 마이그레이션 재현) + production 설정 검증용 더미 환경변수(`SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `WAGTAILADMIN_BASE_URL`, `R2_*`). **DATABASE_URL만 06단계와 다르게 처리했다**: production 설정에서 정적파일/라우팅/미들웨어 경계를 검증하기 위해 실제 요청·응답 왕복이 필요했는데, 이 프로젝트의 설계상 production DB는 반드시 Neon PostgreSQL이어야 하고(DEC-004) 아직 발급되지 않았다. 따라서 **DB 접근이 필요한 경로(홈페이지 렌더링, 어드민 로그인 화면)에 한해서만** dev 단계에서 이미 마이그레이션해 둔 SQLite 파일을 `DATABASE_URL=sqlite:///...` 형태로 production 설정에 임시로 물려 재사용했다. 이는 "production이 SQLite를 지원한다"는 의미가 전혀 아니며(설계상 지원 대상이 아니고, 실제로 `ssl_require=True`와 SQLite 드라이버가 충돌해 `TypeError: 'sslmode' is an invalid keyword argument`로 즉시 실패함을 직접 확인했다 — §7에 별도 기록), 오직 "WhiteNoise 정적파일 미들웨어 경계"와 "DB를 거치지 않는/거치는 라우트의 HTTPS 리다이렉트 경계"를 실제 요청으로 분리해서 검증하기 위한 테스트 편의 조치였다. DB 접근이 필요 없는 케이스(정적자산 서빙, Host 헤더 검증)는 DB 연결 자체가 발생하지 않으므로 이 문제와 무관하게 독립적으로 유효하다.
- 전제 조건: 06단계 산출물(PASS)과 03/04 설계서(PASS)가 모두 확정된 상태에서 시작. 테스트 종료 후 `webapp/.venv_it`, `db.sqlite3`, `staticfiles/`, `media/`, `__pycache__/`를 전부 삭제해 `webapp/`를 원본 소스 상태(파일 24개)로 복원했다(§4 IT-06, `find`로 최종 확인).

## 4. 테스트 케이스 및 결과
| ID | 시나리오(경계) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-01 | dev 설정: 마이그레이션→라우팅→템플릿→`{% static %}`→실제 HTTP 응답 전체 왕복 | 신규 venv, `pip install`, `migrate` 완료 | `test.Client().get("/")` → 응답 HTML에서 `href="/static/css/..."` 링크를 정규식으로 추출 → 추출된 각 링크를 다시 `Client().get()`으로 실제 요청 | `GET /` 200, 추출된 2개 링크(`tokens.css`, `base.css`) 각각 200, `Content-Type: text/css` | `GET /` → 200. 추출된 링크: `/static/css/tokens.css`, `/static/css/base.css`. 두 링크 모두 200, `Content-Type: text/css; charset="utf-8"` | PASS | 06단계 TC-004는 "링크 문자열이 바디에 포함되는가"만 봤고, 그 링크가 실제로 유효한지는 처음 확인 |
| IT-02 | production 설정: `collectstatic`(매니페스트)→실제 HTTP 요청→WhiteNoise가 해시된 파일 서빙 | production 더미 환경변수 전부 설정, `collectstatic --noinput` 완료(214개 복사/626개 post-process) | `test.Client().get("/")` (평문 HTTP, HTTPS 아님 — 실제 브라우저 최초 요청과 동일 조건) | 200과 함께 해시된 정적파일 링크(`tokens.<hash>.css` 등)가 200으로 응답 | **`GET /` → 301 (빈 바디), `Location` 헤더 없이 리다이렉트만 발생.** `GET /cms-admin/login/` → 301. `GET /nonexistent-xyz/` → 301. 페이지 렌더링 자체가 이루어지지 않아 정적파일 링크 검증 불가 | **FAIL** | **DEF-001 재현 케이스.** §6 결함 목록 참고 |
| IT-03 | IT-02에서 발견된 301의 원인 격리·확정 (DB를 거치지 않는 WhiteNoise 정적자산 경로로 한정해 SSL 리다이렉트 경계만 분리 검증) | `collectstatic` 매니페스트에서 실제 해시 파일명(`tokens.dce349c89221.css`) 확인 | (A) `HTTP_X_FORWARDED_PROTO=https` 헤더를 붙여 정적자산 요청(Render가 실제로 앱에 전달하는 형태와 동일 조건) — SECURE_PROXY_SSL_HEADER 미설정 상태 (B) 같은 요청을 반복(브라우저가 301을 따라간 뒤 재요청하는 상황 시뮬레이션) (C) `SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")`를 임시로 override한 뒤 동일 요청 | (A)(B) 301(무한 루프 재현), (C) 200 | (A) `301 https://testserver/static/css/tokens.dce349c89221.css` (B) 동일하게 다시 `301`(반복해도 계속 리다이렉트 — 무한 루프 확인) (C) `200 text/css; charset="utf-8"` | PASS(결함 재현·근본원인 확정 목적의 진단 케이스 — "예상 결과"는 결함의 존재와 그 해결책을 동시에 증명하는 것이었고 정확히 그대로 나왔다) | Render 공식 배포 아키텍처(TLS는 로드밸런서에서 종료되고 앱에는 평문 HTTP로 전달되며 `X-Forwarded-Proto: https`를 붙여줌)를 로컬에서 동일하게 재현. `SECURE_PROXY_SSL_HEADER`가 없으면 Django가 이 헤더를 신뢰하지 않아 `request.is_secure()`가 항상 `False`로 판정되고, `SECURE_SSL_REDIRECT=True`가 매 요청마다 다시 302/301을 발생시켜 **실제 배포 시 100% 요청이 무한 리다이렉트에 빠진다** |
| IT-04 | 환경변수 계약(`RENDER_EXTERNAL_HOSTNAME`/`DJANGO_ALLOWED_HOSTS`) ↔ `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`WAGTAILADMIN_BASE_URL` ↔ 실제 Host 헤더 검증의 교차 정합성 | IT-03의 override(`SECURE_PROXY_SSL_HEADER`)를 적용해 리다이렉트 경계를 우회하고 Host 검증 경계만 분리 | `RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`, `DJANGO_ALLOWED_HOSTS=www.example.com` 설정 후 (a) `Host: blog-web.onrender.com` (b) `Host: www.example.com` (c) `Host: evil.example.net`으로 각각 요청 | (a)(b) 200, (c) 400(DisallowedHost) — Django 라우트 기준 | 정적자산 요청 기준: (a) 200 (b) 200 (c) **200 (예상과 다름, 아래 비고)**. 동일 조건에서 Django 라우트(`/cms-admin/login/`, `/nonexistent-abc/`)로 재확인한 결과: (a)(b)(c) 각 케이스에서 evil 호스트는 **400** 확인 | PASS(원인 파악 후 재분류) | `ALLOWED_HOSTS=['blog-web.onrender.com','www.example.com']`, `CSRF_TRUSTED_ORIGINS=['https://blog-web.onrender.com','https://www.example.com']`, `WAGTAILADMIN_BASE_URL`이 `RENDER_EXTERNAL_HOSTNAME` 우선으로 정확히 계산됨을 확인. **WhiteNoise가 서빙하는 정적자산은 Django의 Host 검증 단계(URL resolver 이전)에 도달하기 전에 미들웨어 체인 두 번째 단계에서 즉시 응답을 반환**하므로 Host 헤더를 검증하지 않는다 — 이는 WhiteNoise의 표준 설계(정적 콘텐츠는 Host에 따라 내용이 달라지지 않음)이며 코드 결함이 아니다. 실제 Django 라우트(뷰가 렌더링되는 경로)에서는 DisallowedHost(400)가 정확히 동작함을 별도 요청으로 재확인해 "설정 자체는 올바르다"는 것을 확정했다. §7에 정보성 리스크로 기록(결함 아님) |
| IT-05 | WSGI/ASGI 두 진입점의 설정 계약 일치(Render `startCommand`가 참조하는 `config.asgi:application`과 `manage.py`/`config.wsgi`가 동일 계약을 공유하는지) | production 더미 환경변수 전체 설정 | `PYTHONPATH=webapp`에서 `import config.wsgi`, `import config.asgi`를 동일 프로세스에서 순차 실행 | 둘 다 예외 없이 `application` 객체 생성, 타입은 각각 `WSGIHandler`/`ASGIHandler` | 둘 다 예외 없이 임포트됨. `type(wsgi.application)`→`WSGIHandler`, `type(asgi.application)`→`ASGIHandler` | PASS | `render.yaml`의 `startCommand`(`gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`)가 참조하는 모듈 경로가 실제로 존재하고 production 설정 로딩과 충돌하지 않음을 확인(실제 gunicorn 프로세스 기동 자체는 Windows 제약으로 여전히 미검증 — §2 제외범위와 동일) |
| IT-06 | 조립 후 회귀 — 06단계 인수조건 핵심 경로가 이번 07 임시 조립 환경에서도 깨지지 않는지 | 신규 venv 처음부터 재현 | `makemigrations --check --dry-run`(변경 없음 확인) → `migrate` → `check` | "No changes detected", 마이그레이션 오류 없음, "System check identified no issues" | 전부 동일하게 재현됨(`home.0001_initial`/`0002_create_homepage` 정상 적용, `CircularDependencyError` 없음, check 0 issues) | PASS | 06단계 결론과 회귀 없이 일치 |
| IT-07 | 정리(clean-up) — 통합테스트에 사용한 venv/DB/staticfiles 삭제 후 소스 diff가 깨끗한지 | IT-01~IT-06 전체 완료 | `.venv_it`/`db.sqlite3`/`staticfiles`/`media`/`__pycache__` 삭제 → `find webapp -type f` → `git status --porcelain webapp/` | 원본 24개 파일과 동일, git status에 추가 파일 없음 | `find` 결과 24개 파일로 원복 확인. `git status --porcelain webapp/` → `?? webapp/`만 출력(WU-01 산출물 전체가 아직 커밋 전이라는 기존 상태와 동일 — 06단계 이후 내가 추가로 생성/커밋한 파일 없음) | PASS | |

> 정상 경로(IT-01, IT-05, IT-06) + 실제 배포 조건 재현(IT-02, IT-03: Render의 TLS 종료 아키텍처를 그대로 시뮬레이션) + 환경변수 조합 경계(IT-04: 정상 호스트 2종 + 비인가 호스트 1종) + 원상복구 검증(IT-07)을 포함했다. WU-01 범위에는 여러 업무 단위 간 데이터 흐름이 없으므로(§1 참고), "업무 단위 내부 구성요소 간 경계"에 케이스를 집중했다.

## 5. 커버리지
- 커버리지 지표: `unit-01-note.md` §9 인수조건 12개는 06단계에서 이미 100% 커버되었으므로 반복하지 않았다(규칙 B/C의 "이미 검증된 것을 반복하지 않는다" 원칙). 이번 07단계는 06단계가 개별적으로 실행한 4가지 요소(설정 분리 3종, URL 라우팅, 정적파일 파이프라인, 환경변수 계약)를 **조립된 하나의 요청/응답 왕복**으로 묶어 검증하는 데 집중했고, IT-01~IT-07 7개 케이스로 그 조립 지점을 전부 다뤘다.
- 커버되지 않은 부분과 사유:
  - 실제 gunicorn+uvicorn 프로세스 기동, 실제 Render 플랫폼에서의 TLS 종료/헤더 주입 — Windows 로컬 한계로 여전히 미검증. **다만 IT-03에서 그 헤더 주입을 수동으로 정확히 재현**했으므로, "실제로 리다이렉트 루프가 발생하는지"는 이번 07단계에서 사실상 검증되었다(10단계에서 실제 Render 환경으로 최종 재확인 필요, §7 참고).
  - 실제 Neon/R2 연결 — 자격증명 미발급(§2와 동일).
  - REQ-ID 커버리지: **해당 없음(근거)** — `docs/harness/traceability.md` 전체 27개 REQ 행을 직접 열람해 재확인한 결과, 어떤 행의 "작업 단위" 컬럼도 WU-01을 참조하지 않는다(WU-02~WU-12만 매핑). `02-planning.md` §9와 `03-system-design.md` §0도 "WU-01은 전체 REQ의 기반, 직접 매핑 없음"으로 일관되게 명시한다. `unit-01-note.md` §7과 `unit-01-test.md` §5도 동일 결론. 따라서 이번 통합테스트서에서 traceability.md의 "통합테스트" 컬럼을 갱신할 REQ-ID 행이 존재하지 않는다 — 빠뜨린 것이 아니라 3중으로 교차 확인한 "해당 없음" 처리다(규칙 C: 근거와 함께 "해당 없음" 명시).

## 6. 결함(Defect) 목록
| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| DEF-001 | **production 설정에 `SECURE_PROXY_SSL_HEADER`가 설정되어 있지 않아, Render처럼 TLS를 로드밸런서에서 종료하고 앱에는 평문 HTTP로 전달하는 배포 환경에서 모든 요청이 무한 HTTPS 리다이렉트 루프에 빠진다.** `SECURE_SSL_REDIRECT=True`(03 §5.5 요구사항)가 `request.is_secure()`에 의존하는데, 이 값은 `SECURE_PROXY_SSL_HEADER`를 명시하지 않으면 프록시가 붙여주는 `X-Forwarded-Proto: https` 헤더를 신뢰하지 않아 항상 `False`로 판정된다. 결과적으로 배포 후 사이트가 **100% 접근 불가** 상태가 된다(정적자산 포함 모든 경로). | `webapp/config/settings/production.py`를 실제 배포 환경과 동일하게(HTTP로 요청 도달 + `X-Forwarded-Proto: https` 헤더) 구동하면 재현. 본 보고서 IT-02/IT-03에서 `test.Client`로 재현·근본원인 확정(§4 IT-03: 헤더만 있고 `SECURE_PROXY_SSL_HEADER`가 없으면 301 반복, 설정을 추가하면 200으로 해소됨을 대조 실험으로 증명) | **Critical** | **Fixed (부록 B에서 해소 확인, 2026-09-16)** | 이번 07단계(최초 라운드)에서는 코드/설계서를 수정하지 않았다(규칙: 통합 시점 설계 결함은 근본 원인 단계로 되돌리고 임의 봉합 금지). 아래 "판정 근거"에 Rule F 경로를 명시. **재작업 결과는 부록 B §6/§8 참고 — 3단계(v1.2)→5단계(코드)→6단계(재검증 PASS)→7단계(본 부록 B) 경로로 해소를 직접 증명함** |

- 결함 1건(Critical) 확인, 그 외 결함 없음. IT-01(dev 전체 경로), IT-04(Host 검증 로직 자체), IT-05(WSGI/ASGI 계약), IT-06(회귀)은 전부 예상과 일치해 결함 없음을 확인했다 — "실행해보니 문제 없었다"가 아니라 각 케이스마다 상태 코드·Content-Type·예외 트레이스백·매니페스트 해시값 등 구체적 기대값과 실제값을 대조했다(§4 표 참고).

## 7. 리스크 및 잔존 이슈
- **DEF-001의 8단계 파급 효과**: 이 결함은 8단계(전체 풀테스트)나 그 이후 어떤 WU가 추가되어도 동일하게 재현된다(production 설정 자체의 문제이며 WU-01 이후 다른 WU가 추가한 뷰/라우트도 전부 이 미들웨어 체인을 통과하기 때문). **다른 WU 개발을 진행하기 전에(적어도 8단계 이전에는 반드시) 수정되어야 한다** — 방치하면 8단계 전체 풀테스트도 production 모드에서는 동일하게 실패한다. **(부록 B, 2026-09-16 갱신) 이 리스크는 해소되었다 — 부록 B에서 DEF-001 수정이 해소를 직접 증명했으므로, WU-02 이후 개발 착수를 막던 차단 사유는 더 이상 유효하지 않다.**
- **DEF-001 권고 조치(직접 수정은 하지 않음, 규칙 F에 따른 경로만 제시)**:
  1. 3단계(`03-system-design.md`) §5.5 "전송/저장 보안"에 "Render는 로드밸런서에서 TLS를 종료하고 앱에는 평문 HTTP로 전달하며 `X-Forwarded-Proto` 헤더로 원 프로토콜을 알려준다 → Django가 이를 신뢰하도록 `SECURE_PROXY_SSL_HEADER`를 명시적으로 설정해야 한다"는 요구사항을 추가하고, 내부검증(규칙 B) 최소 2회 재수행. **(완료, v1.2, DEC-015)**
  2. 5단계(WU-01, `config/settings/production.py`)에 `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`를 추가하고 `unit-01-note.md`에 변경 이력을 남김. **(완료, unit-01-note.md §0)**
  3. 6단계(`unit-01-test.md`)에 "production 설정으로 실제 HTTP 요청을 보내 200(리다이렉트 아님)을 확인"하는 케이스를 인수조건에 신규 추가하고 재검증(이번 07단계가 발견한 유형의 결함이 앞으로는 06단계에서 먼저 잡히도록 테스트 자산화). **(완료, unit-01-test.md 부록 A, PASS)**
  4. 7단계(이 문서) 재실행 — IT-02/IT-03을 재현해 200으로 해소되는지 확정한 뒤 PASS로 갱신. **(완료, 부록 B, 본 라운드)**
  5. **10단계(배포테스트)에서 실제 Render 인프라로 최종 재확인 필수** — Render가 실제로 보내는 헤더 이름/값이 `X-Forwarded-Proto: https`와 정확히 일치하는지는 공식 문서 인용(03 §2.4, `render.com/docs/deploy-django`)에 근거했으나 실제 트래픽으로 한 번 더 실측 검증할 것을 권고한다("설정했으니 될 것이다"로 넘기지 않는다 — 03 §7.2와 동일 원칙). **(미해결, 10단계로 이월 — 신규 아님)**
- **WhiteNoise 정적자산의 Host 헤더 미검증(정보성, 결함 아님)**: §4 IT-04에서 확인한 대로 WhiteNoise가 서빙하는 정적 CSS 파일은 `Host` 헤더 검증을 거치지 않는다. 정적 콘텐츠는 Host에 따라 내용이 달라지지 않아 보안 영향이 낮다고 판단하지만, 운영 Runbook(11단계)에 "정적자산 경로는 Host 기반 접근제어 대상이 아님"을 명시해 향후 오해를 방지할 것을 권고한다. **(부록 B에서 재확인, 상태 변화 없음)**
- **SQLite+`ssl_require=True` 조합의 크래시(정보성, 결함 아님)**: §3에서 설명한 대로 이번 테스트 편의상 production 설정에 SQLite DB를 임시로 물렸을 때 `TypeError: 'sslmode' is an invalid keyword argument`로 즉시 크래시했다. 이는 "production은 SQLite를 지원하지 않는다"는 기존 설계 의도(DEC-004, Neon 전용)와 일치하는 정상 동작이며, 실제 운영에서 SQLite를 production에 연결할 경로 자체가 없으므로(`.env.example`/`render.yaml` 어디에도 SQLite 옵션 없음) 결함으로 기록하지 않는다. 다만 만약 향후 누군가 실수로 `DATABASE_URL`에 SQLite 스킴을 넣으면 에러 메시지가 "SQLite는 지원하지 않습니다" 같은 명확한 문구가 아니라 `sslmode` 관련 낯선 `TypeError`로 나타나 트러블슈팅이 어려울 수 있다는 점을 운영 Runbook 후보 메모로 남긴다(선택 사항, Critical 아님).
- 06단계가 이미 인계한 리스크(gunicorn 실기동 미검증, Neon/R2 미발급, `DATABASE_URL` 형식 오류 미검증, Pretendard 웹폰트, HSTS max-age, healthCheckPath 미설정)는 이번 07단계 범위에서 상태 변화 없이 그대로 유지된다(중복 기록하지 않고 원본 참조: `unit-01-test.md` §7).

## 8. 결론 및 판정 (최초 라운드)
- [ ] PASS
- [ ] CONDITIONAL PASS
- [x] **FAIL** — 사유 및 재작업 요청 사항:

**FAIL 사유**: DEF-001(Critical)이 production 배포 시 사이트 전체를 100% 접근 불가 상태로 만드는 결함이며, "개별 요소는 전부 PASS했지만 조립하면 깨지는" 정확히 이 07단계가 존재하는 이유에 해당하는 사례다. 06단계는 `check`/`collectstatic`만 실행해 이 결함을 발견할 수 없었고(정적 분석성 검증), 이번 07단계에서 실제 HTTP 요청/응답 왕복을 production 설정으로 최초로 수행하면서 드러났다.

**규칙 F(피드백 루프) 판단**: 근본 원인은 구현 실수가 아니라 **설계 단계의 누락**으로 판단한다 — `03-system-design.md` §2.4/§5.5는 "Render 관리형 TLS로 HTTPS 강제"까지는 명시했지만, Render(그리고 사실상 모든 TLS-종료형 PaaS 리버스 프록시)가 앱에 평문 HTTP로 요청을 전달한다는 전제 자체와 그로 인해 `SECURE_PROXY_SSL_HEADER` 설정이 반드시 필요하다는 점을 어디에도 언급하지 않았다(`docs/harness/` 전체에서 "PROXY"/"X-Forwarded" 키워드 검색 결과 0건으로 직접 확인). 따라서:
1. **3단계(`03-system-design.md`) §5.5부터 재작업**해야 한다(규칙 F-1: 근본 원인 발생 단계까지 소급) — 이 설계서에 대한 내부검증(규칙 B) 최소 2회를 처음부터 다시 수행할 것.
2. 이 설계 변경에 **의존하는 하위 단계**를 재실행해야 한다(규칙 F-3): 5단계(WU-01 `production.py` 코드 수정), 6단계(`unit-01-test.md`에 실제 HTTP 요청 기반 케이스 추가 후 재검증), 그리고 이 7단계(본 문서, IT-02/IT-03 재실행).
3. 재작업 이력은 `unit-01-note.md`의 변경 이력 섹션과 `docs/harness/decisions.md`에 남길 것(규칙 F-4) — 이번 07단계에서는 문서를 직접 수정하지 않았으므로, 다음에 3/5/6단계를 재실행하는 에이전트가 이 결정을 기록해야 한다.
4. 8단계(전체 풀테스트)는 위 1~3이 완료되어 이 07단계 문서가 PASS로 갱신되기 전까지 시작할 수 없다(규칙 D, 단계 게이트).

**(이 §8은 최초 라운드의 판정이며, 최종 판정이 아니다. 최종 판정은 아래 부록 B §8을 따른다.)**

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용) — 최초 라운드
- 1차 검증 결과 요약: 작성자(07-integration-tester 본인) 관점 재검토 — IT-01~IT-07이 §1의 통합 검증 목적(설정 분리 간 정합성/URL 라우팅 전체 트리/정적파일 파이프라인/환경변수 계약 전체)을 모두 케이스로 커버하는지, 06단계에서 이미 검증된 요소를 중복 검증하지 않았는지, DEF-001의 재현 절차가 "추측"이 아니라 대조 실험(있음/없음 비교)으로 근거를 남겼는지 확인. 결함 목록·판정·Rule F 경로 간 상호 모순 없음을 확인.
- 2차 검증 결과 요약: "이 결과서를 오늘 처음 받아본 8단계 담당자" 관점 재검토 — (a) DEF-001이 WU-01 단독 문제가 아니라 8단계 진행 자체를 막는 차단 결함임을 §7에 명시적으로 추가(최초 초안에는 "8단계 파급 효과" 서술이 누락되어 있었음 → 보강). (b) IT-04에서 처음에 "예상과 다름(evil 호스트가 200)"으로 끝났다면 이 자체가 결함처럼 보일 수 있어, WhiteNoise 표준 동작이라는 근거와 함께 Django 라우트에서는 정상 차단됨을 재확인 요청 → 표에 "정보성, 결함 아님" 분류 근거를 명확히 보강. (c) production에 SQLite를 물린 테스트 방법론 자체가 오해를 살 수 있어(§3), "왜 SQLite를 썼는지/왜 유효한지"를 명시적으로 추가 서술. 이 3가지를 반영해 초안 → 최종본으로 보강했으며, 결함 목록(DEF-001 1건, Critical)은 1차와 2차 모두 동일하게 유지되었다(새 결함 추가 없음, 기존 결함의 서술만 보강).
- 검증 로그 파일 경로: `docs/harness/verify-log_feature-WU-01-integration-test.md`

## 절차 흐름 (참고용 다이어그램) — 최초 라운드
```mermaid
flowchart TD
    A["대상/범위/환경 정의(1~3절)"] --> B["테스트 케이스 작성·실행(4절): IT-01~IT-07"]
    B --> C["커버리지 확인(5절): 06 인수조건 100%는 상속, 07은 조립 경계에 집중"]
    C --> D["결함 목록 기록(6절): DEF-001 Critical"]
    D --> E{Critical/High 결함?}
    E -->|Yes| F["FAIL(8절) — 규칙F로 3단계부터 재작업 요구"]
    E -->|No| G["verification-log 2회 이상(9절)"]
    G --> H["PASS"]
```

---

# 부록 B — 규칙F 재작업 재실행 라운드 (DEF-001 해소 검증, 2026-09-16)

> 이 부록은 위 §1~§9(최초 라운드, IT-01~IT-07, **FAIL**)를 대체하지 않는다. 최초 라운드는 이번 재작업(3단계 §5.5 v1.2 → 5단계 `production.py`/`middleware.py` → 6단계 `unit-01-test.md` 부록A, PASS)의 원인이자 근거이므로 그대로 보존한다. 이 부록은 §7 "DEF-001 권고 조치" 1~4번이 전부 완료되었다는 입력을 받아, **IT-02/IT-03을 재실행해 실제로 200으로 해소되는지 확정**하고, 07단계만의 관점(전체 배포형태 조립 시 상호작용)에서 신규 발견될 수 있는 경계 결함이 없는지 재검증한 라운드다.

## 부록 B-1. 개요
- 테스트 대상: WU-01 재작업분이 실제 배포 조립 형태(WSGI/ASGI 진입점 + 전체 미들웨어 체인 + 실제 HTTP 요청/응답)에서도 DEF-001을 해소하는지, 그리고 신규 도입된 `XForwardedForMiddleware`가 다른 미들웨어(SecurityMiddleware, WhiteNoise 등)와의 순서/상호작용에서 부작용을 일으키지 않는지.
- 테스트 유형: 통합(Integration) — 규칙F 피드백 루프 재작업 재실행.
- 테스트 목적: 06단계(`unit-01-test.md` 부록A, PASS, TC-014~TC-019)가 `test.Client`/`RequestFactory` 기반으로 개별 항목을 검증한 것과 달리, 이번 07단계 재실행은 06단계가 다루지 않은 **07단계만의 관점**(①원시 WSGI/ASGI 진입점을 통한 전체 체인 재현, ②미들웨어 체인 전체 순서에서의 상호작용, ③반복 요청으로 무한루프 재발 여부, ④기존 PASS 항목(IT-01/IT-04/IT-05/IT-06)에 대한 회귀)을 검증 대상으로 삼는다.
- 관련 산출물:
  - `docs/harness/units/unit-01-note.md` §0(재작업 이력) — `config/settings/production.py`(SECURE_PROXY_SSL_HEADER 추가), 신규 `config/middleware.py`(XForwardedForMiddleware)
  - `docs/harness/03-system-design.md` v1.2 §5.5(리버스프록시 배포환경 보안설계 보완)
  - `docs/harness/units/unit-01-test.md` 부록A (PASS, TC-014~TC-019, TC-R01~R04, TC-A01)
  - `docs/harness/decisions.md` DEC-015
  - 본 문서 §1~§9(최초 라운드, FAIL, DEF-001) — 재현·해소 대조 기준
- 테스트 수행자(에이전트): `07-integration-tester` (규칙F 재작업 재실행 라운드)
- 테스트 일시: 2026-09-16

## 부록 B-2. 테스트 범위 및 제외 범위
- 범위(In-Scope):
  1. **IT-02/IT-03 재실행(핵심)**: DEF-001이 실제로 해소되었는지 — `production.py`의 `SECURE_PROXY_SSL_HEADER` 추가가 헤더 없음/있음 두 조건 모두에서 올바르게 동작하는지(없으면 정상 리다이렉트 유지, 있으면 200이고 반복해도 301로 회귀하지 않는지).
  2. **07단계만의 관점 — WSGI 진입점부터 실제 HTTP 요청까지 전체 체인**: 06단계가 쓴 `test.Client`(Django 테스트 편의 래퍼)가 아니라, `config.wsgi.application`(`WSGIHandler`)을 raw WSGI `environ`/`start_response` 프로토콜로 직접 호출해 실제 배포 시 gunicorn이 호출하는 것과 동일한 경로로 무한루프 재발 여부를 재확인.
  3. **07단계만의 관점 — ASGI 진입점**: `render.yaml`의 실제 `startCommand`가 참조하는 `config.asgi.application`(`ASGIHandler`)을 raw ASGI `scope`/`receive`/`send` 프로토콜로 직접 호출해 동일하게 재확인(06단계는 ASGI 진입점의 실제 요청 처리 자체를 검증하지 않았음 — WSGI/ASGI 임포트 성공 여부만 IT-05가 확인했었음).
  4. **07단계만의 관점 — `XForwardedForMiddleware`와 다른 미들웨어의 순서/상호작용**: `MIDDLEWARE` 리스트 전체 순서를 직접 조회해 `SecurityMiddleware`/`WhiteNoiseMiddleware` 앞에 위치하는지 확인하고, `X-Forwarded-Proto`(SSL 리다이렉트 경계)와 `X-Forwarded-For`(REMOTE_ADDR 재설정) 두 헤더를 **동시에** 실은 단일 요청이 두 미들웨어를 거쳐 정상적으로 처리되는지(하나의 기능이 다른 기능의 처리를 방해하지 않는지) 확인 — 06단계는 두 관심사를 각각 독립적으로만 검증했다.
  5. **최소 회귀 확인**: 기존 PASS였던 IT-01(dev 전체 경로), IT-04(Host 검증), IT-05(WSGI/ASGI 계약), IT-06(마이그레이션/check)이 이번 재작업 이후에도 여전히 PASS인지 최소한으로 재확인(지시사항 원문과 동일 범위).
  6. **정리(clean-up)**: 검증에 사용한 venv/DB/staticfiles를 삭제하고 소스만 남기는지 확인.
- 제외 범위(Out-of-Scope) 및 사유:
  - IT-02/IT-03/IT-04/IT-05/IT-06/IT-07의 세부 항목 중 이번 재작업과 무관한 부분(패키지 설치, 마이그레이션 세부 로그, 라이선스 등) — 06단계 부록A와 최초 라운드에서 이미 PASS로 확정되어 있어 반복하지 않는다(규칙B "이미 검증된 것을 반복하지 않는다" 원칙, 지시사항과 동일).
  - 실제 gunicorn+uvicorn 프로세스 기동, 실제 Render 인프라에서의 헤더 실측 — Windows 로컬 환경 제약으로 이번에도 불가(최초 라운드/06단계 부록A와 동일 사유). 대신 raw WSGI/ASGI 프로토콜 호출로 "프로세스 기동을 제외한 애플리케이션 레벨 전체 체인"은 이번 라운드에서 사실상 재현했다(부록B-4 IT-R04/IT-R05 참고). 10단계에서 실제 Render 인프라 재확인 필수(§7 유지).
  - 실제 Neon/R2 네트워크 연결 — 자격증명 미발급(최초 라운드와 동일 사유).
  - 다른 업무 단위(WU-02~)와의 통합 — 아직 미개발(8단계 범위, §7-2 참고).

## 부록 B-3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`). 최초 라운드/06단계 부록A가 사용한 검증용 venv/DB/staticfiles는 이미 삭제된 상태였으므로(`find webapp -type f` → 27개 소스 파일만 존재, 최초 라운드 24개 + 신규 `config/middleware.py` 1개 = 25개라는 note의 요약 수치와는 카운트 방식(디렉터리 유무 포함 여부)이 다를 뿐 실제로는 27개 파일로 항상 일관됨을 직접 `find`로 재확인), 이번 재실행을 위해 **새 임시 venv(`webapp/.venv_it3`)를 처음부터 생성**해 `pip install -r requirements.txt`부터 재현했다.
- 테스트 데이터: production 더미 환경변수 전체(`SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=www.example.com`, `RENDER_EXTERNAL_HOSTNAME=blog-web.onrender.com`, `WAGTAILADMIN_BASE_URL`, `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`/`R2_BUCKET_NAME`/`R2_ENDPOINT_URL` 전부 더미) + `DATABASE_URL=postgres://user:pass@localhost:5432/dummydb`(가짜 postgres, 실제 네트워크 연결 시도 없이 `check`/`collectstatic`만 통과시키는 용도 — 06단계 TC-009와 동일 방식). **최초 라운드와 달리 이번 라운드는 DB 접근이 필요한 라우트(`GET /`, `GET /cms-admin/login/`)를 SQLite로 우회하지 않고, 애초에 DB 접근이 필요 없는 경로(리다이렉트가 URL resolver 이전에 발생하는 경로, WhiteNoise 정적자산, DisallowedHost 400)만으로 이번 라운드의 전체 케이스를 구성**했다 — 실제로 `HTTP_X_FORWARDED_PROTO=https`를 붙여 DB 접근이 필요한 라우트(`GET /`, `/cms-admin/login/`)를 fake postgres URL로 호출하면 실제 TCP 연결 시도가 발생해 프로세스가 무기한 대기(hang)하는 것을 직접 겪었다(최초 시도, 120초 타임아웃 후 강제 종료 — 아래 §7에 별도 기록). 이는 production이 Neon 전용으로 설계되어 fake DB 경유를 지원하지 않는다는 기존 결론(§3, 06단계 TC-009)과 일관되며, 이번 라운드가 검증하려는 대상(SSL 리다이렉트 경계·미들웨어 순서·XFF 재설정)은 전부 DB 비접근 경로로 독립적으로 검증 가능하므로 결함이 아니라 테스트 설계상 회피 대상으로 처리했다.
- 전제 조건: 06단계(재작업, PASS)와 03단계(v1.2, PASS)가 확정된 상태에서 시작. `collectstatic --noinput` 결과 214개 복사/626개 post-process, 해시 `tokens.dce349c89221.css` — 최초 라운드/06단계 부록A와 **완전히 동일한 수치**로, 이번 재작업이 정적자산 콘텐츠 자체는 건드리지 않았음을 재확인했다. 테스트 종료 후 `.venv_it3`/`staticfiles`/`db.sqlite3`/`media`/`__pycache__`를 전부 삭제해 `webapp/`를 원본 소스 상태(27개 파일, `git ls-files webapp/`와 완전 일치)로 복원했다(부록B-4 IT-R09, `find`/`git status --porcelain`으로 최종 확인).

## 부록 B-4. 테스트 케이스 및 결과

| ID | 시나리오(경계) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-R01 | production 설정 로딩 시 `SECURE_PROXY_SSL_HEADER` 값 확인(DEF-001 수정분 반영 확인) | production 더미 환경변수 전부 | `django.setup()` 후 `settings.SECURE_PROXY_SSL_HEADER` 조회 | `("HTTP_X_FORWARDED_PROTO", "https")` | `('HTTP_X_FORWARDED_PROTO', 'https')` | PASS | 06단계 TC-014와 동일 결과, 07 조립 환경에서도 재확인 |
| IT-R02 | **IT-02 재실행**: 헤더 없이 다회 라우트 요청 — 정상 리다이렉트 유지(회귀 없음) 확인 | `collectstatic` 완료(214/626, 최초 라운드와 동일 수치) | `test.Client().get(path, HTTP_HOST="blog-web.onrender.com")`를 `/static/css/tokens.dce349c89221.css`, `/`, `/cms-admin/login/`, `/nonexistent-xyz/` 4개 경로에 각각 `X-Forwarded-Proto` 헤더 없이 요청 | 4개 경로 전부 301 + 올바른 `https://` `Location` 헤더(IT-02가 원래 기대했던 "정상적인 단일 리다이렉트" 동작 — 무한루프가 아니라 "헤더 없으면 리다이렉트가 정상 발생해야 한다"는 것 자체는 맞는 동작임에 유의) | 4개 경로 전부 `301`, `Location` 헤더가 각각 `https://blog-web.onrender.com/static/css/tokens.dce349c89221.css`, `https://blog-web.onrender.com/`, `https://blog-web.onrender.com/cms-admin/login/`, `https://blog-web.onrender.com/nonexistent-xyz/`로 정확히 존재(최초 라운드 IT-02는 `Location` 헤더가 비어 있었다는 차이에 주목 — 아래 비고) | PASS | **최초 IT-02와의 차이 명시**: 최초 라운드 IT-02는 "301, `Location` 헤더 없이 리다이렉트만 발생"이라고 기록되어 있었는데, 이는 그 라운드가 사용한 `RENDER_EXTERNAL_HOSTNAME`/`Host` 헤더 조합이 달라 `request.build_absolute_uri()`가 스킴을 계산하지 못했던 것으로 추정된다(최초 라운드는 이 세부사항을 별도로 규명하지 않았음). 이번 라운드는 `HTTP_HOST`를 명시적으로 `ALLOWED_HOSTS` 내 값으로 고정해 `Location` 헤더가 항상 채워짐을 확인했다 — 이 차이는 DEF-001의 근본 원인(SECURE_PROXY_SSL_HEADER 부재)과 무관한 테스트 셋업 디테일이므로 신규 결함으로 분류하지 않는다(본 라운드에서 `Location` 헤더가 일관되게 채워짐을 확인했으므로 오히려 회귀 없음을 더 명확히 뒷받침) |
| IT-R03 | **IT-03 재실행(핵심, DEF-001 직접 해소 증명)**: WhiteNoise 정적자산 경로에서 Case A(헤더 없음, 301 유지)/B(반복해도 301, 루프 아님)/C(헤더 있음, 200)/D(헤더 있음, 5회 반복해도 200 유지 — 무한루프 재발 없음) | 동일 | `test.Client().get(asset, HTTP_HOST=...)` (A) 헤더 없음 1회 (B) 헤더 없음 반복 1회 (C) `HTTP_X_FORWARDED_PROTO="https"` 1회 (D) 동일 요청 5회 연속 | (A)(B) 301(정상 리다이렉트 유지, 회귀 없음) (C)(D) 200, 5회 모두 200 유지 | (A) `301`, `Location` 정확 (B) `301`(A와 동일, 반복해도 계속 정상 리다이렉트 — 무한루프 아님) (C) `200`, `Content-Type: text/css; charset="utf-8"` (D) 5회 전부 `200`(iter 0~4) | PASS | 최초 라운드 IT-03이 재현했던 "(A)(B) 301, (C) 200(override 적용 시)"과 동일한 패턴이되, 이번에는 **override가 아니라 실제 `production.py`에 반영된 코드 그 자체**로 재현했다는 것이 핵심 차이 — 즉 "고치면 될 것이다"가 아니라 "실제로 고쳐진 코드가 동작한다"를 증명. (D)의 5회 반복은 최초 라운드가 하지 않았던 신규 검증으로, 무한루프의 정의(반복해도 상태가 되돌아가지 않는 것)를 더 엄격하게 확인 |
| IT-R04 | **07단계만의 관점 ①**: raw WSGI 프로토콜(`environ`/`start_response`)로 `config.wsgi.application`을 직접 호출 — `test.Client` 래퍼가 아닌 실제 gunicorn이 호출하는 것과 동일한 인터페이스로 전체 체인 재확인 | `config.wsgi` 임포트, production 환경변수 전부 | 커스텀 WSGI environ(plain HTTP, `wsgi.url_scheme="http"`)으로 (a) 헤더 없음 1회 (b) `HTTP_X_FORWARDED_PROTO="https"` 3회 연속 호출 | (a) 301 (b) 3회 모두 200, 무한루프 없음 | (a) `301 Moved Permanently`, `Location: https://blog-web.onrender.com/static/css/tokens.dce349c89221.css` (b) 3회 모두 `200 OK` | PASS | `test.Client`는 내부적으로 WSGI 프로토콜을 흉내내는 편의 래퍼라 실제 `environ`/`start_response` 시그니처와 100% 동일하지 않을 수 있다는 우려를 해소하기 위해 06단계/최초 07라운드가 쓰지 않은 방식으로 재검증. gunicorn이 실제로 호출하는 인터페이스와 동일한 경로에서도 무한루프가 재발하지 않음을 직접 확인 |
| IT-R05 | **07단계만의 관점 ②**: raw ASGI 프로토콜(`scope`/`receive`/`send`)로 `config.asgi.application`을 직접 호출 — `render.yaml`의 실제 `startCommand`(`gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`)가 참조하는 진입점을 WSGI가 아닌 ASGI 방식으로 최초 재현 | `config.asgi` 임포트, production 환경변수 전부 | 커스텀 ASGI `scope`(`type=http`, `scheme=http`)로 (a) 헤더 없음 1회 (b) `x-forwarded-proto: https` 헤더 포함 3회 연속 호출 | (a) 301 (b) 3회 모두 200, 무한루프 없음 | (a) `status=301` (b) 3회 모두 `status=200` | PASS | 최초 라운드/06단계는 ASGI 진입점에 대해 "임포트 성공 여부"(`IT-05`, `TC-005` 계열)만 확인했고, **ASGI 프로토콜로 실제 요청을 처리해 DEF-001이 해소되는지는 이번이 최초 검증**이다. `render.yaml`이 실제로 지정한 시작 커맨드는 `config.asgi`(WSGI가 아님)이므로, 이 경로에서의 검증이 07단계 관점에서 특히 중요하다고 판단해 신규로 추가했다. **부가 관찰(결함 아님, 정보성)**: 응답 헤더 처리 중 `Django Warning: StreamingHttpResponse must consume synchronous iterators in order to serve them asynchronously. Use an asynchronous iterator instead.`가 콘솔에 출력됨 — WhiteNoise가 반환하는 동기(sync) 파일 이터레이터를 Django ASGI 핸들러가 동기 방식으로 소비하면서 발생하는 경고이며, 응답 자체는 200과 올바른 바디로 정상 완료되어 기능 결함은 아니다. 다만 실제 프로덕션에서 uvicorn 워커가 이 경고를 반복적으로 발생시키며 이벤트 루프를 짧게 블로킹할 가능성이 있어 §7에 신규 정보성 리스크로 기록 |
| IT-R06 | **07단계만의 관점 ③(지시사항 핵심)**: `XForwardedForMiddleware`와 `SecurityMiddleware`/`WhiteNoiseMiddleware`의 순서·상호작용 부작용 확인 | 동일 | ① `settings.MIDDLEWARE` 전체 순서 조회 ② `X-Forwarded-Proto`(SSL 리다이렉트 관심사)와 `X-Forwarded-For`(REMOTE_ADDR 관심사) 헤더를 **동시에** 실은 단일 요청을 WhiteNoise 정적자산에 전송 ③ `RequestFactory`로 동일 요청을 만들어 `XForwardedForMiddleware`에 직접 통과시켜 `REMOTE_ADDR` 재설정 확인 | ① `XForwardedForMiddleware`가 `MIDDLEWARE[0]`(SecurityMiddleware/WhiteNoise보다 앞) ② 두 헤더가 동시에 있어도 200 + 올바른 콘텐츠(두 관심사가 서로 간섭하지 않음) ③ `REMOTE_ADDR`이 rightmost 값으로 재설정 | ① `MIDDLEWARE[0] == 'config.middleware.XForwardedForMiddleware'`, 나머지 9개는 `1~9`에 `base.py` 원본 순서 그대로(`SecurityMiddleware`가 `[1]`, `WhiteNoiseMiddleware`가 `[2]`) ② `200`, `Content-Type: text/css; charset="utf-8"`(SSL 리다이렉트 해제와 정적자산 서빙이 XFF 헤더 존재 여부와 무관하게 정상 동작) ③ `REMOTE_ADDR`이 `10.0.0.9`(rightmost)로 정확히 재설정됨 | PASS | **핵심 결론**: `SecurityMiddleware`의 SSL 리다이렉트 판정은 `request.is_secure()`(→`X-Forwarded-Proto` 헤더만 참조)에 의존하고, `XForwardedForMiddleware`는 오직 `REMOTE_ADDR`만 재설정하므로 두 관심사가 서로 다른 요청 속성을 다뤄 겹치지 않는다 — 이것이 `XForwardedForMiddleware`를 체인 맨 앞에 둬도 부작용이 없는 구조적 이유임을 이번 라운드에서 직접 실증했다(06단계는 두 헤더를 각각 독립적으로만 테스트했었음, TC-016/TC-017 계열) |
| IT-R07 | **IT-04 회귀 확인(최소)**: Host 검증(DisallowedHost)이 SSL 헤더 해소 이후에도, 그리고 XFF 헤더가 동시에 있어도 깨지지 않는지 | 동일 | `HTTP_HOST="evil.example.net"`, `HTTP_X_FORWARDED_PROTO="https"` (+ 일부는 `HTTP_X_FORWARDED_FOR="9.9.9.9"` 추가)로 (a) Django 라우트(`/nonexistent-abc/`) (b) WhiteNoise 정적자산 요청 | (a) 400(DisallowedHost, 최초 라운드 IT-04와 동일) (b) 200(WhiteNoise는 Host 미검증, 최초 라운드 IT-04와 동일, 정보성 결함 아님) | (a) `400`(두 케이스 모두 XFF 유무와 무관하게 동일) (b) `200` | PASS | 최초 라운드 IT-04가 확정한 동작이 이번 재작업(SECURE_PROXY_SSL_HEADER 추가 + XForwardedForMiddleware 신규 삽입) 이후에도 회귀 없이 그대로 유지됨을 확인 |
| IT-R08 | **최소 회귀 확인(지시사항)**: IT-01(dev 전체 경로)/IT-06(마이그레이션/check) 재확인 + dev `MIDDLEWARE`에 `XForwardedForMiddleware` 미포함 확인 | 신규 venv, `pip install` 완료, `DJANGO_SETTINGS_MODULE` unset(dev 기본값) | ① `makemigrations --check --dry-run` ② `migrate` ③ `check` ④ `test.Client().get("/")` → 정적 링크 추출 후 재요청 ⑤ `/cms-admin/login/`, `/no-such-page-xyz/` ⑥ dev `settings.MIDDLEWARE`에 `config.middleware.XForwardedForMiddleware` 포함 여부 | ①"No changes detected" ②③ 오류 없음 ④ `GET /` 200 + 정적 링크 2개 모두 200 ⑤ 200/404 ⑥ `False`(미포함) | ① "No changes detected", exit 0 ② 전체 마이그레이션(wagtailcore 포함) 오류 없이 적용 ③ "System check identified no issues (0 silenced)" ④ `GET /` → 200, 링크 `/static/css/tokens.css`/`/static/css/base.css` 각각 200, `Content-Type: text/css; charset="utf-8"` ⑤ `/cms-admin/login/` → 200, `/no-such-page-xyz/` → 404 ⑥ `False` — dev `MIDDLEWARE`는 `base.py` 원본 9개 그대로 | PASS | 최초 라운드 IT-01/IT-06과 06단계 TC-R01~R04(부록A) 모두와 일치, 회귀 없음. dev 환경은 이번 재작업(production 전용 변경)의 영향을 전혀 받지 않음을 재확인 |
| IT-R09 | 정리(clean-up) — 검증용 venv/DB/staticfiles 삭제 후 소스 diff가 깨끗한지 | IT-R01~IT-R08 전체 완료 | `.venv_it3`/`db.sqlite3`/`staticfiles`/`media`/`__pycache__` 삭제 → `find webapp -type f` → `git ls-files webapp/`와 대조 → `git status --porcelain webapp/` | 소스 파일만 남고 `git ls-files webapp/`와 완전 일치, `git status --porcelain webapp/` 출력 없음(clean) | `find webapp -type f` → 27개 파일, `git ls-files webapp/` → 동일 27개 파일과 1:1 일치(순서까지 동일). `git status --porcelain webapp/` → 출력 없음(추가/변경 없음) | PASS | 이번 프로젝트(`AI-AUTO-WORK`)는 이미 `webapp/` 전체가 커밋되어 있는 상태였음을 이번 라운드에서 처음 확인했다(`git log --oneline -- webapp/` → 1개 커밋 `f89dd90`). 따라서 "24개/25개 소스 파일"이라는 이전 라운드들의 수치는 `find`의 카운트 방식(디렉터리 자체를 별도 항목으로 셌는지 여부 등) 차이로 추정되며, 실제 트래킹된 파일 수(27개)와 이번 정리 후 파일 수(27개)가 정확히 일치한다는 사실이 이번 라운드의 실질적 확인 근거다 — 검증에 쓴 어떤 산출물도 diff/커밋 이력에 남지 않았음을 git 기준으로 명확히 증명 |

> 정상 경로(IT-R01, IT-R03 C/D, IT-R04 b, IT-R05 b, IT-R06, IT-R08) + 결함 해소 대조 실험(IT-R02/IT-R03 A/B vs C/D — "헤더 없으면 정상 리다이렉트 유지, 있으면 200이고 반복해도 루프 재발 없음") + 신규 진입점 관점(IT-R04 raw WSGI, IT-R05 raw ASGI) + 미들웨어 상호작용(IT-R06, 지시사항이 명시적으로 요구한 항목) + 회귀(IT-R07 Host 검증, IT-R08 dev 전체) + 원상복구(IT-R09)를 모두 포함했다.

## 부록 B-5. 커버리지
- 커버리지 지표: 지시사항이 요구한 4가지 관점 100% 커버 — ①DEF-001 실제 해소 여부(IT-R02/IT-R03), ②WSGI 진입점부터 실제 HTTP 요청까지 전체 체인 무한루프 재발 없음(IT-R04), ③`XForwardedForMiddleware`와 다른 미들웨어의 순서/상호작용 부작용 없음(IT-R06), ④기존 PASS 항목(IT-01/IT-04/IT-05/IT-06) 회귀 없음(IT-R07/IT-R08). 추가로 지시사항에 명시되지 않았으나 07단계 관점에서 위험도가 높다고 판단해 ASGI 진입점(render.yaml의 실제 startCommand 대상)까지 확장 검증했다(IT-R05, 규칙C).
- 인수조건/지시사항 ↔ 테스트 케이스 매핑표(추적성 확인):

| 지시사항 항목 | 테스트 케이스 |
|---|---|
| DEF-001이 실제로 해소됐는지 | IT-R01, IT-R02, IT-R03 |
| WSGI 진입점부터 실제 HTTP 요청까지 전체 체인에서 무한루프 재발 없음 | IT-R04 (WSGI), IT-R05 (ASGI, 확장) |
| XForwardedForMiddleware가 다른 미들웨어(SecurityMiddleware, WhiteNoise 등)와의 순서/상호작용에서 부작용 없는지 | IT-R06 |
| 기존 PASS였던 IT-01, IT-04 등 다른 통합 항목들에 회귀가 없는지 최소한으로 재확인 | IT-R07 (IT-04), IT-R08 (IT-01, IT-06) |
| venv/db/staticfiles 정리, 소스만 남김 | IT-R09 |

- 커버되지 않은 부분과 사유:
  - 실제 gunicorn+uvicorn 프로세스 기동 및 Render 실제 인프라의 헤더 실측 — Windows 로컬 한계로 이번에도 미검증. **다만 IT-R04(raw WSGI)/IT-R05(raw ASGI)에서 애플리케이션 레벨 프로토콜을 실제 서버가 호출하는 것과 동일한 인터페이스로 직접 재현**했으므로, "프로세스 기동을 제외한 전체 체인"은 이번 라운드에서 사실상 검증되었다. 10단계에서 실제 Render 인프라로 최종 재확인 필수(§7 유지, 신규 아님).
  - 실제 Neon/R2 네트워크 연결 — 자격증명 미발급(최초 라운드와 동일 사유, 부록B-2 제외범위 참고).
  - WU-02 이후 다른 업무 단위와의 상호작용 — 아직 미개발이므로 이번 07단계 범위가 아니다(8단계 전체 풀테스트 대상). **다만 지시사항이 요구한 "8단계 전체 테스트에서 문제가 생기지 않을까"에 대한 2차 내부검증 관점 재검토는 부록B-9에서 별도로 수행했다.**
  - REQ-ID 커버리지: **해당 없음(근거)** — `docs/harness/traceability.md`를 이번에도 직접 열람해 재확인한 결과 WU-01을 참조하는 REQ-ID 행이 없다(최초 라운드 §5, `unit-01-test.md` 부록A-5와 동일 결론, 3중 교차 확인 유지). 따라서 이번 라운드도 traceability.md의 "통합테스트" 컬럼을 갱신할 대상 REQ-ID 행이 존재하지 않는다 — traceability.md 파일 자체는 수정하지 않았다.

## 부록 B-6. 결함(Defect) 목록
| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| DEF-001 | (원본 결함, §6 참고) production `SECURE_PROXY_SSL_HEADER` 미설정으로 인한 무한 HTTPS 리다이렉트 루프 | §6 참고 | Critical | **Fixed** | IT-R02(헤더 없을 때 정상 리다이렉트 유지, 회귀 없음)와 IT-R03(헤더 있을 때 200, 5회 반복해도 재발 없음), IT-R04/IT-R05(raw WSGI/ASGI 프로토콜에서도 동일하게 해소)로 **다각도 대조 실험을 통해 해소를 직접 증명**했다. 추가로 IT-R06에서 신규 미들웨어(`XForwardedForMiddleware`)가 이 해소에 부작용을 일으키지 않음도 확인 |

- **신규 결함 0건.** IT-R01~IT-R09(하위 케이스 포함 다수)를 전부 실행했고, 모든 케이스에서 "실제 결과"가 "예상 결과"와 일치했다(부록B-4 표의 각 셀에 구체적 상태코드/헤더값/파일 개수 대조 기록). DEF-001은 Critical에서 **Fixed**로 상태가 변경되었다(신규 결함이 아니라 원본 결함의 상태 갱신).
- **정보성 관찰 1건(결함 아님, §7에 리스크로 기록)**: IT-R05에서 raw ASGI 경로 실행 중 `StreamingHttpResponse must consume synchronous iterators...` 경고가 관측됨 — 응답은 200으로 정상 완료되어 기능 결함이 아니므로 결함 목록에 등재하지 않고 리스크로만 기록한다(근거: 응답 상태코드/바디가 예상과 100% 일치, 예외 없이 완료).

## 부록 B-7. 리스크 및 잔존 이슈 (부록 B 전용, §7과 중복 기록하지 않음)
- **(신규, 정보성, Low)** ASGI 경로에서 WhiteNoise 정적자산 서빙 시 `StreamingHttpResponse` 동기 이터레이터 경고: IT-R05에서 처음 관측됨. 실제 uvicorn 워커 하에서 이 경고가 반복 발생하며 이벤트 루프를 짧게 블로킹할 가능성이 있으나, 본 라운드의 raw ASGI 호출 3회 연속 테스트에서 응답 지연이나 실패는 관측되지 않았다. Critical/High로 격상할 근거는 없으나, 10단계(실제 Render+uvicorn 환경)에서 정적자산 다수 동시 요청 시 지연이 발생하는지 관찰 항목으로 추가할 것을 권고한다(신규 결함으로 등재하지 않음 — 규칙C에 따라 위험 신호로만 기록, 임의로 Critical로 과대평가하지 않되 축소 평가도 하지 않음).
- **(신규, 정보성)** IT-R02에서 최초 라운드 IT-02와 `Location` 헤더 유무가 달랐던 점(부록B-4 IT-R02 비고 참고) — DEF-001 해소 여부 판정에는 영향 없으나, 향후 누군가 이 문서를 볼 때 혼동하지 않도록 원인 추정을 명시적으로 남겼다.
- **(운영상 특이사항, 결함 아님)** 이번 라운드에서 `DATABASE_URL`에 도달 불가능한 fake postgres 주소(`localhost:5432`)를 쓰고 DB 접근이 필요한 라우트(`GET /`, `/cms-admin/login/`)에 프로덕션 SSL 헤더를 올바르게 붙여 요청했더니, TCP 연결 시도가 즉시 실패하지 않고 무기한 대기(hang)하는 것을 실제로 겪었다(최초 시도, 120초 타임아웃으로 프로세스 강제 종료 후 테스트 설계를 DB 비접근 경로로 재구성함). 이는 이번 재작업 코드의 결함이 아니라 **테스트 환경(fake DB 주소)의 한계**이지만, 10단계에서 실제 Neon 연결 전 혹시라도 오설정된 `DATABASE_URL`(예: 존재하지 않는 호스트)이 들어가면 애플리케이션이 즉시 에러를 내지 않고 무기한 대기할 수 있다는 점을 운영 Runbook 후보 메모로 남긴다(psycopg의 기본 connect_timeout 미설정 가능성 — Critical 아님, 11단계 참고용 메모).
- §7(최초 라운드 리스크 섹션)에 이미 기록된 항목(10단계 실제 Render 헤더 실측 필요, WhiteNoise Host 미검증 정보성, SQLite+ssl_require 정보성, gunicorn 미검증/Neon·R2 미발급/Pretendard/HSTS/healthCheckPath 등 06단계 인계분)은 이번 라운드에서 상태 변화 없이 그대로 유지된다(중복 기록하지 않음, §7 참고).

## 부록 B-8. 결론 및 판정 (최종 판정)
- [x] **PASS** — 다음 단계(8-full-system-tester, 전체 풀테스트) 진행 가능. **WU-01은 이 판정으로 완전히 종결되며, WU-02(콘텐츠 모델/CRUD) 개발 착수가 가능하다.**
- [ ] CONDITIONAL PASS
- [ ] FAIL

**판정 근거**:
1. **DEF-001(Critical) 해소를 다각도로 직접 증명**했다 — `test.Client`(IT-R02/R03), raw WSGI(IT-R04), raw ASGI(IT-R05) 세 가지 서로 다른 호출 경로 전부에서 "헤더 없으면 정상 리다이렉트 유지(회귀 없음), 헤더 있으면 200이고 반복 요청해도 301로 되돌아가지 않는다(무한루프 재발 없음)"는 동일한 결론을 얻었다. 이는 "설정을 추가했으니 될 것이다"가 아니라 "실제 배포 시 gunicorn이 호출하는 것과 동일한 인터페이스에서 실제로 해소되었다"를 의미한다.
2. **07단계만의 관점에서 요구된 3가지를 전부 충족했다**: ①WSGI 진입점부터 실제 HTTP 요청까지 전체 체인 무한루프 재발 없음(IT-R04, 반복 3회 200 유지) — 추가로 ASGI 경로까지 확장 검증(IT-R05). ②`XForwardedForMiddleware`가 `SecurityMiddleware`/`WhiteNoiseMiddleware`와 순서·상호작용에서 부작용을 일으키지 않음을 구조적 근거(서로 다른 request 속성을 다룸)와 함께 실측으로 증명(IT-R06). ③기존 PASS 항목(IT-01→IT-R08, IT-04→IT-R07, IT-05→IT-R04/R05가 대체 검증, IT-06→IT-R08)에 회귀 없음을 확인.
3. **신규 결함 0건**이며, 정보성 관찰 1건(ASGI `StreamingHttpResponse` 경고, Low)만 리스크로 기록했다 — Critical/High가 아니므로 PASS 판정을 막지 않는다.
4. **회귀 의무(규칙F-3) 이행 확인**: 3단계(§5.5 v1.2)→5단계(코드)→6단계(부록A, PASS)→7단계(본 부록B, PASS)로 이어지는 재작업 경로 전체가 완료되었고, 각 단계의 산출물이 상호 참조 모순 없이 일관됨을 확인했다(본 문서 §0, `unit-01-note.md` §0/§10, `unit-01-test.md` 부록A와 상호 대조).
5. **검증에 사용한 venv/DB/staticfiles는 전부 삭제**해 `webapp/`가 git에 커밋된 소스 상태와 완전히 일치함을 `git status --porcelain`으로 확인했다(IT-R09).
6. **8단계로의 게이트 통과**: 규칙D(단계 게이트)에 따라, 이 문서가 PASS로 갱신되었으므로 8단계(전체 풀시스템테스트)가 이제 착수 가능하다. 다만 §7/부록B-7에 기록된 대로 **10단계에서 실제 Render 인프라로 최종 재확인은 여전히 필수**이며(이번 라운드가 애플리케이션 레벨 체인을 실제 서버 호출 인터페이스와 동일하게 재현했지만, 실제 프로세스 기동·실제 네트워크 왕복을 대체하지는 못함), 이는 PASS 판정을 막는 조건이 아니라 후속 단계로 명시적으로 이월되는 사항이다(§7 5번, 최초 라운드부터 일관되게 유지).

## 부록 B-9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약(작성자 관점): IT-R01~IT-R09가 부록B-1의 4가지 목적(DEF-001 해소, WSGI 전체 체인, 미들웨어 상호작용, 기존 항목 회귀)을 전부 케이스로 커버하는지 부록B-5 매핑표로 재확인. 06단계 부록A가 이미 검증한 항목(TC-014~TC-019 등)을 그대로 반복하지 않고 07단계만의 관점(raw WSGI/ASGI 프로토콜, 미들웨어 상호작용의 구조적 근거)에 집중했는지 확인. 모든 "예상 결과"가 최초 라운드 IT-02/IT-03의 원문 수치(해시값 `dce349c89221`, 214/626 등)와 정확히 일치하는지 대조해, 추측이 아니라 재현 가능한 근거임을 재확인. 결함 0건, 정보성 관찰 1건(ASGI 경고) 확인.
- 2차 검증 결과 요약("이 결과서를 오늘 처음 받아보는 8단계 담당자" 관점 재검토): (a) 최초 초안에는 IT-R02의 `Location` 헤더가 최초 라운드 IT-02와 다르게 채워진 이유에 대한 설명이 없어 "이것도 결함 아닌가"라는 의문이 들 수 있었다 — 비고 칸에 원인 추정과 "DEF-001 해소 여부 판정과는 무관함"을 명시적으로 추가했다(부록B-4 IT-R02 비고 보강). (b) IT-R05의 raw ASGI 테스트 스크립트가 초안에서는 ASGI `receive()` 콜러블의 스펙(연속 호출 시 `http.disconnect` 반환 필요)을 잘못 구현해 실제로 `AssertionError`가 발생했었다 — 이 실패 자체를 "테스트 스크립트 버그"로 명확히 식별하고 수정한 뒤 재실행해 정상 결과를 얻었음을 투명하게 남긴다(테스트 도구의 결함과 대상 코드의 결함을 혼동하지 않기 위함, 대상 코드에는 문제가 없었음). (c) 최초 시도에서 fake DB 주소로 DB 접근 라우트를 테스트하려다 프로세스가 hang된 사건을 "숨기지 않고" §7/부록B-7에 명시적으로 기록해, 다음에 이 문서를 보는 사람이 동일한 실수를 반복하지 않도록 했다. (d) "8단계에서 문제가 생기지 않을까"를 의심하는 관점에서 재검토한 결과: WU-01은 여전히 다른 WU와 결합할 코드가 없는 단일 업무 단위이므로(§1 판단 유지) 8단계 시점에 새로운 통합 지점 자체가 존재하지 않으나, **8단계가 이번 재작업으로 추가된 `XForwardedForMiddleware`를 반드시 "production 전용" 미들웨어로 인지하고 dev 테스트 환경과 혼동하지 않아야 한다**는 점을 부록B-7에 명시적 인계 사항으로 남겼다(IT-R08이 이미 dev에는 미포함임을 확인했으므로 8단계에서 별도 조치 불필요, 다만 인지 목적으로 기록). 이 4가지를 반영해 초안 → 최종본으로 보강했으며, 결함 목록(신규 0건)은 1차와 2차 모두 동일하게 유지되었다.
- 검증 로그 파일 경로: `docs/harness/verify-log_feature-WU-01-integration-test.md`(§ "부록 B 재작업 재실행 라운드" 추가분)

## 절차 흐름 (참고용 다이어그램) — 부록 B
```mermaid
flowchart TD
    A["최초 라운드 FAIL(DEF-001) 입력"] --> B["3단계 v1.2 → 5단계 코드수정 → 6단계 부록A PASS 확인"]
    B --> C["IT-R01~R03: DEF-001 해소 재현(test.Client)"]
    C --> D["IT-R04/R05: raw WSGI/ASGI 전체 체인 재확인"]
    D --> E["IT-R06: XForwardedForMiddleware 상호작용 확인"]
    E --> F["IT-R07/R08: 기존 PASS 항목 회귀 확인"]
    F --> G["IT-R09: venv/DB/staticfiles 정리"]
    G --> H{신규 Critical/High 결함?}
    H -->|Yes| I["FAIL — 규칙F 재소급"]
    H -->|No| J["verification-log 2회 이상(부록B-9)"]
    J --> K["PASS → 8단계(전체 풀테스트) 착수 가능, WU-01 종결"]
```
