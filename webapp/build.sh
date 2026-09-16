#!/usr/bin/env bash
# Render 빌드 커맨드 (03-system-design.md §2.4 Render 공식 배포 패턴).
# 마이그레이션을 빌드 스크립트 안에서 실행하는 것이 별도 pre-deploy 훅이 아니라
# Render가 공식으로 권장하는 방식이다.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
