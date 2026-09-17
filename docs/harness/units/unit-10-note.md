# WU-10 — 백업/복구 절차(Neon PITR 6시간 한계 보완) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-10, 02-planning.md §9)
- 입력: `docs/harness/decisions.md`(DEC-001~031, 특히 DEC-004/DEC-008/DEC-010/DEC-011), `docs/harness/traceability.md`(REQ-013 이전 상태: Not Started), `docs/harness/02-planning.md`(§4 REQ-013 정의, §5 KPI 7, §7 리스크 3번), `docs/harness/03-system-design.md`(v1.2, PASS — §1.1/§1.2/§2.3/§3.3/§5.4/§6.4/§7.2/§7.3/§7.4/§7.5), `webapp/render.yaml`(WU-03/WU-08이 이미 준비해 둔 `R2_BACKUP_*` env 자리)
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-013(Neon PITR 6시간 한계 보완 백업 정책)

---

## 0. 프로젝트 경로 확인

작업 지시가 명시한 프로젝트 루트(`C:\big21\vibe-coding\AI-AUTO-WORK`)와 이번 세션
환경변수가 알려준 "Primary working directory"(`STOCK-ANALYZER-KR`)가 서로 다른
저장소였다. 두 저장소의 `docs/harness/decisions.md`를 직접 열어 대조한 결과,
`AI-AUTO-WORK`가 DEC-004(Neon)/DEC-008(R2)/DEC-010(백업)/DEC-011(킵얼라이브
미도입)을 정확히 담고 있고(작업 지시가 인용한 문구와 100% 일치), `STOCK-
ANALYZER-KR`는 완전히 다른 프로젝트(주식 스크리닝 서비스, DEC-011=상장시장
정의·DEC-012=코스피/코스닥 필터)였다. 이번 WU-10은 작업 지시가 명시한
`AI-AUTO-WORK`를 대상으로 진행했다(경로 충돌 시 작업 지시 문구를 신뢰 — 파일
내용 대조로 결과가 갈리지 않는 명확한 판단이라 규칙A 질문 대상은 아니라고
판단).

---

## 1. 구현 범위

```
AI-AUTO-WORK/
  .github/
    workflows/
      neon-db-backup.yml        (신규) 1일 1회 스케줄 + 수동 트리거 백업 워크플로
  webapp/
    BACKUP_RESTORE_GUIDE.md     (신규) 복구 절차 초안(운영자용) — 11단계에서 최종 Runbook에 통합
docs/harness/
  decisions.md                   DEC-032(백업 방식/시크릿 분리/트리거 구조), DEC-033(R2 Lifecycle 자동화) 추가
  traceability.md                REQ-013 행 갱신
  units/unit-10-note.md          (이 문서)
```

### 1.1 `.github/workflows/neon-db-backup.yml`

DEC-010이 확정한 아키텍처("GitHub Actions 스케줄 워크플로 → `pg_dump` → R2
`backup-private` 버킷 업로드")를 실제로 구현했다.

- **트리거**: `schedule`(cron `0 18 * * *`, UTC 18:00 = KST 03:00, DEC-010의
  "1일 1회") + `workflow_dispatch`(수동 실행, 03 §3.3-3이 요구하는 destructive
  마이그레이션 직전 수동 백업을 이 워크플로 재사용으로 충족 — DEC-032).
- **단계 구성**: (1) 필수 시크릿 5종 사전점검(누락 시 어떤 시크릿이 없는지
  명시하고 즉시 실패) → (2) `postgresql-client` 설치(`apt-get`) → (3) `pg_dump
  --no-owner --no-privileges --clean --if-exists --verbose` 실행 후 gzip 압축
  → (4) 덤프 파일 크기 0바이트 이상 확인(조용한 실패 방지) → (5) R2 Object
  Lifecycle 규칙(14일 만료)을 `aws s3api put-bucket-lifecycle-configuration`
  으로 멱등 재적용(DEC-033) → (6) `aws s3 cp`로 R2 `backup-private` 버킷의
  `db-backups/` 프리픽스에 업로드 → (7) `aws s3api head-object`로 업로드 실제
  성공 확인 → (8) 로컬 임시 파일 정리(`if: always()`).
- **권한**: `permissions: contents: read`(최소 권한 — 이 워크플로는 저장소에
  아무것도 쓰지 않는다).
- **동시 실행 방지**: `concurrency: group: neon-db-backup, cancel-in-progress:
  false` — 스케줄 실행과 수동 실행이 겹쳐도 Neon 컴퓨트 시간을 이중으로
  소모하지 않도록 순차 대기시킨다(DEC-011의 "Neon 무료 컴퓨트시간 보호"
  정신과 일관).

### 1.2 `webapp/BACKUP_RESTORE_GUIDE.md`

작업 지시가 요구한 "복구 절차 문서화(이번 5단계 초안, 11단계에서 최종
Runbook 통합)"를 구현했다. 구성: ①백업 아키텍처 요약, ②사고 발생 시점별
복구 우선순위표(Neon PITR 6시간 이내 / R2 백업 6시간~14일 / 14일 초과 복구
불가), ③Neon PITR·R2 백업·destructive 마이그레이션 수동 백업 3가지 시나리오
별 단계별 운영자 절차(실제 명령어 포함), ④필요한 GitHub Actions Secrets
6종 목록과 각각의 용도/분리 원칙, ⑤백업 성공/실패 확인 방법(02 §5 KPI 7
대응), ⑥10단계 인계 사항(로컬에서 실측 못한 것 명시), ⑦로컬에서 실제로
검증한 범위 명시.

