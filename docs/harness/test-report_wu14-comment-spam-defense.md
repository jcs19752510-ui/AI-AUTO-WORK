# 테스트 결과서 (Test Result Report)

## 1. 개요
- 테스트 대상: WU-14(댓글 스팸 자동/수동 차단) — `comments.Comment.source_ip_raw`, `comments.BlockedIP`, 반복 거부 자동차단 신호(`comments/signals.py`), 제출 경로(`comment_submit`/`comment_write_page`) 차단 적용, 개인정보처리방침 갱신
- 테스트 유형: 단위+통합 병합(Low~Standard 경계, 모델/신호/뷰/권한/법적 페이지 5개 영역이지만 작업 단위 수는 5개 이하)
- 적용 Tier: Standard(개인정보처리방침 문구 변경과 원본 IP 신규 보관이 걸려 있어 Low보다는 위, DEC-055 비가역성 Medium과 일치)
- 테스트 목적: (1) 자동 차단(상습범, 30일 내 3회 거부 시 30일 차단)이 정확히 임계치에서만 발동하는지 (2) 수동 차단 목록(BlockedIP)이 제출 경로 양쪽(AJAX/무-JS)에서 동일하게 작동하는지 (3) 차단된 IP에게 허니팟과 동일한 위장 응답이 가는지(공격자에게 노출 안 됨) (4) 권한 경계(Moderators만 관리 가능)가 실제로 걸려 있는지 (5) 개인정보처리방침이 원본 IP 보관 목적을 정확히 반영하는지 (6) 프로젝트 전체 회귀 없음
- 관련 산출물: `docs/harness/decisions.md` DEC-055, `webapp/ADMIN_ACCESS_GUIDE.md` §8
- 테스트 수행자: Claude (세션 에이전트)
- 테스트 일시: 2026-09-27

## 2. 테스트 범위 및 제외 범위
- 범위(In-Scope): `comments.models.BlockedIP`(모델+`is_blocked()`), `comments.Comment.source_ip_raw`, `comments/signals.py`(자동차단 신호), `comments/views.py`(차단 판정 삽입), `comments/migrations/0003~0004`, `legal/migrations/0005`(개인정보처리방침 갱신)
- 제외 범위 및 사유: 사용자가 명시적으로 선택하지 않은 항목 — 링크 포함 댓글 자동거부(콘텐츠 기반 휴리스틱), CAPTCHA(reCAPTCHA/hCaptcha, 구글 계정 필요), 이름/키워드 기반 수동 차단 목록. 전부 DEC-055에 "미채택"으로 기록, 향후 요청 시 별도 라운드로 착수

## 3. 테스트 환경
- 실행 환경: Windows 11, 로컬 개발 서버, SQLite, DEBUG=True, Django TestCase
- 테스트 데이터: 테스트별로 생성한 임시 `BlogPostPage`/`Comment`/`BlockedIP` 레코드(전부 `TestCase` 트랜잭션 롤백으로 자동 정리)
- 전제 조건: `comments.0003_add_blocked_ip_and_source_ip_raw`, `comments.0004_grant_blockedip_permissions`, `legal.0005_add_comment_ip_blocklist_notice` 마이그레이션 적용 완료

