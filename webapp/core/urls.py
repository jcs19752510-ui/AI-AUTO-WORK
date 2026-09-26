from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots_txt"),
    # DEC-053 — 애드센스 게시자 확인 파일. 사이트 루트 마운트 필수(구글 공식 요구사항).
    path("ads.txt", views.ads_txt, name="ads_txt"),
    # WU-08, REQ-011/012 — 03 §4 계약(`GET /healthz`). 어드민 경로가 아니라
    # 사이트 루트에 마운트해야 Render Health Check Path(render.yaml)가 인증
    # 없이 조회할 수 있다.
    path("healthz", views.healthz, name="healthz"),
]
