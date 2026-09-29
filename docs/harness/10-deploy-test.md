# 10단계 — 배포테스트 결과서

- 문서 버전: v1.0 (본문) + 재검증 addendum(§11, 2026-09-25) + 재검증 addendum(§13/§14, 2026-09-28)
- 작성 일시(KST): 20260918 013454
- 작성 에이전트: 10-deploy-tester

> **최종 판정 갱신(규칙F 재작업, 2026-09-25)**: 아래 §1~§10(원본, 2026-09-18 작성)은 **CONDITIONAL PASS**로 판정했다 — 12단계 착수 전 필수 조건 2건(DEF-10-01 High, DEF-10-03 Medium)이 미해결이었기 때문이다. 이후 규칙F 재작업(05단계 WU-01/WU-10 라운드2, DEC-044, `unit-01-note.md` §0-2/§4-2, `unit-10-note.md` §10, `03-system-design.md` v1.4)이 두 조건을 모두 해소했고, **이 문서 맨 아래 §11 "재검증(규칙F 재작업)"이 그 재작업의 최종 확인 단계로서 독립적으로 재검증**했다. 결론: **DEF-10-01/DEF-10-03 Fixed 확인, 신규 결함 없음 → 최종 판정 PASS로 갱신**(§9 조건 3번 DEF-10-02/04/05는 원래도 비차단이며 11단계 Runbook 반영 권고로 그대로 승계). 원본 §1~§10은 최초 작성 당시 기록 그대로 보존하며(수정하지 않음), 최신 판정 근거는 §11을 따른다.

> **[2026-09-28 추가] 재검증 addendum (§13/§14) - comments/adsense/spam-defense 반영 - CONDITIONAL PASS**: §1~§12(WU-01~10 범위) PASS 확정 이후 추가된 comments(REQ-019)/adsense_client_id(REQ-023)/댓글 스팸차단(DEC-055) 3개 기능을 배포 파이프라인 관점(10단계 고유 책임)에서 재검증했다. 결과: Critical 결함 1건(DEF-10-06 - legal 신규 데이터 마이그레이션이 실제 Postgres에서 migrate 전체를 크래시시킴, 12단계 착수 전 필수 해결) + Low 1건(DEF-10-07, 비차단) 발견. §1~§12는 원문 그대로 보존하며 최신 addendum 판정은 §13.10/§14를 따른다.


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
| DEF-10-01 | `/healthz`가 `X-Forwarded-Proto: https` 헤더 없이 요청되면 `SECURE_SSL_REDIRECT=True`에 의해 301로 리다이렉트된다(TC-004). 이 동작 자체는 WU-08 통합테스트(IT-11)가 이미 "의도된 동작"으로 PASS 확정한 것과 동일하다 — **새로운 버그가 아니라, 이 의도된 동작이 Render의 실제 헬스체크 프로브 요청 방식에 의존한다는 사실이 어느 단계에서도 명시적으로 검증되지 않았다는 것이 이번에 새로 드러난 점**이다. Render의 zero-downtime 배포는 `healthCheckPath`가 200을 반환해야 신규 인스턴스로 트래픽을 전환하는데, 만약 Render의 헬스체크 프로브가 (일반 사용자 트래픽과 달리) TLS-종료 엣지를 거치지 않고 인스턴스에 직접 HTTP로 접속하며 `X-Forwarded-Proto` 헤더를 붙이지 않는다면, 이 서비스는 **최초 배포부터 헬스체크를 영원히 통과하지 못해 배포 자체가 막힐 수 있다.** | TC-004(§4) | **High** | **Fixed (2026-09-25, §11 재검증 참고)** — ~~Open~~. 근본원인은 03 §4(`/healthz` 계약, WU-08 소유)와 §5.5.2(HTTPS 강제, WU-01 소유)가 서로를 참조하지 않은 설계 공백(3단계) | **12단계 착수 전 필수 조치 권고**: (a) `production.py`에 `SECURE_REDIRECT_EXEMPT = [r"^healthz$"]` 추가(헬스체크는 민감정보 없는 "ok" 응답뿐이라 HTTPS 강제 예외로 인한 보안 손실 없음, 03 §4가 이미 "내부용"으로 분류) — 이러면 Render의 실제 헤더 처리 방식과 무관하게 항상 안전. 또는 (b) Render 공식 문서/지원팀에 헬스체크 프로브의 헤더 처리 방식을 명시적으로 확인. 오케스트레이터 판단으로 규칙F(3+5단계 소범위 재작업) 여부 결정 권고. **→ (a) 채택, §11 참고** |
| DEF-10-02 | `.env.example`이 `render.yaml`/`production.py`가 실제로 요구하는 환경변수 목록과 불일치 — `DJANGO_ADMIN_EMAIL`, `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD`, `EMAIL_HOST/HOST_USER/HOST_PASSWORD/PORT/USE_TLS`, `SERVER_EMAIL` 총 10개가 `.env.example`에 없다(`PYTHON_VERSION`은 플랫폼 변수라 제외 대상이 맞음). 코드가 `_require_env`로 강제하지 않아 기동 자체는 막지 않지만, 운영자가 `.env.example`을 "Render 대시보드에 입력할 체크리스트"로 삼을 경우 REQ-012(장애 알림)/DEC-030(최초 슈퍼유저 부트스트랩)에 필요한 값을 빠뜨릴 위험이 크다 | TC-010(§4) | Medium | Open | `.env.example`에 누락 10개 항목 + 설명 주석 추가 권고(5단계 또는 11단계 문서화 시 처리 가능, 코드 로직 변경 없음) |
| DEF-10-03 | 백업 워크플로가 `apt-get install postgresql-client`로 설치하는 클라이언트 버전(현재 Debian 계열 기준 실측 v15.19)이 실제 DB 서버 메이저 버전(테스트 환경 postgres:16.14)보다 낮으면 `pg_dump`가 "server version mismatch"로 **100% 실패**한다(TC-013). BACKUP_RESTORE_GUIDE.md §6 항목2가 이미 "확인 필요"로 남겼던 리스크가 실제로 재현 가능함을 이번에 처음 실증했다. GitHub `ubuntu-latest`가 기본 제공하는 `postgresql-client` 버전이 실제 Neon 프로젝트의 PostgreSQL 서버 버전과 항상 일치한다는 보장이 없다(Neon은 프로젝트 생성 시 PG 메이저 버전을 선택할 수 있고 최신 버전을 계속 릴리스함) | TC-013(§4) | Medium | **Fixed (2026-09-25, §11 재검증 참고)** — ~~Open~~ | 워크플로에 Neon 서버 버전에 맞는 `postgresql-client-<N>` 명시적 설치 스텝 추가, 또는 PostgreSQL 공식 APT 저장소(apt.postgresql.org) 사용 권고. **실패 시 GitHub이 기본 기능으로 이메일 알림을 보내므로(03 §7.2) "조용한 실패"는 아님** — 심각도를 Medium으로 제한하는 근거. **→ PGDG 저장소 방식 채택, §11 참고** |
| DEF-10-04 | 코드 롤백(Render "이전 배포로 롤백") 시, 롤백 대상이 DEF-09-01 수정(라운드2) 이전 커밋이면 관리자 로그인 무차별대입 방어가 **조용히 사라진다**(TC-018로 실증). 스키마/마이그레이션 리스크는 없음(TC-017/TC-021로 확인)이나, 이 보안 리트로그레션 가능성이 `BACKUP_RESTORE_GUIDE.md`/03 §7.3(롤백 전략)/`ADMIN_ACCESS_GUIDE.md` 어디에도 명시되어 있지 않다 | TC-017+TC-018(§4) | Low | Open | 11단계 운영 Runbook에 "롤백 실행 전 대상 커밋이 DEC-039~042(관리자 로그인 보안수정) 이후 버전인지 반드시 확인" 경고 추가 권고. **구체적 식별 기준(2차 내부검증에서 보강)**: 롤백 대상 배포에 `webapp/core/admin_auth.py`의 `RateLimitedAdminLoginView` 클래스와 `webapp/config/urls.py`의 `path("django-admin/login/", RateLimitedAdminLoginView.as_view(), ...)` 오버라이드가 존재하는지로 즉시 판별 가능(2026-09-17 라운드2 커밋 이후에만 존재) |
| DEF-10-05 | 저장소에 `.gitattributes`가 없어(확인됨: 파일 부재), 로컬 git 설정이 `core.autocrlf=true`인 Windows 환경(이번 세션 실측 확인)에서 `git archive`/`checkout` 시 `build.sh`의 LF가 CRLF로 변환되어 셔뱅이 깨진다(TC-019로 실제 재현: `env: 'bash\r': No such file or directory`). Render의 실제 빌드는 Linux 러너에서 git clone하므로 직접 영향 가능성은 낮으나(Linux 기본 git은 통상 CRLF 변환을 하지 않음), 이 프로젝트가 WU-01~10 전 구간에서 반복적으로 "Windows 로컬 제약"에 부딪혀 온 이력을 고려하면 다른 기여자/운영자가 Windows에서 로컬 재현을 시도할 때 동일 문제를 반복해서 겪을 것이 확실하다 | TC-019(§4) | Low | **Fixed (2026-09-25)** — ~~Open~~ | `.gitattributes`에 `*.sh text eol=lf` 추가 권고(5단계 또는 11단계 처리 가능, 런타임 동작 영향 없음). **→ 채택, 저장소 루트에 `.gitattributes` 생성 완료. `git check-attr eol -- webapp/build.sh` → `eol: lf` 확인** |

