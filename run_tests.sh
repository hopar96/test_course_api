#!/bin/bash

# 테스트 실행 스크립트
echo "=== API 테스트 실행 ==="

# 환경변수 설정
export DJANGO_DB_ENGINE=django.db.backends.sqlite3
export DJANGO_DB_NAME=db.sqlite3
export DJANGO_DB_USER=examuser
export DJANGO_DB_PASSWORD=exampass
export DJANGO_DB_HOST=localhost
# export DJANGO_DB_PORT=

# 가상환경 활성화
source .venv/bin/activate

echo "1. 인증 테스트 실행..."
python manage.py test api.tests.test_auth -v 2

echo ""
echo "2. API 기능 테스트 실행..."
python manage.py test api.tests.test_api -v 2

echo ""
echo "=== 모든 테스트 완료 ==="
