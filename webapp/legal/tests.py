"""WU-06/WU-08 규칙F 재작업 (2026-09-25, DEC-045) 회귀 테스트.

개인정보처리방침 "문의처" 절에 실제 연락처가 없던 격차(11단계 사용자 매뉴얼
작성 중 발견, 사용자 확인 후 진행 승인)를 메우기 위해 신설한
`core.models.SiteSettings.contact_email`이 legal_page.html에 올바르게
반영되는지 확인한다.

`LegalPage.serve()`가 `cache_page(VIEW_CACHE_SECONDS)`로 캐시되므로(03
§2.5/DEC-012), 서로 다른 `contact_email` 값을 검증하는 테스트가 캐시를
공유하면 이전 테스트의 응답을 그대로 돌려받아 거짓 PASS/FAIL이 날 수 있다
— `core.tests.AdminLoginRateLimitTests`가 레이트리밋 캐시를 초기화하는 것과
동일한 이유로, 여기서도 매 테스트마다 `cache.clear()`로 초기화한다.
"""

from django.core.cache import cache
from django.test import Client, TestCase

from core.models import SiteSettings
from wagtail.models import Site


class PrivacyPolicyContactEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.site = Site.objects.get(is_default_site=True)

    def _set_contact_email(self, value):
        settings_obj = SiteSettings.for_site(self.site)
        settings_obj.contact_email = value
        settings_obj.save()

    def test_no_contact_block_when_unset(self):
        """기본값(빈 문자열)일 때는 연락처 블록을 렌더링하지 않는다 —
        운영자가 아직 설정하지 않은 상태에서도 페이지가 깨지지 않아야 한다."""
        response = self.client.get("/privacy-policy/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"legal-page__contact", response.content)

    def test_contact_block_rendered_when_set(self):
        self._set_contact_email("ops@example.com")
        response = self.client.get("/privacy-policy/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"mailto:ops@example.com", response.content)
        self.assertIn("ops@example.com".encode(), response.content)

    def test_contact_block_not_shown_on_terms_page(self):
        """연락처 블록은 개인정보처리방침에만 노출된다(약관/쿠키 고지는
        "문의처" 절이 없으므로 무관한 정보를 섞지 않는다)."""
        self._set_contact_email("ops@example.com")
        response = self.client.get("/terms/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"legal-page__contact", response.content)

    def test_contact_block_not_shown_on_cookies_page(self):
        self._set_contact_email("ops@example.com")
        response = self.client.get("/cookies/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"legal-page__contact", response.content)