**결함 요약(원본, 2026-09-18)**: Critical 0건, High 1건(DEF-10-01), Medium 2건(DEF-10-02/03), Low 2건(DEF-10-04/05). Critical/High 결함이 배포 프로세스 자체(빌드/기동/헬스체크/롤백 플러밍)를 근본적으로 막지는 않지만(모든 핵심 배포 절차는 TC-001/002/005/006/007/014/015/016/017/021에서 PASS로 실증됨), DEF-10-01은 "실제 12단계 배포 성공 여부"에 영향을 줄 수 있는 미해결 리스크이므로 아래 §9에서 CONDITIONAL PASS로 판정한다.

**결함 요약 갱신(§11 재검증, 2026-09-25)**: DEF-10-01(High)·DEF-10-03(Medium) **Fixed**. 잔존 Open: DEF-10-02(Medium)·DEF-10-04/05(Low) — 전부 비차단, 11단계 Runbook 반영 권고(§9 갱신 조건 참고).

**결함 요약 재갱신(추가 검토 라운드, 2026-09-25)**: DEF-10-02(`.env.example`)·DEF-10-05(`.gitattributes`) 추가 **Fixed**. 잔존 Open: DEF-10-04(Low, 문서 경고로 대응 완료·코드 조치 불필요 항목).

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

## 9. 결론 및 판정 (원본, 2026-09-18 — §11 갱신 전)

- [ ] PASS
- [x] **CONDITIONAL PASS** — 조건:
  1. **(12단계 착수 전 필수)** DEF-10-01 해소: `production.py`에 `/healthz` HTTPS 강제 예외 추가(권고안 §6 참고) 또는 Render 공식 채널을 통한 헬스체크 헤더 처리 방식 확인. 둘 중 하나 없이 12단계(실배포) 착수 시 최초 배포가 영구히 실패할 수 있는 리스크를 사용자가 인지한 상태에서 승인해야 한다(규칙E).
  2. **(12단계 착수 전 필수)** DEF-10-03 해소 또는 완화: 백업 워크플로에 Neon 서버 버전 대응 `postgresql-client` 설치 스텝 보강, 또는 최초 배포 후 실제 Neon 서버 버전을 확인해 워크플로를 조정.
  3. (권고, 비차단) DEF-10-02/04/05는 11단계 운영 Runbook에 명시적으로 반영.
- [ ] FAIL

**판정 근거**: 빌드/기동/헬스체크(정상 경로)/관리자 인증 보안수정/장애 알림/R2 스토리지/백업/복구/롤백(스키마 안전성)이라는 배포 파이프라인의 핵심 절차는 전부 실제 도구로 실측 PASS했다(§4, Critical 결함 0건). 다만 DEF-10-01(High)이 "실제 12단계 배포의 성공 여부" 자체에 영향을 줄 수 있는 미해결 리스크이고, DEF-10-03(Medium)이 REQ-013(백업정책)을 무력화할 수 있는 재현 가능한 실패 시나리오이므로, 이 두 가지를 확인/해소하지 않은 채로 "완전한 PASS"로 넘기는 것은 20년차 운영자 관점에서 무책임하다고 판단했다(CLAUDE.md 페르소나: "롤백이 되지 않는 배포는 배포가 아니라 도박"과 동일한 원칙을 "헬스체크가 통과 못 하는 배포도 배포가 아니라 도박"에 적용). **11단계(문서화/인수인계)로는 그대로 handoff 가능**하다 — 11단계는 이 결과서와 조건을 있는 그대로 Runbook에 반영하는 것이 역할이며, 12단계(실배포, 사용자 승인 필요)만 위 조건 충족을 전제로 진행해야 한다.

## 9-1. 결론 및 판정 갱신 (§11 재검증, 2026-09-25)

- [x] **PASS**
- [ ] CONDITIONAL PASS
- [ ] FAIL

**판정 근거**: 위 §9 조건 1·2(DEF-10-01/DEF-10-03, 12단계 착수 전 필수)가 §11의 독립 재검증으로 모두 **Fixed** 확인되었다 — DEF-10-01은 `SECURE_REDIRECT_EXEMPT` 코드와 03 §5.5.2-1(v1.4) 설계 근거·회귀 테스트(`HealthzHttpsRedirectExemptTests` 3케이스)가 갖춰졌고, DEF-10-03은 PGDG 기반 워크플로 수정이 "구버전 client+신버전 server" 실패 재현 후 해소됨을 Docker로 직접 실증했다. 조건 3(DEF-10-02/04/05, 비차단)은 원래도 12단계 착수를 막는 조건이 아니었으며 11단계 Runbook 반영 권고로 그대로 승계한다. **12단계(실배포) 착수 전 필수 조건이 모두 해소되었으므로, 이 시점부터는 CONDITIONAL PASS가 아니라 정식 PASS로 취급한다.** 단, §8의 잔존 리스크(실제 Render/Neon/R2/GitHub Actions 계정 부재로 인한 벤더 특유 동작 미검증)는 12단계 실배포 이후에만 관측 가능하다는 원본 판단이 여전히 유효하며, 이 PASS가 "12단계 이후 어떤 문제도 없다"는 보증은 아니다.

## 10. 내부 검증 (최소 2회)

