"""WU-05, REQ-005 — robots.txt.

03-system-design.md §4 `GET /robots.txt`(200, `text/plain`)를 구현한다. §6.3/§8
이 이미 기록한 대로, Render가 스핀다운 상태일 때는 이 뷰에 도달하기도 전에
플랫폼이 "disallow all" 정적 응답으로 가로챈다 — 애플리케이션 코드로 해결할
수 없는 플랫폼 제약이므로 이 뷰는 "정상 기동 중"인 경우의 응답만 책임진다.
"""

from django.http import HttpResponse
from django.urls import reverse


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("blog:sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /cms-admin/",
        "Disallow: /django-admin/",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
