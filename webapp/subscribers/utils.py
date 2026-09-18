"""IP 마스킹 유틸 (03-system-design.md §3.2/§5.6 "마지막 옥텟 마스킹").

`request.META["REMOTE_ADDR"]`은 `config.middleware.XForwardedForMiddleware`
(production 전용, 03 §5.5.4)가 Render 엣지의 X-Forwarded-For rightmost 값으로
이미 정규화해 둔 값을 그대로 읽는다 — 이 앱이 직접 헤더를 파싱하지 않는다.
"""


def mask_ip(ip: str) -> str:
    """마지막 옥텟(IPv4)/마지막 세그먼트(IPv6)를 0으로 마스킹한다.

    03 §3.2/§5.6은 IPv4 기준 "마지막 옥텟 마스킹"만 명시했다. IPv6 처리
    방식은 설계서에 없지만, "스팸 판별 신호로 쓸 수 있는 최소 단위까지만
    남기고 마지막 구획을 지운다"는 동일한 원칙을 그대로 확장한 자연스러운
    귀결이라 별도 질문 없이 구현했다(두 갈래로 해석이 갈리는 지점이 아님).
    형식을 알 수 없는 입력은 마스킹하지 않고 그대로 돌려준다(빈 값 방어).
    """
    if not ip:
        return ""

    if ":" in ip:
        parts = ip.split(":")
        if len(parts) > 1:
            parts[-1] = "0"
        return ":".join(parts)

    parts = ip.split(".")
    if len(parts) == 4:
        parts[-1] = "0"
        return ".".join(parts)

    return ip