- 1차 검증 결과 요약: 체크리스트(빌드 재현성/환경변수·시크릿/무중단·헬스체크/롤백 실제 실행/마이그레이션 순서/모니터링·알림 채널 실제 연결) 6개 항목 전부 실측 수행 여부 확인 — 6/6 완료. DEF-10-01의 심각도 표기(Critical→High로 하향 조정, 근거: zero-downtime 배포 특성상 기존 서비스 다운타임을 유발하지 않음)를 1차 검증에서 재조정했다.
- 2차 검증 결과 요약: "실제 배포 당일 새벽에 문제가 생기면 이 문서만 보고 롤백할 수 있는가" 관점에서 재검토 — §6 DEF-10-04/TC-017/TC-018이 "코드 롤백은 스키마 안전하지만 보안수정을 되돌릴 수 있다"는 사실을 명시적으로 남겨, 새벽 온콜 담당자가 이 문서만 보고도 "롤백해도 되는지/롤백 후 무엇을 해야 하는지"를 판단할 수 있음을 확인. §7 Teardown의 `git status` 전체 첨부가 요약 없이 그대로 포함되어 있음을 재확인.
- 검증 로그 파일 경로: `docs/harness/verify-log_10-deploy-test.md`

---

## 11. 재검증 (규칙F 재작업 — DEF-10-01/DEF-10-03 해소, 2026-09-25)

- **트리거**: 사용자 지시("10단계 CONDITIONAL PASS 조건 1·2를 5단계에서 처리한 뒤 11단계로 진행") + DEC-044.
- **DEF-10-01 재검증**:
  - `webapp/config/settings/production.py` 77행에 `SECURE_REDIRECT_EXEMPT = [r"^healthz$"]`가 이미 존재함을 `git blame`(커밋 `bcc17a2d7`, 2026-09-18)으로 직접 확인 — 이 코드는 원본 §4 TC-004 실행 당시와 동일한 상태였다(즉 원본 TC-004는 이 예외가 없던 구코드가 아니라, 예외가 있었는데도 당시 결과서가 "Open"으로 남겨둔 하네스 기록 공백이었을 가능성과, 이후 별도 세션이 코드만 고치고 기록을 갱신하지 않았을 가능성 두 가지가 있으나, **어느 쪽이든 지금 시점의 정확한 상태를 실측으로 재확인하는 것이 이 재검증의 목적**이므로 원인 구분 자체는 판정에 영향을 주지 않는다).
  - 05단계(WU-01) 라운드2가 추가한 `core.tests.HealthzHttpsRedirectExemptTests`(3케이스)를 `webapp/.harness-tmp/venv_05_def10fix`(임시 venv, 규칙K 준수, 검증 후 삭제)에서 `manage.py test`로 실행 — 3케이스 전부 PASS(§4-2 unit-01-note.md 인용). 전체 회귀(`manage.py test`, 38케이스) OK, `manage.py check` 이상 없음.
  - **TC-004 등가 재현**: 이번 재검증은 05단계가 확보한 단위테스트 증거(override_settings + Client()로 `SecurityMiddleware`가 실제로 이 설정을 반영함을 실측)를 10단계 관점("Render 헬스체크 프로브가 헤더 없이 직접 접속하는 시나리오와 동일한가")에서 재검토했다 — `SECURE_REDIRECT_EXEMPT`는 Django `SecurityMiddleware`가 프록시 헤더 유무와 무관하게 요청 경로만으로 판단하는 설정이므로, 단위테스트 수준의 검증이 TC-004가 원래 재현했던 "헤더 없는 직접 요청" 조건과 기술적으로 동일하다(Django 소스 로직상 경로 매칭이 `is_secure()` 판단보다 먼저 이루어짐, §5.5.2-1 서술과 일치). 실제 gunicorn 컨테이너를 다시 띄워 TC-004를 문자 그대로 반복 실행하지 않은 이유: 원본 §4가 이미 같은 컨테이너 스택(TC-001~003)에서 gunicorn 기동 자체를 검증했고, 이번 변경은 미들웨어 설정 하나이며 WSGI/ASGI 서버 계층과 무관하므로 실서버 재기동이 새로운 정보를 주지 않는다고 판단(규칙B "레이어별 책임 분리", 과잉 반복 지양) — 판정: **Fixed**.
- **DEF-10-03 재검증**:
  - `.github/workflows/neon-db-backup.yml`의 client 설치 스텝을 PGDG 방식으로 교체(unit-10-note.md §10 참고).
  - **Docker로 원본 TC-013/014와 동일한 서버/클라이언트 버전 역전 조건을 재현**: `postgres:17`(서버) + `ubuntu:24.04`(GitHub `ubuntu-latest` 등가) 컨테이너를 전용 네트워크로 연결 → 수정 전 스텝 그대로 실행 시 `pg_dump 16.15`가 설치되고, 이 클라이언트로 `postgres:17`에 접속하면 원본 결함이 서술한 그대로 **`pg_dump: error: aborting because of server version mismatch`(종료코드 1)**가 재현됨을 먼저 확인(원본 TC-013의 재현성 재확인) → 수정된 스텝 실행 시 `pg_dump 18.6`이 설치되고, 동일 서버에 대해 **덤프가 성공(종료코드 0)**하며 사전 삽입한 프로브 데이터(`wu10-def03-probe`)가 백업 파일 안에 그대로 포함됨을 `zcat | grep`으로 확인. 이는 원본 TC-014(정상 백업 파이프라인 재현)와 동일한 성공 판정 기준(덤프 성공 + 데이터 무결성)을 충족한다 — 판정: **Fixed**.
  - **회귀 확인**: 워크플로의 나머지 6개 스텝(시크릿 사전점검/덤프 크기 확인/R2 lifecycle/업로드/업로드 검증/로컬 정리)은 diff상 전혀 변경되지 않았음을 확인 — 원본 TC-014~016(백업/lifecycle/재난복구 리허설)이 검증한 로직에 영향 없음.
  - **정리(규칙K)**: Docker 컨테이너 3개/네트워크 1개, `.harness-tmp/wu10-def03-verify` 전부 삭제 후 `automation/harness-janitor.sh --check` 재확인 — 잔여물 없음.
- **신규 결함 여부**: 0건. 두 조치 모두 기존 정상 경로(TC-001~012, TC-015~021 등)에 영향을 주지 않음을 diff 검토와 회귀 테스트로 확인했다.
- **11단계 handoff 판정**: 위 §9-1 참고 — **PASS**. 12단계(실배포, 사용자 승인 필요) 착수 전 필수 조건 전부 해소.

## 12. 내부 검증 (최소 2회, §11 재작업분)

- 1차 검증(작성자 관점, 2026-09-25): DEF-10-01/DEF-10-03 각각에 대해 "원본 결함이 서술한 정확한 실패 시나리오를 재현했는가, 아니면 다른 것을 검증하고 성공이라 주장하는가"를 재확인 — DEF-10-03은 Docker로 정확히 동일한 버전 역전 조건을 재현 후 수정으로 해소됨을 실측(가장 엄격한 기준 충족). DEF-10-01은 실서버 재기동 대신 단위테스트+로직 동치성 논증으로 대체했음을 위 서술에서 명시적으로 밝혔는지 확인 — 명시됨. 결함 0건.
- 2차 검증(독립 심사자 관점 — "이 문서만 보고 12단계 승인 여부를 판단하는 사용자"의 시각, 2026-09-25): (a) §9-1의 PASS 판정이 §8 리스크(벤더 계정 부재)를 여전히 열어두고 있어 "모든 문제가 사라졌다"는 과장이 없는가 — 명시적으로 "12단계 이후에만 관측 가능"이라고 재확인해 과장 없음. (b) DEF-10-01 재검증이 실서버 재확인을 생략한 근거가 "귀찮아서"가 아니라 "레이어 무관성" 기술적 근거인지 재검토 — `SecurityMiddleware`의 경로 매칭이 WSGI 서버 종류와 무관한 순수 Django 설정 계층 로직임을 재확인, 타당한 생략으로 판정. (c) DEF-10-02/04/05가 조건 3(비차단)에서 빠지지 않고 11단계로 정확히 승계되는 경로가 명시되어 있는가 — §9-1/§6 요약에 명시됨. 결함 0건.
- **최종 판정**: PASS(결함 0건, 2회 검증 완료). 규칙B Standard 원문(최소 2회 고정)에 따라 1차 결함 0건이었음에도 2차를 생략하지 않고 수행했다.
- 검증 로그 파일 경로: `docs/harness/verify-log_10-deploy-test.md`("재작업 addendum" 절, 아래 추가)

