"""전역 템플릿 컨텍스트 — 헤더 내비게이션 카테고리 목록
(04-ux-design.md §2 전역 컴포넌트 Header/Nav, §4 컴포넌트 명세).

모든 화면(법적 페이지 등 이후 WU가 추가할 화면 포함)이 동일한 헤더를 공유하므로,
뷰마다 카테고리 목록을 개별적으로 context에 채워 넣지 않고 컨텍스트 프로세서로
전역 제공한다. `@cache_page`로 캐시된 응답은 이 프로세서 자체를 다시 실행하지
않으므로 추가 쿼리 비용도 캐시 히트 시에는 발생하지 않는다.
"""

from .models import Category


def nav_categories(request):
    return {"nav_categories": Category.objects.all()}
