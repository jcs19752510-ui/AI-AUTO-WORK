"""WU-04 공개 뷰 전역 상수.

- POSTS_PER_PAGE: S-01/S-03/S-04 목록의 페이지당 게시물 수. 03-system-design.md
  §4는 `page` 쿼리파라미터만 못박고 구체적 개수는 지정하지 않아 5단계 판단으로
  10을 채택했다(모바일 한 화면에 과도한 스크롤을 만들지 않는 통상적인 블로그 목록
  크기, 가역적 설정값).
- VIEW_CACHE_SECONDS: 03 §2.5(DEC-012)가 지정한 "5~15분 TTL" 범위 내에서 10분을
  채택했다.
"""

POSTS_PER_PAGE = 10
VIEW_CACHE_SECONDS = 60 * 10
