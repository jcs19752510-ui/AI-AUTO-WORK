# 10단계 — 배포테스트 결과서

- 문서 버전: v1.0
- 작성 일시(KST): 20260918 013454
- 작성 에이전트: 10-deploy-tester

> 본 결과서는 `templates/test-report-template.md` 양식을 그대로 따른다. 본 단계는 **실제 프로덕션 배포를 수행하지 않는다**(12단계, 사용자 명시적 승인 필요 — 규칙E). 목적은 빌드 스크립트·배포 설정·환경변수·롤백 절차·모니터링/알림 채널을 스테이징(로컬 Docker 재현) 관점에서 실측 검증하는 것이다.

---

## 1. 개요

- 테스트 대상: `webapp/`(Wagtail/Django 블로그) 전체의 **배포 파이프라인** — `webapp/build.sh`, `webapp/render.yaml`, `webapp/config/settings/production.py`, `.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`, `webapp/ADMIN_ACCESS_GUIDE.md`, `.env.example`
- 테스트 유형: 배포 전(Deploy Test)
- 적용 Tier: Standard (DEC-036)
- 테스트 목적: WU-01~WU-10이 "Windows 로컬 제약으로 검증 못함"으로 반복 이월한 항목(실제 gunicorn+uvicorn 기동, `/healthz` 실측, R2 네트워크 업로드, 백업/복구 실행, 관리자 로그인 레이트리밋의 실서버 동작, 장애 알림 실제 수신, 롤백 절차 실제 검증)을 **이번 세션이 처음으로 실측**한다.
- 관련 산출물: `docs/harness/decisions.md`(DEC-001~042, 특히 DEC-026/032~034/039~042), `docs/harness/traceability.md`, `docs/harness/03-system-design.md` §6/§7, `docs/harness/08-full-system-test.md`(PASS), `docs/harness/09-security-audit.md`(재작업 라운드2 최종 PASS), `webapp/render.yaml`, `webapp/build.sh`, `.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`, `webapp/ADMIN_ACCESS_GUIDE.md`
- 테스트 수행자(에이전트): 10-deploy-tester
- 테스트 일시(KST): 2026-09-18 01:15 ~ 01:35경 (세션 1회, 내부검증 포함)

## 2. 테스트 범위 및 제외 범위

### In-Scope
1. `webapp/build.sh` 전체(=`pip install`/`collectstatic`/`migrate`/`ensure_superuser`)를 실제 Linux 컨테이너에서 처음부터 끝까지 실행
2. `render.yaml`의 `startCommand`(`gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 1`)를 **문자 그대로** 실제 기동해 `/healthz` 등 핵심 라우트를 실제 HTTP로 응답 실측
3. `render.yaml`의 `healthCheckPath`/`envVars` 목록과 실제 코드(`production.py`, 뷰)의 100% 일치 여부 대조
4. `.env.example`과 실제 필요한 환경변수 전체 목록 일치 여부
5. DEF-09-01 재작업(관리자 로그인 레이트리밋, DEC-039~042)이 **Django `Client()`가 아닌 실제 gunicorn/uvicorn 워커** 위에서도 동일하게 동작하는지 실측(기존 검증은 전부 `Client()`/`RequestFactory` 기반이었음)
6. 장애 알림 채널(03 §7.2) 실측: 강제 500 에러 → `ADMINS`/`AdminEmailHandler` → SMTP 실제 발송/수신
7. R2(S3 호환) 오브젝트 스토리지 실제 네트워크 저장/조회/삭제(REQ-006, 여러 WU가 "10단계 이월"로 명시)
8. 백업 파이프라인(`.github/workflows/neon-db-backup.yml`)의 `pg_dump`/`gzip`/S3 업로드/Lifecycle 설정/복구(`psql -f`) 로직을 실제 도구로 실행 — **재난복구 리허설 1회**(BACKUP_RESTORE_GUIDE.md §6 항목5 권고 이행)
9. GitHub Actions 워크플로 파일의 위치/`workflow_dispatch` 트리거 조건 확인(문법 자체는 6/7단계 actionlint로 이미 검증되어 재검증하지 않음)
10. **롤백 절차 실제 검증**: (a) 코드 롤백(직전 커밋으로 재기동) 시 마이그레이션 방향/스키마 안전성, (b) 롤백이 보안수정(DEF-09-01)에 미치는 영향
11. 빌드 재현성(동일 소스로 독립 재빌드 시 동일 산출물인지)