## 4. 테스트 케이스 및 결과
| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail |
|----|----------|-----------|-----------|-----------|-----------|
| TC-001 | 차단 기록 없음 | `BlockedIP.is_blocked(ip)` | False | False | Pass |
| TC-002 | 영구 차단(만료시각 없음) | 항목 생성 후 조회 | True | True | Pass |
| TC-003 | 만료 전 임시 차단 | `expires_at`=미래 | True | True | Pass |
| TC-004 | 만료 후 임시 차단 | `expires_at`=과거 | False(자동 해제) | False | Pass |
| TC-005 | 다른 IP는 영향 없음 | IP A 차단, IP B 조회 | False | False | Pass |
| TC-006 | `comment_submit` — 차단된 IP | 차단 등록 후 제출 | 200 위장 응답, DB 미저장 | 확인 | Pass |
| TC-007 | `comment_write_page` — 차단된 IP(무-JS 경로) | 동일 | 302 위장 리다이렉트, DB 미저장 | 확인 | Pass |
| TC-008 | 대조군 — 차단 안 된 IP는 정상 저장 | 일반 제출 | 200, DB 저장됨 | 확인 | Pass |
| TC-009 | 임계치 미만 — 자동차단 안 됨 | 동일 IP 거부 2회(임계치 3) | `is_blocked`=False | False | Pass |
| TC-010 | 임계치 도달 — 자동차단 발동 | 동일 IP 거부 3회 | `BlockedIP` 자동 생성, `is_auto=True`, `expires_at`≈+30일 | 확인(초 단위 오차 60초 이내) | Pass |
| TC-011 | 무관한 IP의 거부 이력은 합산 안 됨 | IP A 거부 2회, IP B 거부 2회 | 둘 다 미차단(각자 임계치 미달) | 확인 | Pass |
| TC-012 | 자동차단 → 실제 제출 경로까지 이어짐(E2E) | 임계치 도달 후 같은 IP로 재제출 | 200 위장, DB 미저장 | 확인 | Pass |
| TC-013 | 권한 — Moderators는 차단 목록 관리 가능 | `has_perm` 확인 | add/change/delete/view 전부 True | 확인 | Pass |
| TC-014 | 권한 — Editors는 불가 | 동일 | add/change 전부 False | 확인 | Pass |
| TC-015 | 개인정보처리방침 반영 확인 | `/privacy-policy/` 조회 | "반복 거부 자동차단", "운영자 화면에는 노출되지" 문구 포함 | 확인 | Pass |
| TC-016 | 회귀 — `comments` 앱 테스트 | `manage.py test comments` | 전부 PASS(기존 34 + 신규 15 = 49) | 49/49 PASS | Pass |
| TC-017 | 회귀 — 프로젝트 전체 테스트 스위트 | `manage.py test` | 전부 PASS(기존 94 + 신규 15 = 109) | 109/109 PASS, 223.4초 | Pass |

## 5. 커버리지
- 커버리지 지표: `BlockedIP.is_blocked()` 4가지 경로(없음/영구/미만료/만료) 전부, 제출 경로 2곳(AJAX용 `comment_submit`, 무-JS `comment_write_page`) 전부, 자동차단 임계치 경계(미만/도달/무관 IP) 전부, 권한 경계(Moderators/Editors) 전부
- 커버되지 않은 부분과 사유: 실제 봇 트래픽 패턴(다양한 IP 회전 속도, 분산 정도)은 로컬 테스트로 재현 불가 — 실제 운영 후 관측 데이터로 임계치(3회/30일/30일)를 조정하는 것을 전제로 설계됨(기존 레이트리밋 값과 동일한 "일단 시작, 관측 후 조정" 원칙)

## 6. 결함(Defect) 목록
- 결함 없음 — TC-001~TC-017 전부 Pass(자동화 테스트 총 109건, 이번 라운드 신규 15건 포함).

## 7. 테스트 환경 정리(Teardown) 확인 — 규칙 K
- 이번 테스트에서 생성한 임시 아티팩트: 없음 — 자동화 테스트는 전부 Django `TestCase` 트랜잭션 내에서 생성/자동 롤백되었다. 로컬 라이브 서버에서 수동 스모크 확인을 위해 `BlockedIP` 테스트 항목(`192.0.2.200`)을 1건 만들었으나, 확인 직후 즉시 삭제 완료.
- 정리 후 `git status --short` 실행 결과(그대로 첨부):
  ```
   M docs/harness/decisions.md
   M webapp/ADMIN_ACCESS_GUIDE.md
   M webapp/comments/apps.py
   M webapp/comments/constants.py
   M webapp/comments/models.py
   M webapp/comments/tests.py
   M webapp/comments/views.py
  ?? docs/harness/test-report_wu14-comment-spam-defense.md
  ?? webapp/LOCAL_DEV_SERVER_GUIDE.md
  ?? webapp/comments/migrations/0003_add_blocked_ip_and_source_ip_raw.py
  ?? webapp/comments/migrations/0004_grant_blockedip_permissions.py
  ?? webapp/comments/signals.py
  ?? webapp/legal/migrations/0005_add_comment_ip_blocklist_notice.py
  ```
  (전부 이번 WU-14 작업 또는 직전 로컬 서버 가이드 작성으로 설명되는 변경분 — 의도하지 않은 파일 없음)
