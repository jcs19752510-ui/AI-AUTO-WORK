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