---

## 13. 재검증 addendum — comments/adsense/spam-defense 반영 (2026-09-28)

### 13.0 트리거 및 배경
- §1~§12(원본 PASS, 2026-09-18 작성 + 2026-09-25 규칙F 재작업 PASS 갱신) 확정 이후, 아래 3개 기능이 배포 대상 코드에 추가되었다.
  1. `comments` 앱(댓글, REQ-019) — DEC-047/048/052, 08단계·09단계 addendum 각각 PASS.
  2. `adsense_client_id`(애드센스 준비, REQ-023) — DEC-053/054, `core`/`legal` 앱 신규 마이그레이션.
  3. 댓글 스팸 자동/수동 차단(`comments.BlockedIP`, `source_ip_raw`) — DEC-055, 09단계 자체 재적용(DEC-056)에서 SEC-26~29/DEF-09-04로 별도 검증됨.
- 이 addendum은 08/09단계가 이미 검증한 "기능 자체의 정확성/보안"을 재검증하지 않는다. **10단계 고유 책임 범위(빌드 스크립트·배포 환경 재현·환경변수·마이그레이션 체인이 실제 배포 파이프라인에서 깨지지 않는지·롤백 절차)**에 한정한다.
- 규칙B(최소 2회 내부검증)·규칙C(완전한 결과서)·규칙K(임시 아티팩트는 `.harness-tmp/`에만, 정리 후 Teardown 기재)를 그대로 따른다.

### 13.1 테스트 환경 (원본 §3 방식 재사용)
- 원본 §3과 동일한 로컬 Docker 재현 방식을 그대로 재사용했다: `postgres:16-alpine` 자체 빌드(자체서명 인증서로 `ssl=on` 강제, Neon SSL 필수 연결 재현) + `python:3.12.9-slim` 기반 `web`(requirements.txt 그대로 설치, `render.yaml`의 `startCommand` 문자 그대로 실행) + `mailhog`(SMTP 캐처).
- **환경 차이 1건 발견 및 대체 수단 적용**: 원본 §3이 사용한 `quay.io/minio/minio`·`quay.io/minio/mc` 이미지가 이번 세션 시점에는 `401 UNAUTHORIZED`(quay.io 인증 요구)로 pull 불가능했고, `minio/minio`(Docker Hub) 역시 `pull access denied`로 확인됐다(MinIO 프로젝트의 이미지 배포 정책 변경으로 추정, 외부 요인). **대체 판단**: 이번 3개 신규 기능은 R2/S3 오브젝트 스토리지 백엔드 설정을 전혀 건드리지 않는다(DEC-054가 명시적으로 "슬롯 UX 대신 Auto ads 스크립트 한 줄"만 채택, adsense_client_id는 DB 필드일 뿐 스토리지 무관 — 코드로 직접 확인, `core/models.py`/`core/migrations/0003·0004` 어디에도 STORAGES 관련 변경 없음). R2/S3 네트워크 경로 자체는 원본 §4 TC-009/TC-014/TC-015가 이미 실측 검증했고 이번 변경과 무관하므로, MinIO 없이 DB/mailhog만으로 스택을 구성하고 `build.sh`가 실제로 S3에 네트워크 호출을 하지 않음(collectstatic은 whitenoise 로컬 스토리지, migrate/ensure_superuser도 스토리지 미사용)을 코드로 재확인한 뒤, `_require_env`를 만족시키는 더미 R2 값만 채워 진행했다. 이 대체 판단과 사유를 여기 명시적으로 기록한다(규칙C).
- 임시 아티팩트는 `webapp/.harness-tmp/deploy-staging-addendum/`(Dockerfile.postgres/Dockerfile.web/docker-compose.yml/pg_hba_ssl.conf 등) 하위에만 생성했다(규칙K).
- Docker Desktop이 이번 세션 시작 시 실행되어 있지 않아 직접 기동한 뒤(사용자 계정 소유 애플리케이션 실행, 파괴적 동작 아님) 가용성을 확인하고 진행했다.

### 13.2 빌드 재현성
- `docker compose build`로 `web` 이미지를 처음부터(`--no-cache` 아님, 최초 빌드) 성공 확인 — `pip install -r requirements.txt`가 `Django==5.2.17`/`wagtail==7.4.3` 등 기존 고정 버전 그대로 설치되어 재현성이 유지됨을 확인(신규 3개 기능이 `requirements.txt`를 변경하지 않았음을 diff 확인과 일치 — `comments`/`core` adsense/`legal` 신규 마이그레이션 전부 표준 Django/Wagtail API만 사용, 신규 서드파티 패키지 없음).
- **PASS** (기존 TC-012 "동일 소스 재빌드 시 동일 산출물" 원칙에 반하는 변화 없음).

### 13.3 환경변수/시크릿/설정값 검증
- `webapp/render.yaml`·`webapp/.env.example`를 코드와 직접 대조했다.
- **결론: 신규 환경변수 불필요.** 근거:
  - `adsense_client_id`는 `core.SiteSettings`의 **DB 필드**(Wagtail `BaseSiteSetting`)이며 운영자가 Wagtail 어드민(`/cms-admin/settings/core/sitesettings/`)에서 직접 입력하는 값이다(DEC-054) — `render.yaml`/`.env.example`에 새 키를 추가할 필요가 없다.
  - `comments`의 신규 알림(DEC-049)은 **기존 `DJANGO_ADMIN_EMAIL`/`EMAIL_HOST` 등 500-에러 알림과 동일한 채널을 재사용**한다(`comments/notifications.py`가 `mail_admins()` 호출, 신규 설정값 없음) — 코드 직접 확인.
  - `comments.BlockedIP`/`source_ip_raw`(스팸 차단, DEC-055)도 신규 환경변수를 요구하지 않는다(전부 DB 필드·Wagtail 권한 시스템 기반).
- **PASS** — `render.yaml`/`.env.example` 자체를 수정할 필요 없음(DEF-10-02는 원본 §6에서 이미 Fixed 처리된 무관 항목).

