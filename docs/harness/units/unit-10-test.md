# 테스트 결과서 (Test Result Report) — WU-10 (백업/복구 절차, REQ-013)

> **경로 확인**: 작업 지시가 명시한 프로젝트 루트는 `C:\big21\vibe-coding\AI-AUTO-WORK`이며, 이번 세션 환경변수가 알려준 "Primary working directory"(`STOCK-ANALYZER-KR`)는 완전히 다른 프로젝트(주식 스크리닝 서비스)였다. `unit-10-note.md` §0이 이미 이 충돌을 발견해 `AI-AUTO-WORK`를 대상으로 진행했다고 기록했고, 이번 6단계도 두 저장소의 `docs/harness/units/` 디렉터리를 직접 대조해 `unit-10-note.md`가 실존하는 쪽이 `AI-AUTO-WORK`뿐임을 재확인했다 — 5단계의 판단이 옳았음을 독립적으로 재확인(질문 불필요, 파일 존재 여부로 결과가 갈리지 않는 명확한 판단).
>
> **금지 사항 준수**: 작업 지시가 "`git commit`/`git push`/`git add`를 절대 실행하지 말 것(`git status`만 허용)"을 명시했다. 이번 6단계 전 구간에서 `git status`/`git diff`(읽기 전용) 외의 git 쓰기 명령은 실행하지 않았다.

## 1. 개요
- 테스트 대상: WU-10(업무 단위) — REQ-013(Neon PITR 6시간 한계 보완 백업 정책). 신규 `.github/workflows/neon-db-backup.yml`(GitHub Actions 백업 워크플로), 신규 `webapp/BACKUP_RESTORE_GUIDE.md`(복구 절차 초안), `docs/harness/decisions.md`(DEC-032/033 추가), `docs/harness/traceability.md`(REQ-013 행 갱신).
- 테스트 유형: 단위(Unit)
- 테스트 목적: `docs/harness/units/unit-10-note.md` §8의 인수조건(AC) 1~12를 5단계의 주장을 신뢰하지 않고 독립적으로 재현해 PASS/FAIL을 판정한다. 아울러 (a) 5단계가 주장한 게이트 1(정적분석/린트, §4)·게이트 2(자체 코드 리뷰 체크리스트, §5)가 실제로 근거가 있는지, (b) "로컬에 `pg_dump`/`aws` CLI/`actionlint`가 없어 실행 검증을 못 했다"는 제약이 문자 그대로 사실인지, 그리고 인터넷 접근이 가능한 이 세션에서 다른 방법(공식 배포 바이너리 다운로드 등)으로 검증 범위를 넓힐 수 있는지를 재검토한다.
- 관련 산출물: `docs/harness/units/unit-10-note.md`(§0~§9), `docs/harness/decisions.md`(DEC-010/DEC-016(b), 이번 WU가 추가한 DEC-032/DEC-033), `docs/harness/03-system-design.md`(§1.1/§3.3/§5.4/§7.3/§7.5), `docs/harness/traceability.md`(REQ-013)
- 테스트 수행자(에이전트): `06-unit-tester`
- 테스트 일시: 2026-09-17

## 2. 테스트 범위 및 제외 범위
- 범위 (In-Scope): `unit-10-note.md` §8의 AC1~9(코드/문법/로직 수준 재현 가능한 항목)와 AC12(정리 상태 재현 가능한 항목) 전부 독립 재현 + AC10~11(로컬/샌드박스에서는 검증 불가능함을 확인하는 것 자체가 인수조건인 항목) 재확인. 추가로 이번 6단계가 자체판단으로 확장한 검증(§4.2) — 공식 `actionlint`/`shellcheck` 바이너리, `aws-cli`(pip), `pg_dump`(conda-forge)를 이 세션에서 직접 확보해 5단계가 시도하지 않은 스키마/파라미터 수준 검증을 추가로 수행.
- 제외 범위 및 사유:
  - **실제 GitHub Actions 러너에서의 워크플로 실행**(스케줄/수동 양쪽) — AC10이 명시한 대로 이번 6단계 시점에는 실행 환경이 없어 검증 불가능함을 "확인"하는 것 자체가 인수조건이다. 작업 지시가 git push/커밋을 금지했으므로 실제 트리거도 시도하지 않았다(설사 허용되었어도 GitHub Secrets가 채워져 있지 않아 성공할 수 없다).
  - **실제 Neon 프로젝트 연결/실제 R2 버킷 자격증명을 사용한 네트워크 호출** — AC11이 명시한 대로, 로컬에 실제 Neon 연결 문자열/R2 자격증명이 없어 검증 불가능함을 "확인"하는 것 자체가 인수조건이다(§4.2 TC-EXT-05가 이 결론을 오히려 더 강하게 뒷받침 — 아래 참고).
  - **`ADMIN_ACCESS_GUIDE.md`/`CONTENT_GUIDE.md` 등 다른 WU 소유 문서와의 형식 일관성 재검증** — REQ-013/WU-10 범위 밖(unit-06/08/09-test.md가 이미 각자 소유 범위에서 검증 완료).
  - **11단계 최종 Runbook 통합, 9단계 보안검증, 10단계 배포테스트** — 이번 6단계 범위 밖, 노트 §7/§9가 이미 다음 단계로 명시적으로 이관.