### Out-of-Scope 및 사유
- **실제 프로덕션 배포(Render/Neon/Cloudflare R2/GitHub 실계정 연동)**: 규칙E(배포는 사용자 승인 없이 절대 실행 금지) — 12단계 전용, 이번엔 수행하지 않음
- **실제 Cloudflare R2 계정**: 아직 발급되지 않음(DEC-008/decisions.md 전반이 명시한 기존 제약, WU-01~10 전체 동일). **대체 수단**: MinIO(S3 API 완전 호환)를 로컬 Docker로 띄워 `django-storages`의 S3 백엔드 코드 경로 자체(저장/조회/삭제/Lifecycle API)를 실제 네트워크 호출로 검증했다 — Cloudflare라는 특정 벤더의 API 엔드포인트 자체까지 검증한 것은 아니라는 점을 명확히 구분해 기록한다(§4 TC-009/TC-014/TC-015 비고)
- **실제 Neon PostgreSQL 계정**: 아직 발급되지 않음. **대체 수단**: SSL(TLS)이 필수인 PostgreSQL 16 컨테이너를 직접 빌드해(`ssl=on` + 자체서명 인증서) `production.py`의 `ssl_require=True` 강제 조건을 실제로 충족하는 환경에서 검증했다
- **실제 GitHub Actions 실행**: push 없이 원격 실행은 불가능(이번 세션 지시사항 및 규칙 — git add/commit/push 절대 금지). **대체 수단**: 워크플로가 실행하는 각 셸 스텝의 실제 로직(`pg_dump`/`gzip`/`aws s3 cp`/`put-bucket-lifecycle-configuration` 동등 호출)을 로컬에서 실제 도구로 그대로 재현했다
- **Render 플랫폼 자체의 헬스체크 프로브 요청이 실제로 `X-Forwarded-Proto` 헤더를 포함하는지**: 외부 공식문서 실시간 조회 도구(MCP 등)가 이번 세션에 연결되어 있지 않아 확인 불가 — §6 DEF-10-01, §8에 미해결 리스크로 명시하고 11단계 인계
- **동시성/부하 테스트**: 8단계(전체 풀테스트) 영역이며 이번 배포테스트는 "배포 절차 자체"에 집중(요청 범위)

## 3. 테스트 환경

- **실행 환경**: Windows 10 Pro 로컬 머신 + **Docker Desktop(WSL2 백엔드) 컨테이너** — Windows에서 gunicorn(POSIX 전용 `fcntl` 등 의존)을 직접 실행할 수 없는 기존 제약(WU-01~09 전체가 반복 기록)을 이번 세션은 **Docker(비-Windows 실행 환경)로 실제 우회 성공**했다. WSL 자체(`wsl -l`)는 출력이 깨졌으나 Docker Desktop이 `docker-desktop`(WSL2) 배포판으로 정상 동작 중임을 `docker info`/`docker pull`로 실측 확인했다.
- **컨테이너 구성**(전부 `webapp/.harness-tmp/deploy-staging/`, 규칙K):
  - `db`: `postgres:16-alpine` 기반 자체 빌드 — Neon과 동일하게 **SSL 필수** 연결을 재현(자체서명 인증서, `ssl=on`)
  - `minio`(`quay.io/minio/minio`) + `mc`(`quay.io/minio/mc`): Cloudflare R2의 S3 호환 API를 로컬에서 재현, `media-public`/`backup-private` 버킷을 실제 생성
  - `mailhog`: SMTP 캐처(장애 알림 이메일의 실제 발송/수신 확인용)
  - `web`: `python:3.12.9-slim`(render.yaml `PYTHON_VERSION`과 동일) 기반, `requirements.txt`를 그대로 설치하고 `render.yaml`의 `startCommand`를 **글자 그대로** 실행
- **테스트 데이터**: 스테이징 DB에 실제 시드 데이터 생성(`BlogPostPage` 1건 `wu10-backup-probe`, `NewsletterSubscriber` 1건 `probe@example.com`) — 백업/복구 리허설의 데이터 무결성 확인용
- **전제 조건**: 08단계(PASS)/09단계(재작업 라운드2 최종 PASS, DEC-042) 완료, `automation/harness-janitor.sh --check`로 세션 시작 전 `.harness-tmp/` 클린 상태 확인(잔여물 없음)