### 13.4 마이그레이션 체인 — 실제 배포환경(Postgres) 검증 — **Critical 결함 발견(DEF-10-06)**
- **절차**: 빈 SSL Postgres 16 DB에 `webapp/build.sh`를 컨테이너 안에서 **그대로(무수정)** 실행(`docker compose run --rm web sh -c "./build.sh"`) — `pip install` → `collectstatic` → `migrate` → `ensure_superuser` 순서 그대로.
- **결과**: `collectstatic`(219 static files copied, 641 post-processed)까지는 정상 진행되었고, `migrate`가 `comments.0001~0004`, `core.0001~0004`(adsense 포함), `legal.0001`, `legal.0002`까지는 전부 `OK`로 순조롭게 적용되다가, **`legal.0003_add_comment_privacy_notice`(DEC-055, REQ-019 후속 — 스팸방지 개인정보 문구 갱신) 적용 중 `django.db.utils.InternalError: current transaction is aborted, commands ignored until end of transaction block`로 전체 `migrate` 명령이 비정상 종료(exit 1)**했다. `build.sh`는 `set -o errexit`이므로 여기서 **빌드 자체가 실패로 끝난다**.
- **재현성**: DB를 완전히 초기화(`docker compose down -v` → 재기동)한 뒤 **동일 조건으로 재실행해 100% 동일하게 재현**됨을 확인(2회 독립 실행, 2회 모두 `legal.0003`에서 동일 에러로 크래시).
- **근본 원인 규명(코드/DB 직접 조사로 확정)**:
  1. `psql`로 크래시 직후 DB 상태를 직접 조회 — `legal.0002_create_legal_pages`까지는 **실제로 커밋됨**(3개 LegalPage 정상 생성 확인), `legal.0003`은 `django_migrations`에 기록되지 않음(진짜로 실패), `wagtailsearch_*` 테이블은 **단 하나도 존재하지 않음**(해당 앱 마이그레이션이 아직 실행되지 않은 시점).
  2. `legal`이 `INSTALLED_APPS`(`config/settings/base.py`)에서 `wagtail.search`(app label `wagtailsearch`)보다 훨씬 앞에 위치하고, `legal`의 마이그레이션 어디에도 `wagtailsearch`에 대한 명시적 `dependencies`가 없다 — Django의 마이그레이션 위상정렬이 이 경우 `legal`을 `wagtailsearch`보다 먼저 적용한다(실측 확인).
  3. Wagtail의 기본 검색 백엔드(`WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}`, 03 설계 당시부터 존재, 이번 3개 기능과 무관)는 `Page.save()`마다 `post_save` 시그널로 `wagtailsearch_indexentry` 테이블에 색인 INSERT를 시도한다(`modelsearch` 패키지). 이 INSERT는 `modelsearch/index.py`의 `insert_or_update_object()`가 `try/except Exception: logger.exception(...)`로 **감싸서 로그만 남기고 삼킨다** — Python 예외는 전파되지 않지만, Postgres 세션 자체는 실패한 SQL 때문에 "aborted transaction" 상태가 되고 **롤백-투-세이브포인트 처리가 없어 그대로 남는다.**
  4. `legal.0002_create_legal_pages`는 `add_child()`(treebeard 저수준 생성)로 페이지를 **1회**만 저장 — 색인 시도가 (감춰진 채) 실패해도 그 migration 안에서 추가 SQL이 없어 "OK"로 끝난다.
  5. 반면 신규 `legal.0003`(DEC-055)은 기존 페이지를 `LegalPage.objects.get(...)`로 조회해 **`page.save_revision(user=None).publish()`**로 수정한다 — 이 한 줄이 내부적으로 `page.save()`를 **2회**(리비전 저장 1회, 발행 1회) 호출해 색인 시도도 2회 발생한다. 첫 번째 실패로 세션이 이미 "aborted" 상태가 된 뒤, 두 번째 시도(django-tasks의 `insert_or_update_object_task`가 `model.objects.get(pk=pk)`로 인스턴스를 다시 조회하는 SELECT)가 **이 예외를 먼저 만나(캐치 범위 밖) 그대로 전파**되어 `migrate` 전체를 크래시시킨다.
  6. **`legal.0004_add_adsense_cookie_notice`(DEC-054)·`legal.0005_add_comment_ip_blocklist_notice`(DEC-055)도 동일하게 `save_revision().publish()` 패턴을 사용**한다(코드 확인) — 0003이 먼저 크래시하므로 이번 실행에서는 도달하지 못했지만, 0003만 우회해도 0004/0005에서 동일 문제가 재발할 것이 코드 패턴상 확실하다.
- **원인 확정(대조 실험)**: `python manage.py migrate wagtailsearch --noinput`를 **먼저** 실행해 `wagtailsearch_*` 테이블을 만든 뒤 `python manage.py migrate --noinput`을 실행하면 `legal.0003/0004/0005` 전부 포함해 **전체 마이그레이션이 끝까지 정상 완료**됨을 별도 컨테이너에서 확인했다(진단 목적 실험 — `build.sh` 자체를 수정하지는 않았다, 아래 "적용하지 않음" 참고).
- **왜 08단계 addendum(DEC-052)에서는 드러나지 않았는가**: 08단계 addendum은 SQLite(빈 DB)를 사용했다(DEC-052 명시). SQLite는 Postgres와 트랜잭션/세션 오류 처리 방식이 달라 이 특정 실패 모드가 재현되지 않는 것으로 판단된다(정확한 SQLite 내부 동작까지 규명하지는 않았음 — "확인 필요"로 남김). **이것이 바로 10단계가 "실제 배포환경 재현"이라는 별도 관점으로 존재하는 이유**이며, 이번 발견은 그 필요성을 실증한다.
- **영향 범위/심각도**: Neon(PostgreSQL)은 표준 Postgres이므로 이 실패는 **실제 Neon 배포에서도 100% 동일하게 재현될 것으로 판단**된다(트랜잭션 abort는 Postgres 코어 동작이며 Neon 특유의 예외 사항이 아니다). `build.sh`가 `set -o errexit`로 종료되므로 **Render의 첫 배포(빌드 단계)부터 실패**하고, 이 상태에서는 애플리케이션이 전혀 기동조차 되지 않는다(healthz/gunicorn 등 이후 어떤 검증도 무의미해짐). 우회 방법이 코드 수정 없이는 없다(환경변수 조정으로 회피 불가). **심각도: Critical** — 원본 §6 DEF-10-01(High, 조건부 리스크)보다 확정적이고 전면적이다(조건 없이 100% 재현되는 빌드 실패).
- **적용하지 않음**: 위 "원인 확정" 실험은 진단 목적으로만 별도 컨테이너에서 수행했고, `webapp/legal/migrations/*`·`webapp/config/settings/*`·`webapp/build.sh` 등 **실제 저장소 코드는 전혀 수정하지 않았다** — 10단계는 배포 파이프라인을 검증하는 역할이며 코드 수정은 규칙F에 따른 5단계(근본원인 단계) 소관이다(오케스트레이터 지시 및 ORCHESTRATOR.md 규칙F).
- **권고 조치 방향(택1, 5단계 재작업 시 판단)**:
  1. `legal`의 `save_revision().publish()`류 데이터 마이그레이션에 `wagtailsearch`(및 그 전제인 `wagtailcore`)에 대한 명시적 `dependencies`를 추가해 위상정렬이 항상 검색 테이블을 먼저 만들도록 강제.
  2. `INSTALLED_APPS`에서 `wagtail.search`를 `legal`(및 `post_save`로 페이지를 다루는 다른 커스텀 앱)보다 앞으로 재배치 — 다만 이는 다른 앱 간 상대 순서에도 영향을 줄 수 있어 더 넓은 회귀 확인이 필요.
  3. 마이그레이션 내에서 색인 신호를 일시적으로 끊고(`post_save.disconnect(...)` 후 재연결) `save_revision().publish()` 호출 — 데이터 마이그레이션이 검색 색인에 의존하지 않도록 격리.
  - 세 방향 모두 스키마 변경이 아니며 데이터 손실 위험이 없다. 최종 선택은 5단계 재작업 에이전트가 근거와 함께 결정하고 `decisions.md`에 기록해야 한다(본 addendum은 진단과 후보 제시까지만 수행, 결정은 하지 않음).

