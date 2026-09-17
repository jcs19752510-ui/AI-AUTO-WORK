"""Django 어드민 등록 (03 §5.6 파기절차, 04 OP-07).

탈퇴 요청 접수 시 운영자가 여기서 해당 레코드를 하드 삭제한다(§3.2 —
`status` 토글이 아니라 실제 행 삭제가 v1의 실제 삭제 경로다). 목록/검색만
지원하고 값 수정은 막아 둔다 — 이 레코드가 담는 값(동의 시각/버전/IP)은
시스템이 구독 시점에 기록한 근거 데이터이므로, 운영자가 어드민에서 임의로
고쳐 쓰는 것은 개인정보 처리 근거 추적성을 해친다.
"""

from django.contrib import admin

from .models import NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "status", "consented_at", "source_ip_masked", "created_at")
    list_filter = ("status",)
    search_fields = ("email",)
    readonly_fields = ("id", "email", "consented_at", "consent_version", "source_ip_masked", "status", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