## 4. 테스트 케이스 및 결과

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | `build.sh` 전체(pip install/collectstatic/migrate/ensure_superuser) 실제 실행 | SSL 필수 Postgres 16 컨테이너, 빈 DB | `docker compose up --build`로 `web` 서비스가 `build.sh` 실행 | 오류 없이 전 과정 완료, 최초 슈퍼유저 생성 | `218 static files copied... 638 post-processed`, 전체 마이그레이션(admin/auth/blog/.../wagtailusers) OK, `슈퍼유저 'stagingadmin' 계정을 생성했습니다.` | PASS | WU-01~10 전체 마이그레이션 체인이 실제 SSL Postgres에서 처음부터 재현됨 |
| TC-002 | `render.yaml` `startCommand` 그대로 실제 기동 | TC-001 완료 | 동일 컨테이너에서 이어서 `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:8000` 실행 | 정상 기동, 포트 리스닝 | `Starting gunicorn 23.0.0`/`Using worker: uvicorn.workers.UvicornWorker`/`Application startup complete.` | PASS | 이 프로젝트 최초의 실제 gunicorn+uvicorn 프로세스 기동(WU-01~09는 전부 Windows 제약으로 `Client()`만 사용) |
| TC-003 | `/healthz`(X-Forwarded-Proto: https 포함, Render 엣지 트래픽 재현) | TC-002 | `curl -H "X-Forwarded-Proto: https"` | `200 ok` | `HTTP 200`, body `ok` | PASS | `render.yaml healthCheckPath`와 정확히 일치(`/healthz`) |
| TC-004 | `/healthz`(헤더 없이, 직접 프로브 재현) | TC-002 | `curl`(헤더 없음) | (검증 대상) | `HTTP 301 Location: https://localhost:18000/healthz` | **관찰됨 — DEF-10-01** | 03 §5.5.2(`SECURE_SSL_REDIRECT=True`)가 헬스체크 경로에도 예외 없이 적용됨(WU-08 IT-11이 이미 "의도된 동작"으로 PASS 확정한 것과 동일 동작 — §6 DEF-10-01에서 "왜 지금 다시 문제로 보는지" 설명) |
| TC-005 | 핵심 공개 라우트 10종 스모크(X-Forwarded-Proto 포함) | TC-002 | `/`, `/robots.txt`, `/sitemap.xml`, `/feed.xml`, `/privacy-policy/`, `/terms/`, `/cookies/`, `/cms-admin/login/`, `/django-admin/login/`, `/newsletter/form/`, `/static/css/components.css` | 전부 200 | 전부 200 | PASS | 실제 gunicorn 위에서 전 라우트 최초 확인 |
| TC-006 | DEF-09-01 재작업(관리자 로그인 레이트리밋) 실서버 재현 | TC-002, 신규 CSRF 쿠키 | `/django-admin/login/`에 동일 IP로 잘못된 자격증명 11회 연속 POST(실제 CSRF 토큰 사용) | 10회 200, 11회째 429 | `[200×10, 429]` | PASS | 기존 검증(06/07/09단계)은 전부 `Client()` 기반 — **실제 서버 프로세스 위에서 첫 실측**, DEC-042 판정 그대로 재확인 |
| TC-007 | 두 로그인 경로 카운터 공유(DEC-040/041) 실서버 재현 | TC-006 직후(동일 IP, django-admin 예산 소진) | `/cms-admin/login/`에 같은 IP로 1회 POST | 즉시 429(공유 카운터 소진) | `429` | PASS | IP 기준 공유 카운터가 실제 서버에서도 동일하게 동작 |
| TC-008 | 장애 알림(REQ-012, 03 §7.2 항목1) 실제 발송/수신 | TC-002, `DJANGO_ADMIN_EMAIL`/`EMAIL_HOST`(mailhog) 설정 | 실제 요청-응답 파이프라인(`django.test.override_settings(ROOT_URLCONF=...)` + 실제 예외 발생)으로 강제 500 유발 | `AdminEmailHandler`가 SMTP로 이메일 발송, mailhog가 수신 | 응답 500 확인, mailhog API에 `Subject: "[Django] ERROR (EXTERNAL IP): Internal Server Error: /__wu10_force_500__/"` 메일 1건 실제 수신(트레이스백/Installed Middleware 목록 포함) | PASS | 03 §7.2 "10단계에서 반드시 실측 검증"으로 명시했던 항목(1) 최초 실증 |
| TC-009 | R2(S3 호환) 오브젝트 스토리지 실제 네트워크 저장/조회/삭제 | TC-002, MinIO `media-public` 버킷 | `default_storage.save/exists/size/open/delete` 실행(코드 미변경, `django-storages` 그대로) | 전부 성공 | `SAVED`, `EXISTS: True`, `SIZE: 25`, `READBACK` 원문 일치, `DELETED` 확인 | PASS | Cloudflare R2 벤더 자체는 미검증(자격증명 미발급) — S3 호환 API 코드 경로는 실네트워크로 검증됨을 명확히 구분 |
| TC-010 | `render.yaml` envVars/healthCheckPath/startCommand ↔ 실제 코드 대조 | - | `render.yaml`, `production.py`, `core/views.py`, `core/urls.py`, `.env.example` 대조 | 100% 일치 | `healthCheckPath`/`startCommand` 일치. `envVars` 25개 중 `.env.example`에 10개 누락 발견 | **부분 불일치 — DEF-10-02** | §6 참고 |
| TC-011 | gunicorn 워커 수 실측(DEC-026 `--workers 1`) | TC-002 | 로그에서 `Booting worker` 출현 횟수 카운트 | 정확히 1회 | 1회 | PASS | DEC-026 의도대로 단일 워커로 기동됨을 실측 확인 |
| TC-012 | 빌드 재현성(동일 커밋/소스 재빌드 시 동일 산출물) | TC-001 완료 | 동일 소스로 `docker build --no-cache` 독립 재빌드 후 `pip freeze`, `collectstatic` 결과 비교 | 완전 동일 | `pip freeze` diff 없음(`PIP_FREEZE_IDENTICAL`), `collectstatic` 결과 두 빌드 모두 `218 static files copied... 638 post-processed` 동일 | PASS | `requirements.txt` 버전 고정(DEC-006/008/010 등)이 실제로 재현성을 보장함을 실증 |
| TC-013 | 백업 워크플로 `pg_dump` 버전 호환성 실측 | TC-002, `postgresql-client`(apt, v15.19) vs DB서버(v16.14) | 워크플로와 동일 플래그로 `pg_dump` 실행 | (검증 대상) | `pg_dump: error: aborting because of server version mismatch` — **100% 실패 재현** | **관찰됨 — DEF-10-03** | BACKUP_RESTORE_GUIDE.md §6 항목2가 "확인 필요"로 남겼던 리스크가 실제로 발생함을 최초 실증 |
| TC-014 | 백업 파이프라인(버전 일치 클라이언트) 전체 재현: pg_dump→gzip→R2 업로드→head-object | TC-013 실패를 우회해 서버와 동일한 `pg_dump`(v16.14, `db` 컨테이너 자체) 사용 | 워크플로 스텝 그대로 실행 | 성공, 시드 데이터 포함 | `size=29774 bytes`, 덤프 안에 `wu10-backup-probe`(2회)/`probe@example.com`(1회) 포함 확인. MinIO 업로드 `ContentLength: 29774`(무결성 일치) | PASS | 버전만 맞으면 나머지 백업 로직(`--no-owner --no-privileges --clean --if-exists`)은 정상 동작 |
| TC-015 | R2 Object Lifecycle(14일 만료) 규칙 실제 API 호출(DEC-033) | TC-014 | `put_bucket_lifecycle_configuration`(워크플로와 동일 JSON) 호출 후 `get_bucket_lifecycle_configuration`로 재확인 | 성공, 설정값 일치 | `Expiration: 14 Days`, `Prefix: db-backups/`, `Status: Enabled` 그대로 반영 확인 | PASS | BACKUP_RESTORE_GUIDE.md §6 항목3("실제 자격증명으로 호출 검증 못함") 최초 실증(S3 호환 API 기준) |
| TC-016 | **재난복구 리허설**(BACKUP_RESTORE_GUIDE.md §6 항목5 권고 이행) | TC-014 백업 파일 | 신규 빈 DB(`restoretest`) 생성 → R2에서 백업 재다운로드 → `psql -f`로 복구 | 복구 성공, 원본 데이터 확인 가능 | `psql` exit code 0, 에러 로그 없음(`grep -iE "error|fatal"` 결과 없음), 복구된 DB에서 `wu10-backup-probe` 게시물과 `probe@example.com` 구독자 데이터 모두 조회 성공 | PASS | REQ-013(백업정책)의 실제 "복구까지" 왕복 검증은 이번이 최초 |
| TC-017 | **코드 롤백 리허설** — 직전 커밋(DEF-09-01 수정 이전)으로 재기동 | 동일 스테이징 DB(마이그레이션 상태 유지) | `git archive HEAD`(round-2 이전)로 별도 이미지 빌드 후 같은 DB에 연결해 `build.sh` 재실행 | 마이그레이션 충돌 없이 정상 기동 | `No migrations to apply.`(스키마 변경 없음 확인), `슈퍼유저가 이미 존재합니다. 건너뜁니다.`(ensure_superuser 멱등성 확인), gunicorn 정상 기동 | PASS | round-2(DEF-09-01 수정)는 마이그레이션 파일 변경이 전혀 없음(코드 diff로도 재확인, §6-2)을 실기동으로도 재확인 — Render "이전 배포로 롤백"이 스키마 붕괴를 일으키지 않음을 실증 |
| TC-018 | 롤백된 버전에서 관리자 로그인 무차별대입 방어 재현 여부 | TC-017 | 롤백된 컨테이너의 `/django-admin/login/`에 동일 IP로 11회 연속 잘못된 로그인 POST | (검증 대상) | 11회 전부 `200`(429 없음) — **DEF-09-01 취약점 재현됨** | **관찰됨 — DEF-10-04(문서화 격차)** | 코드 롤백 자체는 스키마 안전하지만, "직전 배포"가 보안수정 이전 버전이면 그 수정이 조용히 사라진다는 사실이 어떤 운영 문서에도 명시되어 있지 않음(§6) |
| TC-019 | `git archive`/체크아웃 시 셸 스크립트 줄바꿈 안전성 | Windows, `core.autocrlf=true`(로컬 git 설정 실측 확인), `.gitattributes` 부재 확인 | `git archive HEAD -- webapp`로 추출한 `build.sh` 실행 | 정상 실행 | `/usr/bin/env: 'bash\r': No such file or directory`(CRLF로 셔뱅 손상, 셸 스크립트 실행 자체가 불가능) — `sed 's/\r$//'`로 우회 후에야 TC-017 진행 가능했음 | **관찰됨 — DEF-10-05** | Render 실제 배포는 Linux 러너에서 clone하므로 직접 영향 가능성은 낮으나(§6에서 근거 설명), 이 프로젝트의 반복된 "Windows 로컬 제약" 이력을 고려하면 재발 가능성이 높은 구조적 공백 |
| TC-020 | GitHub Actions 워크플로 위치/트리거 조건 확인 | - | `.github/workflows/neon-db-backup.yml` 경로 확인, `on:` 블록 검사 | 올바른 위치, `schedule` + `workflow_dispatch` 존재 | `.github/workflows/neon-db-backup.yml`(정확한 표준 경로), `on.schedule`(`cron: "0 18 * * *"`) + `on.workflow_dispatch.inputs.reason` 확인 | PASS | 실제 원격 실행은 규칙(push 금지)상 수행 안 함 — 문법은 6/7단계 actionlint로 기검증되어 반복 안 함(규칙B) |
| TC-021 | 마이그레이션 순서/되돌리기 가능 여부(round-2 diff 범위) | - | `git diff --stat HEAD -- webapp/` | round-2 변경분에 마이그레이션 파일 없음 | `ADMIN_ACCESS_GUIDE.md`/`config/urls.py`/`core/admin_auth.py`/`core/tests.py` 4개 파일만 변경, `*/migrations/*` 0건 | PASS | TC-017의 "No migrations to apply." 결과와 상호 확인됨 |
| TC-022 | 규칙K 사전/사후 점검 | - | `automation/harness-janitor.sh --check` 세션 시작 전/정리 후 각 1회 | 두 번 다 "잔여물 없음" | 시작 전: `이상 없음`. 정리 후: `이상 없음` | PASS | §7 참고 |

