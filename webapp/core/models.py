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

두 번째 재작업(2026-09-26, DEC-053)의 트리거: `decisions.md` DEC-053이
"수익화 모델(§11 Q1)"을 광고 기반(애드센스)으로 확정하면서 REQ-023(광고
SDK 연동)이 Out-of-Scope에서 해제됐다. 사용자가 아직 애드센스 계정이
없다고 명시했으므로(가입은 사용자가 구글 계정으로 직접 해야 하는 영역),
이번 라운드는 "계정이 생기면 값만 붙여넣으면 바로 켜지는" 상태까지만
준비한다 — `adsense_client_id` 하나만 추가하고, 광고 슬롯 수동 배치 같은
추가 설계는 실제 계정 발급 이후(및 04-ux-design.md 재검토) 범위로 미룬다
(과설계 방지, contact_email과 동일한 선례).
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

    adsense_client_id = models.CharField(
        max_length=32,
        blank=True,
        help_text=(
            "Google 애드센스 게시자 ID(예: ca-pub-1234567890123456). 애드센스 "
            "심사 승인 후 발급받은 값을 그대로 붙여넣는다. 비워두면 광고 "
            "스크립트·ads.txt·개인정보처리방침 광고 쿠키 안내 전부 렌더링되지 "
            "않는다(contact_email과 동일한 '값 없으면 조용히 비활성' 원칙 — "
            "애드센스 계정이 없는 상태에서도 사이트가 정상 동작해야 하므로)."
        ),
    )

    panels = [FieldPanel("contact_email"), FieldPanel("adsense_client_id")]
