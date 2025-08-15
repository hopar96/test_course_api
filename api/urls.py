from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import (
    PaymentDetailViewSet,
    SignupViewSet,
    TestViewSet,
    CourseViewSet,
    PaymentViewSet,
    TestRegistrationViewSet,
    CourseRegistrationViewSet,
    RegistrationsViewSet, RecommendCoursesViewSet, CombinationRecommendViewSet
)
from .authentication import EmailTokenObtainPairView

router = DefaultRouter()
router.register(r"tests", TestViewSet, basename="tests")
router.register(r"courses", CourseViewSet, basename="courses")
router.register(r"payments", PaymentViewSet, basename="payments")
 

urlpatterns = [
    # Router 기반 기본 REST 경로
    path("", include(router.urls)),

    path("login", EmailTokenObtainPairView.as_view(), name="login"),    #로그인
    path("signup", SignupViewSet.as_view({"post": "create"}), name="signup"),   #회원가입

    # 시험 응시
    path("tests/<int:pk>/apply", TestViewSet.as_view({"post": "apply"}), name="apply_test"),
    # 시험 완료
    path("tests/<int:pk>/complete", TestRegistrationViewSet.as_view({"post": "complete"}), name="complete_test"),
    # 수업 수강
    path("courses/<int:pk>/enroll", CourseViewSet.as_view({"post": "enroll"}), name="enroll_course"),
    # 수업 완료
    path("courses/<int:pk>/complete", CourseRegistrationViewSet.as_view({"post": "complete"}), name="complete_course"),
    # 결제 취소
    path("payments/<int:pk>/cancel", PaymentViewSet.as_view({"post": "cancel"}), name="cancel_payment"),
    # 내 결제 내역
    path("me/payments", PaymentDetailViewSet.as_view({"get": "me"}), name="me_payments"),
    # 수업/시험 조합 추천 (페이지네이션 지원)
    path("combination/recommend", CombinationRecommendViewSet.as_view({"post": "combination_recommend"}), name="combination_recommend"),
    # 수업/시험 동시에 수강/응시
    path("registrations", RegistrationsViewSet.as_view({"post": "registrations"}), name="bulk_registrations"),
    # 태그 기반 수업 추천 (페이지네이션 지원)
    path("courses/recommend", RecommendCoursesViewSet.as_view({"get": "recommend"}), name="recommend_course"),
]
