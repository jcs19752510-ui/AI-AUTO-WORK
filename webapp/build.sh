#!/usr/bin/env bash
# Render 빌드 커맨드 (03-system-design.md §2.4 Render 공식 배포 패턴).
# 마이그레이션을 빌드 스크립트 안에서 실행하는 것이 별도 pre-deploy 훅이 아니라
# Render가 공식으로 권장하는 방식이다.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# 최초 슈퍼유저 계정 부트스트랩 (WU-09, REQ-010, core/management/commands/
# ensure_superuser.py 참고) — Render Free 티어에는 Shell/SSH/one-off Job이
# 없어(render.com/docs/free "Other limitations", 2026-09-17 확인) 이 빌드
# 단계가 대화형 createsuperuser를 대체하는 유일한 경로다. 멱등하므로 이미
# 슈퍼유저가 있으면 아무 일도 하지 않는다.
python manage.py ensure_superuser