> 정상 경로뿐 아니라 경계값(TC-006/007 레이트리밋 경계), 예외 입력(TC-008 강제 500), 신뢰 경계(TC-004 프록시 헤더 유무), 버전 비호환(TC-013), 인코딩/줄바꿈(TC-019) 등 위험 케이스를 포함했다(규칙C).

## 5. 커버리지

- **커버리지 지표**: 오케스트레이터가 이번 단계에 명시적으로 지목한 6개 중점 영역(gunicorn 실기동/`build.sh` 전체 실행/`render.yaml` 대조/롤백 절차/GH Actions 트리거 조건/`.env.example` 일치) **6/6 전부** 실측 완료. `templates/test-report-template.md`가 요구하는 배포 체크리스트(빌드 재현성/환경변수 검증/무중단 배포·헬스체크/롤백 실제 검증/마이그레이션 순서/모니터링·알림 채널 실제 연결)도 **6/6 전부** 실측 수행.
- **커버되지 않은 부분과 사유**:
  1. Render 플랫폼 자체(실제 클라우드 인프라)에서의 기동 — Render 계정/실제 배포는 12단계 전용(규칙E). 이번엔 Docker로 최대한 충실히 재현했으나 "Render라는 특정 PaaS의 헬스체크 프로브 헤더 처리 방식" 같은 플랫폼 고유 동작까지는 확인 불가(§6 DEF-10-01).
  2. 실제 Cloudflare R2/Neon/GitHub Actions 원격 인프라 — 자격증명 미발급(기존 제약 계승). S3 호환 API/SSL Postgres/워크플로 로직은 대체 수단으로 커버했으나 벤더 특유의 엣지 케이스(예: R2의 리전별 지연, Neon의 실제 콜드스타트 특성)는 미확인.
  3. Render의 실제 "무료 인스턴스시간 임박 시 자동 이메일"(03 §7.2 알림 항목2), GitHub Actions 실패 시 자동 이메일(항목3), Render 빌드 실패 알림(항목4) — 전부 플랫폼이 트리거하는 알림으로, 로컬 재현이 원천적으로 불가능하다(실제 계정에서 조건을 유발해야 함). 11단계 Runbook에 "최초 배포 후 실제로 한 번 확인" 항목으로 인계.

