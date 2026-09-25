"""사이트 전역 템플릿 컨텍스트(WU-05, REQ-005) — canonical URL.

DEC-017(`BlogPostPage.get_url_parts`/`serve` 오버라이드)에 의해 정규 URL이
아닌 트리 URL(`/<slug>/`) 요청은 템플릿이 렌더링되기 전에 이미 301로 정규
URL(`/blog/<slug>/`)로 리다이렉트된다. 즉 base.html이 실제로 렌더링되는
시점의 `request.path`는 항상 이미 정규 URL이다 — 그래서 이를 그대로 절대
URL로 바꾸기만 하면 canonical이 항상 정규 URL을 가리키게 된다(DEC-017과의
정합성).

쿼리스트링(예: `?page=2`)까지 포함해 `request.build_absolute_uri()`(인자
없음 = 현재 요청 URL 전체)를 쓰는 이유: 페이지네이션된 목록 페이지는 서로
다른 콘텐츠를 보여주므로, 전부 1페이지 URL로 canonical을 몰아주면 구글의
현재 공식 가이드("각 페이지가 스스로를 canonical로 가리켜야 한다" — 과거의
rel=next/prev 권고는 폐기됨)에 어긋나 2페이지 이후가 색인에서 누락될 수
있다.
"""


def canonical_url(request):
    return {"canonical_url": request.build_absolute_uri()}


def contact_email(request):
    """SiteSettings.contact_email을 전역 템플릿 컨텍스트에 노출한다(WU-08
    규칙F 재작업, DEC-045). `BaseSiteSetting.for_request()`는 요청당
    캐시되므로 페이지마다 추가 쿼리를 반복하지 않는다."""
    from core.models import SiteSettings

    return {"contact_email": SiteSettings.for_request(request).contact_email}