---

## 2. 설계서 대비 편차 (사유 포함)

이번 WU는 설계서(03 §1.1/§7.5)가 이미 확정한 아키텍처를 그대로 구현했고,
설계서가 "5단계에 위임"한 세부 사항만 자체판단으로 채웠다(DEC-032/DEC-033에
근거와 함께 기록). 설계서 문언과 실제 구현이 어긋나는 편차는 없다. 세부
구현 판단 3가지만 정리한다(전부 DEC-032/033 참고):

1. **`pg_dump` 포맷을 커스텀(`-Fc`)이 아니라 plain SQL + gzip으로 선택** —
   1인 운영(가정 A1)에서 `psql`로 바로 복구 가능한 단순함을 우선했다.
2. **백업 전용 DB 시크릿(`NEON_BACKUP_DATABASE_URL`)을 앱의 `DATABASE_URL`로
   자동 대체(fallback)하지 않도록 구현** — DEC-016(b)가 WU-03 시점 R2 백업
   자격증명에 허용했던 "임시 재사용" 패턴을 DB 쓰기 자격증명에는 적용하지
   않았다(03 §5.4 최소 권한 원칙을 더 엄격히 적용 — DB 자격증명 노출의
   파급력이 R2 media 키보다 크다고 판단).
3. **R2 Object Lifecycle 규칙을 대시보드 수동 설정이 아니라 워크플로가 매
   실행마다 S3 API로 자동 재적용** — Cloudflare 공식 문서(developers.
   cloudflare.com/r2/buckets/object-lifecycles/, 2026-09-17 직접 조회)로
   S3 호환 API 지원을 확인한 뒤 결정했다.

---

## 3. 로컬 동작 확인 (실제 실행 결과)

Windows 로컬 환경에는 `pg_dump`/`aws` CLI/`actionlint`가 전혀 설치되어
있지 않음을 먼저 확인했다(`which pg_dump`, `which aws`, `which actionlint`
전부 not found). GitHub Actions 자체도 트리거할 수 없다(WU-01~09와 동일
제약, 작업 지시가 이미 명시). 따라서 검증 범위는 **코드/문법/로직 수준**으로
한정했다.

1. **YAML 문법 검증**: `python`(로컬 설치, PyYAML 6.0.3)로 `neon-db-backup.yml`
   전체를 `yaml.safe_load()`로 파싱 — 예외 없이 성공, `jobs.backup.steps`
   8개 전부 정상 인식. (참고: 최상위 키 목록에 `'on'`이 아니라 `True`로
   표시되는데, 이는 PyYAML이 YAML 1.1 스펙의 `on/off/yes/no` 불리언 리터럴
   해석 규칙을 그대로 따르기 때문이며 실제 GitHub Actions 파서의 동작과는
   무관한 로컬 검증 도구의 알려진 특성이다 — 실제 워크플로가 매번
   "on:" 트리거로 정상 인식됨은 GitHub 공식 문서/무수한 실사용 예시로
   이미 검증된 사실이라 별도 결함으로 취급하지 않았다).
2. **각 `run:` 스텝 bash 문법 검증**: YAML에서 8개 스텝의 `run` 스크립트를
   각각 추출해 개별 파일로 저장 후 `bash -n <파일>` 실행 — 8개 전부
   `OK`(문법 오류 없음).
