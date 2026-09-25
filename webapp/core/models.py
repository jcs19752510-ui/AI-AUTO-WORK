"""사이트 전역 설정 모델 (WU-08 규칙F 재작업 라운드, REQ-011/012, 03 §3.1/§1.2).

03-system-design.md §3.1(ER 다이어그램)이 애초에 `SiteSettings`에
`contact_email` 필드를 명시했었지만, WU-05(DEC-020)/WU-08(unit-08-note.md
§2-1)이 "이번엔 필요한 것만 만든다"(DEC-016/DEC-019 선례) 원칙에 따라 v1
범위에서 의도적으로 미루고 04-ux-design.md §2에 "향후 규칙F 재작업 대상"으로
명시해 두었다.

이번 재작업(2026-09-25, DEC-045)의 트리거: 11단계(사용자 매뉴얼) 작성 중
`legal/migrations/0002_create_legal_pages.py`의 개인정보처리방침 "문의처"
절이 "사이트 운영자에게 연락해 주시기 바랍니다"라고만 안내하고 실제
연락처가 어디에도 렌더링되지 않는 격차가 발견되었다(사용자 확인 후 진행
승인). `contact_email` 하나만 추가한다 — 04번이 함께 언급했던 "콜드스타트
문구 커스터마이즈"는 이번 요청 범위 밖이므로 손대지 않는다(과설계 방지,
요청 범위를 벗어난 확장 금지 원칙).
"""

from django.db import models

from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting


@register_setting
class SiteSettings(BaseSiteSetting):
    contact_email = models.EmailField(
        blank=True,
        help_text=(
            "개인정보처리방침 등에 노출되는 운영자 문의 이메일. 비워두면 "
            "연락처 안내를 표시하지 않는다(값이 없다고 페이지 렌더링이 "
            "깨지지 않음 — legal_page.html이 빈 값을 조건 분기로 처리)."
        ),
    )

    panels = [FieldPanel("contact_email")]
