# 테스트 결과서 (Test Result Report) — WU-10 통합테스트 (백업/복구 절차, REQ-013)

> **재작성 경위(중요)**: 이 파일은 직전 세션(2번째 시도)이 API 사용량 한도로 중단되기 전 작성한 버전을 완전히 대체한다. 직전 버전은 본문 10절에서 `docs/harness/verify-log_feature-WU-10-integration-test.md`가 존재한다고 주장했으나, 실제로는 그 파일이 디스크에 없었다(작업 착수 전 `ls`/`find`로 재확인 — 규칙C 위반). 따라서 이번 3번째 시도는 직전 버전의 결함 목록·PASS 판정 등 어떤 주장도 그대로 신뢰하지 않고, 참고자료로만 열람한 뒤 이 문서에 기록된 모든 항목을 처음부터 직접 재현했다. 본문과 `verify-log_feature-WU-10-integration-test.md` 둘 다 이번 세션이 실제로 디스크에 생성했다.
> **경로 확인**: 작업 지시가 명시한 프로젝트 루트는 `C:\big21\vibe-coding\AI-AUTO-WORK`다. 이번 세션 환경변수가 알려준 "Primary working directory"(`STOCK-ANALYZER-KR`)는 완전히 다른 프로젝트(주식 스크리닝 서비스)이며, `unit-10-note.md` §0/`unit-10-test.md` 머리말이 이미 이 충돌을 발견해 `AI-AUTO-WORK`를 대상으로 진행했다고 기록한 판단을 이번 07단계도 독립적으로 재확인했다(`docs/harness/units/unit-10-note.md` 파일이 `AI-AUTO-WORK`에만 실존, `git remote -v`로 `AI-AUTO-WORK` 저장소임을 재확인).
> **금지 사항 준수**: 작업 지시가 "`git commit`/`git push`/`git add`를 절대 실행하지 말 것(`git status`만 허용)"을 명시했다. 이번 07단계 전 구간에서 `git status`/`git diff`/`git log`(읽기 전용) 외의 git 쓰기 명령은 실행하지 않았다.

