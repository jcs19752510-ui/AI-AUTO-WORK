"""WU-09, REQ-010, 03 §5.1 [DEC-009] — Wagtail 표준 그룹(Editors/Moderators)의
권한 범위를 확정한다.

**발견한 결함(WU-09 조사)**: `blog.Category`는 `@register_snippet`으로 등록된
평범한 스니펫이라 기본 권한 정책이 `ModelPermissionPolicy(Category)`다(Wagtail
소스 `wagtail/snippets/views/snippets.py` `permission_policy` 프로퍼티로 직접
확인) — 즉 Django 표준 모델 권한(`blog.add_category`/`change_category`/
`delete_category`)을 그대로 검사한다. 그런데 이 권한을 Editors/Moderators
그룹에 부여하는 마이그레이션이 WU-02(Category 최초 도입) 어디에도 없었다 —
Wagtail 코어가 `wagtailcore/migrations/0002_initial_data.py`에서 자동으로
부여하는 것은 **페이지** 권한(add/edit/[publish])뿐이고, 스니펫 모델 권한은
각 스니펫을 도입하는 쪽이 직접 부여해야 한다(Wagtail 공식 패턴 —
`wagtail/images/migrations/0002_initial_data.py`가 이미지에 대해 동일하게
`get_or_create` + `group.permissions.add()`로 처리하는 것을 그대로 참고했다).
이 결함이 있으면 슈퍼유저가 아닌 Editors/Moderators 그룹 사용자는 Wagtail
어드민에서 카테고리(REQ-002)를 추가/수정/삭제할 수 없다.

**이미지(`custom_images.CustomImage`) 권한은 이 마이그레이션이 다루지
않는다** — Wagtail이 `WAGTAILIMAGES_IMAGE_MODEL`을 스왑해도 권한 코드네임은
항상 원본 `wagtailimages.Image`에 고정된다(`wagtail/images/permissions.py`
`CollectionOwnershipPermissionPolicy(get_image_model(), auth_model=Image, ...)`
소스로 직접 확인 — `auth_model`이 실제 권한 판정에 쓰이는 콘텐츠타입을
결정한다). 이미지 add/change 권한은 Wagtail 자체 마이그레이션
(`wagtailimages 0002_initial_data`/`0012_copy_image_permissions_to_collections`)이
이미 Editors/Moderators에 올바르게 부여해 두었으므로 WU-03의 이미지 모델
스왑과 무관하게 정상 동작한다 — 이 마이그레이션이 다시 손댈 필요가 없다
(unit-09-note.md §2에서 로컬로 재확인).
"""

from django.db import migrations

_CATEGORY_PERMISSIONS = [
    ("add_category", "Can add 카테고리"),
    ("change_category", "Can change 카테고리"),
    ("delete_category", "Can delete 카테고리"),
]

_GROUP_NAMES = ["Editors", "Moderators"]


def grant_category_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    # post_migrate 시그널이 Permission 행을 자동 생성하는 시점(모든 앱의
    # 마이그레이션이 끝난 뒤)보다 이 데이터 마이그레이션이 먼저 실행되므로,
    # Wagtail 코어 마이그레이션과 동일하게 get_or_create로 직접 만든다.
    category_content_type, _created = ContentType.objects.get_or_create(
        app_label="blog", model="category"
    )

    permissions = []
    for codename, name in _CATEGORY_PERMISSIONS:
        permission, _created = Permission.objects.get_or_create(
            content_type=category_content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions.append(permission)

    for group in Group.objects.filter(name__in=_GROUP_NAMES):
        group.permissions.add(*permissions)


def revoke_category_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    try:
        category_content_type = ContentType.objects.get(
            app_label="blog", model="category"
        )
    except ContentType.DoesNotExist:
        return

    codenames = [codename for codename, _name in _CATEGORY_PERMISSIONS]
    Permission.objects.filter(
        content_type=category_content_type, codename__in=codenames
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),
        ("wagtailcore", "0002_initial_data"),
    ]

    operations = [
        migrations.RunPython(grant_category_permissions, revoke_category_permissions),
    ]
