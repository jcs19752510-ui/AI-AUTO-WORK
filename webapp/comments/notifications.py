"""신규 댓글 등록 알림 (REQ-019 후속, 2026-09-25, 사용자 요청).

11-ops-handoff-runbook.md §8 항목17이 "권고(비차단)"로 남겼던 항목이다.
사용자가 "DJANGO_ADMIN_EMAIL 재사용" 방식을 선택했다 — 이미 500 에러
알림(REQ-012, `production.py`의 `ADMINS`/`AdminEmailHandler`)에 쓰이는
채널을 그대로 재사용한다. 새 설정값이나 새 SiteSettings 필드를 만들지
않는다(과설계 방지, 기존 채널 재사용 원칙 — subscribers/comments가
`mask_ip`를 각자 복제한 것과 반대로, 이번엔 "운영자에게 메일 보내기"라는
범용 채널 자체를 재사용하는 것이라 앱 경계 원칙과 충돌하지 않는다).

`settings.ADMINS`가 비어 있으면(`DJANGO_ADMIN_EMAIL` 미설정) `mail_admins()`가
아무 것도 하지 않고 조용히 끝난다 — 500 알림과 동일한 "값이 없으면 알림이
조용히 발송되지 않을 뿐 기동/요청 처리를 막지 않는다"는 원칙을 그대로
따른다(production.py 주석 참고). 메일 발송 실패(SMTP 오류 등)가 댓글 제출
자체를 실패시키지 않도록 예외를 삼킨다 — 알림은 부가 기능이지 핵심 경로가
아니다.
"""

import logging

from django.core.mail import mail_admins

logger = logging.getLogger(__name__)


def notify_new_comment(comment):
    subject = f"[댓글 승인 대기] {comment.page.title}"
    message = (
        f"새 댓글이 등록되어 승인을 기다리고 있습니다.\n\n"
        f"게시물: {comment.page.title}\n"
        f"작성자 표시명: {comment.author_name}\n"
        f"내용:\n{comment.body}\n\n"
        f"모더레이션: /cms-admin/snippets/comments/comment/{comment.id}/edit/\n"
    )
    try:
        mail_admins(subject, message, fail_silently=False)
    except Exception:
        # 알림 발송 실패는 댓글 저장 자체를 되돌리지 않는다(핵심 경로 보호).
        # 운영자는 여전히 Wagtail 어드민에서 직접 확인할 수 있다.
        logger.exception("댓글 등록 알림 메일 발송 실패 (comment id=%s)", comment.id)
