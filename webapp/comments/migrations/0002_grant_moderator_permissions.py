"""REQ-019, 03 §3.2-1 [DEC-047] — 댓글 스니펫(`Comment`)의 모더레이션
권한을 확정한다.

`core/migrations/0001_setup_editor_permissions.py`(Category 권한)와 동일한
결함을 처음부터 피하기 위해, WU-02(Category)가 그랬듯 이 스니펫 도입
마이그레이션 자체에서 권한을 함께 부여한다.

**Editors에게는 부여하지 않는다** — 03 §3.2-1이 "Editors는 발행 권한이
없는 것과 동일한 논리로 댓글 승인 권한도 없다"고 명시했다(사전승인제가
스팸/명예훼손 리스크를 통제하는 최종 방어선이므로, 이 권한은 Moderators
이상으로 제한한다). `add_comment`는 어느 그룹에도 부여하지 않는다 — 댓글은
공개 제출 폼(`comments:submit`)으로만 생성되며, 관리자가 어드민에서 새
댓글을 "추가"할 필요가 없다(03 §3.2-1).
"""

from django.db import migrations

_COMMENT_PERMISSIONS = [
    ("view_comment", "Can view 댓글"),
    ("change_comment", "Can change 댓글"),
    ("delete_comment", "Can delete 댓글"),
]

_GROUP_NAMES = ["Moderators"]


def grant_comment_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    comment_content_type, _created = ContentType.objects.get_or_create(
        app_label="comments", model="comment"
    )

    permissions = []
    for codename, name in _COMMENT_PERMISSIONS:
        permission, _created = Permission.objects.get_or_create(
            content_type=comment_content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(permission)

    for group in Group.objects.filter(name__in=_GROUP_NAMES):
        group.permissions.add(*permissions)


def revoke_comment_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    try:
        comment_content_type = ContentType.objects.get(
            app_label="comments", model="comment"
        )
    except ContentType.DoesNotExist:
        return

    codenames = [codename for codename, _name in _COMMENT_PERMISSIONS]
    Permission.objects.filter(
        content_type=comment_content_type, codename__in=codenames
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("comments", "0001_initial"),
        ("wagtailcore", "0002_initial_data"),
    ]

    operations = [
        migrations.RunPython(grant_comment_permissions, revoke_comment_permissions),
    ]
