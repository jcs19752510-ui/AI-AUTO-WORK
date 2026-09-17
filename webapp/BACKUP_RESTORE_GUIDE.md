# 백업/복구 가이드 (DRAFT — WU-10)

> **이 문서는 초안(draft)이다.** 최종 운영 Runbook은 11단계(`docs/harness` 산출물)에서
> 이 문서 + `ADMIN_ACCESS_GUIDE.md` §7.4 후보 항목 + 03-system-design.md §7.4를
> 통합해 작성한다. 지금은 WU-10 개발 시점에 실제 Neon/R2 자격증명이 아직
> 발급되지 않았으므로(로컬 Windows 환경 제약, WU-01~09와 동일 사유), 아래
> 절차는 **문서/명령어 수준까지 준비된 상태**이며 실제 실행 결과는 10단계
> (배포테스트) 이후 실측 확인이 필요하다.

- 관련 REQ: REQ-013(Neon PITR 6시간 한계 보완 백업 정책)
- 관련 설계: `docs/harness/03-system-design.md` §1.1(아키텍처), §3.3(destructive
  마이그레이션 전 수동 백업 원칙), §5.4(시크릿 관리), §7.3(RPO/RTO), §7.5(R2
  Lifecycle 14일)
- 관련 결정: `docs/harness/decisions.md` DEC-010, DEC-032, DEC-033
- 워크플로 파일: `.github/workflows/neon-db-backup.yml`

---

## 1. 백업 아키텍처 요약

- 매일 1회(UTC 18:00 = KST 03:00, 익일) GitHub Actions가 `pg_dump`로 Neon
  PostgreSQL 전체를 덤프하고 gzip 압축해 Cloudflare R2의 `backup-private`
  버킷, `db-backups/` 프리픽스 아래 업로드한다.
- 파일명 형식: `db-backup-<UTC 타임스탬프, YYYYMMDDTHHMMSSZ>.sql.gz`
  (예: `db-backup-20260917T180003Z.sql.gz`)
- 보관 기간: R2 Object Lifecycle 규칙(워크플로가 매 실행마다 멱등하게
  재적용, DEC-033)에 의해 업로드 후 **14일**이 지나면 자동 삭제된다. 항상
  최근 14일치 백업이 유지된다.
- Render(앱)와 완전히 독립된 GitHub Actions 러너에서 실행되므로, 앱이
  다운되어도 백업은 계속 정상 동작한다(장애 격리, 03 §1.1).

## 2. 이 백업이 필요한 이유(복구 우선순위)

| 사고 발생 시점 | 1차 복구 수단 | 2차 복구 수단 |
|---|---|---|
| 최근 6시간 이내 | **Neon PITR**(Point-in-Time Recovery) — Neon 콘솔에서 특정 시각으로 즉시 복원 가능, 무료 티어 보존 한도 6시간 | 불필요 |
| 6시간 초과 ~ 최대 14일 이내 | **이번 워크플로의 GitHub Actions 일일 백업**(R2 `backup-private`) | - |
| 14일 초과 | 복구 불가(설계상 한계, 03 §7.3에 이미 명시된 트레이드오프) | - |

**RPO(목표 복구 시점) ≈ 최대 24시간**(PITR 6시간을 넘는 사고는 전날 백업까지만
복구 가능), **RTO(목표 복구 시간)는 수동 restore 기준 1시간 이내가 잠정
목표**다(03 §7.3). 실측 재난복구 리허설은 아직 수행되지 않았다 — 10단계에서
1회 이상 실제로 리허설할 것을 권고한다(§6 참고).

## 3. 장애 시 운영자 절차

### 3-1. 6시간 이내 사고 — Neon PITR 사용

1. Neon 콘솔(console.neon.tech) 로그인 → 해당 프로젝트 → **Branches** →
   **Restore**(또는 "Time Travel"/"Point-in-Time Restore" — 실제 메뉴 명칭은
   Neon 콘솔 UI 버전에 따라 달라질 수 있으므로 배포 후 1회 직접 확인해
   이 문서에 정확한 메뉴 경로를 갱신할 것, §6 인계 사항).
2. 복구할 시각을 지정하고 새 브랜치(또는 기존 브랜치 롤백)로 복원한다.
3. 복원된 브랜치의 연결 문자열로 `DATABASE_URL`(Render 환경변수)을 임시
   전환하거나, 기존 브랜치를 그대로 되돌린다(Neon 브랜칭 정책에 따라 선택).
4. 애플리케이션이 정상 동작하는지 확인 후 Render에서 재배포/재시작한다.

### 3-2. 6시간 초과 ~ 14일 이내 사고 — R2 백업으로 복구

1. 가장 가까운(사고 시점 직전) 백업 파일을 R2에서 다운로드한다.

   ```bash
   aws s3 ls "s3://<R2_BACKUP_BUCKET_NAME>/db-backups/" \
     --endpoint-url "<R2_ENDPOINT_URL>" --region auto
   aws s3 cp "s3://<R2_BACKUP_BUCKET_NAME>/db-backups/<파일명>.sql.gz" ./backup.sql.gz \
     --endpoint-url "<R2_ENDPOINT_URL>" --region auto
   ```