## 6. 결함(Defect) 목록

| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| DEF-10-01 | `/healthz`가 `X-Forwarded-Proto: https` 헤더 없이 요청되면 `SECURE_SSL_REDIRECT=True`에 의해 301로 리다이렉트된다(TC-004). 이 동작 자체는 WU-08 통합테스트(IT-11)가 이미 "의도된 동작"으로 PASS 확정한 것과 동일하다 — **새로운 버그가 아니라, 이 의도된 동작이 Render의 실제 헬스체크 프로브 요청 방식에 의존한다는 사실이 어느 단계에서도 명시적으로 검증되지 않았다는 것이 이번에 새로 드러난 점**이다. Render의 zero-downtime 배포는 `healthCheckPath`가 200을 반환해야 신규 인스턴스로 트래픽을 전환하는데, 만약 Render의 헬스체크 프로브가 (일반 사용자 트래픽과 달리) TLS-종료 엣지를 거치지 않고 인스턴스에 직접 HTTP로 접속하며 `X-Forwarded-Proto` 헤더를 붙이지 않는다면, 이 서비스는 **최초 배포부터 헬스체크를 영원히 통과하지 못해 배포 자체가 막힐 수 있다.** | TC-004(§4) | **High** | Open — 코드 수정은 5단계(개발) 소관, 근본원인은 03 §4(`/healthz` 계약, WU-08 소유)와 §5.5.2(HTTPS 강제, WU-01 소유)가 서로를 참조하지 않은 설계 공백(3단계). 이번 10단계는 검증 전담이라 직접 코드를 고치지 않는다 | **12단계 착수 전 필수 조치 권고**: (a) `production.py`에 `SECURE_REDIRECT_EXEMPT = [r"^healthz$"]` 추가(헬스체크는 민감정보 없는 "ok" 응답뿐이라 HTTPS 강제 예외로 인한 보안 손실 없음, 03 §4가 이미 "내부용"으로 분류) — 이러면 Render의 실제 헤더 처리 방식과 무관하게 항상 안전. 또는 (b) Render 공식 문서/지원팀에 헬스체크 프로브의 헤더 처리 방식을 명시적으로 확인. 오케스트레이터 판단으로 규칙F(3+5단계 소범위 재작업) 여부 결정 권고 |
| DEF-10-02 | `.env.example`이 `render.yaml`/`production.py`가 실제로 요구하는 환경변수 목록과 불일치 — `DJANGO_ADMIN_EMAIL`, `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD`, `EMAIL_HOST/HOST_USER/HOST_PASSWORD/PORT/USE_TLS`, `SERVER_EMAIL` 총 10개가 `.env.example`에 없다(`PYTHON_VERSION`은 플랫폼 변수라 제외 대상이 맞음). 코드가 `_require_env`로 강제하지 않아 기동 자체는 막지 않지만, 운영자가 `.env.example`을 "Render 대시보드에 입력할 체크리스트"로 삼을 경우 REQ-012(장애 알림)/DEC-030(최초 슈퍼유저 부트스트랩)에 필요한 값을 빠뜨릴 위험이 크다 | TC-010(§4) | Medium | Open | `.env.example`에 누락 10개 항목 + 설명 주석 추가 권고(5단계 또는 11단계 문서화 시 처리 가능, 코드 로직 변경 없음) |
| DEF-10-03 | 백업 워크플로가 `apt-get install postgresql-client`로 설치하는 클라이언트 버전(현재 Debian 계열 기준 실측 v15.19)이 실제 DB 서버 메이저 버전(테스트 환경 postgres:16.14)보다 낮으면 `pg_dump`가 "server version mismatch"로 **100% 실패**한다(TC-013). BACKUP_RESTORE_GUIDE.md §6 항목2가 이미 "확인 필요"로 남겼던 리스크가 실제로 재현 가능함을 이번에 처음 실증했다. GitHub `ubuntu-latest`가 기본 제공하는 `postgresql-client` 버전이 실제 Neon 프로젝트의 PostgreSQL 서버 버전과 항상 일치한다는 보장이 없다(Neon은 프로젝트 생성 시 PG 메이저 버전을 선택할 수 있고 최신 버전을 계속 릴리스함) | TC-013(§4) | Medium | Open | 워크플로에 Neon 서버 버전에 맞는 `postgresql-client-<N>` 명시적 설치 스텝 추가, 또는 PostgreSQL 공식 APT 저장소(apt.postgresql.org) 사용 권고. **실패 시 GitHub이 기본 기능으로 이메일 알림을 보내므로(03 §7.2) "조용한 실패"는 아님** — 심각도를 Medium으로 제한하는 근거 |
| DEF-10-04 | 코드 롤백(Render "이전 배포로 롤백") 시, 롤백 대상이 DEF-09-01 수정(라운드2) 이전 커밋이면 관리자 로그인 무차별대입 방어가 **조용히 사라진다**(TC-018로 실증). 스키마/마이그레이션 리스크는 없음(TC-017/TC-021로 확인)이나, 이 보안 리트로그레션 가능성이 `BACKUP_RESTORE_GUIDE.md`/03 §7.3(롤백 전략)/`ADMIN_ACCESS_GUIDE.md` 어디에도 명시되어 있지 않다 | TC-017+TC-018(§4) | Low | Open | 11단계 운영 Runbook에 "롤백 실행 전 대상 커밋이 DEC-039~042(관리자 로그인 보안수정) 이후 버전인지 반드시 확인" 경고 추가 권고. **구체적 식별 기준(2차 내부검증에서 보강)**: 롤백 대상 배포에 `webapp/core/admin_auth.py`의 `RateLimitedAdminLoginView` 클래스와 `webapp/config/urls.py`의 `path("django-admin/login/", RateLimitedAdminLoginView.as_view(), ...)` 오버라이드가 존재하는지로 즉시 판별 가능(2026-09-17 라운드2 커밋 이후에만 존재) |
| DEF-10-05 | 저장소에 `.gitattributes`가 없어(확인됨: 파일 부재), 로컬 git 설정이 `core.autocrlf=true`인 Windows 환경(이번 세션 실측 확인)에서 `git archive`/`checkout` 시 `build.sh`의 LF가 CRLF로 변환되어 셔뱅이 깨진다(TC-019로 실제 재현: `env: 'bash\r': No such file or directory`). Render의 실제 빌드는 Linux 러너에서 git clone하므로 직접 영향 가능성은 낮으나(Linux 기본 git은 통상 CRLF 변환을 하지 않음), 이 프로젝트가 WU-01~10 전 구간에서 반복적으로 "Windows 로컬 제약"에 부딪혀 온 이력을 고려하면 다른 기여자/운영자가 Windows에서 로컬 재현을 시도할 때 동일 문제를 반복해서 겪을 것이 확실하다 | TC-019(§4) | Low | Open | `.gitattributes`에 `*.sh text eol=lf` 추가 권고(5단계 또는 11단계 처리 가능, 런타임 동작 영향 없음) |

