from django.apps import AppConfig


class LegalConfig(AppConfig):
    """법적 페이지(WU-06, REQ-007/008/009/015) — 개인정보처리방침/이용약관
    (콘텐츠 정책 하위 섹션 포함)/쿠키 사용 고지.

    03-system-design.md §1.2 모듈 경계 표가 지정한 `legal` 앱이다. 세 페이지는
    모두 단일 재사용 가능한 `LegalPage` 모델(§3.2가 "각각 별도 Page 서브클래스
    (또는 공통 RichTextPage 1개 모델을 재사용)"로 명시한 두 옵션 중 후자)로
    관리한다 — decisions.md DEC-022 참고.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "legal"
    verbose_name = "법적 페이지"