## 1. 개요
- 테스트 대상 (모듈/기능/업무단위/전체 시스템 중 명시): **업무 단위(feature) WU-10 — REQ-013(Neon PITR 6시간 한계 보완 백업 정책)**. `.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`, `docs/harness/decisions.md`(DEC-032~034), `docs/harness/traceability.md`(REQ-013 행)가 이 업무 단위를 구성하는 산출물이다.
- 테스트 유형: 통합(Integration) — 07단계
- 적용 Tier: **Standard**(`docs/harness/decisions.md` DEC-036, 2026-09-17 사용자 확인 — 회원가입/결제/규제데이터 없음, AI/LLM 기능 비해당. Standard는 06/07 분리·최소 2회 검증 원칙이 그대로 적용되며 병합 생략 조건(Low 등급 전용)에 해당하지 않는다).
- 테스트 목적: WU-10은 02-planning.md §9 계획상 **단일 작업 단위(unit-10)로만 구성된 업무 단위**다 — 따라서 "업무 단위 내부"의 단위 간 데이터 흐름은 자명하게 1개뿐이다. 이 07단계의 실질적 가치는 페르소나 지침("단위 테스트를 반복하지 않고 단위 간 상호작용에 집중")에 따라 **WU-10이 이미 완료된 다른 업무 단위(WU-01/WU-03/WU-08/WU-09)의 실제 산출물과 만나는 경계**에서 나온다: (1) 시크릿 이름이 `production.py`/`render.yaml`(WU-01/03이 정의)과 정확히 일치하는가, (2) R2 버킷 분리 체계(WU-03/DEC-008)와 충돌이 없는가, (3) 복구 절차가 `render.yaml`/`build.sh`(WU-09의 `ensure_superuser` 포함)의 실제 배포 흐름과 모순이 없는가, (4) 워크플로/스크립트 문법을 실제 도구로 재현 검증하는가, (5) WU-10이 WU-01~09 소유 실행 코드를 침범(회귀)하지 않았는가. 아울러 06단계가 "검증 불가"로 정직하게 기록한 AC10/11, 그리고 Low 결함 DEF-001(DEC-034)의 실제 파급력을 07단계 수준에서 한 번 더 실측으로 의심한다.
- 관련 산출물: `docs/harness/units/unit-10-note.md`, `docs/harness/units/unit-10-test.md`, `docs/harness/units/verify-log_unit-10-test.md`(전부 06단계까지 PASS), `docs/harness/decisions.md`(DEC-004/008/010/016/032/033/034/035/036), `docs/harness/03-system-design.md`(§1.1/§1.2/§2.3/§3.3/§5.4/§6.4/§7.2/§7.3/§7.4/§7.5), `webapp/render.yaml`, `webapp/build.sh`, `webapp/config/settings/production.py`, `webapp/core/management/commands/ensure_superuser.py`, `webapp/.env.example`. (참고만 하고 결론은 전부 재검증한 자료: 직전 세션의 `feature-WU-10-integration-test.md` 구버전 — 이번 작성으로 덮어씀)
- 테스트 수행자(에이전트): `07-integration-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- 범위 (In-Scope):
  - WU-10 산출물과 WU-01/03/08/09 산출물 사이의 실제 경계 검증(시크릿 이름/버킷 체계/배포 흐름/회귀) — §1의 (1)~(5).
  - 06단계가 이미 실측 PASS로 확인한 항목(YAML 문법, 8개 스텝 bash 문법, 시크릿 사전점검 정상 케이스, 타임스탬프 생성, R2 Lifecycle JSON 스키마)은 **반복하지 않는다** — 다만 "실제로 존재하는 최신 커밋의 실제 파일"을 대상으로 actionlint/shellcheck(공식 배포본, 체크섬 검증)를 이번 세션이 독립적으로 재다운로드해 한 번 더 직접 실행해, 06단계의 도구 기반 검증(TC-EXT-01)이 재현 가능한 결과인지 교차 확인한다(단순 반복이 아니라 "다른 세션에서도 같은 결론이 나오는가"라는 재현성 검증 — 규칙C).
  - DEC-034(DEF-001, Low, Deferred)가 주장하는 "조용한 성공으로 이어지지 않는다"는 판단을 **실제 `pg_dump` 바이너리로 1번 스텝→3번 스텝을 체인 실행**해 직접 재현(06단계는 1번 스텝만 단독 실행했음 — 07단계가 처음으로 단계 간 데이터 흐름을 실측).
  - 복구 절차(`BACKUP_RESTORE_GUIDE.md`)와 실제 배포 스크립트(`build.sh`/`render.yaml`/`ensure_superuser.py`) 사이의 논리적 모순 여부.
- 제외 범위 및 사유:
  - **실제 GitHub Actions 러너 실행, 실제 Neon/R2 자격증명을 사용한 네트워크 호출** — `unit-10-test.md` AC10/11과 동일하게 이번 세션도 GitHub Secrets가 없고(작업 지시가 push/트리거 자체를 금지) 실제 Neon/R2 계정이 없어 구조적으로 불가능하다. 10단계(배포테스트)로 이관(변경 없음).
  - **WU-01~09 각자의 06/07단계가 이미 PASS로 확정한 자신의 기능 자체 재검증**(예: WU-09 로그인 레이트리밋 로직 자체, WU-08 모니터링 대시보드 자체) — 이번 07단계는 "WU-10과의 경계"만 본다. WU-01~09 상호 간 조립은 각자의 `feature-WU-0X-integration-test.md`가 이미 담당했다.
  - **8단계(전체 풀테스트)/9단계(보안검증)/10단계(배포테스트)/11단계(운영 Runbook)** — 이번 07단계 범위 밖, §8에 명시적으로 이관.
  - **WU-11(부가기능) 착수** — 작업 지시가 이번 세션 범위를 WU-10까지로 명시했으므로 시작하지 않았다.

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Git Bash(MINGW64, bash 5.3.15). Python 3.13.9(Anaconda, `C:\Users\mega\anaconda3\python`, PyYAML 6.0.3 기설치 확인).
- 이번 07단계가 **저장소 밖 세션 스크래치패드**(`...\scratchpad\wu10-it\`, 규칙K 취지상 허용 — 작업 지시가 명시적으로 이 방식을 승인)에 한시적으로 내려받아 사용한 도구(전부 검증 종료 후 정리, §7 Teardown 참고):
  - `actionlint` v1.7.12(공식 GitHub Release `rhysd/actionlint`, `actionlint_1.7.12_windows_amd64.zip`) — 이번 세션이 독립적으로 재다운로드 후 `actionlint_1.7.12_checksums.txt`의 SHA-256(`6e7241b5...`)과 직접 일치 확인(06단계와 동일한 체크섬 — 같은 공식 릴리스를 가리킴을 재확인).
  - `shellcheck` v0.11.0(공식 GitHub Release `koalaman/shellcheck`, `shellcheck-v0.11.0.zip`).
  - PostgreSQL 18.6(`pg_dump.exe`, conda-forge 채널, 격리된 conda 환경 `...\scratchpad\wu10-it\pgenv`에만 설치 — 검증 종료 후 `conda env remove` 실행, §7 참고).
- 테스트 데이터: 저장소의 실제 `.github/workflows/neon-db-backup.yml`에서 Python `yaml.safe_load`로 직접 추출한 8개 `run:` 스크립트(스크래치패드 임시 파일), 더미 환경변수 값(`x`, 공백 문자 1개 등 — 실제 시크릿 아님), 명백히 존재하지 않는 더미 호스트명(`this-host-does-not-exist-wu10-test.invalid`).
- 전제 조건:
  - 저장소의 실제 소스(`.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`, `webapp/render.yaml`, `webapp/build.sh`, `webapp/config/settings/production.py`, `webapp/core/management/commands/ensure_superuser.py`, `docs/harness/decisions.md`, `docs/harness/traceability.md`)를 수정 없이 그대로 읽어 사용했다.
  - 작업 착수 전 `bash automation/harness-janitor.sh --check`(저장소 루트) 실행 — `.harness-tmp/`가 비어있거나 없음을 확인(잔여 아티팩트 없음, 이상 없음).
  - 작업 착수 전 `git status`(저장소 루트) 실행 — `nothing to commit, working tree clean`을 확인(작업 지시가 언급한 과거 `.venv_wu09_it` 삭제 흔적은 이미 커밋된 이력 상태이며 현재 워킹트리에는 나타나지 않음 — 무시 대상 그대로 무시).
  - 이번 07단계는 검증에 쓴 모든 임시 파일/디렉터리/conda 환경을 저장소 밖 세션 스크래치패드에만 만들었고, 저장소 작업 트리 안에는 어떤 임시 파일도 생성하지 않았다(§7 근거, `git status --porcelain`으로 최종 확인).

## 4. 테스트 케이스 및 결과

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| IT-01 | 시크릿 이름 일치성 — WU-10(워크플로/가이드) × WU-01/03(설정/설계) 경계 | 저장소 실제 소스 | `.github/workflows/neon-db-backup.yml`의 `secrets.*`/`env:` 키, `webapp/config/settings/production.py`의 `_require_env`/`os.environ.get`, `webapp/render.yaml`의 `envVars[].key`, `webapp/BACKUP_RESTORE_GUIDE.md` §4 표, `webapp/.env.example`을 각각 `grep -oE`로 추출해 이름 집합 대조 | `NEON_BACKUP_DATABASE_URL`/`R2_BACKUP_ACCESS_KEY_ID`/`R2_BACKUP_SECRET_ACCESS_KEY`/`R2_BACKUP_BUCKET_NAME`/`R2_ENDPOINT_URL`/`R2_REGION` 6개 이름이 모든 파일에서 철자 단위로 정확히 일치 | 워크플로 `secrets.*` 6개 = 워크플로 `env:` LHS 6개(+`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`는 boto3 표준 이름으로 의도된 별도 매핑) = `render.yaml`의 `R2_BACKUP_*`/`R2_ENDPOINT_URL`/`R2_REGION` = `production.py`의 `os.environ.get("R2_BACKUP_*")` = `.env.example`의 동일 키 = `BACKUP_RESTORE_GUIDE.md` §4 표의 6개 Secret 이름. `NEON_BACKUP_DATABASE_URL`만 `render.yaml`에 없음 — **의도된 정상 상태**(GitHub Actions 전용 시크릿이며 Render 앱은 이 값을 쓸 필요가 없음, `unit-10-note.md` §2-2/DEC-032 근거와 일치). `R2_ENDPOINT_URL`/`R2_REGION`은 media-public용(Render)과 backup용(GitHub Secrets)이 이름은 같지만 서로 다른 저장소(Render 대시보드 vs GitHub Secrets)에 별도로 입력해야 한다는 사실이 `BACKUP_RESTORE_GUIDE.md` §4에 명시적으로 경고되어 있음을 확인 | PASS | 결함 0건. 전체 grep 원본 출력은 §6 근거 |
| IT-02 | R2 버킷 분리 체계(`backup-private`/`media-public`) 일관성 — WU-10 × WU-03(DEC-008) 경계 | 저장소 실제 소스 전체(`webapp/`, `.github/`) | `grep -rn "backup-private\|media-public"` 실행 후, 각 매치가 **실행되는 코드/설정값**인지 **주석/문서 설명**인지 분류 | 버킷 이름 리터럴이 실행 경로(워크플로 YAML의 실제 값, Django 설정의 실제 값)에 하드코딩되어 있지 않고 전부 환경변수(`R2_BACKUP_BUCKET_NAME`)로만 주입되어야 한다(하드코딩되면 GitHub Secrets/Render 환경변수 값과 문자열이 어긋나도 발견이 늦어지는 리스크) | 전체 9개 매치(`webapp/.env.example` 2, `webapp/BACKUP_RESTORE_GUIDE.md` 4, `webapp/render.yaml` 1, `webapp/config/settings/production.py` 3, `.github/workflows/neon-db-backup.yml` 3) **전부 주석/문서 설명**이며, 실행되는 YAML 값(`bucket: "${{ secrets.R2_BACKUP_BUCKET_NAME }}"`)이나 Django 코드(`R2_BACKUP_BUCKET_NAME = os.environ.get("R2_BACKUP_BUCKET_NAME")`)에는 `"backup-private"` 리터럴이 전혀 없음을 확인. `production.py`의 `STORAGES["backup"]`(WU-03이 골격만 구성, DEC-016(b))은 여전히 애플리케이션 코드 어디에서도 참조되지 않음(WU-10도 이 별칭을 쓰지 않음 — 03 §1.1이 백업을 GitHub Actions로 명시적으로 설계했기 때문에 정상, `unit-10-note.md` §5 관찰사항과 일치) | PASS | 결함 0건 |
| IT-03 | 복구 절차(`BACKUP_RESTORE_GUIDE.md`) × WU-09(`ensure_superuser`/`build.sh`/`render.yaml`) 배포 흐름 모순 여부 | `webapp/core/management/commands/ensure_superuser.py`, `webapp/build.sh`, `webapp/render.yaml` 실제 소스 | `BACKUP_RESTORE_GUIDE.md` §3-2(6시간 초과~14일 이내 R2 복구 절차)가 서술한 "검증 후 Render `DATABASE_URL` 전환 → 재배포" 흐름을, `ensure_superuser.py`의 실제 로직(멱등 가드 조건)과 대조 | 복구된(과거 시점) DB로 `DATABASE_URL`을 전환해 재배포(`build.sh` 재실행)해도 `ensure_superuser`가 오동작(비밀번호 강제 초기화, 중복 계정 생성 등)하지 않아야 함 | `ensure_superuser.py` 44행: `if User.objects.filter(is_superuser=True).exists(): ... return` — 가드 조건이 **환경변수가 아니라 복구된 DB 자체의 상태**를 조회한다. `pg_dump --clean --if-exists`(DEC-032)로 뜬 백업은 `auth_user` 테이블을 포함한 전체 스키마를 복원하므로, 복구 직후 DB에는 백업 시점의 슈퍼유저 계정이 이미 존재 → `ensure_superuser`는 무조건 건너뛴다(비밀번호 재설정/중복 생성 없음). `ADMIN_ACCESS_GUIDE.md`가 권고하는 "최초 배포 성공 후 `DJANGO_SUPERUSER_*` 환경변수 삭제" 상태에서도 이 가드는 DB 상태만 보므로 동일하게 안전하다(env var 존재 여부와 무관). `migrate --noinput`도 복구된 DB의 `django_migrations` 테이블 기준으로 멱등하게 동작(누락된 신규 마이그레이션만 적용) — 두 스크립트 사이에 모순되는 가정 없음 | PASS | 결함 0건. 다만 **정보성 관찰**: 백업 시점 이후 배포된 신규 마이그레이션이 있으면 복구 후 `migrate --noinput`이 이를 적용하는 것은 설계상 의도된 정상 동작(RPO 트레이드오프 그 자체)이므로 결함으로 취급하지 않음 |
| IT-04 | actionlint(공식, 체크섬 검증)+shellcheck 재현 — 06단계 결과의 독립 재현성 | actionlint v1.7.12(체크섬 `6e7241b5...` 이번 세션이 재확인), shellcheck v0.11.0, 둘 다 PATH에 추가 | 저장소 루트에서 `actionlint -verbose .github/workflows/neon-db-backup.yml` 실행 | GitHub Actions 공식 스키마 + shellcheck 임베드 검증에서 0 errors(06단계 TC-EXT-01과 동일 결론이 이번 세션에서도 재현되어야 함) | `verbose: Found 0 parse errors in 0 ms`, `verbose: Found total 0 errors in 125 ms`, `exit=0`. 저장소에 워크플로 파일이 이 1개뿐임을 `ls .github/workflows/`로 재확인(다른 워크플로와의 충돌 가능성 없음) | PASS | 06단계 결론의 재현성 확인(다른 세션·다른 다운로드에서도 동일 결과) |
| IT-05 | R2 Lifecycle JSON — 실제 커밋된 파일에서 직접 추출 재검증 | 저장소 실제 워크플로 파일 | `grep -A1 "printf '%s'" .github/workflows/neon-db-backup.yml`로 실제 JSON 리터럴을 추출해 `python -c "json.loads(...)"`로 파싱 | 유효한 JSON, `Rules[0].Expiration.Days==14`, `Rules[0].Filter.Prefix=="db-backups/"` | `parsed OK: 14 db-backups/` — 03 §7.5(14일) 요구사항과 정확히 일치 | PASS | 06단계는 YAML 파싱 경유로 추출했고, 이번엔 파일 grep으로 직접 추출 — 같은 결론에 도달함을 다른 경로로 재확인 |
| IT-06 | 회귀 — WU-10이 WU-01~09 소유 실행 코드를 침범하지 않았는가 | 저장소 최신 커밋(`HEAD`=`5c7fac77`), WU-10 착수 직전 기준 커밋(`unit-10-test.md`가 명시한 `e8900bf7`) | `git diff --stat e8900bf7 HEAD -- . ':(exclude)docs/harness'`(비-docs/harness 전체) + `git diff --stat e8900bf7 HEAD -- docs/harness` | `webapp/` 애플리케이션 소스(`*.py`, 템플릿, 마이그레이션 등) 변경 0건. 변경은 WU-10 자체 산출물(`neon-db-backup.yml` 신규, `BACKUP_RESTORE_GUIDE.md` 신규) + 하네스 메타 변경(DEC-035/036, `.gitignore`, 템플릿/에이전트 정의 — 사용자 승인된 전역 규칙 신설이며 WU-10 범위가 아님) + WU-09가 이미 남긴 미커밋(현재는 커밋된) 산출물만 있어야 함 | 16개 비-`docs/harness` 파일 변경 확인 — `webapp/` 하위는 `webapp/.gitignore`(규칙K, +3줄, DEC-035)와 `webapp/BACKUP_RESTORE_GUIDE.md`(신규, WU-10 소유)뿐이고, `webapp/core/`·`webapp/blog/`·`webapp/subscribers/`·`webapp/legal/`·`webapp/custom_images/`·`webapp/config/`·`webapp/render.yaml`·`webapp/build.sh` 등 WU-01~09 소유 실행 코드는 **단 1바이트도 변경되지 않음**. `docs/harness` 8개 파일 변경은 `decisions.md`/`feature-WU-09-integration-test.md`/`feature-WU-10-integration-test.md`/`traceability.md`/`units/unit-10-*.md`(전부 WU-09/WU-10 자신의 산출물)뿐 | PASS | 결함 0건. WU-01~09에 대한 재테스트 불필요(회귀 표면이 원천적으로 없음이 diff로 실증됨) |
| IT-07 | 거버넌스 무결성 — `decisions.md`/`traceability.md` append-only 여부 | 위와 동일 커밋 범위 | `git diff --numstat e8900bf7 HEAD -- docs/harness/decisions.md` | 삭제(deletion) 라인 0, 삽입(insertion)만 존재(DEC-032~036이 DEC-001~031을 덮어쓰지 않았어야 함) | `6\t0\tdocs/harness/decisions.md` — 삽입 6, 삭제 0. `git diff ... \| grep "^-" \| grep -v "^---"` 결과 공백(삭제된 라인 없음) | PASS | 결함 0건 |
| IT-08 | 단계 간 데이터 흐름(DEF-001/DEC-034 실측) — "1번 스텝(시크릿 사전점검) 통과 → 3번 스텝(`pg_dump`) 실제 실행" 체인을 **실제 `pg_dump` 바이너리**로 재현 | conda-forge PostgreSQL 18.6 `pg_dump.exe`(격리 conda env), 워크플로에서 직접 추출한 `step1.sh`/`step3.sh` | (a) `NEON_BACKUP_DATABASE_URL=" "`(공백 1개)로 `step1.sh` 실행 → exit 확인. (b) exit 0이면 그대로 이어서 `GITHUB_ENV`를 임시파일로 지정하고 동일 값으로 `step3.sh`(`pg_dump ... \| gzip`) 실행 → exit/생성 파일 확인. (c) 대조군으로 명백히 존재하지 않는 호스트명(`postgres://baduser:badpass@this-host-does-not-exist-wu10-test.invalid:5432/db`)으로 (b)를 반복 | DEC-034의 주장("1번 통과해도 3번이 `set -euo pipefail`로 결국 실패, 조용한 성공 없음")이 실측으로 재현되어야 함 | (a) `exit=0`(DEF-001 그대로 재현 — 공백 값이 "설정됨"으로 오인됨, 06단계와 동일). (b) `step3.sh`를 그대로 연결 실행한 결과 **행(hang)** — Windows 샌드박스에서 `pg_dump`가 호스트 미지정 시 기본 로컬 연결을 시도하며 10초 타임아웃(`timeout 10`)까지도 반환하지 않아 강제 종료(`exit=124`), 생성된 `.sql.gz` 파일은 0바이트(펌프 데이터 없음 — 4번 스텝 "Verify dump is non-empty"가 있었다면 포착했을 상태). (c) 대조군(명백히 무효한 호스트명)은 `pg_dump: error: could not translate host name ... : Name or service not known`로 **즉시(1초 미만) 실패**, `set -euo pipefail`에 의해 `step3.sh` `exit=1` — 조용한 성공이 아님을 명확히 재현 | PASS(핵심 주장 재현됨) — **단, 정보성 관찰 1건 발견** | DEC-034의 "결국 실패한다"는 결론 자체는 (c)로 실증되어 유효하다. 다만 (b)에서 "공백 문자값" 특유의 경계 케이스가 **즉시 실패가 아니라 행(hang)**으로 나타난 것은 새로운 발견(06단계는 1번 스텝만 단독 실행해 이 경로를 실측하지 못했음) — 상세 분석은 §6/§8 |

