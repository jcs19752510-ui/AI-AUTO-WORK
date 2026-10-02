"""반복 거부 자동차단(DEC-055) — Wagtail 어드민에서 운영자가 댓글
`status`를 "거부됨"으로 바꿔 저장하는 순간(스니펫 편집 폼이 호출하는
`Comment.save()`) 발동한다. 승인/대기 전환은 무시한다.

`Comment.created_at`(제출 시각)을 "거부 시각"의 근사값으로 쓴다 — 실제
거부 처리 시각을 별도 필드로 추가하는 대신, 이미 있는 값으로 충분히
근사할 수 있다고 판단했다(과설계 방지). 스팸 IP는 보통 짧은 시간에
여러 건을 몰아 제출하므로 이 근사가 실제 판단을 왜곡할 가능성은 낮다.
"""

from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .constants import (
    AUTO_BLOCK_DURATION_DAYS,
    AUTO_BLOCK_REJECTION_THRESHOLD,
    AUTO_BLOCK_WINDOW_DAYS,
)
from .models import BlockedIP, Comment


@receiver(post_save, sender=Comment)
def auto_block_repeat_offenders(sender, instance, **kwargs):
    if instance.status != Comment.STATUS_REJECTED or not instance.source_ip_raw:
        return

    if BlockedIP.is_blocked(instance.source_ip_raw):
        # 이미 차단 중인 IP를 또 거부해도 중복 레코드를 만들지 않는다.
        return

    window_start = timezone.now() - timedelta(days=AUTO_BLOCK_WINDOW_DAYS)
    rejection_count = Comment.objects.filter(
        source_ip_raw=instance.source_ip_raw,
        status=Comment.STATUS_REJECTED,
        created_at__gte=window_start,
    ).count()

    if rejection_count >= AUTO_BLOCK_REJECTION_THRESHOLD:
        BlockedIP.objects.create(
            ip_address=instance.source_ip_raw,
            reason=f"자동: {AUTO_BLOCK_WINDOW_DAYS}일 내 반복 거부 {rejection_count}회",
            is_auto=True,
            expires_at=timezone.now() + timedelta(days=AUTO_BLOCK_DURATION_DAYS),
        )
