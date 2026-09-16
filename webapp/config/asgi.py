"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.
Render 프로덕션 기동 커맨드가 gunicorn + uvicorn 워커로 이 모듈을 사용한다
(03 §1.1, §2.4: `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker`).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_asgi_application()
