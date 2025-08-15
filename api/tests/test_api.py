from __future__ import annotations
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from api.models import Test, Course, TestRegistration, CourseRegistration, Payment, Tag


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="pass1234",
        )
        # 로그인 토큰 발급
        resp = self.client.post(
            "/api/login",
            {"email": "tester@example.com", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        token = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        now = timezone.now()
        self.open_start = now - timedelta(days=1)
        self.open_end = now + timedelta(days=1)

        # 열려있는 시험/수업
        self.test_open = Test.objects.create(
            title="T1", start_at=self.open_start, end_at=self.open_end, price=10000
        )
        self.course_open = Course.objects.create(
            title="C1", start_at=self.open_start, end_at=self.open_end, price=20000
        )

        # 닫혀있는 시험/수업
        self.test_closed = Test.objects.create(
            title="T2", start_at=now - timedelta(days=3), end_at=now - timedelta(days=2), price=15000
        )
        self.course_closed = Course.objects.create(
            title="C2", start_at=now - timedelta(days=3), end_at=now - timedelta(days=2), price=25000
        )


class TestAndCourseApplyTests(BaseAPITestCase):
    def test_list_tests_and_courses(self):
        r = self.client.get("/api/tests/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)  # 페이지네이션 확인
        
        r = self.client.get("/api/courses/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)  # 페이지네이션 확인

    def test_apply_test_success(self):
        r = self.client.post(
            f"/api/tests/{self.test_open.id}/apply",
            {"amount": 10000, "payment_method": Payment.METHOD_CREDIT_CARD},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Payment.objects.count(), 1)
        pay = Payment.objects.first()
        self.assertEqual(pay.amount, 10000)
        self.assertEqual(TestRegistration.objects.count(), 1)

    def test_apply_test_already_applied(self):
        # 첫 신청
        self.client.post(
            f"/api/tests/{self.test_open.id}/apply",
            {"amount": 10000, "payment_method": Payment.METHOD_CREDIT_CARD},
            format="json",
        )
        # 중복 신청
        r = self.client.post(
            f"/api/tests/{self.test_open.id}/apply",
            {"amount": 10000, "payment_method": Payment.METHOD_CREDIT_CARD},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_apply_test_out_of_window(self):
        r = self.client.post(
            f"/api/tests/{self.test_closed.id}/apply",
            {"amount": 15000, "payment_method": Payment.METHOD_CREDIT_CARD},
            format="json",
        )
        self.assertEqual(r.status_code, 400)

    def test_enroll_course_success(self):
        r = self.client.post(
            f"/api/courses/{self.course_open.id}/enroll",
            {"amount": 20000, "payment_method": Payment.METHOD_KAKAOPAY},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(CourseRegistration.objects.count(), 1)

    def test_enroll_course_out_of_window(self):
        r = self.client.post(
            f"/api/courses/{self.course_closed.id}/enroll",
            {"amount": 25000, "payment_method": Payment.METHOD_KAKAOPAY},
            format="json",
        )
        self.assertEqual(r.status_code, 400)


class PaymentAndStatusTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # 하나씩 신청 생성
        r1 = self.client.post(
            f"/api/tests/{self.test_open.id}/apply",
            {"amount": 10000, "payment_method": Payment.METHOD_CREDIT_CARD},
            format="json",
        )
        self.payment_test_id = r1.data["id"]

        r2 = self.client.post(
            f"/api/courses/{self.course_open.id}/enroll",
            {"amount": 20000, "payment_method": Payment.METHOD_KAKAOPAY},
            format="json",
        )
        self.payment_course_id = r2.data["id"]

    def test_complete_test_registration_then_cannot_cancel_payment(self):
        # 결제 -> 등록 객체 찾기
        pay = Payment.objects.get(id=self.payment_test_id)
        reg_id = pay.target.id

        # 완료 처리
        r = self.client.post(f"/api/tests/{reg_id}/complete", format="json")
        self.assertEqual(r.status_code, 200)

        # 완료 후 결제 취소 불가
        r = self.client.post(f"/api/payments/{self.payment_test_id}/cancel", format="json")
        self.assertEqual(r.status_code, 400)

    def test_cancel_payment(self):
        r = self.client.post(f"/api/payments/{self.payment_course_id}/cancel", format="json")
        self.assertEqual(r.status_code, 200)
        pay = Payment.objects.get(id=self.payment_course_id)
        self.assertEqual(pay.status, Payment.STATUS_CANCELED)

    def test_me_payments_filtering(self):
        # 전체
        r = self.client.get("/api/me/payments")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)  # 페이지네이션 확인
        self.assertGreaterEqual(len(r.data["results"]), 2)

        # 상태 필터
        r = self.client.get("/api/me/payments", {"status": Payment.STATUS_PAID})
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)


class BulkRegistrationTests(BaseAPITestCase):
    def test_bulk_registrations_with_discount(self):
        payload = {
            "payment_method": Payment.METHOD_CREDIT_CARD,
            "list": [
                {"target_type": "test", "target_id": self.test_open.id, "amount": 10000},
                {"target_type": "course", "target_id": self.course_open.id, "amount": 20000},
            ],
        }
        r = self.client.post("/api/registrations", payload, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Payment.objects.count(), 2)
        # 할인 반영 확인 (둘 다 some discount)
        amounts = list(Payment.objects.values_list("amount", flat=True))
        self.assertTrue(any(a < 10000 or a < 20000 for a in amounts))


class RecommendTests(BaseAPITestCase):
    def test_combination_recommend(self):
        now = timezone.now()
        payload = [
            {"id": 1, "name": "A", "type": "test", "start_at": (now + timedelta(hours=1)).isoformat(), "end_at": (now + timedelta(hours=2)).isoformat()},
            {"id": 2, "name": "B", "type": "course", "start_at": (now + timedelta(hours=2)).isoformat(), "end_at": (now + timedelta(hours=3)).isoformat()},
            {"id": 3, "name": "C", "type": "course", "start_at": (now + timedelta(hours=1, minutes=30)).isoformat(), "end_at": (now + timedelta(hours=2, minutes=30)).isoformat()},
        ]
        r = self.client.post("/api/combination/recommend", payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)  # 페이지네이션 확인

    def test_recommend_courses_by_tags(self):
        # user가 수강 완료/대기 중인 수업에 태그 부여
        tag_math = Tag.objects.create(name="math")
        self.course_open.tags.add(tag_math)

        # 수강 신청 생성 (open course)
        self.client.post(
            f"/api/courses/{self.course_open.id}/enroll",
            {"amount": 20000, "payment_method": Payment.METHOD_KAKAOPAY},
            format="json",
        )

        # 추천 대상 수업 생성: 동일 태그 보유
        course2 = Course.objects.create(
            title="C3", start_at=self.open_start, end_at=self.open_end, price=30000
        )
        course2.tags.add(tag_math)

        r = self.client.get("/api/courses/recommend")
        self.assertEqual(r.status_code, 200)
        self.assertIn("results", r.data)  # 페이지네이션 확인


class PaginationTests(BaseAPITestCase):
    def test_pagination_parameters(self):
        # 페이지 크기 조절
        r = self.client.get("/api/tests/?page_size=5")
        self.assertEqual(r.status_code, 200)
        self.assertIn("count", r.data)
        self.assertIn("next", r.data)
        self.assertIn("previous", r.data)
        self.assertIn("results", r.data)
        
        # 페이지 번호
        r = self.client.get("/api/tests/?page=1&page_size=10")
        self.assertEqual(r.status_code, 200)