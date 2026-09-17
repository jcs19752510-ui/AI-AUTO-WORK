"""목록 화면(S-01/S-03/S-04) 공용 페이지네이션 헬퍼 (03 §4 `page` 쿼리파라미터).

`Paginator.get_page()`는 잘못된/범위 밖 `page` 값(문자열이 아님, 음수, 존재하지
않는 페이지 번호 등)을 404가 아니라 가장 가까운 유효 페이지(1페이지 또는 마지막
페이지)로 조용히 보정한다 — 03 §4 API 표는 목록 라우트의 실패 응답을 404(카테고리/
태그 자체가 없는 경우)로만 규정하고, 페이지 번호 자체의 오류는 별도로 규정하지
않는다. 목록이 존재하는 한 "페이지 번호가 이상하다"는 이유로 방문자에게 404를
보여주는 것은 불필요하게 가혹하다고 판단해 보정 동작을 그대로 채택했다.
"""

from django.core.paginator import Paginator

from .constants import POSTS_PER_PAGE


def paginate(request, queryset, per_page=POSTS_PER_PAGE):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page") or 1
    return paginator.get_page(page_number)
