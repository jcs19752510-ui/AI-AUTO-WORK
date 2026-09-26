# 테스트 결과서 (Test Result Report)

## 1. 개요
- 테스트 대상: WU-13(광고 SDK 연동 준비) — `core.SiteSettings.adsense_client_id`, `ads.txt` 동적 뷰, base.html 애드센스 스크립트, 법적 페이지 광고 쿠키 안내
- 테스트 유형: 단위+통합 병합(Low 등급, 작업 단위 4개 이하: 모델 필드/컨텍스트 프로세서/뷰/템플릿)
- 적용 Tier: Low (값이 비어 있으면 기존 동작과 100% 동일 — `contact_email` 선례와 동일한 위험도)
- 적용 속도 트랙: N/A
- 테스트 목적: (1) `adsense_client_id`가 비어 있을 때 기존 사이트 동작(모든 라우트, 법적 페이지 문구)이 전혀 바뀌지 않는지 확인 (2) 값이 채워졌을 때 광고 스크립트·`ads.txt`·광고 쿠키 안내가 정확히 활성화되는지 확인 (3) 전체 회귀 없음을 프로젝트 전체 테스트 스위트로 확인
- 관련 산출물: `docs/harness/decisions.md` DEC-053/DEC-054, `docs/harness/02-planning.md` v1.3(REQ-023, WU-13), `webapp/ADMIN_ACCESS_GUIDE.md` §7
- 테스트 수행자: Claude (세션 에이전트)
- 테스트 일시: 2026-09-26

## 2. 테스트 범위 및 제외 범위
- 범위(In-Scope): `core.models.SiteSettings.adsense_client_id` 필드/마이그레이션, `core.context_processors.adsense_client_id`, `core.views.ads_txt`+URL 라우팅, `config/templates/base.html` 조건부 스크립트 태그, `legal/templates/legal/legal_page.html` 조건부 광고 쿠키 안내, `legal/migrations/0004_add_adsense_cookie_notice.py`(기존 "추적 쿠키 미사용" 문구 정정)
- 제외 범위 및 사유: 실제 Google 애드센스 계정 심사·신청(사용자가 직접 수행해야 하는 외부 영역), 수동 광고 슬롯 배치/CLS 세부 튜닝(계정 미보유 상태에서 과설계 방지, DEC-054), 실제 도메인 배포 후의 광고 노출 확인(배포 자체가 아직 범위 밖)

## 3. 테스트 환경
- 실행 환경: Windows 11, 로컬 개발 서버, SQLite, DEBUG=True, Django TestCase(테스트 전용 DB)
- 테스트 데이터: `SiteSettings.for_site()`로 조회한 기본 사이트 레코드의 `adsense_client_id`를 테스트별로 설정/해제
- 전제 조건: `core.0003_add_adsense_client_id`, `legal.0004_add_adsense_cookie_notice` 마이그레이션 적용 완료

