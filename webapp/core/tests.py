"""WU-09 로컬 검증 (REQ-010). unit-09-note.md §3이 이 결과를 요약해 인용한다.

subscribers/tests.py(WU-07)와 동일한 방식으로, 수동 확인 대신 자동화된
테스트로 남겨 6단계 테스터가 그대로 재실행해 회귀를 확인할 수 있게 한다.
"""

import io
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from config.middleware import XForwardedForMiddleware
from core.admin_auth import RATE_LIMIT_MAX_ATTEMPTS, RateLimitedLoginView

User = get_user_model()


class CategoryEditorPermissionTests(TestCase):
    """core/migrations/0001_setup_editor_permissions.py가 실제로 그룹에
    카테고리 스니펫 권한을 부여했는지 확인한다 — 이 마이그레이션이 없던
    상태에서는 아래 두 assertTrue가 실패했다(WU-09가 발견한 결함)."""

    def test_editors_group_has_category_permissions(self):
        editors = Group.objects.get(name="Editors")
        codenames = set(
            editors.permissions.filter(content_type__app_label="blog").values_list(
                "codename", flat=True
            )
        )
        self.assertEqual(
            codenames, {"add_category", "change_category", "delete_category"}
        )

    def test_moderators_group_has_category_permissions(self):
        moderators = Group.objects.get(name="Moderators")
        codenames = set(
            moderators.permissions.filter(content_type__app_label="blog").values_list(
                "codename", flat=True
            )
        )
        self.assertEqual(
            codenames, {"add_category", "change_category", "delete_category"}
        )

    def test_non_group_staff_user_cannot_add_category(self):
        """그룹에 속하지 않은 일반 스태프 사용자는 여전히 카테고리를
        추가할 수 없어야 한다(권한이 슈퍼유저/그룹에만 한정됨을 대조 확인)."""
        staff_user = User.objects.create_user(
            username="plain-staff", password="unused-not-checked-here", is_staff=True
        )
        self.assertFalse(staff_user.has_perm("blog.add_category"))

    def test_editors_group_member_can_add_category(self):
        editor = User.objects.create_user(
            username="editor-1", password="unused-not-checked-here", is_staff=True
        )
        editor.groups.add(Group.objects.get(name="Editors"))
        self.assertTrue(editor.has_perm("blog.add_category"))
        self.assertTrue(editor.has_perm("blog.change_category"))
        self.assertTrue(editor.has_perm("blog.delete_category"))


class AdminLoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.url = reverse("wagtailadmin_login")
        User.objects.create_user(
            username="admin-user", password="correct-horse-battery-staple-1"
        )

    def _post_login(self, **overrides):
        payload = {"username": "admin-user", "password": "wrong-password"}
        payload.update(overrides)
        return self.client.post(self.url, payload, REMOTE_ADDR="203.0.113.50")

    def test_get_request_renders_login_form_without_counting(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS + 5):
            response = self.client.get(self.url, REMOTE_ADDR="203.0.113.50")
            self.assertEqual(response.status_code, 200)

    def test_failed_attempts_within_limit_return_normal_response(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            response = self._post_login()
            self.assertEqual(response.status_code, 200)
            self.assertNotEqual(response.status_code, 429)

    def test_attempt_beyond_limit_returns_429(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            self._post_login()

        response = self._post_login()
        self.assertEqual(response.status_code, 429)

    def test_valid_credentials_still_succeed_within_limit(self):
        response = self._post_login(password="correct-horse-battery-staple-1")
        self.assertEqual(response.status_code, 302)

    def test_rate_limit_is_scoped_per_ip(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            self._post_login()
        blocked = self._post_login()
        self.assertEqual(blocked.status_code, 429)

        other_ip = self.client.post(
            self.url,
            {"username": "admin-user", "password": "wrong-password"},
            REMOTE_ADDR="198.51.100.20",
        )
        self.assertNotEqual(other_ip.status_code, 429)

    def test_x_forwarded_for_rightmost_value_used_as_client_ip(self):
        """subscribers/tests.py(WU-07)와 동일한 방식: production 전용
        XForwardedForMiddleware를 뷰에 직접 감싸 배치를 재현한다(03 §5.5.4)."""
        wrapped_view = XForwardedForMiddleware(RateLimitedLoginView.as_view())
        factory = RequestFactory()

        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            request = factory.post(
                self.url,
                data={"username": "admin-user", "password": "wrong-password"},
                HTTP_X_FORWARDED_FOR=f"9.9.9.{_}, 203.0.113.88",
            )
            response = wrapped_view(request)
            self.assertNotEqual(response.status_code, 429)

        # leftmost(클라이언트가 조작 가능한 값)가 매번 달라도 rightmost가
        # 같으면 같은 카운터로 취급되어야 한다.
        blocked_request = factory.post(
            self.url,
            data={"username": "admin-user", "password": "wrong-password"},
            HTTP_X_FORWARDED_FOR="1.1.1.1, 203.0.113.88",
        )
        blocked_response = wrapped_view(blocked_request)
        self.assertEqual(blocked_response.status_code, 429)

    def test_real_browser_like_login_with_csrf_still_succeeds(self):
        """`Client(enforce_csrf_checks=True)`로 실제 브라우저와 동일하게
        GET에서 CSRF 토큰을 받아 POST에 그대로 실어 보낸다(subscribers/
        tests.py NewsletterCachedPageCsrfTests와 동일한 방법론) — 레이트리밋
        도입이 정상 로그인 흐름 자체를 깨지 않았는지 end-to-end로 확인한다."""
        client = Client(enforce_csrf_checks=True)
        get_response = client.get(self.url)
        csrf_token = get_response.cookies["csrftoken"].value

        response = client.post(
            self.url,
            {
                "username": "admin-user",
                "password": "correct-horse-battery-staple-1",
                "csrfmiddlewaretoken": csrf_token,
            },
        )
        self.assertEqual(response.status_code, 302)

    def test_csrf_rejected_requests_are_not_counted_but_cannot_test_credentials(self):
        """6단계(unit-09-test.md TC-CSRF-01/02, DEC-031)가 실측 재현한 경계:
        전역 `CsrfViewMiddleware`가 뷰(`RateLimitedLoginView.dispatch()`)가
        호출되기도 전에 요청을 거부하면, 이 뷰의 레이트리밋 카운터는 전혀
        증가하지 않는다(모두 403, 한 번도 429가 아님). 이는 실질적인
        무차별대입 방어 결함이 아니다 — CSRF가 실패한 요청은 사용자명/
        비밀번호를 애초에 검사하지 않으므로(항상 동일한 403), 카운트되지
        않아도 공격자가 자격증명을 하나도 시험해보지 못한다는 사실은
        바뀌지 않는다."""
        client = Client(enforce_csrf_checks=True)
        statuses = [
            client.post(
                self.url,
                {"username": "admin-user", "password": "wrong-password"},
                REMOTE_ADDR="203.0.113.70",
            ).status_code
            for _ in range(RATE_LIMIT_MAX_ATTEMPTS + 5)
        ]
        self.assertTrue(all(status == 403 for status in statuses))
        self.assertNotIn(429, statuses)
        self.assertIsNone(cache.get("core:admin_login:ratelimit:203.0.113.70"))

    def test_csrf_rejected_noise_does_not_consume_budget_for_later_valid_attempts(self):
        """같은 IP가 CSRF-무효 POST를 아무리 많이 보내도(위 테스트), 이후
        유효한 CSRF로 전환하면 정확히 새 `RATE_LIMIT_MAX_ATTEMPTS`회 예산을
        그대로 받는다 — CSRF-무효 트래픽이 카운터를 "선점"해 정당한 로그인
        시도의 예산을 깎아먹는 일이 없음을 증명한다."""
        noisy_client = Client(enforce_csrf_checks=True)
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS + 5):
            noisy_client.post(
                self.url,
                {"username": "admin-user", "password": "wrong-password"},
                REMOTE_ADDR="203.0.113.71",
            )

        real_client = Client(enforce_csrf_checks=True)
        get_response = real_client.get(self.url, REMOTE_ADDR="203.0.113.71")
        csrf_token = get_response.cookies["csrftoken"].value

        statuses = []
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            response = real_client.post(
                self.url,
                {
                    "username": "admin-user",
                    "password": "wrong-password",
                    "csrfmiddlewaretoken": csrf_token,
                },
                REMOTE_ADDR="203.0.113.71",
            )
            statuses.append(response.status_code)
        self.assertTrue(all(status != 429 for status in statuses))

        blocked = real_client.post(
            self.url,
            {
                "username": "admin-user",
                "password": "wrong-password",
                "csrfmiddlewaretoken": csrf_token,
            },
            REMOTE_ADDR="203.0.113.71",
        )
        self.assertEqual(blocked.status_code, 429)


class EnsureSuperuserCommandTests(TestCase):
    def setUp(self):
        cache.clear()

    def _run(self, env):
        out = io.StringIO()
        with mock.patch.dict("os.environ", env, clear=False):
            call_command("ensure_superuser", stdout=out)
        return out.getvalue()

    def test_creates_superuser_from_env(self):
        output = self._run(
            {
                "DJANGO_SUPERUSER_USERNAME": "bootstrap-admin",
                "DJANGO_SUPERUSER_EMAIL": "admin@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "a-reasonably-long-passphrase-9",
            }
        )
        user = User.objects.get(username="bootstrap-admin")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertIn("생성했습니다", output)

    def test_skips_when_superuser_already_exists(self):
        User.objects.create_superuser(
            username="existing-admin", email="e@example.com", password="whatever-pw-123"
        )
        output = self._run(
            {
                "DJANGO_SUPERUSER_USERNAME": "another-admin",
                "DJANGO_SUPERUSER_EMAIL": "another@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "a-reasonably-long-passphrase-9",
            }
        )
        self.assertFalse(User.objects.filter(username="another-admin").exists())
        self.assertIn("건너뜁니다", output)

    def test_skips_when_env_vars_missing(self):
        output = self._run({"DJANGO_SUPERUSER_USERNAME": "", "DJANGO_SUPERUSER_PASSWORD": ""})
        self.assertFalse(User.objects.filter(is_superuser=True).exists())
        self.assertIn("건너뜁니다", output)

    def test_skips_when_password_fails_validation(self):
        output = self._run(
            {
                "DJANGO_SUPERUSER_USERNAME": "weak-admin",
                "DJANGO_SUPERUSER_EMAIL": "weak@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "12345678",
            }
        )
        self.assertFalse(User.objects.filter(username="weak-admin").exists())
        self.assertIn("비밀번호 정책", output)
