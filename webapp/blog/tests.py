"""WU-02(REQ-001/002) 글쓰기/발행 워크플로 자동 회귀 테스트.

06/07/08단계가 이 워크플로(초안 저장/예약발행/즉시게시/수정재발행)를 반복해서
수동 스크립트로 실측 PASS 확인해 왔지만(`unit-02-test.md`,
`feature-WU-02-integration-test.md`, `08-full-system-test.md` SEED-01), 그
검증 코드 자체는 이 저장소의 `manage.py test`에 커밋되어 있지 않았다 —
`core.tests`/`legal.tests`/`subscribers.tests`만 있고 `blog.tests`가
없었다. 사용자가 "글쓰기 관리 운영이 가능한지" 자동 테스트로 확인해 달라고
요청한 것을 계기로, 그 반복 수동 검증을 이 파일에 회귀 테스트로 고정한다
(2026-09-25).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from blog.models import BlogPostPage, Category
from wagtail.models import Page

User = get_user_model()


class BlogAuthoringWorkflowTests(TestCase):
    """실제 운영자가 "글쓰기"로 할 수 있어야 하는 것들 — 초안, 예약발행,
    즉시 게시, 수정 후 재발행, 카테고리 필수 제약 — 을 unit-02-test.md
    AC6/AC9/AC10/AC11/AC13와 동일한 시나리오로 재현한다."""

    def setUp(self):
        self.home = Page.objects.get(depth=2).specific  # HomePage(루트 바로 아래)
        self.category = Category.objects.create(name="공지", slug="notice")

    def test_category_is_required(self):
        """AC6 — category 없이는 저장 자체가 거부되어야 한다."""
        page = BlogPostPage(title="카테고리 없는 글", slug="no-category")
        with self.assertRaises(Exception):
            self.home.add_child(instance=page)

    def test_draft_save_does_not_publish(self):
        """AC9 — save_revision()만 호출하면(publish 없음) live로 바뀌지 않는다.
        Wagtail Page.live 기본값이 True이므로 반드시 live=False를 명시해야
        한다(unit-02-test.md TC-009가 최초 발견한 테스트 스크립트 함정과
        동일 — 여기서도 동일하게 명시)."""
        page = BlogPostPage(
            title="초안 글", slug="draft-post", category=self.category, live=False
        )
        self.home.add_child(instance=page)
        page.save_revision(user=None)

        page.refresh_from_db()
        self.assertFalse(page.live)
        self.assertGreaterEqual(page.revisions.count(), 1)

    def test_scheduled_publish_not_live_until_go_live_at(self):
        """AC10 — go_live_at이 미래면 publish()를 호출해도 즉시 live가 되지
        않는다(예약발행)."""
        page = BlogPostPage(
            title="예약 글",
            slug="scheduled-post",
            category=self.category,
            live=False,
            go_live_at=timezone.now() + timezone.timedelta(days=7),
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        page.refresh_from_db()
        self.assertFalse(page.live)
        self.assertIsNotNone(page.go_live_at)

    def test_publish_makes_post_live_and_publicly_visible(self):
        """AC11 — go_live_at 없이 publish()하면 즉시 live가 되고, 공개
        URL(`/blog/<slug>/`)에서 실제로 200으로 조회된다. 이것이 "글을 써서
        발행하면 방문자가 볼 수 있다"는 사용자 시나리오의 핵심이다."""
        page = BlogPostPage(
            title="발행된 글", slug="published-post", category=self.category, live=False
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        page.refresh_from_db()
        self.assertTrue(page.live)
        self.assertIsNotNone(page.first_published_at)

        cache.clear()
        response = self.client.get("/blog/published-post/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("발행된 글".encode(), response.content)

    def test_unpublished_draft_not_publicly_reachable(self):
        """대조군 — live=False인 초안은 공개 URL에서 200이 아니어야 한다
        (404, Wagtail 기본 동작: draft-only page는 익명 방문자에게 안 보임)."""
        page = BlogPostPage(
            title="아직 비공개", slug="still-draft", category=self.category, live=False
        )
        self.home.add_child(instance=page)
        page.save_revision(user=None)

        cache.clear()
        response = self.client.get("/blog/still-draft/")
        self.assertEqual(response.status_code, 404)

    def test_edit_and_republish_updates_live_content(self):
        """AC13 — 발행된 글을 수정하고 재발행하면 공개 화면에도 반영된다."""
        page = BlogPostPage(
            title="원래 제목", slug="editable-post", category=self.category, live=False
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        page.title = "수정된 제목"
        page.save_revision().publish()

        cache.clear()
        response = self.client.get("/blog/editable-post/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("수정된 제목".encode(), response.content)
        self.assertNotIn("원래 제목".encode(), response.content)

    def test_category_listing_shows_published_post_only(self):
        """카테고리 목록(`/category/<slug>/`)에 발행된 글만 노출되는지 확인
        (REQ-002 분류체계가 실제로 운영자가 쓸 수 있는 상태인지)."""
        published = BlogPostPage(
            title="공지 발행글", slug="notice-published", category=self.category, live=False
        )
        self.home.add_child(instance=published)
        published.save_revision().publish()

        draft = BlogPostPage(
            title="공지 초안글", slug="notice-draft", category=self.category, live=False
        )
        self.home.add_child(instance=draft)
        draft.save_revision(user=None)

        cache.clear()
        response = self.client.get("/category/notice/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("공지 발행글".encode(), response.content)
        self.assertNotIn("공지 초안글".encode(), response.content)

    def test_delete_removes_post_from_public_site(self):
        """"삭제" 관리 작업 — 발행된 글을 삭제하면 공개 URL에서 더 이상
        조회되지 않아야 한다(Wagtail Page.delete()가 트리에서 제거)."""
        page = BlogPostPage(
            title="삭제될 글", slug="to-be-deleted", category=self.category, live=False
        )
        self.home.add_child(instance=page)
        page.save_revision().publish()

        cache.clear()
        self.assertEqual(self.client.get("/blog/to-be-deleted/").status_code, 200)

        page_id = page.id
        page.delete()

        self.assertFalse(BlogPostPage.objects.filter(id=page_id).exists())
        cache.clear()
        self.assertEqual(self.client.get("/blog/to-be-deleted/").status_code, 404)


class BlogAdminPermissionBoundaryTests(TestCase):
    """"관리" 권한 경계 — Editors 그룹은 작성/수정만 가능하고 발행 권한이
    없어야 하며(11-admin-manual.md가 이미 서술한 계약), Moderators/superuser는
    발행할 수 있어야 한다. Wagtail 표준 그룹 권한 체계 자체를 재구현하지
    않고 그대로 쓰기로 한 03-system-design.md §5.1 결정이 실제로 이 프로젝트
    그룹 구성에서 유효한지 확인한다."""

    def setUp(self):
        self.home = Page.objects.get(depth=2).specific
        self.category = Category.objects.create(name="테스트", slug="test-cat")
        self.page = BlogPostPage(
            title="권한 테스트 글", slug="permission-test", category=self.category, live=False
        )
        self.home.add_child(instance=self.page)

    def test_editor_cannot_publish(self):
        editor = User.objects.create_user(username="editor-perm", password="unused", is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))
        perms = self.page.permissions_for_user(editor)
        self.assertTrue(perms.can_edit())
        self.assertFalse(perms.can_publish())

    def test_moderator_can_publish(self):
        moderator = User.objects.create_user(
            username="moderator-perm", password="unused", is_staff=True
        )
        moderator.groups.add(Group.objects.get(name="Moderators"))
        perms = self.page.permissions_for_user(moderator)
        self.assertTrue(perms.can_publish())