**결함 요약**: Critical 0건, High 1건(DEF-10-01), Medium 2건(DEF-10-02/03), Low 2건(DEF-10-04/05). Critical/High 결함이 배포 프로세스 자체(빌드/기동/헬스체크/롤백 플러밍)를 근본적으로 막지는 않지만(모든 핵심 배포 절차는 TC-001/002/005/006/007/014/015/016/017/021에서 PASS로 실증됨), DEF-10-01은 "실제 12단계 배포 성공 여부"에 영향을 줄 수 있는 미해결 리스크이므로 아래 §9에서 CONDITIONAL PASS로 판정한다.

## 7. 테스트 환경 정리(Teardown) 확인 — 규칙 K

- **이번 테스트에서 생성한 임시 아티팩트 목록**:
  - `webapp/.harness-tmp/deploy-staging/`(Dockerfile, Dockerfile.postgres, Dockerfile.rollback, docker-compose.yml) — 메인 스테이징 스택
  - `webapp/.harness-tmp/rollback-rehearsal/`(docker-compose.rollback.yml + `git archive`로 추출한 임시 소스 사본) — 롤백 리허설 전용
  - Docker 리소스(컨테이너 6개, 이미지 4개, 네트워크 1개, 볼륨) — 저장소 파일이 아니라 Docker 엔진 내부 상태이므로 규칙K의 "저장소에 남는 파일 산출물"에는 해당하지 않으나, 동일한 정리 원칙을 적용해 전부 제거했다
