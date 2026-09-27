"""댓글 모델 (WU-11 부분 착수, REQ-019, 03-system-design.md §3.1/§3.2-1).

회원가입이 없으므로(DEC-009) 순수 Django 모델이다(Wagtail Page 아님 —
`NewsletterSubscriber`와 동일한 판단, 03 §3.2). Wagtail Snippet으로
등록해 Moderators 그룹이 어드민에서 승인/거부(`status` 전환)와 하드 삭제를
할 수 있게 한다 — 새 커스텀 관리 화면을 만들지 않고 Wagtail 스니펫 CRUD를
그대로 재사용한다(과설계 방지, `Category` snippet과 동일 패턴).

`source_ip_raw`/`BlockedIP`는 WU-14(DEC-055, 스팸 방지 강화 — 사용자
요청)에서 추가됐다. `source_ip_raw`는 **의도적으로 `panels`에 넣지
않는다** — 자동 반복거부 차단 로직(`comments/apps.py`)과 수동 차단
목록(`BlockedIP`) 매칭에만 내부적으로 쓰이는 값이라, 운영자가 매일 보는
댓글 목록 화면(`source_ip_masked`)의 개인정보 노출 수준은 그대로 유지한다.
"""

from django.db import models
from django.utils import timezone

from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet


@register_snippet
class Comment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "승인 대기"),
        (STATUS_APPROVED, "승인됨"),
        (STATUS_REJECTED, "거부됨"),
    ]

    page = models.ForeignKey(
        "blog.BlogPostPage",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author_name = models.CharField(
        max_length=100,
        help_text="자유입력 표시명(회원가입 없음, 실명 검증 없음, 03 §3.2-1).",
    )
    body = models.TextField(
        help_text="댓글 본문(plain text만 허용 — 템플릿에서 HTML 이스케이프 후 렌더링, 03 §3.2-1 XSS 방지 원칙)."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    source_ip_masked = models.CharField(
        max_length=45,
        blank=True,
        help_text="스팸 판별용, 마지막 옥텟/세그먼트를 마스킹한 접속 IP(subscribers 앱과 동일 원칙).",
    )
    source_ip_raw = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=(
            "자동 반복거부 차단 판정에만 내부적으로 쓰이는 원본 접속 IP. "
            "어드민 화면에는 노출하지 않는다(panels 미포함, DEC-055)."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("page"),
        FieldPanel("author_name"),
        FieldPanel("body"),
        FieldPanel("status"),
        FieldPanel("source_ip_masked"),
    ]

    class Meta:
        verbose_name = "댓글"
        verbose_name_plural = "댓글"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author_name}: {self.body[:30]}"


@register_snippet
class BlockedIP(models.Model):
    """댓글 스팸 차단 목록(DEC-055). 수동 등록(운영자가 직접 추가)과
    자동 등록(`comments/apps.py`가 반복 거부 시 생성, `is_auto=True`)
    양쪽을 같은 테이블로 관리한다 — 차단 판정 로직(`is_blocked`) 입장에서는
    출처가 다를 뿐 "이 IP는 막는다"는 동일한 사실이라 테이블을 분리할
    이유가 없다(과설계 방지).

    `expires_at`이 비어 있으면 영구 차단이다. 자동 차단은 항상 만료 시각을
    채워서 생성한다(사람이 검토하지 않은 판정이 영구히 남지 않도록 —
    core/admin_auth.py의 IP 레이트리밋이 "계정이 아니라 IP 기준, 일정
    시간 후 자동 해제"를 택한 것과 동일한 설계 철학)."""

    ip_address = models.GenericIPAddressField(
        help_text="차단할 접속 IP. 마스킹하지 않은 원본 값을 그대로 입력한다."
    )
    reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="차단 사유(선택). 자동 차단은 '자동: N일 내 반복 거부 M회' 형식으로 채워진다.",
    )
    is_auto = models.BooleanField(
        default=False,
        help_text="자동 차단 로직이 생성했으면 True. 운영자가 직접 추가했으면 False.",
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="이 시각 이후 자동으로 차단이 풀린다. 비워두면 영구 차단(수동 차단의 기본값).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [
        FieldPanel("ip_address"),
        FieldPanel("reason"),
        FieldPanel("expires_at"),
        FieldPanel("is_auto"),
    ]

    class Meta:
        verbose_name = "차단된 IP"
        verbose_name_plural = "차단된 IP"
        ordering = ["-created_at"]

    def __str__(self):
        suffix = "(자동)" if self.is_auto else "(수동)"
        return f"{self.ip_address} {suffix}"

    @classmethod
    def is_blocked(cls, ip):
        """제출 시점에 이 IP가 현재 차단 상태인지 확인한다. 만료된 자동
        차단은 더 이상 유효하지 않음(만료 레코드를 지우지 않고 그냥
        무시한다 — 이력 확인용으로 남겨두는 것이 삭제보다 안전, 필요하면
        운영자가 직접 정리)."""
        if not ip:
            return False
        return cls.objects.filter(
            ip_address=ip,
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).exists()