> 정상 경로(Happy Path)는 06단계(`unit-10-test.md` TC-001~012, TC-EXT-01~06)가 이미 충분히 커버했으므로 이번 07단계는 반복하지 않고 전량 경계 검증에 집중했다(페르소나 원칙 — "단위 테스트를 반복하지 않는다").

## 5. 커버리지
- 이번 07단계가 의도한 커버리지: §1에서 정의한 "WU-10 × 다른 업무 단위 경계" 5개 항목(시크릿 이름/버킷 체계/복구-배포 흐름/문법 재현성/회귀) 전부 IT-01~08에 1:1 이상 대응됨(IT-01↔①, IT-02↔②, IT-03↔③, IT-04/05↔④, IT-06/07↔⑤). DEF-001/DEC-034 실측(IT-08)은 작업 지시가 명시한 "결함 0건/Fixed 확인"을 위한 심화 재검증이다.
- 06단계 AC 커버리지 재확인: `unit-10-test.md`의 AC1~9/12는 06단계가 이미 독립 재현 PASS(재반복 안 함, 이번 07단계 IT-04/05가 재현성만 교차확인), AC10~11은 여전히 "검증 불가"로 정직하게 유지(10단계 이관, 이번 07단계도 GitHub Actions 트리거/실제 Neon·R2 자격증명 둘 다 이용 불가능함을 §2 제외범위에서 재확인).
- 커버되지 않은 부분과 사유: (1) 실제 GitHub Actions 러너 실행 — 구조적으로 이번 단계에서 검증 불가(§2), 10단계 이관. (2) 실제 Neon/R2 자격증명을 사용한 네트워크 호출 — 동일 사유로 10단계 이관. (3) IT-08에서 발견한 "공백 값 + 로컬/샌드박스 특유의 연결 행(hang) 조합"이 실제 `ubuntu-latest` 러너에서도 재현되는지는 이번 단계에서 확인 불가(§8에 10단계 실측 권고로 명시).