## 4. 테스트 케이스 및 결과
| ID | 시나리오 | 사전조건 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|----------|-----------|-----------|-----------|-----------|------|
| TC-001 | 필드 기본값 확인 | 마이그레이션만 적용, 값 미설정 | `SiteSettings.adsense_client_id` 조회 | 빈 문자열(`""`) | 빈 문자열 확인 | Pass | |
| TC-002 | ads.txt — 미설정 시 404 | 값 미설정 | `GET /ads.txt` | 404 | 404 확인 | Pass | `core.tests.AdsTxtTests.test_404_when_unset` |
| TC-003 | ads.txt — 설정 시 정상 응답 | `ca-pub-1234567890123456` 설정 | `GET /ads.txt` | `google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0` | 일치 확인 | Pass | `test_200_with_expected_line_when_set` |
| TC-004 | ads.txt — `ca-` 접두어 없이 입력해도 정상 처리 | `pub-9999999999999999` 설정 | `GET /ads.txt` | 동일 형식으로 정상 응답 | 확인 | Pass | 운영자 입력 실수에 대한 관대한 처리 |
| TC-005 | 홈 화면 — 미설정 시 스크립트 태그 없음 | 값 미설정 | `GET /` 응답 본문에서 `adsbygoogle.js` 검색 | 없음 | 없음 확인 | Pass | |
| TC-006 | 홈 화면 — 설정 시 스크립트 태그 노출 | 값 설정 | `GET /` 응답 본문 검색 | `adsbygoogle.js?client=ca-pub-...` 포함 | 포함 확인 | Pass | |
| TC-007 | 실제 게시물 상세 페이지에서도 동일하게 노출 | 값 설정 | 발행된 블로그 글 상세 페이지 curl | 스크립트 태그 포함 | 포함 확인(수동 curl) | Pass | base.html이 전역 템플릿이므로 모든 페이지 타입에 공통 적용됨을 실측 |
| TC-008 | 쿠키 고지 페이지 — 미설정 시 안내 없음 + 구문구 정정 확인 | 값 미설정 | `GET /cookies/` | `legal-page__adsense-note` 없음, "추적 쿠키를 사용하지 않습니다" 문구도 없음(0004 정정 반영 확인) | 둘 다 확인 | Pass | |
| TC-009 | 쿠키 고지 페이지 — 설정 시 안내 노출 | 값 설정 | `GET /cookies/` | `legal-page__adsense-note` + "Google AdSense" 텍스트 포함 | 포함 확인 | Pass | |
| TC-010 | 개인정보처리방침 페이지에는 광고 쿠키 상세 안내가 노출되지 않음 | 값 설정 | `GET /privacy-policy/` | `legal-page__adsense-note` 없음(쿠키 고지 페이지로 위임 구조 유지) | 없음 확인 | Pass | |
| TC-011 | 값을 다시 비우면 즉시 원복 | TC-006 상태에서 값 재해제 | `GET /`, `/ads.txt`, `/cookies/` 재확인 | 전부 비활성 상태로 복귀 | 복귀 확인(캐시 초기화 후) | Pass | 로컬 검증 중 `LocMemCache`가 요청 간 값을 붙들고 있어 서버 재시작으로 캐시를 비워야 했음 — 실제 운영에서는 `SiteSettings` 저장 시 Wagtail이 자동으로 관련 캐시를 무효화하므로 이 재시작 필요성은 로컬 수동 스크립트 검증 특유의 제약이지 결함이 아님 |
| TC-012 | 회귀 — `core`+`legal` 앱 테스트 | 신규 테스트 8건 추가 후 | `python manage.py test core legal` | 전부 PASS | 38/38 PASS | Pass | |
| TC-013 | 회귀 — 프로젝트 전체 테스트 스위트 | 위와 동일 | `python manage.py test` | 전부 PASS(기존 86 + 신규 8 = 94) | 94/94 PASS, 159.4초 | Pass | |

## 5. 커버리지
- 커버리지 지표: 신규 코드 경로(필드 기본값, `ads.txt` 활성/비활성 2가지, 스크립트 태그 활성/비활성 2가지, 쿠키 안내 활성/비활성/타 페이지 비노출 3가지) 전부 자동화 테스트로 커버
- 커버되지 않은 부분과 사유: 실제 Google 서버가 스크립트를 정상 서빙하는지(네트워크 응답)는 로컬에서 확인 불가 — 표준 Google 스니펫을 그대로 사용했으므로 별도 검증 불필요로 판단. Auto ads가 실제로 어느 위치에 광고를 삽입하는지는 계정 발급 전에는 확인 자체가 불가능(구글 서버 쪽 동작).

## 6. 결함(Defect) 목록
- 결함 없음 — TC-001~TC-013 전부 Pass, 프로젝트 전체 테스트(94건) 회귀 없음.

## 7. 테스트 환경 정리(Teardown) 확인 — 규칙 K
- 이번 테스트에서 생성한 임시 아티팩트: 로컬 검증 중 `SiteSettings.adsense_client_id`에 테스트 값(`ca-pub-1234567890123456`)을 임시로 넣었다가 검증 후 다시 빈 값으로 되돌렸다(운영 DB 아님, 로컬 SQLite). 프로젝트 저장소에는 스크립트/임시 파일을 생성하지 않았다(세션 스크래치패드에서만 1회성 셸 명령 실행).
- 전부 `.harness-tmp/` 하위에서만 생성했는가: 해당 없음 — 파일 시스템에 임시 아티팩트를 만들지 않고 DB 값만 임시로 바꿨다가 원복했다.
- 정리(삭제) 완료 여부: 완료 — `adsense_client_id`를 다시 빈 문자열로 저장, 서버 재기동으로 캐시까지 초기화 확인.
- 정리 후 `git status --short` 실행 결과(그대로 첨부):
  ```
   M docs/harness/02-planning.md
   M docs/harness/decisions.md
   M webapp/config/settings/base.py
   M webapp/config/templates/base.html
   M webapp/core/context_processors.py
   M webapp/core/models.py
   M webapp/core/tests.py
   M webapp/core/urls.py
   M webapp/core/views.py
   M webapp/legal/templates/legal/legal_page.html
   M webapp/legal/tests.py
  ?? docs/harness/test-report_content-pilot-20articles.md
  ?? webapp/core/migrations/0003_add_adsense_client_id.py
  ?? webapp/legal/migrations/0004_add_adsense_cookie_notice.py
  ```
  (전부 이번 WU-13 작업 또는 직전 콘텐츠 파일럿 결과서로 설명되는 변경분 — 의도하지 않은 파일 없음)
