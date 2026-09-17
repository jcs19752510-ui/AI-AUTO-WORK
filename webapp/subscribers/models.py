"""뉴스레터 구독자 모델 (WU-07, REQ-016, 03-system-design.md §3.1/§3.2).

Wagtail Page가 아닌 순수 Django 모델이다(공개 콘텐츠 트리와 무관, §3.2).
회원가입이 없으므로(DEC-009) 이 레코드가 곧 구독자의 유일한 식별 수단이다.
"""

import uuid

from django.db import models


class NewsletterSubscriber(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_UNSUBSCRIBED = "unsubscribed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "구독중"),
        (STATUS_UNSUBSCRIBED, "구독취소"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, help_text="구독 시점에 소문자로 정규화되어 저장된다(views.py 참고).")
    consented_at = models.DateTimeField()
    consent_version = models.CharField(
        max_length=50,
        help_text="동의 시점의 개인정보처리방침 버전 스냅샷(constants.PRIVACY_POLICY_VERSION).",
    )
    source_ip_masked = models.CharField(
        max_length=45,
        blank=True,
        help_text="스팸 판별용, 마지막 옥텟/세그먼트를 마스킹한 접속 IP.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "뉴스레터 구독자"
        verbose_name_plural = "뉴스레터 구독자"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
