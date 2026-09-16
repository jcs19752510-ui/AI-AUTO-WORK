"""
프로젝트 전역 미들웨어 (03-system-design.md §5.5.4).

WU-01 범위에서는 재사용 가능한 유틸/미들웨어만 준비하고, 실제 레이트리밋·
스팸 방지 로직(WU-07 뉴스레터, WU-09 로그인)은 각 WU가 구현할 때
request.META["REMOTE_ADDR"]를 그대로 신뢰해 쓰면 되도록 이 시점에
한 번만 정규화해 둔다.
"""


class XForwardedForMiddleware:
    """Render 엣지(단일 신뢰 홉)가 붙이는 X-Forwarded-For의 rightmost 값을
    실제 클라이언트 IP로 채택해 REMOTE_ADDR을 재설정한다.

    단일 신뢰 홉 구조(클라이언트 -> Render 엣지 -> 이 앱)에서는 Render 엣지가
    체인의 마지막에 추가한 값(rightmost)만 신뢰할 수 있다. 클라이언트가 직접
    보낸 X-Forwarded-For 값(leftmost 쪽)은 임의로 조작 가능하므로 신뢰하지
    않는다(03 §5.5.4). production 설정에서만 MIDDLEWARE에 등록한다 — 이
    전제(엣지가 유일한 진입 경로) 자체가 Render 배포 환경에서만 성립하기
    때문이다(dev 로컬 실행에는 해당 전제가 없음).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[-1].strip()
            if client_ip:
                request.META["REMOTE_ADDR"] = client_ip
        return self.get_response(request)
