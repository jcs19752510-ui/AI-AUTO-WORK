"""댓글 관련 상수 (REQ-019, 03-system-design.md §3.2-1).

레이트리밋 임계값은 뉴스레터(`subscribers.constants`)와 동일한 근거로
정했다 — 사전 승인제가 최종 방어선이므로 지금은 뉴스레터와 같은 수준으로
시작하고, 실제 스팸 패턴이 관측되면 조정한다(과설계 방지, 03 §3.2-1).
값을 `subscribers.constants`에서 import하지 않고 이 앱에 독립적으로
정의하는 이유도 `subscribers/constants.py`가 이미 설명한 것과 동일한
"경계 원칙"(03 §1.2) — 한 앱의 정책 변경이 다른 앱에 번지지 않게 한다.
"""

RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 600

# 반복 거부 자동차단(DEC-055, 사용자 요청) — 같은 IP에서 온 댓글이
# AUTO_BLOCK_WINDOW_DAYS 이내에 AUTO_BLOCK_REJECTION_THRESHOLD번 "거부됨"
# 처리되면 자동으로 AUTO_BLOCK_DURATION_DAYS 동안 차단한다. 로그인
# 레이트리밋(core/admin_auth.py)이 계정이 아니라 IP·일정 시간 자동해제를
# 택한 것과 동일한 이유로, 사람이 검토하지 않은 자동 판정은 영구가 아니라
# 기간을 둔다 — 실제 스팸 패턴이 관측되면 조정한다(rate limit 값과 동일한
# "일단 시작하고 관측 후 조정" 원칙, comments/constants.py 기존 주석 참고).
AUTO_BLOCK_REJECTION_THRESHOLD = 3
AUTO_BLOCK_WINDOW_DAYS = 30
AUTO_BLOCK_DURATION_DAYS = 30