- **위 아티팩트를 전부 `.harness-tmp/` 하위에서만 생성했는가(규칙 K 1번)**: [x] 예
- **정리(삭제) 완료 여부**: 완료. `docker compose down -v` × 2(스테이징/롤백 스택), `docker rmi`로 빌드 이미지 4종 삭제, `docker network prune -f`, `rm -rf webapp/.harness-tmp/deploy-staging webapp/.harness-tmp/rollback-rehearsal` 실행 완료. 이후 `automation/harness-janitor.sh --check` 재실행 결과 `.harness-tmp/ 는 비어있거나 없습니다 — 이상 없음` / `잔여 임시 아티팩트 없음` 확인.
- **정리 후 `git status` 실행 결과(그대로 첨부)**:

```
 M docs/harness/03-system-design.md
 M docs/harness/decisions.md
 M docs/harness/feature-WU-09-integration-test.md
 M docs/harness/feature-WU-10-integration-test.md
 M docs/harness/traceability.md
 M docs/harness/units/unit-09-note.md
 M docs/harness/units/unit-09-test.md
 M docs/harness/units/verify-log_unit-09-test.md
 M docs/harness/verify-log_03-system-design.md
 M docs/harness/verify-log_feature-WU-09-integration-test.md
 M webapp/ADMIN_ACCESS_GUIDE.md
 M webapp/config/urls.py
 M webapp/core/admin_auth.py
 M webapp/core/tests.py
?? docs/harness/08-full-system-test.md
?? docs/harness/09-security-audit.md
?? docs/harness/verify-log_08-full-system-test.md
?? docs/harness/verify-log_09-security-audit.md
?? docs/harness/verify-log_feature-WU-10-integration-test.md
```

  (참고: 이 목록은 세션 시작 시점 스냅샷과 완전히 동일하다 — 이번 10단계 작업으로 인한 신규 변경/잔여물이 0건임을 확인. `git diff --cached --stat` 결과도 비어 있어 스테이징 영역 오염 없음을 재확인했다. `git add`/`commit`/`push`는 전혀 실행하지 않았다.)

- **이번 테스트 도중 강제 중단(TaskStop 등)이 있었는가**: [x] 없음
- 이 절의 정리 확인이 완료되었으므로 §9 PASS/CONDITIONAL PASS 판정의 전제조건을 충족한다(규칙 K 2번).

## 8. 리스크 및 잔존 이슈