### 13.5 무중단 배포/헬스체크/정적파일/gunicorn 워커 — 회귀 확인 (진단 컨테이너 기준)
- DEF-10-06 때문에 `build.sh`를 무수정 상태로는 애플리케이션을 끝까지 기동할 수 없어, 13.4의 진단 컨테이너(`migrate wagtailsearch` 선행 실행 — 저장소 코드 변경 아님, 검증 전용 임시 조치)에서 이어서 `collectstatic`(219 static files, 원본과 동일 수치) → `ensure_superuser`(정상 생성) → `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --workers 1 --bind 0.0.0.0:8000`(render.yaml `startCommand` 그대로)를 실행했다.
- 결과(전부 `X-Forwarded-Proto: https` 헤더 포함, Render 엣지 재현):
  - `GET /healthz`(헤더 없음) → 200 (DEF-10-01 수정 `SECURE_REDIRECT_EXEMPT` 회귀 없음 재확인)
  - `GET /healthz`(헤더 있음) → 200
  - `GET /` → 200, `GET /sitemap.xml` → 200, `GET /robots.txt` → 200
  - `GET /privacy-policy/` → 200, `GET /cookies/` → 200 (legal 신규 마이그레이션 반영된 문구로 정상 렌더링)
  - `GET /cms-admin/login/` → 200, `GET /django-admin/login/` → 200 (두 진입점 모두 정상, DEF-09-01 관련 라우팅 회귀 없음)
  - `GET /ads.txt` → **404**(adsense_client_id 미설정 상태의 의도된 동작, DEC-054 설계와 일치 — "값 없으면 조용히 비활성" 원칙 재확인)
  - `GET /static/css/components.css` → 200, `Content-Type: text/css`(whitenoise 정적 서빙 회귀 없음)
- **결론**: DEF-10-06(마이그레이션 순서)만 해소되면, 나머지 배포 파이프라인(헬스체크/정적파일/두 관리자 로그인 라우트/ads.txt 조건부 활성화)은 신규 3개 기능 반영 후에도 전부 정상 동작한다 — 이는 **DEF-10-06이 코드 로직 결함이 아니라 순수 마이그레이션 순서/격리 문제**라는 13.4의 근본원인 판단을 뒷받침하는 추가 근거다.
- gunicorn 워커 수는 `--workers 1`(render.yaml 그대로, DEC-026 정책 변경 없음) — 신규 기능이 LocMemCache 기반 레이트리밋(댓글/뉴스레터/로그인 공용 전제)에 영향을 주지 않음을 코드로 재확인(신규 레이트리밋 로직인 DEC-055 상습범 차단도 동일하게 단일 프로세스 LocMemCache 전제를 그대로 따름, `comments/constants.py`/`comments/views.py` 확인).

### 13.6 롤백 영향 분석
- **코드 롤백(직전 배포로 되돌림) 시 스키마 안전성**: 이번 3개 기능이 추가한 테이블/컬럼(`comments_comment` 확장 컬럼 `source_ip_raw`, `comments_blockedip`, `core_sitesettings.adsense_client_id`, `legal` 갱신 콘텐츠)은 전부 **가산적(additive)**이며, 이전 코드가 이 테이블/컬럼을 전혀 참조하지 않으므로 코드만 롤백(DB는 그대로)하는 경우 옛 코드가 새 스키마 위에서 정상 기동하는 데 지장이 없다(기존 DEF-10-04/TC-017/018과 동일한 원칙 — "추가된 컬럼/테이블은 옛 코드가 몰라도 무해").
- **신규로 추가해야 할 리스크 항목(기존 §6/§9-1 표에 없던 것)**:
  1. **`comments.0003_add_blocked_ip_and_source_ip_raw`는 Django 기본 리버스(자동 생성, `RunPython` 아님)를 사용** — `migrate comments 0002`로 명시적으로 되돌리면 `source_ip_raw` 컬럼과 `BlockedIP` 테이블이 **DROP되어 데이터가 영구 손실**된다. 실제 댓글/차단 데이터가 쌓인 뒤 이런 DB 되돌리기를 하면 스팸 방지 이력이 전부 사라진다 — **코드만 롤백(DB는 그대로 둠)하는 일반적인 Render 롤백 절차에서는 발생하지 않지만**, 운영자가 "DB도 같이 되돌리자"고 판단하는 경우에 한해 위험하므로 운영 Runbook에 "DB 마이그레이션 되돌리기는 코드 롤백과 별개로 별도 승인 필요"라는 경고를 명시할 것을 권고한다.
  2. **`legal.0003/0004/0005`는 전부 `noop_reverse`(고의적 무동작)로 설계되어 있다** — `migrate legal 0002`로 되돌려도 법적 고지 문구는 최신 상태로 남는다(콘텐츠 텍스트 롤백 없음). 이는 DEC-055/054가 이미 의도한 안전한 설계이며(문구가 되돌아가 "우리는 IP를 수집하지 않는다"처럼 실제와 다른 문구가 되는 사고를 막음), 새 리스크가 아니라 오히려 **모범 사례로 §9-1에 긍정적으로 기록할 가치가 있다.**
  3. **`core.0003_add_adsense_client_id`**: 일반 `AddField`라 되돌리면 `adsense_client_id` 값이 사라진다(설정값 손실, Low — 운영자가 재입력하면 그만).
- **결론**: 롤백 자체의 스키마 안전성 원칙(§6/§9-1)에는 위배되지 않으나, "DB까지 되돌리는" 예외적 롤백 시나리오에서 `comments.BlockedIP`/`source_ip_raw` 데이터 손실 리스크가 새로 식별되어 11단계 Runbook에 반영 권고한다.

### 13.7 모니터링/알림 채널 실제 연결 확인
- 이번 3개 기능이 사용하는 알림 채널은 **신규 채널이 아니라 원본 §4 TC-008이 이미 실측 검증한 `DJANGO_ADMIN_EMAIL`/`ADMINS`/`AdminEmailHandler`/mailhog 채널을 그대로 재사용**한다(`comments/notifications.py`가 Django 표준 `mail_admins()`를 호출 — DEC-049에 명시된 설계 그대로임을 코드로 재확인).
- 이번 addendum에서 실제 댓글 제출→이메일 수신까지의 신규 E2E는, `BlogPostPage.body`가 StreamField라 진단 스크립트로 손쉽게 유효한 발행 게시물을 만들지 못해(스트림 블록 직렬화 형식 문제) **이번 세션에서는 재현하지 못했다** — 이 사실을 감추지 않고 명시한다(규칙C). 대신 아래 근거로 이 채널이 실제로 연결되어 있다고 판단한다:
  1. 원본 §4 TC-008이 **동일한 설정 조합**(`DJANGO_ADMIN_EMAIL`→`ADMINS`, `EMAIL_HOST`=mailhog)으로 강제 500 에러를 유발해 mailhog가 실제로 메일을 수신함을 실측 확인했고, 이번 3개 기능은 이 설정을 전혀 변경하지 않았다(13.3에서 확인).
  2. `comments/notifications.py`는 Django 표준 `mail_admins()` API를 그대로 호출하며(자체 SMTP 로직 재구현 없음), DEC-049에 따라 발송 실패가 댓글 저장을 막지 않도록 예외가 격리되어 있음을 코드로 확인했다.
  3. DEC-049/DEC-056에 따르면 이 알림 함수 자체는 이미 `comments/tests.py`의 유닛 테스트(신규 5케이스)로 단위 수준 검증이 완료된 상태다.
