"""댓글 기능 회귀 테스트 (REQ-019, 03-system-design.md §3.2-1/§4).

`subscribers/tests.py`와 동일한 방식으로 자동화한다 — 수동 확인 대신
회귀 테스트로 남겨 6단계 테스터가 그대로 재실행할 수 있게 한다.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import BlogPostPage, Category
from wagtail.models import Page

from .constants import RATE_LIMIT_MAX_ATTEMPTS
from .models import Comment

User = get_user_model()


class CommentSubmissionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="공지", slug="notice")
        self.post = BlogPostPage(
            title="댓글 테스트 글", slug="comment-test-post", category=category, live=False
        )
        home.add_child(instance=self.post)
        self.post.save_revision().publish()
        self.post.refresh_from_db()
        self.url = reverse("comments:submit")

    def _valid_payload(self, **overrides):
        payload = {
            "page_id": self.post.id,
            "author_name": "홍길동",
            "body": "좋은 글 감사합니다.",
            "hp_field": "",
        }
        payload.update(overrides)
        return payload

    def test_submit_creates_pending_comment(self):
        response = self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")

        self.assertEqual(response.status_code, 200)
        comment = Comment.objects.get(page=self.post)
        self.assertEqual(comment.status, Comment.STATUS_PENDING)
        self.assertEqual(comment.author_name, "홍길동")
        self.assertEqual(comment.source_ip_masked, "203.0.113.0")

    def test_pending_comment_not_shown_on_public_page(self):
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")

        cache.clear()
        response = self.client.get(self.post.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"\xed\x99\x8d\xea\xb8\xb8\xeb\x8f\x99", response.content)  # "홍길동" UTF-8

    def test_approved_comment_shown_on_public_page(self):
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")
        comment = Comment.objects.get(page=self.post)
        comment.status = Comment.STATUS_APPROVED
        comment.save(update_fields=["status"])

        cache.clear()
        response = self.client.get(self.post.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("홍길동".encode(), response.content)
        self.assertIn("좋은 글 감사합니다".encode(), response.content)

    def test_rejected_comment_not_shown_on_public_page(self):
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")
        comment = Comment.objects.get(page=self.post)
        comment.status = Comment.STATUS_REJECTED
        comment.save(update_fields=["status"])

        cache.clear()
        response = self.client.get(self.post.url)
        self.assertNotIn("홍길동".encode(), response.content)

    def test_missing_author_name_rejected(self):
        response = self.client.post(self.url, self._valid_payload(author_name=""))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_whitespace_only_author_name_rejected(self):
        response = self.client.post(self.url, self._valid_payload(author_name="   "))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_missing_body_rejected(self):
        response = self.client.post(self.url, self._valid_payload(body=""))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_no_email_field_accepted_or_required(self):
        """사용자 결정(DEC-047) — 이메일 필드 자체가 폼에 없어야 한다."""
        from .forms import CommentForm

        self.assertNotIn("email", CommentForm.base_fields)

    def test_invalid_page_id_rejected(self):
        response = self.client.post(self.url, self._valid_payload(page_id=999999))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_non_numeric_page_id_rejected_not_500(self):
        """09단계 재작업(DEF-09-07) 회귀 테스트 — 숫자가 아닌 page_id는
        500이 아니라 400으로 처리되어야 한다."""
        response = self.client.post(self.url, self._valid_payload(page_id="abc"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_non_numeric_page_id_in_fragment_not_500(self):
        response = self.client.get(reverse("comments:form_fragment"), {"page_id": "abc"})
        self.assertEqual(response.status_code, 404)

    def test_comment_on_unpublished_page_rejected(self):
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="비공개", slug="private-cat")
        draft = BlogPostPage(title="비공개 글", slug="draft-comment-target", category=category, live=False)
        home.add_child(instance=draft)
        draft.save_revision(user=None)

        response = self.client.post(self.url, self._valid_payload(page_id=draft.id))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Comment.objects.exists())

    def test_honeypot_filled_pretends_success_without_saving(self):
        response = self.client.post(self.url, self._valid_payload(hp_field="i-am-a-bot"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.exists())

    def test_rate_limit_blocks_after_threshold(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                self.url, self._valid_payload(), REMOTE_ADDR="198.51.100.20"
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            self.url, self._valid_payload(), REMOTE_ADDR="198.51.100.20"
        )
        self.assertEqual(response.status_code, 429)

    def test_ajax_request_returns_json(self):
        response = self.client.post(
            self.url, self._valid_payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertTrue(response.json()["success"])

    def test_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_body_html_is_escaped_not_rendered(self):
        """XSS 방지(03 §3.2-1) — 댓글 본문에 HTML 태그를 넣어도 스크립트로
        실행되지 않고 이스케이프된 텍스트로만 노출되어야 한다."""
        payload = self._valid_payload(body="<script>alert(1)</script>안녕하세요")
        self.client.post(self.url, payload, REMOTE_ADDR="203.0.113.55")
        comment = Comment.objects.get(page=self.post)
        comment.status = Comment.STATUS_APPROVED
        comment.save(update_fields=["status"])

        cache.clear()
        response = self.client.get(self.post.url)
        self.assertNotIn(b"<script>alert(1)</script>", response.content)
        self.assertIn(b"&lt;script&gt;", response.content)


class CommentWritePageTests(TestCase):
    """무-JS 폴백 전용 페이지(04 §0) — subscribers의 newsletter_page와
    동일한 역할."""

    def setUp(self):
        cache.clear()
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="공지", slug="notice2")
        self.post = BlogPostPage(
            title="무JS 댓글 테스트", slug="nojs-comment-post", category=category, live=False
        )
        home.add_child(instance=self.post)
        self.post.save_revision().publish()
        self.post.refresh_from_db()

    def test_write_page_renders_form(self):
        response = self.client.get(reverse("comments:write_page", args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"csrfmiddlewaretoken", response.content)

    def test_write_page_submits_and_redirects(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse("comments:write_page", args=[self.post.slug]))
        import re

        token = re.search(rb'csrfmiddlewaretoken" value="([^"]+)"', page.content).group(1).decode()

        response = client.post(
            reverse("comments:write_page", args=[self.post.slug]),
            {
                "author_name": "무JS사용자",
                "body": "자바스크립트 없이도 작성했습니다.",
                "hp_field": "",
                "csrfmiddlewaretoken": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Comment.objects.filter(author_name="무JS사용자").exists())

    def test_write_page_404_for_unpublished_slug(self):
        response = self.client.get(reverse("comments:write_page", args=["does-not-exist"]))
        self.assertEqual(response.status_code, 404)


class CommentFormFragmentTests(TestCase):
    def setUp(self):
        cache.clear()
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="공지", slug="notice3")
        self.post = BlogPostPage(
            title="조각 테스트", slug="fragment-test-post", category=category, live=False
        )
        home.add_child(instance=self.post)
        self.post.save_revision().publish()
        self.post.refresh_from_db()

    def test_fragment_returns_fresh_csrf_each_time(self):
        """subscribers의 캐시/CSRF 함정 회귀 테스트와 동일한 목적 — 이
        엔드포인트는 캐시되지 않으므로 두 방문자가 서로 다른 CSRF 토큰을
        받아야 한다."""
        import re

        client_1 = Client(enforce_csrf_checks=True)
        client_2 = Client(enforce_csrf_checks=True)

        frag_1 = client_1.get(reverse("comments:form_fragment"), {"page_id": self.post.id})
        frag_2 = client_2.get(reverse("comments:form_fragment"), {"page_id": self.post.id})

        token_1 = re.search(rb'csrfmiddlewaretoken" value="([^"]+)"', frag_1.content).group(1).decode()
        token_2 = re.search(rb'csrfmiddlewaretoken" value="([^"]+)"', frag_2.content).group(1).decode()
        self.assertNotEqual(token_1, token_2)

    def test_fragment_404_for_missing_page(self):
        response = self.client.get(reverse("comments:form_fragment"), {"page_id": 999999})
        self.assertEqual(response.status_code, 404)


class CommentModeratorPermissionTests(TestCase):
    """관리 권한 경계(03 §3.2-1) — Moderators만 댓글 status를 바꿀 수
    있고, Editors는 없어야 한다(마이그레이션 0002가 실제로 부여한 권한을
    실행 시점에 재확인)."""

    def test_moderators_can_change_comments(self):
        moderator = User.objects.create_user(username="mod-1", password="unused", is_staff=True)
        moderator.groups.add(Group.objects.get(name="Moderators"))
        self.assertTrue(moderator.has_perm("comments.change_comment"))
        self.assertTrue(moderator.has_perm("comments.delete_comment"))

    def test_editors_cannot_change_comments(self):
        editor = User.objects.create_user(username="editor-1", password="unused", is_staff=True)
        editor.groups.add(Group.objects.get(name="Editors"))
        self.assertFalse(editor.has_perm("comments.change_comment"))

    def test_no_group_has_add_permission(self):
        """댓글은 공개 폼으로만 생성된다 — 관리자 "추가" 기능은 불필요
        (03 §3.2-1)."""
        moderator = User.objects.create_user(username="mod-2", password="unused", is_staff=True)
        moderator.groups.add(Group.objects.get(name="Moderators"))
        self.assertFalse(moderator.has_perm("comments.add_comment"))


class PrivacyPolicyCommentNoticeTests(TestCase):
    """개인정보처리방침이 댓글 수집 항목을 실제로 반영하는지(03 §5.6,
    legal/migrations/0003_add_comment_privacy_notice.py)."""

    def test_privacy_policy_mentions_comment_data_collection(self):
        cache.clear()
        response = self.client.get("/privacy-policy/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("댓글 작성 시".encode(), response.content)
        self.assertNotIn("회원가입, 댓글 등 그 외의".encode(), response.content)


class CommentNotificationTests(TestCase):
    """신규 댓글 등록 시 운영자 알림(사용자 요청, 2026-09-25) —
    `DJANGO_ADMIN_EMAIL`(settings.ADMINS)을 재사용한다."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="공지", slug="notice-notify")
        self.post = BlogPostPage(
            title="알림 테스트 글", slug="notify-test-post", category=category, live=False
        )
        home.add_child(instance=self.post)
        self.post.save_revision().publish()
        self.post.refresh_from_db()
        self.url = reverse("comments:submit")

    def _valid_payload(self, **overrides):
        payload = {
            "page_id": self.post.id,
            "author_name": "알림테스터",
            "body": "알림이 잘 가는지 확인합니다.",
            "hp_field": "",
        }
        payload.update(overrides)
        return payload

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    def test_admins_notified_on_new_comment(self):
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.88")

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["admin@example.com"])
        self.assertIn("알림 테스트 글", sent.subject)
        self.assertIn("알림테스터", sent.body)
        self.assertIn("알림이 잘 가는지 확인합니다.", sent.body)

    def test_no_email_sent_when_admins_empty(self):
        """ADMINS(DJANGO_ADMIN_EMAIL)가 비어 있으면(dev 기본값) 조용히
        아무 일도 하지 않아야 한다 — 500 알림과 동일한 원칙."""
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.89")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    def test_honeypot_triggers_no_notification(self):
        """봇이 허니팟에 걸려 저장 자체가 안 되면 알림도 가면 안 된다."""
        self.client.post(self.url, self._valid_payload(hp_field="i-am-a-bot"), REMOTE_ADDR="203.0.113.90")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    def test_mail_failure_does_not_block_comment_creation(self):
        """알림 발송이 실패해도(SMTP 오류 등) 댓글 저장은 성공해야 한다
        (알림은 핵심 경로를 막지 않는다, notifications.py 참고)."""
        with mock.patch("comments.notifications.mail_admins", side_effect=Exception("smtp down")):
            response = self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.91")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comment.objects.filter(author_name="알림테스터").exists())

    @override_settings(ADMINS=[("Admin", "admin@example.com")])
    def test_write_page_also_notifies(self):
        """무-JS 폴백 경로(comment_write_page)도 동일하게 알림을 보내야
        한다(코드 중복 없이 _create_pending_comment를 공유하는지 확인)."""
        response = self.client.get(reverse("comments:write_page", args=[self.post.slug]))
        import re

        token = re.search(rb'csrfmiddlewaretoken" value="([^"]+)"', response.content).group(1).decode()

        self.client.post(
            reverse("comments:write_page", args=[self.post.slug]),
            {
                "author_name": "무JS알림테스터",
                "body": "무JS 경로 알림 확인",
                "hp_field": "",
                "csrfmiddlewaretoken": token,
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("무JS알림테스터", mail.outbox[0].body)


class CommentKoreanSlugTests(TestCase):
    """2026-09-25 실제 브라우저 테스트에서 발견한 버그의 회귀 테스트 —
    Wagtail이 한글 제목에서 자동 생성하는 slug(예: "교토-3박-4일-가을-여행기")
    로 게시물 상세 페이지를 렌더링하면, `comments/urls.py`가 `slug:`
    컨버터(ASCII 전용)를 썼던 시절에는 `{% url 'comments:write_page' %}`가
    NoReverseMatch로 500을 일으켰다. `str:`로 교체해 해소했다."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        home = Page.objects.get(depth=2).specific
        category = Category.objects.create(name="여행", slug="travel-korean-slug-test")
        self.post = BlogPostPage(
            title="교토 3박 4일 가을 여행기",
            category=category,
            live=False,
        )
        home.add_child(instance=self.post)
        self.post.save_revision().publish()
        self.post.refresh_from_db()

    def test_post_detail_with_korean_slug_renders_without_error(self):
        self.assertIn("교토", self.post.slug)  # allow_unicode 슬러그 생성 확인
        response = self.client.get(self.post.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"NoReverseMatch", response.content)

    def test_comment_write_page_url_reverses_for_korean_slug(self):
        url = reverse("comments:write_page", args=[self.post.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_comment_submission_works_for_korean_slug_post(self):
        response = self.client.post(
            reverse("comments:submit"),
            {
                "page_id": self.post.id,
                "author_name": "한글슬러그테스터",
                "body": "한글 슬러그 게시물에도 댓글이 정상 작동합니다.",
                "hp_field": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comment.objects.filter(author_name="한글슬러그테스터").exists())