## 6. 결함(Defect) 목록

| ID | 설명 | 재현 절차 | 심각도(Critical/High/Medium/Low) | 상태(Open/Fixed/Deferred) | 조치 내용 |
|----|------|-----------|-----------------------------------|----------------------------|-----------|
| (없음) | 이번 07단계에서 신규로 발견된 결함은 없다. DEF-001(Low, Deferred, DEC-034)은 06단계가 이미 등록했고 이번 단계가 실제 `pg_dump`로 재현·재확인만 했다(신규 결함 아님, 상태 변경 없음 — 여전히 Deferred) | - | - | - | - |

- **결함 0건**(신규). 근거: IT-01~07 전부 PASS(불일치/침범/버킷혼용/거버넌스 훼손 없음), IT-08은 기존 DEF-001(Low, Deferred)의 재현 범위 안에서 PASS(조용한 성공 없음이라는 핵심 주장 유효).
- **정보성 관찰 1건(결함 아님, DEF-001/DEC-034에 대한 보강 근거)**: OBS-WU10IT-01 — IT-08(b)에서, `NEON_BACKUP_DATABASE_URL`이 공백 문자로만 구성된 경우(DEF-001의 정확한 트리거 조건) `pg_dump`가 이 Windows 샌드박스에서 **즉시 실패가 아니라 행(hang)**했다(대조군 IT-08(c)의 "명백히 무효한 호스트명"은 1초 미만으로 즉시 실패함과 대비). 원인 추정: 공백 값은 URI로 파싱되지 않아 libpq가 "호스트 미지정" 기본 동작(로컬 연결 시도)으로 폴백하는데, 이 샌드박스의 소켓/네트워크 정책이 일반적인 즉시 `ECONNREFUSED`가 아니라 무응답으로 이어진 것으로 보인다(`unit-10-test.md` TC-EXT-05가 이미 "이 샌드박스는 바인드 자체가 거부된다"는 별개의 네트워크 이상 동작을 규명한 바 있어, 같은 계열의 샌드박스 특성으로 판단). **이것이 실제 `ubuntu-latest` GitHub Actions 러너에서도 재현되는지는 이번 단계에서 확인할 수 없다** — 리눅스 표준 동작(호스트 미지정 시 유닉스 도메인 소켓 `/var/run/postgresql` 등 시도 → 소켓 파일 부재 시 즉시 오류)을 따른다면 실제 러너에서는 빠르게 실패할 가능성이 높지만, 확인 없이 단정하지 않는다. 실무적 영향: 어느 쪽이든 `timeout-minutes: 20`(워크플로 전체 잡 타임아웃)이 최종 안전망이므로 "영구 무응답/조용한 성공"으로는 이어지지 않으나, 만약 실제 러너에서도 행(hang) 양상이 나타난다면 빠른 실패(수 초) 대신 최대 20분을 소모하고서야 실패가 확정되므로 알림 지연 측면에서 DEF-001의 실무적 우선순위를 소폭 높일 근거가 된다. 이 관찰은 새 DEC를 만들지 않고 DEC-034/DEF-001에 대한 보강 근거로 §8에 10단계 실측 권고와 함께 남긴다(코드 수정 없이 관찰만 기록 — 범위 외 코드 수정 금지 원칙 유지).

