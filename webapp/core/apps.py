from django.apps import AppConfig


class CoreConfig(AppConfig):
    """사이트 전역 SEO/디스커버리 보조 기능(WU-05, REQ-005) — robots.txt,
    canonical URL 컨텍스트 프로세서. 특정 도메인 모델을 갖지 않는 최소 앱이다.

    03-system-design.md §1.2 모듈 경계 표는 `core` 앱에 헬스체크/SiteSettings/
    콜드스타트 안내 뷰(REQ-011/012)도 함께 배정했지만, 그것들은 각자의 담당
    WU(WU-08/09)에서 이 앱에 이어서 추가한다 — 이번 WU-05는 REQ-005(SEO) 범위만
    구현한다(DEC-016이 WU-03에서 custom_images 앱을 만들 때 쓴 것과 동일한
    "모델/코드를 담을 최소 앱을 먼저 만들고, 같은 앱에 후속 WU가 이어서
    채운다"는 선례를 따른다).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "사이트 전역 설정"
