from django.apps import AppConfig


class CoreConfig(AppConfig):
    """사이트 전역 SEO/디스커버리/운영 보조 기능을 담는 최소 앱.

    - WU-05(REQ-005): robots.txt, canonical URL 컨텍스트 프로세서.
    - WU-08(REQ-011/012): `/healthz`(얕은 헬스체크), 요청량/응답시간 경량
      집계 미들웨어(`core.middleware.RequestMetricsMiddleware`)와 그
      결과를 보여주는 Wagtail 어드민 사용량 대시보드(`/cms-admin/usage/`,
      `core/wagtail_hooks.py`).

    03-system-design.md §1.2 모듈 경계 표가 `core` 앱에 함께 배정했던
    "콜드스타트 안내 뷰"는 04-ux-design.md §2 "콜드스타트 UX 설계"에서
    아키텍처적으로 실시간 뷰가 될 수 없음(앱이 깨어나기 전이라 요청이 코드에
    도달하지 못함)이 확인되어, 전역 Footer 정적 카피로 구체화되었고 WU-04가
    이미 구현했다(`config/templates/partials/footer.html`) — 이 앱에 추가할
    코드가 없다. "SiteSettings"(운영자가 콜드스타트 문구를 어드민에서 직접
    수정하는 기능)도 04-ux-design.md가 "현재는 템플릿 하드코딩으로 충분"이라
    명시적으로 v1 범위 밖(향후 규칙F 재작업 대상)으로 남겼으므로 이번
    WU-08도 만들지 않는다(과설계 방지, DEC-016/DEC-019 선례와 동일 원칙).

    (WU-03이 `custom_images`를 만들 때 쓴 것과 동일한 "모델/코드를 담을
    최소 앱을 먼저 만들고, 같은 앱에 후속 WU가 이어서 채운다"는 선례를
    그대로 따른다 — DEC-016/DEC-019.)
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "사이트 전역 설정"