## 7. 테스트 환경 정리(Teardown) 확인 — 규칙 K
- 이번 테스트에서 생성한 임시 아티팩트 목록(경로 포함):
  - `...\scratchpad\wu10-it\actionlint.zip`, `actionlint_bin\`(actionlint.exe 포함), `checksums.txt`
  - `...\scratchpad\wu10-it\shellcheck.zip`, `shellcheck_bin\`(shellcheck.exe 포함)
  - `...\scratchpad\wu10-it\pgenv\`(conda 환경, PostgreSQL 18.6 `pg_dump.exe`/`pg_dumpall.exe` 포함)
  - `...\scratchpad\wu10-it\extracted\`(워크플로에서 추출한 `step1.sh`~`step8.sh`), `gh_env*.txt`, `*.sql.gz`(빈 덤프 산출물), `db-backup-*.sql.gz`
- 위 아티팩트를 전부 `.harness-tmp/` 하위에서만 생성했는가 (규칙 K 1번): **[ ] 예 / [x] 아니오** — 사유: 작업 지시가 "저장소 밖 세션 스크래치패드를 쓰는 것도 무방(직전 시도가 그렇게 했음, 규칙K 취지를 오히려 더 안전하게 충족)"이라고 명시적으로 승인했다. 실제로 전 과정에서 저장소(`AI-AUTO-WORK`) 내부에는 **어떤 임시 파일도 생성하지 않았다** — `.harness-tmp/`(루트) 및 `webapp/.harness-tmp/` 둘 다 작업 종료 시점까지 존재하지 않음을 `ls`로 재확인(생성 자체를 하지 않았으므로 "정리 대상"이 없는 가장 안전한 형태).
- 정리(삭제) 완료 여부: `actionlint.zip`/`actionlint_bin`/`checksums.txt`/`shellcheck.zip`/`shellcheck_bin`/`extracted`/`gh_env*.txt`/`*.sql.gz`는 전부 삭제 완료. `pgenv`(conda 환경)는 `conda env remove -p ./pgenv -y`로 패키지/환경 등록은 완전히 해제되었으나(`conda env list`에서 더 이상 조회되지 않음), 방금 종료시킨 `pg_dump.exe` 프로세스(PID 22176, `taskkill /F`로 강제 종료함)가 남긴 Windows 파일 잠금으로 `pgenv/Library/bin/` 빈 디렉터리 트리 1개가 `rm -rf`/PowerShell `Remove-Item -Force` 양쪽 시도 모두에서 즉시 삭제되지 않았다(**정직하게 기록** — 은폐하지 않음). 이 잔여물은 (a) 저장소 밖 세션 스크래치패드에만 존재하고 저장소에는 전혀 영향이 없으며, (b) 애플리케이션 코드나 시크릿을 담고 있지 않은 빈 디렉터리이고, (c) 세션 스크래치패드 자체가 "세션 전용/프로젝트와 격리된" 디렉터리로 다음 OS 재시작/세션 정리 주기에 자연 소멸 대상이다. 저장소 관점(규칙K의 실질적 목적)에서는 정리가 완료된 것과 동일한 효과다.
- 정리 후 `git status` 실행 결과 (저장소 루트, 그대로 첨부):
  ```
  $ bash automation/harness-janitor.sh --check
  [janitor] 점검 대상 저장소: C:/big21/vibe-coding/AI-AUTO-WORK
  [janitor] .harness-tmp/ 는 비어있거나 없습니다 — 이상 없음.
  [janitor] 잔여 임시 아티팩트 없음 — 다음 단계 진행 가능.

  $ git status
  On branch PROD_SCH
  nothing to commit, working tree clean
  ```
  (위 스냅샷은 본 보고서 및 `verify-log_feature-WU-10-integration-test.md` 파일을 작성하기 **직전** 시점의 것이다 — 이 두 파일과 `docs/harness/traceability.md` 갱신은 07단계의 정상적인 출력물이며 규칙K가 말하는 "정리 대상 임시 아티팩트"가 아니므로, 작성 후에는 `git status`에 이 3개 파일이 신규/수정으로 나타나는 것이 정상이다. 작업 지시에 따라 이 산출물들은 커밋/추가(`git add`/`git commit`)하지 않았다.)
- 이번 테스트 도중 강제 중단(TaskStop 등)이 있었는가: **[x] 없음** / [ ] 있음
- 규칙K 관점 결론: 저장소 내부에는 정리해야 할 임시 아티팩트가 처음부터 없었고(`.harness-tmp/` 미사용, 스크래치패드 전용 사용), 스크래치패드의 미미한 잔여물도 저장소·애플리케이션에 영향이 없음을 확인했으므로 규칙K 취지(중단-안전 정리, 저장소 청결)는 충족되었다고 판단한다.

## 8. 리스크 및 잔존 이슈
- 이번 테스트로 커버되지 않는 알려진 리스크:
  1. **실제 GitHub Actions 러너에서의 종단 간 실행** — 스케줄/수동 트리거 양쪽 모두 미검증(구조적 제약, 06단계와 동일 결론). 10단계 이관.
  2. **실제 Neon/R2 자격증명을 사용한 네트워크 호출 성공 여부** — 동일 사유로 10단계 이관.
  3. **OBS-WU10IT-01(신규, §6)** — 공백 전용 시크릿 값(DEF-001 트리거 조건)이 실제 `ubuntu-latest` 러너에서도 "빠른 실패"가 아니라 "느린 실패(최대 20분 타임아웃)"로 이어질 가능성을 완전히 배제하지 못함. **10단계에 구체적으로 권고**: 실제 러너에서 `NEON_BACKUP_DATABASE_URL` 시크릿 값을 의도적으로 공백 1개로 설정해 워크플로를 수동 트리거해보고, 실패까지 걸리는 시간을 실측할 것(수 초 내 실패면 OBS-WU10IT-01은 이 샌드박스 특유의 현상으로 결론, 20분 근접이면 DEF-001의 심각도를 Low→Medium 재검토하고 `[ -z "${value// }" ]` 보강을 11단계 이전에 앞당길 것을 권고).
  4. **`apt-get install postgresql-client`가 `ubuntu-latest` 러너에서 실제로 성공하는지, `aws` CLI가 사전 설치되어 있는지** — note/06단계와 동일하게 미검증, 10단계 이관.
  5. **Neon PITR 콘솔 메뉴 명칭 실측**(`BACKUP_RESTORE_GUIDE.md` §3-1) — 10단계 이관(기존 인계 유지).
- 후속 조치가 필요한 항목: (a) 10단계에서 실제 GitHub Secrets 6종 설정 후 스케줄/수동 트리거 양쪽 실행 성공 확인. (b) 10단계에서 재난복구 리허설 1회(신규 Neon 프로젝트에 실제 백업 파일 복구, RTO 1시간 목표 실측). (c) OBS-WU10IT-01 실측(위 3번). (d) DEF-001 보강(`[ -z "${value// }" ]` 또는 값 트리밍) 반영 여부를 코드 소유자가 최종 판단 — 이번 07단계도 Critical/High가 아니므로 즉시 재작업을 강제하지 않는다(규칙F 비례 원칙, DEC-034 판단 유지).

## 9. 결론 및 판정
- [x] **PASS** — 다음 단계(8단계, 전체 풀테스트) 진행 가능 (7절 Teardown 확인 완료가 전제조건 — 충족)
- 판정 근거: IT-01~07 전부 PASS(시크릿 이름 일치/버킷 분리 무결/복구-배포 흐름 무모순/문법 재현성 확보/회귀 없음/거버넌스 append-only 확인), IT-08은 DEF-001(Low, Deferred, DEC-034)의 핵심 주장("조용한 성공으로 이어지지 않는다")을 실제 `pg_dump` 바이너리로 재현해 유효함을 확인했다. 신규 Critical/High/Medium 결함 0건. 정보성 관찰 1건(OBS-WU10IT-01)은 기존 Low 결함의 실무적 우선순위 판단에 참고자료를 더하는 성격이며 규칙F상 재작업을 강제하는 사유가 아니다(비례 대응). Teardown(§7)은 저장소 내부 기준으로 완전히 클린하며, 스크래치패드의 미미한 잔여물은 저장소·애플리케이션에 영향이 없음을 근거와 함께 투명하게 기록했다.
- **WU-10(5→6→7단계) 완료**. 다음 남은 업무 단위는 WU-11(부가기능, Could-have)이며, 이번 세션 범위는 WU-10까지다(WU-11 착수 여부는 오케스트레이터/사용자 판단 대상).
- `docs/harness/traceability.md` 갱신: REQ-013 행의 "통합테스트" 컬럼을 `PASS(feature-WU-10-integration-test.md, IT-01~08 — 시크릿 이름/R2 버킷 분리/복구-배포 흐름 WU-01·03·09 경계 무결 확인, actionlint/shellcheck 공식 도구 재현, git diff 기반 회귀 0건 실증, DEF-001(Low)을 실제 pg_dump로 재현하되 조용한 성공 아님을 재확인. AC10/11은 06단계와 동일하게 구조적 검증 불가로 10단계 이관, 정보성 관찰 1건(OBS-WU10IT-01, 10단계 실측 권고)만 신규)`로 갱신했다(이 편집은 본 보고서 완료 직후 별도 커밋 없이 워킹트리에만 반영 — 작업 지시의 git 금지 원칙 준수).

## 10. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: §1의 5개 경계 항목이 §4 IT-01~08에 전부 매핑되어 있는지, `unit-10-note.md`/`unit-10-test.md`/`decisions.md`/`03-system-design.md`가 실제로 인용대로 반영됐는지 재대조. 오탈자/서술 정합성 결함 발견해 즉시 수정(→ v1). 상세는 검증 로그 참고.
- 2차 검증 결과 요약: "8단계(전체 풀테스트) 접점"과 "이 보고서만 보고 8단계가 추가 질문 없이 시작할 수 있는가" 관점에서 재검토 — OBS-WU10IT-01이 §6에는 있었으나 §8(리스크)의 10단계 권고 문구가 막연해 구체적 실측 방법이 없었던 gap을 발견해 §8-3에 "의도적으로 공백 값 설정 후 실패까지 걸리는 시간 실측"이라는 구체적 실행 절차를 보강(→ v2, 최종). 상세는 검증 로그 참고.
- 검증 로그 파일 경로: `docs/harness/verify-log_feature-WU-10-integration-test.md`

## 절차 흐름 (참고용 다이어그램)
```mermaid
flowchart TD
    A["해당 feature의 모든 06 결과 PASS 확인<br/>unit-10-test.md PASS 재확인"] --> B["단위 간 경계 검증(4절)<br/>WU-01/03/09와의 시크릿·버킷·배포흐름 경계"]
    B --> C["회귀 확인(IT-06/07)<br/>git diff로 WU-01~09 소스 무변경 실증"]
    C --> D["DEF-001 단계간 데이터흐름 재현(IT-08)<br/>실제 pg_dump로 1번→3번 스텝 체인 실행"]
    D --> E{통합 시점 설계 결함 발견?}
    E -->|No, 정보성 관찰 1건만| G["내부검증 1차/2차(10절)"]
    G -->|PASS| H["traceability.md 통합테스트 갱신<br/>8단계로 handoff"]
```