2. 압축을 해제한다.

   ```bash
   gunzip backup.sql.gz
   ```

3. **새 Neon 프로젝트/브랜치(빈 DB)를 우선 대상으로 복구해 먼저 검증**할
   것을 강력히 권고한다(기존 프로덕션 DB에 바로 덮어쓰지 않음 — 복구
   자체가 실패하면 되돌릴 수 없는 2차 사고가 될 수 있다).

   ```bash
   psql "<검증용 Neon DATABASE_URL>" -f backup.sql
   ```

   덤프는 `--clean --if-exists` 옵션으로 생성되어 있어(`.github/workflows/
   neon-db-backup.yml` 참고) 대상 DB에 기존 스키마가 남아있어도 안전하게
   재적용된다.
4. 검증용 DB에서 최근 게시물/구독자 수 등 핵심 데이터가 정상인지 스팟
   체크한다.
5. 검증이 끝나면 Render의 `DATABASE_URL` 환경변수를 검증된 DB(또는 같은
   방식으로 복구한 프로덕션 DB)로 전환하고 재배포한다.
6. 복구 완료 후, 사고 시점과 백업 시점 사이의 데이터(뉴스레터 구독,
   게시물 수정 등)는 유실되었을 수 있음을 인지하고 필요 시 수동 보정한다.

### 3-3. destructive 마이그레이션 배포 직전 — 수동 백업 트리거

03 §3.3-3이 요구하는 "컬럼/테이블 삭제 등 destructive 마이그레이션 배포
직전 수동 `pg_dump` 백업"은 이 워크플로를 **수동 실행(workflow_dispatch)**
하는 것으로 수행한다(별도 스크립트를 새로 만들지 않음 — 과설계 방지).

```bash
gh workflow run neon-db-backup.yml --ref main -f reason="destructive migration 배포 전 수동 백업"
```

또는 GitHub 웹 UI의 Actions 탭 → "Neon DB Backup to R2" → "Run workflow"에서
사유를 입력하고 실행한다. 완료 후 Actions 실행 로그에서 "백업 업로드 확인
완료" 메시지를 확인한 뒤에만 마이그레이션을 배포한다.

## 4. 사전 준비 — GitHub Actions Secrets (운영자가 배포 단계에서 설정)

이 워크플로가 실제로 동작하려면 아래 Repository Secrets
(`Settings > Secrets and variables > Actions`)가 채워져 있어야 한다. 값은
**절대 코드/이 문서에 커밋하지 않는다**(03 §5.4).

| Secret 이름 | 용도 | 비고 |
|---|---|---|
| `NEON_BACKUP_DATABASE_URL` | pg_dump 대상 Neon 연결 문자열 | **Render 앱이 쓰는 `DATABASE_URL`과 별도 값을 권장**(03 §5.4 최소 권한 원칙). 가능하면 Neon에서 해당 프로젝트에 읽기 전용에 가까운 별도 role을 만들어 그 연결 문자열을 사용한다. 이 워크플로는 앱용 `DATABASE_URL`로 자동 대체(fallback)하지 않는다(DEC-032) — GitHub Actions라는 별도 신뢰 경계에 프로덕션 쓰기 권한을 암묵적으로 넘기지 않기 위함. |
| `R2_BACKUP_ACCESS_KEY_ID` | `backup-private` 버킷 전용 R2 액세스 키 | `media-public` 버킷용 키(Render `R2_ACCESS_KEY_ID`)와 **다른 키를 발급**할 것을 권장(DEC-016(b)가 WU-10 시점에 재검토하도록 남긴 항목). 이 워크플로는 media-public 키로 자동 대체하지 않는다. |
| `R2_BACKUP_SECRET_ACCESS_KEY` | 위 키의 시크릿 | 위와 동일 |
| `R2_BACKUP_BUCKET_NAME` | 백업 버킷 이름(예: `backup-private`) | Render `render.yaml`의 `R2_BACKUP_BUCKET_NAME`과 같은 값을 넣으면 된다(이름은 같아도 되지만 "값"을 GitHub Secrets에 별도로 입력해야 한다 — Render 환경변수와 GitHub Secrets는 서로 다른 저장소다). |
| `R2_ENDPOINT_URL` | R2 S3 호환 엔드포인트 URL | Render `R2_ENDPOINT_URL`과 동일한 값 |
| `R2_REGION` | R2 리전(선택, 비우면 워크플로가 `auto`로 기본 처리) | Cloudflare 공식 권고값 `auto` |

**사전 조건(배포 단계에서 확인)**:
1. R2에 `backup-private` 버킷이 실제로 생성되어 있어야 한다(03 §2.3, WU-03
   설계 시점에는 골격만 준비됨).