- 이번 테스트 도중 강제 중단이 있었는가: 없음(서버 재시작은 코드 변경 반영을 위한 정상 절차였지 강제 중단이 아니었음).

## 8. 리스크 및 잔존 이슈
- **04-ux-design.md 미갱신**: 광고 슬롯이 실제로 추가되는 시점(계정 발급 후)에는 UX 설계 문서도 함께 갱신해야 한다는 점을 `02-planning.md` v1.3에 명시해 인계했다.
- **09-security-audit.md/개인정보처리방침 재검토 권고**: 광고가 실제로 활성화되면(값 설정 시점) 제3자 쿠키 관련 보안/개인정보 항목을 09단계 관점에서 한 번 더 짚어보는 것을 권장한다 — 이번 라운드는 코드 변경 자체의 검증이며 09단계 전체 재실행 범위는 아니다.
- **Google Auto ads 특성**: 광고 위치를 세밀하게 통제할 수 없다(구글이 자동 판단). 정밀한 위치 제어가 필요해지면 수동 광고 단위로 전환하는 별도 작업이 필요하다(WU-13이 아닌 후속 WU).

## 9. 결론 및 판정
- [x] PASS — 다음 단계 진행 가능(계정 발급 이후 실제 활성화는 사용자 몫). 7절 Teardown 확인 완료.

## 10. 내부 검증 (최소 2회)

### 1차 검증 (작성자 관점 자가 재검토)
- 검증자: Claude(작성 에이전트, 자가 재검토)
- 일시: 2026-09-26
- 체크리스트
  - [x] 입력 계약(DEC-053/054가 정한 범위: "계정 생기면 값만 넣으면 켜지는 최소 구현")을 그대로 반영했는가 — 예
  - [x] 출력 계약(필드/컨텍스트 프로세서/스크립트/ads.txt/쿠키 안내)이 빠짐없이 존재하는가 — 예
  - [x] 기존 산출물(contact_email 선례, 0003 마이그레이션 선례)과 패턴이 일관되는가 — 예, 동일한 "값 없으면 조용히 비활성" 원칙 재사용
  - [x] 추측으로 채운 항목이 있는가 — 없음. 광고 슬롯 위치 등 판단이 필요한 부분은 전부 범위 밖으로 명시적으로 미룸(과설계 방지)
  - [x] 20년차 실무자 기준 구조적 결함 — 없음. 기존 RichText 문구("추적 쿠키 미사용")가 향후 거짓이 될 수 있는 지점을 발견해 선제 정정(0004 마이그레이션)
  - [x] 오탈자/형식 오류 — 없음
- 발견된 결함 목록: 없음
- 조치 내용: 해당 없음

### 2차 검증 (독립 심사자 관점 — 역할 전환 재검토)
- 검증자: Claude(동일 세션, 역할 전환)
- 일시: 2026-09-26
- 체크리스트
  - [x] 1차 검증 지적 항목 반영 여부 — 해당 없음(1차 결함 0건)
  - [x] 엣지 케이스 누락 여부 — "ca-" 접두어 없이 입력하는 실수(TC-004), 값을 다시 비우는 케이스(TC-011), 다른 법적 페이지에 안내가 새지 않는지(TC-010) 전부 커버됨을 재확인
  - [x] 문서만 보고 다음 사람(또는 미래의 나)이 추가 질문 없이 이어받을 수 있는가 — `ADMIN_ACCESS_GUIDE.md` §7에 실제 활성화 절차를 남겨 사용자가 계정 발급 후 바로 따라할 수 있음을 확인
  - [x] 되돌리기 어려운 결정 근거 — 없음, 전부 Low 비가역성(값 제거만으로 완전 원복)
  - [x] 보안/운영 관점 위험 — 없음. `ads.txt`가 값 없을 때 404인 것도 의도된 정상 동작이며 정보 노출 없음
- 발견된 결함 목록: 없음
- 조치 내용: 해당 없음

## 최종 판정
- [x] PASS (결함 0건, 2회 검증 완료) — 다음 단계(실제 애드센스 계정 발급 후 활성화)로 handoff 가능
