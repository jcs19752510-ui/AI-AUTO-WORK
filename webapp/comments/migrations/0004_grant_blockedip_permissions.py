"""DEC-055 — `BlockedIP` 스니펫 관리 권한을 확정한다.

`0002_grant_moderator_permissions.py`(Comment 권한)와 동일한 이유로
Moderators에게만 부여한다 — 차단 목록 관리는 댓글 승인/거부와 같은
신뢰 수준의 판단이라, 그 권한을 이미 가진 그룹에게만 준다(과설계 방지,
새 그룹을 만들지 않음).

`add_blockedip`도 함께 부여한다 — Comment와 달리 `BlockedIP`는 운영자가
직접 신규 항목을 등록하는 것이 정상 업무 흐름이다(수동 차단, 사용자
요청).
"""

from django.db import migrations

_BLOCKEDIP_PERMISSIONS = [
    ("add_blockedip", "Can add 차단된 IP"),
    ("view_blockedip", "Can view 차단된 IP"),
    ("change_blockedip", "Can change 차단된 IP"),
    ("delete_blockedip", "Can delete 차단된 IP"),
]

_GROUP_NAMES = ["Moderators"]


def grant_blockedip_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    blockedip_content_type, _created = ContentType.objects.get_or_create(
        app_label="comments", model="blockedip"
    )

    permissions = []
    for codename, name in _BLOCKEDIP_PERMISSIONS:
        permission, _created = Permission.objects.get_or_create(
            content_type=blockedip_content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(permission)

    for group in Group.objects.filter(name__in=_GROUP_NAMES):
        group.permissions.add(*permissions)


def revoke_blockedip_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    try:
        blockedip_content_type = ContentType.objects.get(
            app_label="comments", model="blockedip"
        )
    except ContentType.DoesNotExist:
        return

    codenames = [codename for codename, _name in _BLOCKEDIP_PERMISSIONS]
    Permission.objects.filter(
        content_type=blockedip_content_type, codename__in=codenames
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("comments", "0003_add_blocked_ip_and_source_ip_raw"),
        ("wagtailcore", "0002_initial_data"),
    ]

    operations = [
        migrations.RunPython(grant_blockedip_permissions, revoke_blockedip_permissions),
    ]