3. **시크릿 사전점검 로직 실제 동작 검증**: 1번 스텝의 스크립트를 그대로
   추출해 3가지 케이스로 실행 — (a) 필수 시크릿 5개 전부 비어있음 →
   5개 전부 `::error::` 메시지 출력 + `exit 1`, (b) 5개 전부 채움 →
   `exit 0`(정상 통과), (c) 일부만 채움(2/5) → 누락된 3개만 정확히
   `::error::` 출력 + `exit 1`. 3가지 모두 의도대로 동작.
4. **R2 Lifecycle JSON 생성 로직 검증**: 워크플로의 `printf` 명령을 그대로
   실행해 생성된 `lifecycle.json`을 `python -m json.load`로 파싱 — 유효한
   JSON이며 `Rules[0].Expiration.Days == 14`, `Filter.Prefix == "db-backups/"`
   확인(03 §7.5 "14일" 요구사항과 일치).
5. **타임스탬프/파일명 생성 로직 검증**: `TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"`
   → `BACKUP_FILE="db-backup-${TIMESTAMP}.sql.gz"` 실행 결과가
   `^db-backup-[0-9]{8}T[0-9]{6}Z\.sql\.gz$` 정규식과 정확히 일치함을 확인.
6. **`.github/workflows/` 디렉터리 생성 확인**: 저장소 루트 기준으로
   `.github/workflows/neon-db-backup.yml`이 정확한 경로에 위치함을
   `ls`로 확인(GitHub Actions는 이 정확한 경로에서만 워크플로를 인식한다).

**로컬에서 확인하지 못한 것(10단계 이후 인계, `BACKUP_RESTORE_GUIDE.md` §6과
동일 목록)**:
- 실제 GitHub Actions 러너에서의 워크플로 전체 실행(스케줄/수동 양쪽)
- `sudo apt-get install postgresql-client`의 실제 러너 환경 성공 여부
- `aws` CLI가 `ubuntu-latest` 러너에 실제로 사전 설치되어 있는지(GitHub
  공식 `runner-images` 문서 기준으로는 포함되어 있으나 실측 필요)
- 실제 Neon 프로젝트에 대한 `pg_dump` 실행(서버-클라이언트 버전 호환성
  포함) 및 실제 R2 버킷에 대한 `aws s3 cp`/`aws s3api put-bucket-lifecycle-
  configuration`/`head-object` 호출 성공 여부
- 실제 GitHub Secrets 값 설정 및 워크플로 종단 간(end-to-end) 성공

정리: 검증에 사용한 임시 파일은 프로젝트 저장소 밖의 세션 스크래치패드
디렉터리에만 만들었고(`script_*.sh`, `run_checks.sh`, `lifecycle.json` 등),
작업 종료 시 전부 삭제했다. `git status --porcelain` 결과 이 WU가 만든
`.github/workflows/neon-db-backup.yml`, `webapp/BACKUP_RESTORE_GUIDE.md`
(신규)와 `docs/harness/decisions.md`, `docs/harness/traceability.md`(수정)
외에 다른 소스 변경은 없음을 확인했다(WU-09가 이미 남겨둔 미커밋
`feature-WU-09-integration-test.md` 등은 이번 WU와 무관한 기존 상태이므로
건드리지 않았다 — 범위 외 변경 금지).

---

## 4. 게이트 1 — 정적 분석/린트

