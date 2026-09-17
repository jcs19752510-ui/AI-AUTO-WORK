"""WU-08, REQ-012 — 요청 수/응답시간 경량 집계 미들웨어.

`core.monitoring.record_request()`로 위임한다(집계 로직/한계에 대한 설명은
그 모듈의 docstring 참고). 이 미들웨어 자체는 시간 측정과 위임만 하고,
실패를 절대 요청 처리 경로로 전파하지 않는다.
"""

import time

from . import monitoring


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        monitoring.record_request(duration_ms)
        return response