- **DEF-10-01(§6)이 미해결 상태로 12단계에 진입할 경우**: 최초 배포 자체가 영구히 헬스체크 실패로 막힐 수 있는 잠재 리스크. Render의 zero-downtime 배포 특성상 "이미 떠 있는 이전 버전이 있는 재배포"라면 기존 인스턴스가 계속 트래픽을 받아 **다운타임은 발생하지 않지만**, 신규 배포 자체가 계속 실패해 어떤 코드 변경도 반영되지 않는 상태에 빠질 수 있다. 특히 **이 서비스의 최초(첫) 배포**는 "이전 버전"이 아예 없으므로 이 경우 사이트가 아예 뜨지 못하는 것과 동일한 결과가 된다.
- **실제 Render/Neon/R2/GitHub Actions 계정이 아직 없다**: 이번 10단계의 모든 실측은 로컬 Docker 재현이며, 실제 클라우드 벤더 특유의 동작(정확한 지연시간, 실제 콜드스타트 프로파일, 실제 무료 티어 한도 도달 시나리오)은 12단계(실배포) 이후에만 관측 가능하다 — 03 §7.2가 이미 명시한 3개 플랫폼 자동 알림 항목(Render 사용량/GitHub 실패/Render 빌드실패)도 마찬가지.
- **DEF-10-03(pg_dump 버전 불일치) 미해결 시**: 실제 Neon 프로젝트의 PostgreSQL 서버 버전이 GitHub `ubuntu-latest`의 기본 `postgresql-client` 버전보다 높으면 백업이 매일 100% 실패한다. 다행히 실패는 "조용하지" 않다(GitHub 이메일 알림, 03 §7.2) — 하지만 알림을 인지하고도 수정 전까지는 REQ-013(백업정책)의 목적이 실질적으로 무력화된다.
- **DEF-10-04/05(§6)**: 둘 다 Low지만 운영 연속성(롤백 시 보안 리스크 인지)과 재현성(Windows 기여자 반복 실패)에 영향을 주므로 11단계 Runbook에 반드시 반영 권고.
- **DEC-038이 이미 이관한 항목**(KPI 애널리틱스/FAQ 비율 자동집계 도구 도입 여부)은 이번 10단계 범위가 아니며 그대로 11단계로 승계한다.

## 9. 결론 및 판정

- [ ] PASS
- [x] **CONDITIONAL PASS** — 조건:
  1. **(12단계 착수 전 필수)** DEF-10-01 해소: `production.py`에 `/healthz` HTTPS 강제 예외 추가(권고안 §6 참고) 또는 Render 공식 채널을 통한 헬스체크 헤더 처리 방식 확인. 둘 중 하나 없이 12단계(실배포) 착수 시 최초 배포가 영구히 실패할 수 있는 리스크를 사용자가 인지한 상태에서 승인해야 한다(규칙E).
  2. **(12단계 착수 전 필수)** DEF-10-03 해소 또는 완화: 백업 워크플로에 Neon 서버 버전 대응 `postgresql-client` 설치 스텝 보강, 또는 최초 배포 후 실제 Neon 서버 버전을 확인해 워크플로를 조정.
  3. (권고, 비차단) DEF-10-02/04/05는 11단계 운영 Runbook에 명시적으로 반영.
- [ ] FAIL

**판정 근거**: 빌드/기동/헬스체크(정상 경로)/관리자 인증 보안수정/장애 알림/R2 스토리지/백업/복구/롤백(스키마 안전성)이라는 배포 파이프라인의 핵심 절차는 전부 실제 도구로 실측 PASS했다(§4, Critical 결함 0건). 다만 DEF-10-01(High)이 "실제 12단계 배포의 성공 여부" 자체에 영향을 줄 수 있는 미해결 리스크이고, DEF-10-03(Medium)이 REQ-013(백업정책)을 무력화할 수 있는 재현 가능한 실패 시나리오이므로, 이 두 가지를 확인/해소하지 않은 채로 "완전한 PASS"로 넘기는 것은 20년차 운영자 관점에서 무책임하다고 판단했다(CLAUDE.md 페르소나: "롤백이 되지 않는 배포는 배포가 아니라 도박"과 동일한 원칙을 "헬스체크가 통과 못 하는 배포도 배포가 아니라 도박"에 적용). **11단계(문서화/인수인계)로는 그대로 handoff 가능**하다 — 11단계는 이 결과서와 조건을 있는 그대로 Runbook에 반영하는 것이 역할이며, 12단계(실배포, 사용자 승인 필요)만 위 조건 충족을 전제로 진행해야 한다.

## 10. 내부 검증 (최소 2회)

- 1차 검증 결과 요약: 체크리스트(빌드 재현성/환경변수·시크릿/무중단·헬스체크/롤백 실제 실행/마이그레이션 순서/모니터링·알림 채널 실제 연결) 6개 항목 전부 실측 수행 여부 확인 — 6/6 완료. DEF-10-01의 심각도 표기(Critical→High로 하향 조정, 근거: zero-downtime 배포 특성상 기존 서비스 다운타임을 유발하지 않음)를 1차 검증에서 재조정했다.
- 2차 검증 결과 요약: "실제 배포 당일 새벽에 문제가 생기면 이 문서만 보고 롤백할 수 있는가" 관점에서 재검토 — §6 DEF-10-04/TC-017/TC-018이 "코드 롤백은 스키마 안전하지만 보안수정을 되돌릴 수 있다"는 사실을 명시적으로 남겨, 새벽 온콜 담당자가 이 문서만 보고도 "롤백해도 되는지/롤백 후 무엇을 해야 하는지"를 판단할 수 있음을 확인. §7 Teardown의 `git status` 전체 첨부가 요약 없이 그대로 포함되어 있음을 재확인.
- 검증 로그 파일 경로: `docs/harness/verify-log_10-deploy-test.md`