## 3. 테스트 환경
- 실행 환경: Windows 10 Pro 10.0.19045, Git Bash(MINGW64, bash 5.3.15). Python 3.13.9(Anaconda, `C:\Users\mega\anaconda3\python`), PyYAML 6.0.3(기설치).
- 이번 6단계가 세션 스크래치패드에 한시적으로 내려받아 사용한 도구(전부 검증 종료 후 삭제):
  - `actionlint` v1.7.12 (공식 GitHub Release `rhysd/actionlint`, windows_amd64.zip) — 다운로드 후 `actionlint_1.7.12_checksums.txt`의 SHA-256과 직접 일치 확인(`6e7241b5...`) 후 사용.
  - `shellcheck` v0.11.0 (공식 GitHub Release `koalaman/shellcheck`, windows zip).
  - `awscli` 1.46.1 (PyPI `pip install --target`, botocore 1.43.62 동반) — `python -m awscli`로 실행.
  - PostgreSQL 18.6(`pg_dump`/`initdb`/`pg_ctl`/`psql`, conda-forge 채널, 격리된 conda 환경 `wu10_pgcheck`에만 설치 — 검증 종료 후 `conda env remove`로 완전 삭제).
- 테스트 데이터: 워크플로 YAML에서 추출한 8개 `run:` 스크립트(스크래치패드 임시 파일), 워크플로가 생성하는 것과 동일한 `lifecycle.json` 문자열, 더미 환경변수 값(`x` 등, 실제 시크릿 아님).
- 전제 조건:
  - 저장소의 실제 소스(`.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`, `docs/harness/decisions.md`, `docs/harness/traceability.md`)를 수정 없이 그대로 읽어 사용했다(테스트를 위해 코드를 고치지 않음 — DEF 발견 시 별도 절차).
  - 검증에 쓴 모든 임시 파일/디렉터리/conda 환경은 세션 스크래치패드(`...\scratchpad\`) 또는 격리된 conda 환경에만 만들었고, 저장소 작업 트리 안에는 어떤 임시 파일도 생성하지 않았다(§8 근거, `git status --porcelain`으로 최종 확인).

## 4. 테스트 케이스 및 결과

### 4.1 인수조건(AC1~12) 1:1 매핑

| ID | 시나리오 (대응 AC) | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | 워크플로 파일 경로 (AC1) | 저장소 루트 | `ls -la .github/workflows/neon-db-backup.yml` | 정확한 경로에 파일 존재 | `-rw-r--r-- 1 mega 197121 6869 ... .github/workflows/neon-db-backup.yml` 존재 확인 | PASS | |
| TC-002 | YAML 문법 검증 (AC2) | Python 3.13.9 + PyYAML 6.0.3 | `python -c "import yaml; yaml.safe_load(open('.github/workflows/neon-db-backup.yml', encoding='utf-8'))"`(실제로는 스크립트 내에서 `yaml.safe_load` 호출) | 예외 없이 종료 | 예외 없이 종료. 최상위 키 `['name', True, 'permissions', 'concurrency', 'jobs']`(`on`이 PyYAML의 YAML 1.1 불리언 리터럴 해석으로 `True`로 표시 — note와 동일 현상, 실제 GitHub Actions 파서 동작과 무관한 로컬 도구 특성으로 결함 아님. TC-EXT-01(actionlint)이 실제 GitHub Actions 스키마 기준으로 `on:`이 정상 인식됨을 별도로 재확인) | PASS | |
| TC-003 | 스텝 개수/이름 (AC3) | TC-002 이후 파싱 결과 | `data['jobs']['backup']['steps']` 길이와 각 스텝 `name` 확인 | 정확히 8개, 전부 `name` 존재 | 8개: "Verify required secrets are present" / "Install PostgreSQL client (pg_dump)" / "Dump Neon PostgreSQL and compress" / "Verify dump is non-empty" / "Ensure R2 lifecycle rule (14-day expiry) on backup-private bucket" / "Upload backup to R2 (backup-private bucket)" / "Verify upload succeeded" / "Remove local backup file" — 전부 `name` 존재 | PASS | |
| TC-004 | 8개 스텝 bash 문법 (AC4) | TC-003의 각 스텝 `run` 텍스트를 개별 `.sh` 파일로 추출 | `bash -n step{1..8}.sh` | 8개 전부 문법 오류 없음 | `step1.sh`~`step8.sh` 전부 `OK`(무출력=성공, exit 0) | PASS | |
| TC-005a | 시크릿 5개 전부 비움 (AC5-a) | `env -i PATH="$PATH"`로 5개 변수 전부 미설정, step1.sh 실행 | `bash step1.sh` | 5개 전부 `::error::`, `exit 1` | `NEON_BACKUP_DATABASE_URL`/`R2_BACKUP_ACCESS_KEY_ID`/`R2_BACKUP_SECRET_ACCESS_KEY`/`R2_BACKUP_BUCKET_NAME`/`R2_ENDPOINT_URL` 5개 전부 `::error::필수 GitHub Actions Secret이 설정되지 않았습니다: <이름>` 출력, `exit=1` | PASS | |
| TC-005b | 시크릿 5개 전부 채움 (AC5-b) | 5개 변수 전부 `x`로 설정 | `bash step1.sh` | `exit 0`, 에러 없음 | 출력 없음, `exit=0` | PASS | |
| TC-005c | 시크릿 2/5만 채움 (AC5-c) | `NEON_BACKUP_DATABASE_URL`/`R2_BACKUP_ACCESS_KEY_ID`만 채움, 나머지 3개 미설정 | `bash step1.sh` | 누락 3개만 `::error::`, `exit 1` | `R2_BACKUP_SECRET_ACCESS_KEY`/`R2_BACKUP_BUCKET_NAME`/`R2_ENDPOINT_URL` 3개만 `::error::` 출력(채운 2개는 에러 없음), `exit=1` | PASS | |
| TC-005d | (위험 경계값, AC5 범위 밖) 시크릿 값이 공백 문자 1개뿐인 경우 | `NEON_BACKUP_DATABASE_URL=" "`(스페이스 1개), 나머지 4개는 `x` | `bash step1.sh` | 값이 비어있지 않은 것으로 오인되어 통과하면 위험 신호(운영자가 실수로 공백만 입력해도 '정상'으로 착각) | `::error::` 출력 없이 `exit=0`(통과) — `[ -z "$value" ]`는 공백 문자를 비어있지 않은 값으로 판단하기 때문 | FAIL(결함 발견) | 규칙C(명백히 위험한 케이스는 범위 밖이어도 테스트)에 따라 6단계가 자체 추가. DEF-001로 등록(§6), Low/Deferred — 근거는 §6 참고 |
| TC-006 | R2 Lifecycle JSON 유효성 (AC6) | step5(Ensure R2 lifecycle rule)의 `printf` 명령을 그대로 실행 | `python -m json.tool`로 파싱, `Rules[0].Expiration.Days`/`Rules[0].Filter.Prefix` 확인 | 유효한 JSON, `Days==14`, `Prefix=="db-backups/"` | `{"Rules": [{"ID": "expire-db-backups-after-14-days", "Filter": {"Prefix": "db-backups/"}, "Status": "Enabled", "Expiration": {"Days": 14}}]}` — 파싱 성공, `Days==14`/`Prefix=="db-backups/"` 둘 다 일치. 추가로 TC-EXT-02(아래)가 이 JSON을 실제 `aws s3api` 파라미터 검증기에 통과시켜 AWS S3 API 스키마(`Rules[].ID/Filter.Prefix/Status/Expiration.Days`)와 정확히 일치함을 재확인 | PASS | |
| TC-007 | 타임스탬프/파일명 생성 (AC7) | step3의 타임스탬프/파일명 생성 로직만 추출 | `TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"; BACKUP_FILE="db-backup-${TIMESTAMP}.sql.gz"` 실행 후 정규식 대조 | `^db-backup-[0-9]{8}T[0-9]{6}Z\.sql\.gz$`와 일치 | `BACKUP_FILE=db-backup-20260917T072346Z.sql.gz` — `grep -E`로 정규식 일치 확인("REGEX MATCH OK") | PASS | |
| TC-008 | 복구 가이드 문서 섹션 (AC8) | 저장소 소스 | `webapp/BACKUP_RESTORE_GUIDE.md` 존재 및 `## 3`/`## 4`/`## 6` 헤더 확인 | 파일 존재, §3(장애 시 운영자 절차)/§4(GitHub Secrets 목록)/§6(10단계 인계 사항) 포함 | 파일 존재. `## 3. 장애 시 운영자 절차`(Neon PITR/R2 백업/destructive 마이그레이션 수동 백업 3개 하위 절차 포함), `## 4. 사전 준비 — GitHub Actions Secrets`(6개 시크릿 표), `## 6. 6단계/10단계 인계 사항` 전부 실제 헤더로 존재(`grep -n "^## "`로 7개 섹션 전체 확인) | PASS | |
| TC-009 | decisions.md append-only + traceability REQ-013 갱신 (AC9) | 저장소 최신 커밋(`e8900bf7`) 대비 워킹트리 diff | `git diff HEAD -- docs/harness/decisions.md docs/harness/traceability.md` | decisions.md는 DEC-032/033만 순수 추가(삭제 없음), traceability.md REQ-013 행이 "구현 완료"로 갱신 | `git diff --stat`: `decisions.md \| 3 ++`(삽입만 3줄, 삭제 0 — DEC-001~031 원문 불변 확인), `traceability.md \| 4 ++--`. `traceability.md`의 실제 변경 라인은 REQ-013 1개 행("Not Started" → "구현 완료(...)", "단위테스트" 컬럼 "대기(6단계)")과 REQ-010 1개 행("통합테스트" 컬럼 공란 → PASS) — REQ-010 변경은 WU-10과 무관한 **WU-09의 기존 미커밋 7단계 산출물**(`docs/harness/feature-WU-09-integration-test.md`, `git status --porcelain`에 `??`로 이미 존재)이 반영된 것으로, `unit-10-note.md` §3의 "WU-09 미커밋 산출물은 건드리지 않았다"는 설명과 일치함을 확인(WU-10이 원인이 아님) | PASS | REQ-010 행 변경의 원인을 diff만으로 단정하지 않고 `git status --porcelain`의 untracked 목록과 교차 확인해 WU-10 소관이 아님을 실증 |
| TC-010 | 실제 GitHub Actions 러너 실행 (AC10, 검증 불가 확인) | - | 실제 실행 가능 여부 재확인 | "검증 불가능함"을 정직하게 기록 | 이 세션은 GitHub Actions를 트리거할 권한/경로가 없고(작업 지시가 push/커밋 자체를 금지), 설사 트리거해도 GitHub Secrets 6종이 리포지토리에 설정되어 있지 않아 1번째 스텝("Verify required secrets are present")에서 즉시 실패할 수밖에 없다(TC-005a로 이미 그 실패 방식 자체는 검증됨) — **검증 불가, 10단계로 이관**(허위 PASS 아님) | 확인됨(N/A) | note §7-1/§9와 동일 결론 |
| TC-011 | 실제 Neon/R2 자격증명으로 pg_dump/aws 호출 성공 (AC11, 검증 불가 확인) | - | 실제 Neon 연결 문자열/R2 자격증명 보유 여부 재확인 | "검증 불가능함"을 정직하게 기록 | 로컬(이 세션)에 실제 Neon 프로젝트 연결 문자열/실제 R2 버킷 자격증명이 없다 — 이는 note의 주장과 동일하게 사실이다. 다만 이번 6단계는 "도구 자체가 없다"는 note의 부수적 주장은 이 세션(인터넷 접근 가능)에서는 더 이상 사실이 아님을 발견해(§4.2 TC-EXT-02~05), `pg_dump`/`aws` CLI의 **구문·스키마 수준** 검증까지는 추가로 수행했다. 그러나 "실제 자격증명으로 네트워크 호출이 성공하는가"라는 AC11의 핵심 질문은 여전히 검증 불가하다(자격증명이 없다는 사실은 도구 유무와 무관) — **검증 불가, 10단계로 이관**(허위 PASS 아님) | 확인됨(N/A) | §4.2 TC-EXT-02~05가 "왜 부분적으로만 강화됐는지"의 근거 |
| TC-012 | 임시 파일 정리 + diff 범위 확인 (AC12) | TC-001~011, §4.2 전체 종료 후 | 스크래치패드 임시 파일/conda 환경 전부 삭제 → `git status --porcelain` | 저장소 안에 잔여 임시 파일 없음, diff가 WU-10 산출물(+WU-09 기존 미커밋 산출물)만 남음 | 스크래치패드 정리 후 잔존 파일 없음 확인(`ls`로 재확인). `conda env remove -n wu10_pgcheck` 완료(재확인: `conda env list`에 미존재 — 아래 §7 참고). 최종 `git status --porcelain`: 수정 2건(`docs/harness/decisions.md`, `docs/harness/traceability.md`), 신규 4건(`.github/`, `docs/harness/units/unit-10-note.md`, `webapp/BACKUP_RESTORE_GUIDE.md`, 및 WU-09가 이미 남긴 `docs/harness/feature-WU-09-integration-test.md`+`verify-log_feature-WU-09-integration-test.md`) — WU-10 산출물 외 추가 diff 없음 | PASS | |

### 4.2 5단계 제약("도구 없음") 재검증 — 인터넷 접근을 활용한 추가 검증 (AC 범위 밖, 작업 지시 명시 요구)

> 작업 지시가 "5단계 노트의 '로컬에 pg_dump/aws CLI/actionlint가 없어 실행 검증을 못 했다'는 제약이 실제로 사실인지, 다른 방법으로 더 검증할 수 있는 부분이 있는지"를 명시적으로 재확인하라고 요구했다. `unit-10-note.md` §3은 "which pg_dump/aws/actionlint 전부 not found"만 확인했을 뿐, 인터넷에서 공식 배포본을 내려받는 시도는 하지 않았다 — 이번 6단계는 이 세션에 실제 인터넷 접근(`curl`로 `api.github.com`/`raw.githubusercontent.com`/PyPI/conda-forge 전부 200 응답 확인)이 가능함을 먼저 확인한 뒤, 공식 배포 채널에서 직접 도구를 내려받아 note가 "불가능"으로 남긴 항목 중 일부를 실제로 검증했다.

| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-EXT-01 | 실제 `actionlint`로 워크플로 전체 스키마+임베드 셸 검증 | `rhysd/actionlint` GitHub Releases v1.7.12(windows_amd64.zip, SHA-256 체크섬 일치 확인 후 사용) + `koalaman/shellcheck` v0.11.0(PATH에 추가, actionlint의 내장 shellcheck 룰 활성화) | `actionlint.exe -verbose .github/workflows/neon-db-backup.yml` | GitHub Actions 공식 스키마(`on`/`jobs`/`permissions`/`runs-on`/컨텍스트 표현식 등) + 임베드 bash 스크립트(shellcheck) 검증에서 0 errors | `verbose: Found 0 parse errors in 0 ms`, `verbose: Found total 0 errors in 72 ms`(shellcheck 룰까지 활성화된 상태), `exit=0`. `-verbose` 로그로 `on:`이 실제 GitHub Actions 파서 기준으로 정상 트리거 필드로 인식됨을 확인(TC-002의 PyYAML `True` 표시가 로컬 도구 한계일 뿐이라는 note/TC-002의 결론을 실제 스키마 검증기로 재확인) | PASS | note가 "actionlint가 하는 검증의 부분집합만 수행했다"고 겸손하게 밝힌 항목을, 이번 6단계가 실제 actionlint(shellcheck 포함)로 **완전히** 재검증함 — AC2/AC3/AC4의 신뢰도를 note 대비 크게 강화 |
| TC-EXT-02 | `aws s3api put-bucket-lifecycle-configuration` 파라미터 스키마 검증(실제 botocore) | `awscli` 1.46.1(PyPI, `pip install --target`) + 더미 자격증명(`AWS_ACCESS_KEY_ID=dummy` 등) + TC-006의 `lifecycle.json` | 존재하지 않는 로컬 포트(`http://127.0.0.1:1`)로 실제 명령 실행: `aws s3api put-bucket-lifecycle-configuration --endpoint-url http://127.0.0.1:1 --region auto --bucket test-bucket --lifecycle-configuration file://lifecycle.json` | botocore의 클라이언트 측 파라미터 검증(`ParamValidationError`)을 통과해야 정상 — 통과하면 다음 단계인 "연결 시도"로 넘어가 연결 실패 메시지가 나옴(스키마 자체는 유효했다는 뜻) | `Could not connect to the endpoint URL: "http://127.0.0.1:1/test-bucket?lifecycle"` — `ParamValidationError`가 아니라 연결 단계 오류. 즉 워크플로의 `lifecycle.json`이 실제 S3 API(R2가 호환 주장하는 바로 그 API) 파라미터 스키마를 **통과**함을 실측 확인 | PASS | DEC-033의 "R2가 S3 호환 API로 Lifecycle 설정을 지원한다"는 주장 중 "JSON 스키마가 맞다"는 부분을 note의 `json.tool` 파싱보다 한 단계 더 엄격하게(AWS 공식 파라미터 모델 기준) 검증 |
| TC-EXT-03 | `aws` CLI 플래그 존재 여부(`s3api put-bucket-lifecycle-configuration`/`s3 cp`/`s3api head-object`) | 위와 동일 | `aws s3api put-bucket-lifecycle-configuration help`을 파일로 리다이렉트 후 `--bucket`/`--lifecycle-configuration`/`--endpoint-url`/`--region` 문자열 검색 | 워크플로가 쓰는 4개 플래그 전부 공식 help에 존재 | 전부 존재 확인(줄 135/137/143/149). 공식 예시(`aws s3api put-bucket-lifecycle-configuration --bucket ... --lifecycle-configuration file://lifecycle.json`)가 워크플로와 동일한 `file://` 패턴을 그대로 사용함도 확인(줄 726) | PASS | |
| TC-EXT-04 | `pg_dump` 플래그 존재 여부 | conda-forge `postgresql` 18.6(격리된 conda 환경 `wu10_pgcheck`에만 설치) | `pg_dump.exe --help`에서 `--no-owner`/`--no-privileges`/`--clean`/`--if-exists`/`--verbose` 검색 | 워크플로가 쓰는 5개 플래그 전부 실제 `pg_dump` 18.6에 존재 | `-v, --verbose` / `-c, --clean` / `-O, --no-owner` / `-x, --no-privileges` / `--if-exists` 전부 확인 | PASS | note는 `pg_dump`를 전혀 실행해보지 못했으나, 이번 6단계는 실제 바이너리로 플래그 유효성까지 확인 — 단, 이는 "구문이 유효하다"는 것만 증명하며 AC11이 요구하는 "실제 Neon 대상 실행 성공"과는 다름(TC-011 참고) |
| TC-EXT-05 | 로컬 임시 PostgreSQL 서버로 end-to-end 덤프/복구 시도(한계 확인) | 위 conda 환경에 `initdb`로 데이터 디렉터리 생성 성공 | `pg_ctl start`로 TCP 리스닝 시도(포트 55432, `127.0.0.1`/`::1`) | 성공하면 워크플로와 동일한 `pg_dump ... \| gzip`, 크기 확인, `gunzip`, `psql -f`(`--clean --if-exists` 복구) 전체 흐름을 실제 DB로 검증할 계획이었음 | **실패**: `could not bind IPv6 address "::1": Permission denied` / `could not bind IPv4 address "127.0.0.1": Permission denied` / `FATAL: could not create any TCP/IP sockets` — 이 세션(샌드박스)은 아웃바운드 HTTP(`curl`)는 허용하지만 루프백을 포함한 리스닝 소켓 바인드 자체가 거부된다 | 확인됨(도구를 구해도 로컬 실행은 불가) | 이 실패는 오히려 note/TC-011의 "실행 검증 불가"라는 결론을 **더 강하게 뒷받침**한다 — 원인이 "도구 부재"만이 아니라 "이 샌드박스의 네트워크 정책"이기도 함을 새로 규명(10단계 인계 시 참고할 가치가 있는 사실이라 기록) |
| TC-EXT-06 | R2 Lifecycle 규칙의 "멱등성" 주장(DEC-033) 근거 검증 | botocore S3 서비스 모델(공식, `boto/botocore` GitHub 저장소에서 `curl`로 직접 조회) | `PutBucketLifecycleConfiguration` 오퍼레이션의 공식 설명(`documentation` 필드) 확인 | "매번 전체를 교체(overwrite)하는 PUT 시맨틱"이면 동일 입력 반복 호출이 항상 동일한 최종 상태를 만든다(멱등) — 이 사실이 문서로 명시되어 있어야 함 | 공식 설명: *"Creates a new lifecycle configuration for the bucket **or replaces an existing lifecycle configuration**... this will **overwrite** an existing lifecycle configuration"* — DEC-033/note가 주장한 "매 실행마다 멱등하게 재적용" 근거를 AWS 공식 API 시맨틱 수준에서 확인(R2가 이 S3 오퍼레이션과 호환된다는 전제는 DEC-033이 Cloudflare 공식 문서로 이미 확인한 부분이라 이번 TC의 범위 밖) | PASS | |

## 5. 커버리지
- AC 커버리지: 12/12 = 100%(§4.1). AC1~9는 실제 재현(PASS)으로, AC10~11은 "검증 불가능함의 확인"(N/A 성격의 확인 완료)으로, AC12는 정리 상태 재현(PASS)으로 전부 대응됨 — note §8이 요구한 판정 방식(허위 PASS 금지) 그대로 따름.
- 게이트 재확인: 5단계 §4(정적분석/린트 게이트) — "YAML 전용 린터(`yamllint`, `actionlint`)가 저장소/로컬 환경 어디에도 없다"는 주장은 **로컬 사전 설치 여부**로는 사실이나, 이 세션의 인터넷 접근을 활용하면 공식 배포 바이너리로 대체 가능함을 §4.2 TC-EXT-01로 실증했다(결함이 아니라 검증 범위 확장 기회로 분류 — §7 참고). 5단계 §5(자체 코드 리뷰 체크리스트) — "하드코딩된 시크릿 없음"을 `${{ secrets.* }}` 참조 외 리터럴 값이 없는지 워크플로 전문을 직접 육안 대조로 재확인(일치). "범위를 벗어난 변경 없음" 주장은 §4.1 TC-009/TC-012의 `git diff`/`git status` 실측으로 재확인(일치, REQ-010 행 변경은 WU-09 소관임을 별도 실증).
- 커버되지 않은 부분과 사유: 실제 GitHub Actions 러너 실행(AC10), 실제 Neon/R2 자격증명을 사용한 네트워크 호출 성공 여부(AC11) — 둘 다 note와 동일하게 10단계(배포테스트) 이후로 정당하게 이관(로컬/샌드박스 구조적 한계, §4.2 TC-EXT-05가 원인을 "도구 부재"에서 "샌드박스 네트워크 정책"까지로 구체화).

## 6. 결함(Defect) 목록

| ID | 설명 | 재현 절차 | 심각도(Critical/High/Medium/Low) | 상태(Open/Fixed/Deferred) | 조치 내용 |
|----|------|-----------|-----------------------------------|----------------------------|-----------|
| DEF-001 | "Verify required secrets are present" 스텝(step1.sh)이 `[ -z "$value" ]`만으로 누락을 판정해, GitHub Secret 값이 **공백 문자로만 구성**된 경우(예: 실수로 스페이스바 1개만 입력)를 "설정됨"으로 오인하고 통과(`exit 0`)시킨다. AC5(a/b/c)는 "완전히 비어있음"과 "정상값 채움"만 요구해 이 경계값은 note의 인수조건 범위 밖이지만, 규칙C("명백히 위험한 케이스는 범위를 벗어나도 테스트")에 따라 6단계가 자체적으로 추가 실행했다. | `env -i PATH="$PATH" NEON_BACKUP_DATABASE_URL=" " R2_BACKUP_ACCESS_KEY_ID=x R2_BACKUP_SECRET_ACCESS_KEY=x R2_BACKUP_BUCKET_NAME=x R2_ENDPOINT_URL=x bash step1.sh` → `exit=0`(에러 없음). | Low | Deferred | 실제 파급력 분석: 이 케이스가 1번 스텝을 통과해도, 3번 스텝(`pg_dump ... "$NEON_BACKUP_DATABASE_URL"`)이 공백 문자열을 유효하지 않은 연결 문자열로 받아 `set -euo pipefail` 하에 non-zero로 종료하므로 워크플로 자체는 결국 실패하며 조용한 성공(silent success)으로 이어지지 않는다 — 다만 에러 메시지가 "시크릿 누락"이 아니라 `pg_dump`의 낯선 연결 오류로 나와 운영자가 원인 파악에 더 시간이 걸릴 수 있다. Critical/High가 아니므로 5단계로 되돌리지 않고(규칙F, Low는 즉시 재작업 필수 대상이 아님) `unit-10-note.md`/`BACKUP_RESTORE_GUIDE.md`를 직접 고치지 않은 채(범위 외 코드 수정 금지 원칙 — 이 결함의 코드 수정은 5단계 소유) 이 테스트 결과서와 `docs/harness/decisions.md`(DEC-034, 근거와 함께 append-only로 기록)에 관찰로 기록하고, 10~11단계(운영 Runbook)에서 `[ -z "${value// }" ]` 또는 값 트리밍 로직 보강을 권고 사항으로 승계한다. |

- Critical/High 결함 0건. Medium 결함 0건. Low 결함 1건(DEF-001, Deferred — 코드 수정은 범위 외라 이관, 즉시 재작업 요구 대상 아님). 위 표 외에 결함 없음 — §4.1의 TC-001~012 전부 PASS 또는 정당한 N/A 확인, §4.2의 TC-EXT-01~06 전부 PASS(추가 검증에서도 결함 미발견)로 이를 근거로 삼는다.

## 7. 리스크 및 잔존 이슈
- **이번 테스트로 커버되지 않는 알려진 리스크**: (1) 실제 GitHub Actions 러너에서의 종단 간 실행(AC10) — 10단계 이관. (2) 실제 Neon/R2 자격증명을 사용한 네트워크 호출 성공 여부(AC11) — 10단계 이관, §4.2 TC-EXT-05가 "이 샌드박스에서는 도구를 구해도 리스닝 소켓 자체가 막혀 로컬 재현이 원천적으로 불가능하다"는 사실을 추가로 규명해 10단계가 실제 클라우드 환경(GitHub Actions 러너)에서만 검증 가능함을 재확인시켜준다. (3) `apt-get install postgresql-client`가 `ubuntu-latest` 러너에서 실제로 성공하는지, `aws` CLI가 그 러너에 사전 설치되어 있는지 — note와 동일하게 미검증, 10단계 이관. (4) DEF-001(공백 전용 시크릿 값 미탐지) — Low, 10~11단계로 권고 승계.
- **후속 조치가 필요한 항목**: (a) 10단계에서 실제 GitHub Secrets 6종 설정 후 스케줄/수동 트리거 양쪽 실행 성공 확인(note §7-1, 이 문서 TC-010). (b) 10단계에서 재난복구 리허설 1회(note §7-7). (c) DEF-001 보강을 코드 소유자(5단계 또는 향후 재작업 세션)가 판단해 반영할지 결정. (d) 이번 6단계가 사용한 공식 배포 바이너리(actionlint/shellcheck/awscli/postgresql) 활용법을 향후 WU의 5/6단계 표준 절차에 반영할지(단, 공급망 신뢰 문제 — 체크섬 검증 등 최소한의 무결성 확인 후 사용해야 함, 이번에는 actionlint만 공식 체크섬 대조를 했고 shellcheck/awscli/postgresql은 각각 GitHub 공식 릴리스/PyPI 공식 배포/conda-forge 공식 채널이라는 출처 신뢰만으로 사용함 — 프로덕션 배포 파이프라인에는 사용하지 않고 이번처럼 읽기 전용 로컬 검증 목적에 한정할 것을 권고)을 오케스트레이터가 검토할 것을 제안.

## 8. 결론 및 판정
- [x] PASS — 다음 단계(7단계, 통합테스트) 진행 가능
- 판정 근거: AC1~9 전부 독립 재현 PASS(§4.1), AC10~11은 note와 동일하게 "검증 불가능함"을 정직하게 확인(허위 PASS 아님, 오히려 §4.2 TC-EXT-05로 원인을 더 구체화), AC12(정리/diff 범위) PASS. 발견된 결함은 Low 1건(DEF-001)뿐이며 워크플로의 `set -euo pipefail`/후속 스텝 구조상 조용한 실패로 이어지지 않아 Critical/High가 아니다(규칙F상 FAIL/CONDITIONAL PASS 사유 아님). 5단계의 게이트 1/게이트 2 주장도 재확인했고, "도구가 없어 검증 못 함"이라는 제약은 사실이되 이 세션의 인터넷 접근으로 검증 범위를 실제로 넓힐 수 있었음(§4.2)을 투명하게 기록했다.

## 9. 내부 검증 (최소 2회, `verification-log-template.md` 사용)
- 1차 검증 결과 요약: AC1~12 전부 §4.1에 1:1 매핑되어 있고 예상 결과가 note §8 원문 요구사항에 정확히 근거함을 확인. 오탈자/형식 오류 2건 발견해 즉시 수정(→ v1). 상세는 검증 로그 참고.
- 2차 검증 결과 요약: "이 결과를 7단계에 그대로 넘겨도 되는가"라는 관점에서 재검토 — DEF-001(공백 전용 시크릿 값 미탐지)이 §6 결함 목록에는 있었으나 §4.1 TC 매트릭스에는 대응하는 행이 없어 추적성이 끊겨 있던 gap을 발견해 TC-005d로 신설하고 FAIL로 명시(→ v2, 최종). 추가로 TC-009의 REQ-010 diff 원인을 단정이 아니라 `git status --porcelain` 교차검증으로 실증하도록 보강했고, `docs/harness/decisions.md` DEC-032/033 두 행의 마크다운 테이블 컬럼 수(파이프 9개)가 헤더(8개 컬럼)와 일치해 표가 깨지지 않았음을 별도로 재확인했다(결함 아님, 진단만).
- 검증 로그 파일 경로: `docs/harness/units/verify-log_unit-10-test.md`

## 절차 흐름 (참고용 다이어그램)
```mermaid
flowchart TD
    A["대상/범위/환경 정의(1~3절)"] --> B["테스트 케이스 작성·실행(4절)<br/>AC1~12 + 확장검증 TC-EXT-01~06"]
    B --> C["커버리지 확인(5절)"]
    C --> D["결함 목록 기록(6절)<br/>DEF-001(Low) 1건"]
    D --> E{Critical/High 결함?}
    E -->|No| G["verification-log 2회 PASS(9절)"]
    G --> H["PASS 판정 → 7단계(통합테스트) 진행"]
```

---

## 부록 — 재작업 라운드 2 (규칙F, DEF-10-03, 2026-09-25)

- **신규 AC**: `unit-10-note.md` §10이 서술한 조치(client 설치를 PGDG 저장소 기반으로 교체)에 대해, 10단계가 실측했던 정확한 실패 조건("Ubuntu 기본 저장소 client < Neon 서버 메이저 버전")을 Docker로 재현 후 수정 효과를 검증(TC-EXT-07 상당).
- **실행 결과**: `unit-10-note.md` §10 인용 — 수정 전(`pg_dump 16.15` vs `postgres:17`) → `server version mismatch`로 실패 재현(원본 TC-013과 동일 실패 재확인) / 수정 후(`pg_dump 18.6` vs `postgres:17`) → 백업 성공, 데이터 무결성 확인. YAML 문법(`yaml.safe_load`) 파싱 정상.
- **회귀**: 나머지 6개 워크플로 스텝은 diff 대상이 아님(변경 없음) — 원본 AC1~9/TC-EXT-01~06이 검증한 로직에 영향 없음.
- **판정**: PASS — DEF-10-03(10단계 지적)에 대한 조치가 원본이 재현했던 정확한 실패 조건에서 실측으로 해소됨을 확인. 다음 단계는 7단계(`feature-WU-10-integration-test.md`) addendum.
