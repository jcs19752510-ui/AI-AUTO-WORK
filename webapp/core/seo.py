"""페이지의 정규 절대 URL을 Wagtail Site의 hostname 설정에 의존하지 않고
계산하는 헬퍼(WU-05, REQ-005).

Wagtail `Page.get_full_url()`(그리고 기본 `get_sitemap_urls()`)는 등록된
Wagtail `Site` 레코드의 hostname을 기준으로 절대 URL을 만든다. 그런데 이
프로젝트의 초기 마이그레이션(`home/migrations/0002_create_homepage.py`)이
만드는 기본 Site는 hostname이 `"localhost"`로 고정되어 있고, 이를 실제
운영 도메인으로 갱신하는 절차가 어떤 WU에도 아직 없다 — WU-05 로컬 검증
중 이 상태로 `sitemap.xml`을 생성하면 실제 요청 도메인과 무관하게 URL이
전부 `http://localhost/...`로 나오는 것을 직접 재현했다(unit-05-note.md
§2/§3). 이 함수는 대신 실제 요청(request)의 Host를 그대로 반영해 항상
올바른 절대 URL을 반환한다 — `request.build_absolute_uri`는 인자가 이미
절대 URL이면 그대로 반환하므로, `page.get_url()`이 상대 경로를 주든(단일
사이트가 일치하는 일반적인 경우) 이미 절대 URL을 주든(사이트 불일치 등)
양쪽 모두 안전하게 처리한다.
"""


def absolute_page_url(page, request):
    if request is not None:
        return request.build_absolute_uri(page.get_url(request=request))
    return page.get_full_url()
