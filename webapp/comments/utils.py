"""IP 마스킹 유틸 (03-system-design.md §3.2-1).

`subscribers/utils.py`와 완전히 동일한 로직을 이 앱에 독립적으로 복제한다
— 다른 앱에서 import하지 않는 이유는 `subscribers/constants.py`가 이미
설명한 것과 동일한 "경계 원칙"(03 §1.2, 한 앱의 변경이 다른 앱에 번지지
않게 격리)을 그대로 따르기 위함이다.
"""


def mask_ip(ip: str) -> str:
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
