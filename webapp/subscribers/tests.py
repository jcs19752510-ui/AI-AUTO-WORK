"""WU-07 로컬 검증 (REQ-016). unit-07-note.md §3이 이 결과를 요약해 인용한다.

수동 curl 확인 대신 자동화된 테스트로 남겨, 6단계 테스터가 그대로 재실행해
회귀를 확인할 수 있게 한다. `config.middleware.XForwardedForMiddleware`는
production 설정에서만 등록되므로(WU-01), X-Forwarded-For 시뮬레이션은
unit-01-note.md §Case C와 동일한 방식(미들웨어를 뷰에 직접 감싸 테스트)으로
검증한다 — production 전용 환경변수(R2/DATABASE_URL 등)를 요구하지 않는다.
"""

from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from config.middleware import XForwardedForMiddleware

from .constants import PRIVACY_POLICY_VERSION, RATE_LIMIT_MAX_ATTEMPTS
from .models import NewsletterSubscriber


class NewsletterSubscribeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.url = reverse("subscribers:subscribe")

    def _valid_payload(self, **overrides):
        payload = {
            "email": "reader@example.com",
            "consent": "on",
            "hp_field": "",
            "next": "/",
        }
        payload.update(overrides)
        return payload

    def test_subscribe_creates_record(self):
        response = self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")

        self.assertEqual(response.status_code, 200)
        subscriber = NewsletterSubscriber.objects.get(email="reader@example.com")
        self.assertEqual(subscriber.status, NewsletterSubscriber.STATUS_ACTIVE)
        self.assertEqual(subscriber.consent_version, PRIVACY_POLICY_VERSION)
        self.assertEqual(subscriber.source_ip_masked, "203.0.113.0")

    def test_duplicate_subscribe_does_not_create_second_record(self):
        self.client.post(self.url, self._valid_payload(), REMOTE_ADDR="203.0.113.42")
        first = NewsletterSubscriber.objects.get(email="reader@example.com")

        # 대소문자만 다른 재제출도 동일 레코드로 취급되어야 한다(03 §3.2 소문자 정규화).
        response = self.client.post(
            self.url,
            self._valid_payload(email="Reader@Example.com"),
            REMOTE_ADDR="203.0.113.99",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(NewsletterSubscriber.objects.filter(email="reader@example.com").count(), 1)
        second = NewsletterSubscriber.objects.get(email="reader@example.com")
        self.assertEqual(first.id, second.id)
        self.assertGreaterEqual(second.consented_at, first.consented_at)

    def test_invalid_email_rejected(self):
        response = self.client.post(self.url, self._valid_payload(email="not-an-email"))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(NewsletterSubscriber.objects.exists())

    def test_missing_consent_rejected(self):
        response = self.client.post(self.url, self._valid_payload(consent=""))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(NewsletterSubscriber.objects.exists())

    def test_honeypot_filled_pretends_success_without_saving(self):
        response = self.client.post(self.url, self._valid_payload(hp_field="i-am-a-bot"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(NewsletterSubscriber.objects.exists())

    def test_rate_limit_blocks_after_threshold(self):
        for _ in range(RATE_LIMIT_MAX_ATTEMPTS):
            response = self.client.post(
                self.url,
                self._valid_payload(email="spam@example.com"),
                REMOTE_ADDR="198.51.100.10",
            )
            self.assertNotEqual(response.status_code, 429)

        response = self.client.post(
            self.url,
            self._valid_payload(email="spam2@example.com"),
            REMOTE_ADDR="198.51.100.10",
        )
        self.assertEqual(response.status_code, 429)

    def test_ajax_request_returns_json(self):
        response = self.client.post(
            self.url,
            self._valid_payload(email="ajax@example.com"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertTrue(response.json()["success"])

    def test_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_x_forwarded_for_rightmost_value_used_as_client_ip(self):
        """unit-01-note.md §Case C와 동일한 방식: XForwardedForMiddleware를
        뷰에 직접 감싸 production MIDDLEWARE 배치를 재현한다(03 §5.5.4)."""
        from . import views as subscriber_views

        wrapped_view = XForwardedForMiddleware(subscriber_views.newsletter_subscribe)

        factory = RequestFactory()
        request = factory.post(
            self.url,
            data=self._valid_payload(email="xff@example.com"),
            HTTP_X_FORWARDED_FOR="9.9.9.9, 203.0.113.77",
        )
        response = wrapped_view(request)

        self.assertEqual(response.status_code, 200)
        subscriber = NewsletterSubscriber.objects.get(email="xff@example.com")
        # rightmost 값(203.0.113.77)만 신뢰되어야 한다 — leftmost(9.9.9.9,
        # 클라이언트가 임의로 붙일 수 있는 값)는 채택되지 않는다(03 §5.5.4).
        self.assertEqual(subscriber.source_ip_masked, "203.0.113.0")


class NewsletterCachedPageCsrfTests(TestCase):
    """views.py 모듈 docstring이 설명한 결함(캐시된 페이지에 폼을 직접
    렌더링하면 두 번째 방문자부터 403이 나는 문제)의 회귀 테스트.
    `Client(enforce_csrf_checks=True)`로 실제 브라우저와 동일하게 CSRF를
    검증한다 — 기본 테스트 Client는 CSRF 검사를 건너뛰어 이 결함을 가리므로
    다른 테스트에서는 쓰지 않는다(unit-07-note.md §3이 이 발견 경위를 설명).
    """

    def setUp(self):
        cache.clear()

    def test_cached_home_page_does_not_embed_a_form(self):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/")

        self.assertNotIn(b"data-newsletter-form", response.content)
        self.assertNotIn(b"csrfmiddlewaretoken", response.content)
        self.assertIn(b"data-newsletter-slot", response.content)

    def test_two_independent_visitors_can_each_subscribe_after_shared_cache_fill(self):
        import re

        first_visitor = Client(enforce_csrf_checks=True)
        second_visitor = Client(enforce_csrf_checks=True)

        home_1 = first_visitor.get("/")
        home_2 = second_visitor.get("/")
        # 홈 본문 자체는 여전히 공유 캐시에서 서빙된다(DEC-012 유지 확인).
        self.assertEqual(home_1.content, home_2.content)

        def fetch_token(client):
            fragment = client.get("/newsletter/form/", {"form_id": "footer"})
            match = re.search(rb'csrfmiddlewaretoken" value="([^"]+)"', fragment.content)
            return match.group(1).decode()

        token_1 = fetch_token(first_visitor)
        token_2 = fetch_token(second_visitor)
        self.assertNotEqual(token_1, token_2)

        response_1 = first_visitor.post(
            "/newsletter/subscribe/",
            {"email": "visitor1@example.com", "consent": "on", "hp_field": "", "next": "/", "csrfmiddlewaretoken": token_1},
        )
        response_2 = second_visitor.post(
            "/newsletter/subscribe/",
            {"email": "visitor2@example.com", "consent": "on", "hp_field": "", "next": "/", "csrfmiddlewaretoken": token_2},
        )

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(NewsletterSubscriber.objects.count(), 2)

    def test_dedicated_newsletter_page_works_without_js(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get("/newsletter/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"newsletter-form", page.content)
