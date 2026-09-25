# REQ-019(댓글) v1 범위 승격에 따른 개인정보처리방침 갱신 (03 §3.2-1/§5.6,
# DEC-047).
#
# 0002_create_legal_pages.py의 PRIVACY_POLICY_BODY 마지막 문장이 "회원가입,
# 댓글 등 그 외의 개인정보는 수집하지 않습니다"라고 명시했는데, 이제
# 댓글이 표시명(author_name)과 마스킹된 접속 IP를 수집하므로 이 문장이
# 더 이상 사실과 일치하지 않는다. 이 마이그레이션은 (1) 새 수집 항목을
# "수집하는 개인정보 항목" 목록에 추가하고, (2) 더 이상 사실이 아닌
# 문장을 정정한다.
#
# historical 모델(`apps.get_model`)에는 `save_revision()`/`publish()` 같은
# Wagtail Page 커스텀 메서드가 없다(0002가 필드를 직접 채워 넣었던 것과
# 같은 이유로, 이번에도 raw update로 처리할 수도 있었으나) — 이번엔 실제
# "콘텐츠 편집"이므로 Wagtail의 표준 리비전 이력이 남도록 실제 모델
# 클래스를 그대로 import해 `save_revision().publish()`를 쓴다(운영자가
# 나중에 Wagtail 어드민에서 "이 방침이 언제 왜 바뀌었는지" 리비전
# 이력으로 추적할 수 있게 하기 위함 — 03 §3.2 LegalPage 설명이 이미
# "리비전 기능을 그대로 활용해 방침 변경 이력이 자동으로 남는다"고
# 명시한 이점을 실제로 살린다).

from django.db import migrations

_OLD_ITEMS_CLOSE = "</ul>\n<p>회원가입, 댓글 등 그 외의 개인정보는 수집하지 않습니다.</p>"

_NEW_ITEMS_CLOSE = (
    "<li>댓글 작성 시: 표시명(자유입력, 실명 검증 없음), "
    "스팸 판별용으로 마지막 옥텟을 마스킹한 접속 IP "
    "— 이메일은 수집하지 않습니다. 댓글은 운영자 승인 후에만 공개됩니다.</li>\n"
    "</ul>\n"
    "<p>회원가입 기능은 없으며, 위에 명시한 항목 외의 개인정보는 수집하지 않습니다.</p>"
)


def add_comment_privacy_notice(apps, schema_editor):
    from legal.models import LegalPage

    page = LegalPage.objects.filter(slug="privacy-policy").first()
    if page is None:
        # 0002가 아직 실행되지 않았거나(불가능한 순서, dependencies로 강제됨)
        # 페이지가 삭제된 예외 상황 — 조용히 건너뛴다(마이그레이션 실패로
        # 배포 자체를 막지 않는다, 이 갱신은 콘텐츠 정정이지 스키마 변경이
        # 아니므로).
        return

    if _OLD_ITEMS_CLOSE not in page.body:
        # 이미 갱신되었거나(재실행) 운영자가 어드민에서 직접 수정해 원본
        # 문구가 남아있지 않은 경우 — 덮어쓰지 않는다(운영자의 수동 편집을
        # 존중, 03 §3.2 "운영자가 어드민에서 직접 수정" 원칙과 일치).
        return

    page.body = page.body.replace(_OLD_ITEMS_CLOSE, _NEW_ITEMS_CLOSE)
    page.save_revision(user=None).publish()


def noop_reverse(apps, schema_editor):
    # 콘텐츠 정정은 되돌리지 않는다(0002의 remove_legal_pages처럼 페이지
    # 자체를 지우는 것과 달리, 텍스트 되돌리기는 "거짓 정보로 되돌리기"가
    # 되므로 의도적으로 아무 것도 하지 않는다).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0002_create_legal_pages"),
        ("comments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_comment_privacy_notice, noop_reverse),
    ]
