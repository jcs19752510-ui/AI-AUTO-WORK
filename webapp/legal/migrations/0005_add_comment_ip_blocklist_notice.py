# DEC-055(반복 거부 자동차단 + 수동 IP 차단 목록, 사용자 요청) 후속 —
# 개인정보처리방침 "수집하는 개인정보 항목" 목록의 댓글 관련 문장이 "마지막
# 옥텟을 마스킹한 접속 IP"만 수집한다고 안내했는데, 이제 스팸 차단 목적으로
# 마스킹하지 않은 원본 IP도 내부적으로 별도 보관한다(comments.Comment.
# source_ip_raw, comments.BlockedIP). 이 사실이 실제 수집 항목과 어긋나지
# 않도록 정정한다.
#
# 0003_add_comment_privacy_notice.py/0004_add_adsense_cookie_notice.py와
# 동일한 패턴: 실제 LegalPage를 import해 save_revision().publish()로 리비전
# 이력을 남기고, 원본 문구가 이미 바뀌었으면 건드리지 않는다.

from django.db import migrations

_OLD_COMMENT_ITEM = (
    "<li>댓글 작성 시: 표시명(자유입력, 실명 검증 없음), "
    "스팸 판별용으로 마지막 옥텟을 마스킹한 접속 IP "
    "— 이메일은 수집하지 않습니다. 댓글은 운영자 승인 후에만 공개됩니다.</li>"
)

_NEW_COMMENT_ITEM = (
    "<li>댓글 작성 시: 표시명(자유입력, 실명 검증 없음), 스팸 판별용으로 "
    "마지막 옥텟을 마스킹한 접속 IP(운영자 화면에 표시되는 값) "
    "— 이메일은 수집하지 않습니다. 댓글은 운영자 승인 후에만 공개됩니다. "
    "반복적인 스팸성 댓글을 자동으로 걸러내기 위해 마스킹하지 않은 원본 "
    "접속 IP를 별도로 시스템 내부에만 보관하며, 이 값은 반복 거부 자동차단 "
    "및 운영자의 수동 차단 목록 판정에만 쓰이고 운영자 화면에는 노출되지 "
    "않습니다.</li>"
)


def update_comment_privacy_notice(apps, schema_editor):
    from legal.models import LegalPage

    page = LegalPage.objects.filter(slug="privacy-policy").first()
    if page is None:
        return

    if _OLD_COMMENT_ITEM not in page.body:
        # 이미 갱신되었거나 운영자가 어드민에서 직접 수정한 경우 —
        # 덮어쓰지 않는다(0003/0004와 동일 원칙).
        return

    page.body = page.body.replace(_OLD_COMMENT_ITEM, _NEW_COMMENT_ITEM)
    page.save_revision(user=None).publish()


def noop_reverse(apps, schema_editor):
    # 콘텐츠 정정은 되돌리지 않는다(0003/0004와 동일 원칙).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0004_add_adsense_cookie_notice"),
        ("comments", "0003_add_blocked_ip_and_source_ip_raw"),
    ]

    operations = [
        migrations.RunPython(update_comment_privacy_notice, noop_reverse),
    ]
