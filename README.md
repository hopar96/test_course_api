## Exam/Course API

Django REST Framework 기반 시험(Test)/수업(Course) 신청, 결제, 추천 API

### 기술 스택
- Django, Django REST Framework, SimpleJWT, django-filter, drf-yasg
- DB: PostgreSQL(기본)

### 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 환경변수 (기본값)
- `DJANGO_SECRET_KEY=dev-secret-key-change-me`
- `DJANGO_DEBUG=true`
- `DJANGO_ALLOWED_HOSTS=*`
- `DJANGO_DB_ENGINE=django.db.backends.postgresql`
- `DJANGO_DB_NAME=examdb`
- `DJANGO_DB_USER=examuser`
- `DJANGO_DB_PASSWORD=exampass`
- `DJANGO_DB_HOST=localhost`
- `DJANGO_DB_PORT=5432`

### 인증
- 회원가입: `POST /api/signup`
- 로그인(JWT): `POST /api/login`
  - 응답에서 `access` 토큰 수신 후 헤더에 사용
  - `Authorization: Bearer <access_token>`

### 페이지네이션
- 전역 페이지네이션: PageNumberPagination
- 기본 페이지 크기: 10
- 쿼리 파라미터: `page`, `page_size` (최대 100)
- 응답 포맷
```json
{
  "count": 42,
  "next": "http://.../api/.../?page=3&page_size=10",
  "previous": "http://.../api/.../?page=1&page_size=10",
  "results": [
    { /* 항목 */ }
  ]
}
```

### 엔드포인트
- 시험(Tests)
  - 목록: `GET /api/tests/?status=available`  (정렬: `ordering=popularity` 또는 `ordering=-created_at`)
  - 응시 신청: `POST /api/tests/<test_id>/apply`
  - 응시 완료: `POST /api/tests/<registration_id>/complete`  ← 등록 ID를 사용합니다

- 수업(Courses)
  - 목록: `GET /api/courses/?status=available`  (정렬: `ordering=popularity` 또는 `ordering=-created_at`)
  - 수강 신청: `POST /api/courses/<course_id>/enroll`
  - 수강 완료: `POST /api/courses/<registration_id>/complete`  ← 등록 ID를 사용합니다

- 결제(Payments)
  - 결제 취소: `POST /api/payments/<payment_id>/cancel`
  - 내 결제 내역: `GET /api/me/payments?status=paid&from=YYYY-MM-DD&to=YYYY-MM-DD`
    - 페이지네이션 적용

- 동시 신청(Bulk Registrations)
  - `POST /api/registrations`
  - 본문 예시
    ```json
    {
      "payment_method": "credit_card",
      "list": [
        {"target_type": "test", "target_id": 1, "amount": 10000},
        {"target_type": "course", "target_id": 2, "amount": 20000}
      ]
    }
    ```
  - 할인 정책: 2개 이상 동시 신청 시 항목 수에 따라 5%씩, 최대 20%까지 적용

- 조합 추천(겹치지 않는 일정 조합)
  - `POST /api/combination/recommend`
  - 요청: 액티비티 배열 `[ {id, name, type, start_at, end_at}, ... ]`
  - 응답: 페이지네이션 포맷(`results`에 조합 배열)

- 태그 기반 수업 추천
  - `GET /api/courses/recommend`
  - 사용자가 수강한 수업의 태그와 겹치는 태그를 가진 수업을 추천 (수강했던 수업 제외, 인기/태그일치수 기준 정렬)
  - 페이지네이션 적용

### 예시 요청
```bash
# 회원가입
curl -X POST http://localhost:8000/api/signup \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "pass1234"}'

# 로그인 → access 토큰 획득
ACCESS=$(curl -s -X POST http://localhost:8000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "pass1234"}' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

# 시험 목록 (페이지네이션)
curl -H "Authorization: Bearer $ACCESS" \
  'http://localhost:8000/api/tests/?page=1&page_size=20&status=available&ordering=-created_at'

# 시험 응시 신청
curl -X POST http://localhost:8000/api/tests/1/apply \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"amount": 10000, "payment_method": "credit_card"}'

# 내 결제 내역
curl -H "Authorization: Bearer $ACCESS" \
  'http://localhost:8000/api/me/payments?status=paid&page=1&page_size=10'
```

### 테스트 실행
```bash
# SQLite로 간편 실행
DJANGO_DB_ENGINE=django.db.backends.sqlite3 DJANGO_DB_NAME=db.sqlite3 \
python manage.py test -v 2
```

### API 스키마 (UI 없이 JSON/YAML 제공)
- JSON: `/swagger.json`
- YAML: `/swagger.yaml`

### Docker
```bash
docker-compose up --build
```
# test_course_api