2. 위 6개 Secret이 모두 채워져 있어야 한다 — 워크플로 첫 단계("Verify
   required secrets are present")가 누락된 값을 명확히 알려주고 즉시
   실패하므로, 조용히 아무 일도 안 일어나는 상태는 없다.
3. GitHub 계정(리포지토리 소유자)의 알림 설정에서 Actions 실패 이메일
   수신이 켜져 있는지 확인한다(`github.com/settings/notifications` →
   Actions). 이것이 03 §7.2가 지정한 "백업 실패 알림 채널"이다.

## 5. 백업 성공/실패 확인 방법 (운영자용, 02 §5 KPI 7 대응)

- **정상 여부 확인**: GitHub 리포지토리 → Actions 탭 → "Neon DB Backup to
  R2" 워크플로의 실행 이력. 각 실행은 성공/실패가 색상으로 표시되고,
  "Verify upload succeeded" 스텝 로그에 실제 업로드된 오브젝트 키가
  남는다 — 이 실행 이력 자체가 "정의된 주기(1일 1회)대로 100% 수행되었는지"
  확인 가능한 로그다(별도 로그 저장소를 새로 만들지 않음, 과설계 방지).
- **실패 시**: GitHub 표준 기능으로 리포지토리 소유자에게 이메일이
  자동 발송된다(03 §7.2). 추가로 운영 Runbook(11단계)에 "주 1회 Actions
  탭에서 최근 7일 백업 실행 결과 육안 확인" 절차를 반영할 것을 권고한다
  (03 §7.4 "GitHub Actions 백업 워크플로 성공 여부 주 1회 확인"과 동일
  취지).
- **R2에 실제 파일이 쌓이는지 직접 확인**:
  ```bash
  aws s3 ls "s3://<R2_BACKUP_BUCKET_NAME>/db-backups/" \
    --endpoint-url "<R2_ENDPOINT_URL>" --region auto
  ```

## 6. 6단계/10단계 인계 사항 (이 초안에서 실측하지 못한 것)

이 문서와 워크플로는 **로컬 Windows 개발 환경 제약**(WU-01~09와 동일 제약,
GitHub Actions를 실제로 트리거할 수 없고 실제 Neon/R2 자격증명이 없음)
때문에 아래 항목은 이번 WU-10에서 실제로 실행/검증하지 못했다. 10단계
(배포테스트) 착수 시 반드시 실측이 필요하다:

1. **워크플로 실제 실행**: 스케줄/수동 트리거 양쪽 모두 실제 GitHub Actions
   러너에서 성공적으로 끝나는지(특히 `sudo apt-get install postgresql-client`
   가 실제 ubuntu-latest 러너에서 문제없이 끝나는지, `aws` CLI가 실제로
   사전 설치되어 있는지 — GitHub 공식 `actions/runner-images` 문서 기준으로는
   포함되어 있으나 러너 이미지가 바뀔 수 있으므로 재확인 필요).
2. **pg_dump 버전 호환성**: apt로 설치되는 `postgresql-client` 버전과 Neon이
   실제로 구동하는 PostgreSQL 서버 메이저 버전이 다르면 `pg_dump`가 경고를
   내거나(대개 구버전 클라이언트로 신버전 서버를 덤프하는 것은 위험) 실패할
   수 있다 — 실제 Neon 프로젝트 생성 후 서버 버전을 확인하고 필요시
   `postgresql-client-<버전>` 패키지로 고정할 것.
3. **R2 Lifecycle API 호출 성공 여부**: `aws s3api put-bucket-lifecycle-
   configuration`이 R2의 S3 호환 API에서 실제로 성공하는지 (Cloudflare
   공식 문서상 지원되는 것으로 확인했으나, 실제 자격증명으로 호출 검증은
   못함, §7 참고).
4. **Neon PITR 콘솔 메뉴 명칭 재확인**(§3-1) — 실제 화면으로 정확한 경로를
   이 문서에 갱신.
5. **재난복구 리허설 1회**: 실제 백업 파일을 실제로 새 Neon 프로젝트에
   복구해보고 RTO 1시간 목표가 현실적인지 측정(03 §7.3 권고 사항).
6. 이 항목들이 모두 확인되면 이 문서를 11단계 최종 운영 Runbook에 통합한다.

## 7. 로컬(개발 단계)에서 실제로 검증한 것 — `unit-10-note.md` §3 참고

워크플로 YAML 문법, 각 `run:` 스텝의 bash 문법(`bash -n`), 시크릿 누락 감지
로직의 동작(성공/실패 케이스), 타임스탬프/파일명 생성 로직, R2 Lifecycle
JSON의 유효성은 로컬에서 직접 실행해 확인했다(실측 결과는
`docs/harness/units/unit-10-note.md` §3 참고). `pg_dump`/`aws` CLI 자체와
실제 네트워크 호출은 로컬 환경에 해당 도구가 설치되어 있지 않아
실행하지 못했다 — 이는 10단계로 이관되는 이 프로젝트의 알려진 제약이다.
