"""WU-06 공개 뷰 상수.

VIEW_CACHE_SECONDS: 03-system-design.md §2.5(DEC-012)가 지정한 "5~15분 TTL"
범위 내에서 WU-04(blog.constants.VIEW_CACHE_SECONDS)와 동일한 10분을 채택해
일관된 캐시 정책을 유지한다. blog 앱을 import해 값을 공유하지 않고 이 앱에서
독립적으로 정의하는 이유는 03 §1.2 "경계 원칙"(legal은 blog와 무관하게 격리돼
있어야 향후 변경 영향이 서로 번지지 않는다)을 그대로 따르기 위함이다.
"""

VIEW_CACHE_SECONDS = 60 * 10
