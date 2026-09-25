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
from django.test import Client, RequestFactory, TestCase, override_settings
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


class DjangoAdminLoginRateLimitTests(TestCase):
    """DEF-09-01(High)/DEC-039/DEC-040 규칙F 재작업 회귀 테스트.

    `/django-admin/login/`(Django 기본 관리자, `RateLimitedAdminLoginView`)도
    `/cms-admin/login/`과 동일한 방식으로 방어되는지 확인한다. 09단계
    보안검증(SEC-02)이 실측 재현한 시나리오(동일 IP 11회 연속 POST가 전부
    200, 429 없음)를 그대로 재실행해 11번째에 429가 나오는지 검증한다."""

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.url = reverse("admin_login")
        User.objects.create_user(
            username="django-admin-user",
            password="correct-horse-battery-staple-2",
            is_staff=True,
            is_superuser=True,
        )

    def _post_login(self, **overrides):
        payload = {"username": "django-admin-user", "password": "wrong-password"}
        payload.update(overrides)
        return self.client.post(self.url, payload, REMOTE_ADDR="203.0.113.51")

    def test_get_request_renders_login_form_without_counting(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS + 5):
            response = self.client.get(self.url, REMOTE_ADDR="203.0.113.51")
            self.assertEqual(response.status_code, 200)

    def test_failed_attempts_within_limit_return_normal_response(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            response = self._post_login()
            self.assertEqual(response.status_code, 200)
            self.assertNotEqual(response.status_code, 429)

    def test_eleventh_attempt_returns_429(self):
        """SEC-02(09단계) 재현 절차와 동일: 동일 IP 11회 연속 POST 중
        11번째가 429여야 한다(DEF-09-01 재작업 전에는 11회 전부 200이었음)."""
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            self._post_login()

        response = self._post_login()
        self.assertEqual(response.status_code, 429)

    def test_valid_credentials_still_succeed_within_limit(self):
        response = self._post_login(password="correct-horse-battery-staple-2")
        self.assertEqual(response.status_code, 302)

    def test_rate_limit_is_scoped_per_ip(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            self._post_login()
        blocked = self._post_login()
        self.assertEqual(blocked.status_code, 429)

        other_ip = self.client.post(
            self.url,
            {"username": "django-admin-user", "password": "wrong-password"},
            REMOTE_ADDR="198.51.100.21",
        )
        self.assertNotEqual(other_ip.status_code, 429)


class SharedAdminRateLimitCounterTests(TestCase):
    """DEC-040이 채택한 옵션 2(카운터 공유)의 핵심 계약: 동일 IP가 두
    로그인 URL에 시도를 나눠 보내도 합산 임계값(10회)을 넘으면 차단돼야
    한다 — 분리돼 있었다면 공격자가 예산을 사실상 2배로 늘릴 수 있었다
    (03 §5.1 v1.3, 09단계 SEC-02 권고 회귀 테스트)."""

    def setUp(self):
        cache.clear()
        self.wagtail_url = reverse("wagtailadmin_login")
        self.django_url = reverse("admin_login")
        User.objects.create_user(
            username="shared-admin-user",
            password="correct-horse-battery-staple-3",
            is_staff=True,
            is_superuser=True,
        )

    def test_attempts_split_across_both_urls_share_one_budget(self):
        client = Client()
        ip = "203.0.113.60"
        payload = {"username": "shared-admin-user", "password": "wrong-password"}

        for _ in range(5):
            response = client.post(self.wagtail_url, payload, REMOTE_ADDR=ip)
            self.assertNotEqual(response.status_code, 429)
        for _ in range(5):
            response = client.post(self.django_url, payload, REMOTE_ADDR=ip)
            self.assertNotEqual(response.status_code, 429)

        blocked = client.post(self.django_url, payload, REMOTE_ADDR=ip)
        self.assertEqual(blocked.status_code, 429)

        also_blocked = client.post(self.wagtail_url, payload, REMOTE_ADDR=ip)
        self.assertEqual(also_blocked.status_code, 429)


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


@override_settings(
    SECURE_SSL_REDIRECT=True,
    SECURE_REDIRECT_EXEMPT=[r"^healthz$"],
)
class HealthzHttpsRedirectExemptTests(TestCase):
    """DEF-10-01(10단계 배포테스트, TC-004) 회귀 방지 테스트.

    production.py는 `SECURE_SSL_REDIRECT=True` + `SECURE_REDIRECT_EXEMPT=[r"^healthz$"]`
    조합으로 `/healthz`만 HTTPS 강제 리다이렉트에서 예외 처리한다(Render 헬스체크
    프로브가 X-Forwarded-Proto 헤더 없이 직접 접속해도 301 대신 200을 받게 하기
    위함). `Client()`를 `override_settings` 적용 범위 안에서 생성해야
    `SecurityMiddleware`가 이 설정값으로 다시 초기화된다(Django의
    `ClientHandler`는 인스턴스 생성 시점에 미들웨어 체인을 로드하므로, 이미
    만들어진 Client를 재사용하면 override가 반영되지 않는다)."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_200_without_forwarded_proto_header(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_non_exempt_path_still_redirected_to_https(self):
        """대조군 — 예외 목록에 없는 경로는 여전히 301로 HTTPS 강제되어야
        한다(SECURE_REDIRECT_EXEMPT가 전역이 아니라 healthz 한정임을 확인)."""
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_healthz_with_forwarded_proto_https_also_200(self):
        """`X-Forwarded-Proto: https` 헤더가 붙어 오는 경우(Render 엣지를 거친
        일반 트래픽 재현)에도 여전히 200이어야 한다 — 예외 처리가 헤더 유무와
        무관하게 항상 성립하는지 확인(회귀 방지, 헤더 존재가 예외 로직을
        깨지 않음을 명시적으로 남김)."""
        response = self.client.get("/healthz", HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(response.status_code, 200)