- **판정**: 채널 배선(wiring) 자체는 원본 TC-008로 실측 검증된 것과 동일하며, 이번 3개 기능이 그 위에 새 트리거만 추가했을 뿐 채널 설정을 바꾸지 않았다는 근거로 "연결되어 있다"고 판단하되, **댓글 알림 자체의 실제 E2E 발송은 이번 세션에서 미실측 상태로 남는다는 점을 한계로 명시**한다. 11단계/차기 검증에서 실제 발행 게시물 위에서 댓글 제출→메일 수신까지 1회 실측할 것을 권고(Low, 비차단 — 채널 자체는 검증됨, 트리거 지점만 미확인).

### 13.8 결함(Defect) 목록 (addendum분)

| ID | 설명 | 재현 절차 | 심각도 | 상태 | 조치 내용 |
|----|------|-----------|--------|------|-----------|
| DEF-10-06 | 실제 PostgreSQL(Neon 재현) 대상 `build.sh` 실행 시 `legal.0003_add_comment_privacy_notice`(DEC-055)에서 `migrate`가 `current transaction is aborted` 오류로 100% 재현 가능하게 크래시한다. 근본 원인은 `wagtail.search`(wagtailsearch) 앱의 마이그레이션이 `legal` 앱보다 나중에 적용되는 위상정렬 순서 때문에, `legal.0002/0003`이 호출하는 `page.save_revision().publish()`의 검색색인 시그널이 존재하지 않는 `wagtailsearch_indexentry` 테이블에 INSERT를 시도해 실패하고, 그 실패가 삼켜지되(Python 예외는 캐치) Postgres 트랜잭션은 abort 상태로 남아 같은 마이그레이션(또는 트랜잭션을 공유하는 후속 SQL)의 다음 SQL 호출에서 크래시로 이어진다. `legal.0002`는 `add_child()`(단일 save)라 영향이 없었으나, DEC-055가 추가한 `legal.0003`(및 동일 패턴의 0004/0005)은 `save_revision().publish()`(2회 save)를 처음 사용해 이 잠재 결함을 실제로 노출시켰다. | 13.4절 — 2회 독립 재현, `migrate wagtailsearch` 선행 실행 시 미재현되는 대조실험으로 원인 확정 | **Critical** | **[2026-09-29 Fixed]** DEC-060 참고 — `legal/migrations/0003_add_comment_privacy_notice.py`에 `("wagtailsearch", "0010_add_text_fields")` 명시적 의존성 추가(13.4절 후보 조치 1안 채택). 로컬 Postgres 16(운영과 동일 엔진, `postgres:16-alpine`)에 빈 스키마로 마이그레이션 재실행해 크래시 없이 완주 확인, 전체 자동 테스트(114개) 재실행 OK | `legal/migrations/0003_add_comment_privacy_notice.py`(dependencies 추가 + 원인 설명 주석). 5단계 코드 수정 + 규칙B 검증(수정 전/후 대조 재현)까지 완료했으나, 이번 수정은 정식 06/07 서브에이전트 호출을 거치지 않고 오케스트레이터가 사용자와 함께 직접 진단→수정→재현검증한 경로다(투명하게 기록) — 형식적 06/07 결과서(`unit-XX-test.md`/`feature-WU-XX-integration-test.md`)는 아직 별도로 생성되지 않았으므로, 12단계 착수 전 이 문서화 공백을 메울지(또는 이 §13.8 갱신 + DEC-060으로 충분하다고 볼지) 오케스트레이터가 사용자에게 확인 필요 |
| DEF-10-07 | `comments.0003_add_blocked_ip_and_source_ip_raw`가 Django 자동 리버스를 사용해, 명시적으로 DB 마이그레이션을 롤백(`migrate comments 0002`)하면 `source_ip_raw`/`BlockedIP` 데이터가 영구 손실된다. 코드만 롤백하는 일반적 Render 재배포 롤백에서는 발생하지 않으나, 운영자가 DB까지 되돌리는 경우에 한해 발생 | 13.6절 마이그레이션 리버스 코드 검토(`comments/migrations/0003_add_blocked_ip_and_source_ip_raw.py`에 커스텀 `RunPython`/보존 로직 없음을 확인) | Low | Open(비차단, 문서화로 대응 권장) | 11단계 Runbook에 "DB 마이그레이션 되돌리기는 코드 롤백과 별개 절차이며, `comments` 앱을 0002 이전으로 되돌리기 전 `BlockedIP`/`source_ip_raw` 데이터 백업 필수" 경고 추가 권고 |

**결함 요약(addendum분)**: Critical 1건(DEF-10-06, **[2026-09-29 Fixed]** — DEC-060, 로컬 Postgres 실측 재검증 완료, 정식 06/07 문서화 공백은 사용자 확인 필요로 명시), Low 1건(DEF-10-07, 문서화로 대응 가능, 비차단, Open 유지).

### 13.9 테스트 환경 정리(Teardown) 확인 — 규칙 K (addendum분)
- **생성한 임시 아티팩트**: `webapp/.harness-tmp/deploy-staging-addendum/`(Dockerfile.postgres/Dockerfile.web/pg_hba_ssl.conf/docker-compose.yml/make_post.py 등) — 전부 `.harness-tmp/` 하위에만 생성(규칙K 1번 준수).
- **Docker 리소스**: 컨테이너(`deploy-staging-addendum-db-1`/`mailhog-1`/`web-1`, 진단용 `inspect-web`/`inspect-web2`/`inspect-web3`/`inspect-web4`), 이미지(`deploy-staging-addendum-web`/`deploy-staging-addendum-db`), 네트워크(`deploy-staging-addendum_default`) 전부 `docker rm -f`/`docker compose down -v`/`docker rmi`/`docker network prune -f`로 제거 완료. `docker ps -a`/`docker images` 재확인 결과 관련 리소스 0건.
- **디렉터리 삭제**: `rm -rf webapp/.harness-tmp` 실행 후 `ls` 재확인 — 디렉터리 없음. `bash automation/harness-janitor.sh --check` 재실행 결과 `.harness-tmp/ 는 비어있거나 없습니다 — 이상 없음 / 잔여 임시 아티팩트 없음`.
- **git status 관련 사실 고지(투명성)**: 이번 세션은 워크트리 격리 에이전트로 실행되어, 공유 체크아웃(`C:\big21\vibe-coding\AI-AUTO-WORK`, 실제 `webapp/`·`docs/`가 존재하는 경로)을 대상으로 한 `git status`/`git -C` 등 **git 명령 자체가 도구 차원에서 차단**되어 있다(다중 에이전트 동시 작업 시 공유 체크아웃의 git 상태를 보호하기 위한 안전장치로 판단됨 — 회피 시도하지 않았음). 따라서 원본 §7처럼 `git status` 원문을 그대로 첨부할 수 없다. 대신 아래로 대체 확인했다:
  - `find webapp -maxdepth 1 -newer webapp/manage.py`로 세션 중 변경된 최상위 항목을 조사한 결과, `.venv`/`db.sqlite3`/`media`(세션 시작 전부터 존재하던 로컬 개발 산출물, 이번 세션이 생성하지 않음) 외에 신규/잔존 파일이 없음을 확인했다.
  - 이번 세션이 실제로 수정한 파일은 의도된 산출물뿐이다: `docs/harness/10-deploy-test.md`(본 §13/§14 추가), `docs/harness/verify-log_10-deploy-test.md`(addendum 추가), `docs/harness/traceability.md`(REQ-019/REQ-023 비고 갱신), `docs/harness/decisions.md`(DEC-059 append) — 전부 append/추가이며 기존 내용을 삭제·수정하지 않았다.
  - `webapp/legal`, `webapp/comments`, `webapp/core`, `webapp/config`, `webapp/build.sh`, `webapp/render.yaml`, `webapp/.env.example` 등 **애플리케이션 코드/배포 설정은 이번 세션에서 전혀 수정하지 않았다**(13.4 "적용하지 않음" 참고, Read 전용 조사 + `.harness-tmp/` 내부 진단만 수행).
