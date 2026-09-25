"""댓글 모델 (WU-11 부분 착수, REQ-019, 03-system-design.md §3.1/§3.2-1).

회원가입이 없으므로(DEC-009) 순수 Django 모델이다(Wagtail Page 아님 —
`NewsletterSubscriber`와 동일한 판단, 03 §3.2). Wagtail Snippet으로
등록해 Moderators 그룹이 어드민에서 승인/거부(`status` 전환)와 하드 삭제를
할 수 있게 한다 — 새 커스텀 관리 화면을 만들지 않고 Wagtail 스니펫 CRUD를
그대로 재사용한다(과설계 방지, `Category` snippet과 동일 패턴).
"""

from django.db import models

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