- 이번 테스트 도중 강제 중단: 없음. (로컬 개발 서버 재시작은 코드 반영을 위한 정상 절차)

## 8. 리스크 및 잔존 이슈
- **CAPTCHA/콘텐츠 기반 자동거부 미도입**: 사용자가 이번 라운드에서 선택하지 않았다. 봇이 링크가 없는 순수 텍스트 스팸으로 진화하면 이번 자동차단(상습범 기준)만으로는 초기 3회는 그대로 통과한다는 한계가 있다 — 사전승인제가 최종 방어선이므로 실제 노출은 없지만, 운영 부담은 남는다.
- **공유 IP 오차단 가능성**: ADMIN_ACCESS_GUIDE.md §8에 명시했다. 카페/회사 등 공유 IP를 자동차단하면 같은 IP를 쓰는 무고한 방문자도 함께 막힐 수 있다 — 30일 자동 만료로 완화했으나 완전한 해결책은 아니다.
- **`source_ip_raw`의 장기 보관 정책 미정**: 이번 라운드는 필드 추가와 활용 로직만 다뤘고, 오래된 댓글의 원본 IP를 언제 파기할지(예: N일 후 자동 삭제)는 별도 결정이 필요하다 — 후속 논의 대상으로 남긴다.

## 9. 결론 및 판정
- [x] PASS — 다음 단계 진행 가능. 7절 Teardown 확인 완료, 109/109 테스트 통과.

## 10. 내부 검증 (최소 2회)

### 1차 검증 (작성자 관점 자가 재검토)
- 검증자: Claude(작성 에이전트)
- 일시: 2026-09-27
- 체크리스트
  - [x] 사용자가 선택한 정확히 그 조합(자동=상습범차단, 수동=IP목록)만 구현했는가 — 예, 미선택 옵션(CAPTCHA/링크자동거부/이름목록)은 손대지 않음
  - [x] 사용자가 사전에 인지·수락한 트레이드오프(개인정보처리방침 재검토)를 실제로 이행했는가 — 예, `legal/migrations/0005` 반영·테스트 확인
  - [x] 기존 방어선(허니팟/레이트리밋/사전승인제)과 충돌 없이 계층으로 추가됐는가 — 예, 차단 판정이 레이트리밋보다 먼저 실행되도록 배치
  - [x] 되돌리기 쉬운 설계인가 — 예, `BlockedIP` 행 삭제/`source_ip_raw` 미사용 전환만으로 기능을 끌 수 있음
  - [x] 20년차 실무자 기준 구조적 결함 — 없음. 자동차단에 만료 기한을 둔 것(로그인 레이트리밋과 동일 철학 재사용)이 "사람이 검토 안 한 판정이 영구화"되는 실무 리스크를 미리 차단
- 발견된 결함 목록: 없음
- 조치 내용: 해당 없음

### 2차 검증 (독립 심사자 관점 — 역할 전환 재검토)
- 검증자: Claude(동일 세션, 역할 전환)
- 일시: 2026-09-27
- 체크리스트
  - [x] 엣지 케이스 — 만료 직전/직후 경계(TC-003/004), 무관한 IP(TC-005/011), 두 제출 경로 모두(TC-006/007) 전부 커버됨
  - [x] 공격자 관점에서 차단 사실이 노출되는 경로가 있는가 — 없음. 200/302 위장 응답이 허니팟과 동일하게 유지됨을 코드·테스트 양쪽으로 재확인
  - [x] 문서만 보고 운영자가 추가 질문 없이 쓸 수 있는가 — `ADMIN_ACCESS_GUIDE.md` §8에 정확한 원본 IP 입력 방법("마스킹된 값을 그대로 쓰면 안 됨")까지 명시해 흔한 실수를 미리 차단
  - [x] 보안/개인정보 관점 위험 — 원본 IP가 어드민 화면에 노출되지 않음(panels 미포함)을 모델 코드로 재확인, 개인정보처리방침 문구가 실제 동작과 일치함을 TC-015로 확인
- 발견된 결함 목록: 없음
- 조치 내용: 해당 없음

## 최종 판정
- [x] PASS (결함 0건, 2회 검증 완료, 전체 회귀 테스트 109/109 통과) — 다음 단계로 handoff 가능