- 이번 addendum 작업 도중 강제 중단은 없었다.

### 13.10 결론 및 판정 (addendum분)
- [x] **PASS** — **[2026-09-29 갱신, DEC-060]** 아래 조건 1(DEF-10-06, Critical)이 해소되어 CONDITIONAL PASS에서 PASS로 갱신한다. 근거: 로컬 Postgres 16(`postgres:16-alpine`, 운영 Neon과 동일 엔진)에 빈 스키마로 마이그레이션을 재실행해 크래시 없이 완주 확인(수정 전 코드로 동일 크래시 재현 → 수정 후 미재현, 대조 검증), 전체 자동 테스트 114/114 OK. **단, 이 검증은 08~10단계처럼 별도 Docker 스테이징 스택(`webapp/.harness-tmp/deploy-staging-addendum/`) 전체를 재현한 것이 아니라, 로컬 개발용 Postgres 컨테이너(`aiautowork-blog-db`)를 대상으로 오케스트레이터가 사용자와 함께 직접 진단·수정·재검증한 경로이며, 정식 06/07 서브에이전트 결과서는 생성하지 않았다(사용자 확인 하에 이 수준으로 충분하다고 판단, DEC-060 참고)** — 이 사실을 숨기지 않고 그대로 남긴다.
  2. (권고, 비차단, 여전히 Open) DEF-10-07을 11단계 Runbook에 "DB 마이그레이션 되돌리기 전 BlockedIP/source_ip_raw 백업" 경고로 반영.
  3. (권고, 비차단, 여전히 Open) 13.7에서 확인하지 못한 "댓글 알림 실제 E2E 발송"을 다음 검증(11단계 또는 실배포 후 13단계)에서 1회 실측 권고.
- [ ] FAIL

**판정 근거**: 빌드 재현성(13.2)·환경변수(13.3)·롤백 스키마 안전성 원칙(13.6, 신규 데이터손실 리스크 1건은 Low)·모니터링 채널 배선(13.7)은 이상 없음을 확인했고, DEF-10-06 해소를 가정한 상태에서의 나머지 배포 체인(헬스체크/정적파일/두 관리자 로그인 라우트/ads.txt, 13.5)도 전부 정상 동작함을 실측했다. 그러나 **DEF-10-06(Critical)은 현재 코드 상태 그대로 12단계를 시도하면 최초 배포가 빌드 단계에서 확정적으로 실패하는 결함**이므로, 20년차 운영자 관점에서 이 조건 없이 "완전한 PASS"로 넘기는 것은 무책임하다(CLAUDE.md 페르소나 원칙과 동일하게, "빌드조차 안 되는 배포는 배포가 아니라 도박"). §1~§12(원본, WU-01~10 범위)의 PASS 판정 자체는 유효한 채로 보존하며, 이 addendum은 **그 이후 추가된 코드에 대한 신규 게이트**로 별도 판정한다.

## 14. 내부 검증 (최소 2회, §13 addendum분)

### 1차 검증 (작성자 관점 자가 재검토)
- 체크리스트(빌드 재현성/환경변수·시크릿/무중단·헬스체크/롤백 실제 검증/마이그레이션 순서/모니터링·알림 채널 실제 연결) 6개 항목 전부 수행 여부 확인 — 6/6 완료(13.2~13.7). 특히 "마이그레이션 순서"는 단순 관찰이 아니라 2회 독립 재현 + 대조실험(wagtailsearch 선행 적용 시 미재현)으로 근본원인까지 확정했는지 재확인 — 확정됨.
- "08단계 addendum(SQLite)이 왜 이 문제를 못 잡았는가"를 추측으로 넘기지 않고 명시적으로 "확인 필요"로 남겼는지 재확인 — §13.4 "왜 08단계에서는..." 절에서 명시적으로 한계를 인정하며 서술함(과장/추측 없음).
- MinIO 이미지 pull 실패로 인한 환경 축소(R2 미포함)가 "대충 넘어간 것"이 아니라 "이번 3개 기능이 스토리지를 건드리지 않는다"는 코드 근거와 함께 명시적으로 정당화되었는지 재확인 — §13.1에 근거(코드 확인 결과) 명시됨.
- 10단계 역할 경계(코드 수정 금지, 진단과 보고까지만)를 실제로 지켰는지 재확인 — §13.4 "적용하지 않음", §13.9 Teardown 고지 양쪽에서 애플리케이션 코드 미수정을 명시적으로 확인·기록함.
- 결함 0건이 아니므로(Critical 1건 발견) 규칙B에 따라 2차 검증을 생략하지 않고 진행한다.

### 2차 검증 (독립 심사자 관점 — "오늘 처음 이 문서를 받아본 심사자")
- "이 문서만 보고 12단계 승인 여부를 판단하는 사용자/오케스트레이터"의 시각에서 재검토: (a) DEF-10-06의 설명이 "확실히 실패한다"는 확정적 사실과 "권고 조치 방향"이라는 미확정 제안을 명확히 구분해서 서술했는가 — 13.4 마지막 문단에서 "택1, 5단계 재작업 시 판단"으로 명확히 구분됨, 과도하게 단정하지 않음. (b) 이 addendum이 원본 §1~§12(PASS)를 훼손하거나 덮어쓰지 않고 "이후 추가된 코드에 대한 신규 게이트"로 정확히 범위를 분리했는가 — §13.10 판정 근거 마지막 문장에서 명시적으로 분리함. (c) 롤백 리스크(DEF-10-07)가 과장 없이 "코드만 롤백하는 일반 절차에서는 발생하지 않는다"는 조건을 명확히 달았는가 — 13.6/13.8에서 일관되게 명시됨. (d) 규칙K Teardown에서 git status를 직접 첨부하지 못한 사유(워크트리 격리)가 "책임 회피"가 아니라 "도구 제약 + 대체 확인 방법"으로 투명하게 서술되었는가 — 13.9에서 구체적 대체 확인 절차(find, 수정 파일 목록 명시)와 함께 서술됨, 은폐 없음.
- 결함 0건.

### 최종 판정
- [x] **PASS**(검증 로그 기준 — §13 addendum 자체의 완전성에 대한 판정, 결함 0건, 규칙B 최소 2회 충족). 단 **`10-deploy-test.md` §13이 서술하는 addendum 대상(신규 3개 기능의 배포 파이프라인)의 판정은 CONDITIONAL PASS**(§13.10)이며, DEF-10-06(Critical)이 12단계 착수 전 필수 해결 조건이다.
- [ ] FAIL
- 검증 로그 파일 경로: `docs/harness/verify-log_10-deploy-test.md`("§13 addendum" 절, 아래 추가)
