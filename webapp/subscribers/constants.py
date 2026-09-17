"""WU-07 구독 관련 상수 (REQ-016, 03-system-design.md §3.2/§5.3).

PRIVACY_POLICY_VERSION: 구독 동의 시점의 개인정보처리방침 버전 스냅샷으로
저장할 값(03 §3.2 `consent_version`). `legal.LegalPage`에는 버전 필드가
없으므로(DEC-022 — 3종 공용 RichTextField 1개 모델), subscribers 앱은 그
페이지를 참조하는 대신 정책 게시일을 문자열 버전으로 채택한다. 이 앱이
`legal` 앱을 import하지 않는 이유는 03 §1.2 "경계 원칙"(개인정보를 다루는
`subscribers`와 공개 콘텐츠 앱을 격리해, 한쪽 변경이 다른 쪽에 번지지 않게
한다)을 그대로 따르기 위함이다.

값은 `legal/migrations/0002_create_legal_pages.py`의 PRIVACY_POLICY_BODY가
최초 게시된 날짜(WU-06 완료일)와 동일하다. **운영 절차**: 개인정보처리방침
본문이 실질적으로 바뀌면(WU-06 범위) 이 값도 함께 수동으로 갱신해야 한다 —
두 앱이 격리되어 있어 자동으로 동기화되지 않는다는 트레이드오프를
unit-07-note.md에 명시했다.
"""

PRIVACY_POLICY_VERSION = "2026-09-17"

# 03 §5.3 "IP 기준 레이트리밋" — 구체적 임계치는 설계서에 명시되지 않아
# 자체 판단으로 정했다(허니팟과 병행하는 1차 방어선). 새 패키지를 추가하는
# 대신 DEC-012가 이미 채택한 LocMemCache를 재사용한다(운영 규모 대비
# 과설계 방지 — decisions.md 신규 항목 참고).
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 600