- `AI-AUTO-WORK` 저장소에는 Python용 lint/type-check/formatter 설정
  (`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이
  여전히 존재하지 않음을 재확인했다(WU-01~09와 동일 결론). 이번 WU는 Python
  코드를 추가하지 않았으므로 해당 사항 없음.
- YAML 전용 린터(`yamllint`, `actionlint`)도 저장소/로컬 환경 어디에도
  설정/설치되어 있지 않다(확인했으나 없음, 건너뛴 것이 아님). 대체 수단으로
  §3-1/§3-2(PyYAML 파싱 + `bash -n`)를 수행했다 — 이는 actionlint가 하는
  검증(YAML 스키마 검증 + 임베드된 셸 스크립트 문법 검증)의 부분집합이며,
  GitHub Actions 워크플로 스키마 자체(예: `on`/`jobs`/`permissions` 필드
  이름 오타 등)에 대한 완전한 검증은 아니다 — 10단계 이후 실제 GitHub
  환경에서 워크플로가 인식/실행되는지로 최종 확인 필요(§3 인계 사항과
  동일).
- Markdown 린터(`markdownlint`)도 설정되어 있지 않다 — `BACKUP_RESTORE_GUIDE.md`
  는 다른 WU가 만든 `ADMIN_ACCESS_GUIDE.md`/`CONTENT_GUIDE.md`와 동일한
  포맷 관례(제목/표/코드블록)를 따랐다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. 아키텍처
  (GitHub Actions cron + `pg_dump` + R2 `backup-private`, 03 §1.1), 트리거
  주기(1일 1회, DEC-010), Lifecycle 보관기간(14일, 03 §7.5), 수동 백업 요구
  (03 §3.3-3), 시크릿 관리 원칙(03 §5.4)을 전부 그대로 따랐다. §2의 세부
  구현 판단 3건은 설계서가 "5단계에 위임"한 것을 DEC-032/033으로 기록하며
  결정한 것이라 편차가 아니라 구현의 구체화다.
- [x] **에러 처리가 누락된 경로가 없는가** — `set -euo pipefail`을 모든
  `run:` 스텝에 적용해 어떤 명령이 실패해도(파이프 중간 실패 포함) 스텝이
  조용히 성공한 것처럼 넘어가지 않는다. 필수 시크릿 누락은 명시적으로
  탐지해 `::error::` 주석과 함께 실패시킨다(값이 비어 있는 채로 `pg_dump`가
  알 수 없는 오류를 내는 상황을 방지). 덤프 파일이 0바이트여도 별도로
  탐지해 실패시킨다(파이프가 "성공"했지만 내용이 비어있는 조용한 실패를
  방지). 백업 실패 시 GitHub 표준 기능(리포지토리 소유자 이메일)으로 알림이
  가는 것을 그대로 신뢰했다(03 §7.2가 이미 결정한 채널, 이 워크플로가 새로
  구현할 필요 없음).
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가**
  — 이 워크플로의 유일한 "입력"은 GitHub Secrets(시스템 경계)이며, 5개 필수
  시크릿 전부를 실행 초입에서 명시적으로 검증한다(§1.1 (1)). `workflow_dispatch`
  의 `reason` 입력은 사람이 읽는 로그 용도일 뿐 셸 명령에 그대로 삽입되지
  않으므로(워크플로 어디에서도 `${{ inputs.reason }}`을 셸 문자열에 보간하지
  않음) 셸 인젝션 경로가 없다.
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. 워크플로는 전부
  `${{ secrets.* }}`로만 참조하고(03 §5.4 요구사항 그대로), `BACKUP_RESTORE_GUIDE.md`
  도 실제 값 대신 `<R2_BACKUP_BUCKET_NAME>` 같은 플레이스홀더만 사용한다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `webapp/`
  기존 코드(`core/`, `blog/`, `custom_images/`, `render.yaml`, `config/settings/
  production.py`의 `STORAGES["backup"]` 등)는 전혀 건드리지 않았다. WU-03이
  이미 준비해 둔 `render.yaml`의 `R2_BACKUP_*` env 자리도 그대로 재사용만
  했을 뿐 수정하지 않았다. WU-09의 미커밋 산출물(`feature-WU-09-integration-
  test.md` 등)도 손대지 않았다. WU-11(부가 기능) 관련 파일은 전혀 만들지
  않았다.

**관찰 사항(결함 아님, 참고용)**: DEC-016(b)가 WU-03 시점에 준비해 둔 Django
`STORAGES["backup"]` 별칭(`config/settings/production.py`)은 이번 WU-10에서도
여전히 애플리케이션 코드 어디에서도 참조되지 않는다 — 03 §1.1 아키텍처가
백업을 Django 앱이 아니라 GitHub Actions(순수 `pg_dump`/`aws` CLI)로 수행하도록
명시적으로 설계했기 때문에 정상이다. 다만 이 별칭이 "왜 존재하는데 아무도
쓰지 않는지" 향후 유지보수자가 의아해할 수 있어 기록으로 남긴다(이 별칭을
제거하는 것은 WU-03 소유 코드에 대한 범위 외 변경이라 이번 WU에서 수행하지
않았다).

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-013 행을 "Not Started"에서 "구현
완료"로 갱신했다. "작업 단위" 컬럼(WU-10, 이미 채워져 있었음)은 유지하고,
"구현 상태"에 이번 구현 근거 파일 경로(`unit-10-note.md`, 워크플로,
가이드 문서)를 명시했다. "단위테스트" 컬럼은 "대기(6단계)"로 표기했고,
"통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로
비워둔 채 유지했다(WU-04~09 선례와 동일 패턴). "비고" 컬럼에 로컬 환경
제약으로 실제 실행 검증이 불가능했다는 사실과 인계 대상 문서 위치를
명시했다.

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **실제 GitHub Actions 실행 미검증**(가장 중요): 이 워크플로가 실제
   `ubuntu-latest` 러너에서 스케줄/수동 트리거 양쪽 모두 성공적으로 끝나는지
   전혀 검증하지 못했다. 6단계는 이 WU의 특성상 "실제 배포 환경 실행"을
   검증 대상으로 삼을 수 없으므로(Windows 로컬 제약, WU-01~09와 동일),
   §3에서 서술한 코드/로직 수준 검증을 6단계 인수조건으로 삼아야 한다.
   실제 실행 결과는 10단계(배포테스트) 이후로 명시적으로 이관한다(작업
   지시 원문 요구사항).
2. **`postgresql-client` 실제 설치 가능 여부**: `apt-get install postgresql-
   client`가 GitHub 호스팅 러너의 최신 이미지에서 그대로 성공하는지는
   실측이 필요하다(일반적으로 문제없이 성공하는 표준 패키지이지만, 로컬에서
   실행 불가능해 가정으로만 남긴다).
3. **`pg_dump` 클라이언트-서버 버전 호환성**: 실제 Neon 프로젝트가 구동하는
   PostgreSQL 메이저 버전을 확인한 뒤, apt가 설치하는 클라이언트 버전과
   호환되는지 10단계에서 확인 필요(`BACKUP_RESTORE_GUIDE.md` §6-2).
4. **R2 Lifecycle API 실제 호출 성공 여부**: Cloudflare 공식 문서로 S3 API
   지원을 확인했으나 실제 자격증명으로 호출해본 것은 아니다.
5. **GitHub Secrets 6종의 실제 발급/설정**: `NEON_BACKUP_DATABASE_URL`(별도
   Neon role 권장), `R2_BACKUP_ACCESS_KEY_ID`/`R2_BACKUP_SECRET_ACCESS_KEY`
   (`backup-private` 버킷 전용, media-public과 분리 권장 — DEC-016(b)가
   WU-10에서 재검토하도록 남긴 항목), `R2_BACKUP_BUCKET_NAME`,
   `R2_ENDPOINT_URL`, `R2_REGION` — 전부 실제 인프라가 준비되는 배포 단계
   (10~12단계)에서 운영자가 채워야 한다.
6. **GitHub 계정 알림 설정 확인**: 백업 실패 시 GitHub 기본 이메일 알림이
   실제로 리포지토리 소유자에게 도달하려면, 해당 GitHub 계정의 Actions
   알림 설정이 켜져 있어야 한다 — 10단계에서 강제로 실패를 유발해 실측
   확인 권고(WU-08의 500 에러 이메일 알림 실측 권고와 동일한 성격).
7. **재난복구 리허설 미실시**: 실제 백업 파일을 실제로 복구해보는 리허설은
   이번 WU 범위에 포함되지 않는다(로컬에 Neon/R2가 없어 수행 불가) — 03
   §7.3이 이미 권고한 "10단계에서 재난복구 리허설 1회"를 그대로 인계한다.
8. **운영 Runbook(11단계) 반영 권고**: `webapp/BACKUP_RESTORE_GUIDE.md` 전체를
   11단계 최종 Runbook에 통합하고, §6에 남긴 미실측 항목들이 10단계에서
   해소된 이후 "확인 완료" 표시로 갱신할 것을 권고한다.
9. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에
   따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다린다). 원격 push도
   수행하지 않았다. WU-09가 이미 남겨둔 미커밋 산출물(`feature-WU-09-
   integration-test.md` 등)도 이번 세션에서 건드리지 않고 그대로 두었다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

이 WU는 "실행 가능한 애플리케이션 코드"가 아니라 "CI 워크플로 + 운영 문서"
이므로, 6단계 인수조건도 그 특성에 맞춰 **코드/문법/로직 수준 재현**으로
정의한다(§3에서 실제로 실행해 통과를 확인한 절차와 동일). 6단계 테스터는
아래 1~9번을 그대로 재현하고, 10~12번은 "이번 단계에서 검증 불가능함을
확인"하는 것 자체를 인수 조건으로 삼는다(허위로 PASS 처리하지 않기 위함).

1. `.github/workflows/neon-db-backup.yml`이 저장소 루트 기준 정확한 경로에
   존재하는가.
2. `python -c "import yaml; yaml.safe_load(open('.github/workflows/neon-db-backup.yml', encoding='utf-8'))"`
   가 예외 없이 끝나는가(YAML 문법 검증).
3. 파싱된 YAML에서 `jobs.backup.steps`가 정확히 8개이고, 각 스텝에 `name`
   필드가 있는가.
4. 8개 스텝의 `run` 스크립트를 각각 파일로 추출해 `bash -n <파일>`을 실행하면
   전부 문법 오류 없이 끝나는가.
5. "Verify required secrets are present" 스텝 스크립트를 추출해 (a) 5개
   환경변수(`NEON_BACKUP_DATABASE_URL`, `R2_BACKUP_ACCESS_KEY_ID`,
   `R2_BACKUP_SECRET_ACCESS_KEY`, `R2_BACKUP_BUCKET_NAME`, `R2_ENDPOINT_URL`)
   전부 비운 채 실행하면 `exit 1`이고 5개 모두 `::error::` 메시지가 출력되는가,
   (b) 5개 전부 임의 값으로 채운 채 실행하면 `exit 0`인가, (c) 2개만 채운
   채 실행하면 나머지 3개에 대해서만 `::error::`가 출력되고 `exit 1`인가.
6. "Ensure R2 lifecycle rule" 스텝의 `printf` 명령을 그대로 실행해 생성된
   `lifecycle.json`이 `python -m json.tool`로 파싱 가능한 유효한 JSON이고,
   `Rules[0].Expiration.Days == 14`, `Rules[0].Filter.Prefix == "db-backups/"`
   인가.
7. `TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"; BACKUP_FILE="db-backup-${TIMESTAMP}.sql.gz"`
   를 실행한 결과가 정규식 `^db-backup-[0-9]{8}T[0-9]{6}Z\.sql\.gz$`와
   일치하는가.
8. `webapp/BACKUP_RESTORE_GUIDE.md`가 존재하고, §3(장애 시 운영자 절차),
   §4(필요 GitHub Secrets 목록), §6(10단계 인계 사항) 섹션을 포함하는가.
9. `docs/harness/decisions.md`에 DEC-032, DEC-033이 append-only로 추가되어
   있고(기존 DEC-001~031 내용이 삭제/수정되지 않았는가), `docs/harness/
   traceability.md`의 REQ-013 행이 "구현 완료"로 갱신되어 있는가.
10. (**검증 불가, 확인만**) 실제 GitHub Actions 러너에서 이 워크플로를
    스케줄/수동 두 방식으로 실행해 성공하는지 — 6단계 시점에는 실행 환경이
    없어 검증 불가능함을 테스트 결과서에 명시적으로 기록해야 한다(허위
    PASS 금지).
11. (**검증 불가, 확인만**) 실제 Neon 연결 문자열로 `pg_dump`가 성공하는지,
    실제 R2 자격증명으로 `aws s3 cp`/`aws s3api`가 성공하는지 — 로컬에
    `pg_dump`/`aws` CLI가 설치되어 있지 않아(`unit-10-note.md` §3에서 확인)
    검증 불가능함을 기록해야 한다.
12. 검증에 사용한 임시 파일(스크래치패드에만 생성)을 정리했는지, `git status
    --porcelain`에 이 WU가 만든 파일(`.github/workflows/neon-db-backup.yml`,
    `webapp/BACKUP_RESTORE_GUIDE.md`)과 수정한 파일(`decisions.md`,
    `traceability.md`) 외의 소스 diff가 없는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위
§8의 1~12번 인수 조건을 입력으로 `docs/harness/units/unit-10-test.md`를
작성하도록 한다. 이 WU는 성격상 "실행 코드"가 아니라 "CI 워크플로 정의 +
운영 문서"이므로, 6단계도 §8이 명시한 대로 "검증 가능한 것은 재현 PASS,
검증 불가능한 것은 불가능하다고 정직하게 기록"하는 방식으로 판정해야
한다(허위 PASS 금지, 규칙 전반의 정신과 일치). 6단계가 (조건부) PASS
판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-10)의 7단계
(통합테스트) 착수 여부와, 10단계(배포테스트)에서 실제 실행을 검증하는
일정을 오케스트레이터가 판단한다. 이번 세션 범위는 WU-10까지이며 WU-11은
착수하지 않았다.
