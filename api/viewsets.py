from __future__ import annotations
from typing import Any
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
import logging
from django.db.models import Q, Count

from .models import (
    Test,
    Course,
    TestRegistration,
    CourseRegistration,
    Payment,
    User, RegistrationBase, Tag
)
from .serializers import (
    PaymentDetailSerializer,
    SignupSerializer,
    TestSerializer,
    CourseSerializer,
    PaymentSerializer, ActivitySerializer,
)
from .exceptions import BusinessLogicException, PaymentException, RegistrationException

logger = logging.getLogger(__name__)


# 회원가입 viewset
class SignupViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = SignupSerializer
    queryset = User.objects.all()


# 시험 ViewSet
class TestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TestSerializer
    queryset = Test.objects.all()
    ordering_fields = ["popularity", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        AVAILABLE = "available"

        queryset = super().get_queryset()
        # 요청에 따라 정렬 및 기본 생성일 기준

        if self.request.query_params.get("status") == AVAILABLE:
            return queryset.filter(
                start_at__lte=timezone.now(), end_at__gte=timezone.now()
            ).filter(
                Q(testregistration__isnull=True) | Q(testregistration__status=TestRegistration.STATUS_CANCELED)
            )
        else:
            return queryset

    # 시험 응시 신청
    @action(detail=True, methods=["post"], url_path="apply")
    @transaction.atomic
    def apply(self, request, pk: int | str = None):
        try:
            test = self.get_object()

            # 이미 신청한 시험인지 확인
            test_registration_qs = (
                TestRegistration.objects
                .filter(user=request.user, test=test)
                .exclude(status=TestRegistration.STATUS_CANCELED)
            )
            if test_registration_qs.exists():
                raise RegistrationException("이미 응시 신청한 시험입니다.")
            # 시험 기간 체크
            if test.start_at > timezone.now() or test.end_at < timezone.now():
                raise RegistrationException("시험 응시 기간이 아닙니다.")

            # 결제 정보 검증
            amount = int(request.data.get("amount", 0))
            method = request.data.get("payment_method")

            if amount <= 0 or not method:
                raise PaymentException("결제금액과 결제방식이 필요합니다.")

            if amount != test.price:
                raise PaymentException("결제 금액이 시험 가격과 다릅니다.")

            # 트랜잭션 내에서 모든 작업 수행
            with transaction.atomic():
                # 인기도 증가
                test.popularity += 1
                test.save(update_fields=["popularity"])

                # 신청 생성
                registration = TestRegistration.objects.create(user=request.user, test=test)

                # 결제 생성
                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    original_price=amount,
                    method=method,
                    target_content_type=ContentType.objects.get_for_model(TestRegistration),
                    target_object_id=registration.id,
                )

                logger.info(f"시험 신청 완료: user={request.user.id}, test={test.id}, payment={payment.id}")
                return Response(
                    PaymentSerializer(payment).data, status=status.HTTP_201_CREATED
                )

        except (ValueError, TypeError) as e:
            logger.error(f"시험 신청 중 데이터 오류: {e}")
            raise PaymentException("잘못된 결제 정보입니다.")
        except Exception as e:
            logger.error(f"시험 신청 중 예상치 못한 오류: {e}", exc_info=True)
            raise


# 수업 ViewSet
class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    queryset = Course.objects.all()
    ordering_fields = ["popularity", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        AVAILABLE = "available"
        queryset = super().get_queryset()

        if self.request.query_params.get("status") == AVAILABLE:
            return (queryset
            .filter(start_at__lte=timezone.now(), end_at__gte=timezone.now())
            .filter(
                Q(courseregistration__user=self.request.user) &
                (Q(courseregistration__isnull=True) | Q(courseregistration__status=CourseRegistration.STATUS_CANCELED)))
            )
        else:
            return queryset

    @action(detail=True, methods=["post"], url_path="enroll")
    @transaction.atomic
    def enroll(self, request, pk: int | str = None):
        try:
            course = self.get_object()

            # 이미 신청한 수업인지 확인
            course_registration_qs = (
                CourseRegistration.objects
                .filter(user=request.user, course=course)
                .exclude(status=CourseRegistration.STATUS_CANCELED)
            )
            if course_registration_qs.exists():
                raise RegistrationException("이미 수강 신청한 수업입니다.")
            if course.start_at > timezone.now() or course.end_at < timezone.now():  # 수업 기간 체크
                raise RegistrationException("수업 수강 기간이 아닙니다.")

            # 결제 정보 검증
            amount = int(request.data.get("amount", 0))
            method = request.data.get("payment_method")

            if amount <= 0 or not method:
                raise PaymentException("amount, payment_method가 필요합니다.")

            if amount != course.price:
                raise PaymentException("결제 금액이 수업 가격과 다릅니다.")

            # 트랜잭션 내에서 모든 작업 수행
            with transaction.atomic():
                # 인기도 증가
                course.popularity += 1
                course.save(update_fields=["popularity"])

                # 신청 생성
                registration = CourseRegistration.objects.create(user=request.user, course=course)

                # 결제 생성
                payment = Payment.objects.create(
                    user=request.user,
                    amount=amount,
                    original_price=amount,
                    method=method,
                    target_content_type=ContentType.objects.get_for_model(CourseRegistration),
                    target_object_id=registration.id,
                )

                logger.info(f"수업 신청 완료: user={request.user.id}, course={course.id}, payment={payment.id}")
                return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

        except (ValueError, TypeError) as e:
            logger.error(f"수업 신청 중 데이터 오류: {e}")
            raise PaymentException("잘못된 결제 정보입니다.")
        except Exception as e:
            logger.error(f"수업 신청 중 예상치 못한 오류: {e}", exc_info=True)
            raise


# 결제 ViewSet
class PaymentViewSet(viewsets.GenericViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk: int | str = None):
        try:
            payment = get_object_or_404(Payment, id=pk, user=request.user)

            # 이미 취소된 결제인지 확인
            if payment.status == Payment.STATUS_CANCELED:
                raise PaymentException("이미 취소된 결제입니다.")

            target = payment.target
            # 완료된 항목은 취소할 수 없음
            if target and getattr(target, "status", None) == TestRegistration.STATUS_COMPLETED:
                raise BusinessLogicException("완료된 항목은 취소할 수 없습니다.")

            # 트랜잭션 내에서 취소 처리
            with transaction.atomic():
                try:
                    # 결제 취소
                    payment.cancel()
                    logger.info(f"결제 취소 완료: payment={payment.id}, user={request.user.id}")
                    return Response({"message": "결제가 취소되었습니다."}, status=status.HTTP_200_OK)
                except ValueError as e:
                    logger.error(f"결제 취소 중 오류: {e}")
                    raise BusinessLogicException(str(e))

        except Exception as e:
            logger.error(f"결제 취소 중 예상치 못한 오류: {e}", exc_info=True)
            raise


class PaymentDetailViewSet(viewsets.GenericViewSet):
    serializer_class = PaymentDetailSerializer
    queryset = Payment.objects.all()

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        qs = Payment.objects.filter(user=request.user)
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        from_date = request.query_params.get("from")
        to_date = request.query_params.get("to")
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)
        qs = qs.order_by("-created_at")

        page = self.paginate_queryset(qs)
        data = []
        for payment in page:
            is_test = isinstance(payment.target, TestRegistration)
            data.append(
                {
                    "payment_id": payment.id,
                    "amount": payment.amount,
                    "method": payment.method,
                    "status": payment.status,
                    "created_at": payment.created_at,
                    "canceled_at": payment.canceled_at,
                    "target_type": payment.target_content_type.model,
                    "target_registration_id": payment.target.id,
                    "target_title": payment.target.test.title if is_test else payment.target.course.title,
                    "target_start_at": payment.target.test.start_at if is_test else payment.target.course.start_at,
                    "target_end_at": payment.target.test.end_at if is_test else payment.target.course.end_at,
                }
            )
        serializer = PaymentDetailSerializer(data, many=True)
        return self.get_paginated_response(serializer.data)


# 시험 응시 완료 ViewSet
class TestRegistrationViewSet(viewsets.ViewSet):
    @action(detail=True, methods=["post"], url_path="complete")
    @transaction.atomic
    def complete(self, request, pk: int | str = None):
        try:
            reg = get_object_or_404(TestRegistration, id=pk, user=request.user)

            # 이미 완료된 상태인지 확인
            if reg.status == TestRegistration.STATUS_COMPLETED:
                raise BusinessLogicException("이미 완료된 시험입니다.")
            if reg.status == TestRegistration.STATUS_CANCELED:
                raise BusinessLogicException("취소된 시험은 완료할 수 없습니다.")

            # 트랜잭션 내에서 상태 변경
            with transaction.atomic():
                reg.status = TestRegistration.STATUS_COMPLETED
                (
                    reg.save(update_fields=["status", "updated_at"])
                    if hasattr(reg, "updated_at")
                    else reg.save()
                )

                logger.info(f"시험 완료 처리: registration={reg.id}, user={request.user.id}")
                return Response({"message": "시험 응시 상태가 완료로 변경되었습니다."})

        except Exception as e:
            logger.error(f"시험 완료 처리 중 오류: {e}", exc_info=True)
            raise


# 수업 수강 완료 ViewSet
class CourseRegistrationViewSet(viewsets.ViewSet):
    @action(detail=True, methods=["post"], url_path="complete")
    @transaction.atomic
    def complete(self, request, pk: int | str = None):
        try:
            reg = get_object_or_404(CourseRegistration, id=pk, user=request.user)

            # 이미 완료된 상태인지 확인
            if reg.status == CourseRegistration.STATUS_COMPLETED:
                raise BusinessLogicException("이미 완료된 수업입니다.")
            if reg.status == CourseRegistration.STATUS_CANCELED:
                raise BusinessLogicException("취소된 수업은 완료할 수 없습니다.")

            # 트랜잭션 내에서 상태 변경
            with transaction.atomic():
                reg.status = CourseRegistration.STATUS_COMPLETED
                (
                    reg.save(update_fields=["status", "updated_at"])
                    if hasattr(reg, "updated_at")
                    else reg.save()
                )

                logger.info(f"수업 완료 처리: registration={reg.id}, user={request.user.id}")
                return Response({"message": "수업 수강 상태가 완료로 변경되었습니다."})

        except Exception as e:
            logger.error(f"수업 완료 처리 중 오류: {e}", exc_info=True)
            raise

# 신청 가능한 일정 조합 추천
class CombinationRecommendViewSet(viewsets.GenericViewSet):
    def _is_overlap(self, activity1, activity2):
        """두 액티비티가 겹치는지 확인하는 헬퍼 함수"""
        start1, end1 = activity1['start_at'], activity1['end_at']
        start2, end2 = activity2['start_at'], activity2['end_at']
        return start1 < end2 and start2 < end1

    @action(detail=False, methods=["post"], url_path="combination_recommend")
    def combination_recommend(self, request):
        request_serializer = ActivitySerializer(data=request.data, many=True)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        activities = request_serializer.validated_data

        # 성능을 위해 시작 시간 기준으로 정렬
        activities.sort(key=lambda x: x['start_at'])

        results = []

        # 재귀 함수 정의
        def find_combinations(start_index, current_combination):
            # 현재 조합이 유효하므로 결과에 추가 (단, 비어있지 않은 조합만)
            if current_combination:
                results.append(list(current_combination))

            # 남은 액티비티들을 순회하며 조합 확장
            for i in range(start_index, len(activities)):
                next_activity = activities[i]

                # 현재 조합에 있는 어떤 액티비티와도 겹치지 않는지 확인
                is_compatible = True
                for existing_activity in current_combination:
                    if self._is_overlap(existing_activity, next_activity):
                        is_compatible = False
                        break

                # 겹치지 않는다면, 조합에 추가하고 다음 단계로 재귀 호출
                if is_compatible:
                    current_combination.append(next_activity)
                    find_combinations(i + 1, current_combination)
                    # 다음 탐색을 위해 마지막에 추가한 요소 제거
                    current_combination.pop()

        # 재귀 시작
        find_combinations(0, [])

        # 중복 제거 및 가장 긴 조합부터 정렬하여 응답
        unique_combinations = []
        seen = set()
        for combo in results:
            # 리스트를 정렬된 문자열로 변환하여 중복 체크
            sorted_combo = sorted(combo, key=lambda x: x.get('id', 0))
            combo_str = str(sorted_combo)
            if combo_str not in seen:
                seen.add(combo_str)
                unique_combinations.append(combo)
        
        unique_combinations.sort(key=len, reverse=True)

        # 페이지네이션 적용
        page = self.paginate_queryset(unique_combinations)
        return self.get_paginated_response(page)


# 수업/시험 동시 결제 ViewSet
class RegistrationsViewSet(viewsets.ViewSet):
    @action(detail=True, methods=["post"], url_path="registrations")
    @transaction.atomic
    def registrations(self, request):
        try:
            logger.error('-----------------')
            logger.error(f"{request.data}")

            data_list = request.data.get("list")
            if not isinstance(data_list, list):
                raise ValidationError("잘못된 요청입니다.")
            method = request.data.get("payment_method")
            if not method:
                raise PaymentException("payment_method가 필요합니다.")
            with (transaction.atomic()):
                max_dc = 20
                dc = 0
                if len(data_list) > 1:
                    dc = min(max_dc, (len(data_list) - 1) * 5)

                for param in data_list:
                    if param.get("target_type") == "test":  # 시험의 경우
                        test = get_object_or_404(Test, id=param.get("target_id"))

                        # 이미 신청한 시험인지 확인
                        test_registration_qs = (
                            TestRegistration.objects
                            .filter(user=request.user, test=test)
                            .exclude(status=RegistrationBase.STATUS_CANCELED)
                        )

                        if test_registration_qs.exists():
                            raise RegistrationException("이미 응시 신청한 시험입니다.")
                        if test.start_at > timezone.now() or test.end_at < timezone.now():  # 시험 기간 체크
                            raise RegistrationException("시험 응시 기간이 아닙니다.")

                        # 결제 정보 검증
                        original_price = int(param.get("amount", 0))
                        discount = int(original_price * dc / 100)
                        amount = original_price - discount

                        if original_price < 0:
                            raise PaymentException("amount가 필요합니다.")
                        if original_price != test.price:
                            raise PaymentException("결제 금액이 시험 가격과 다릅니다.")

                        test.popularity += 1
                        test.save(update_fields=["popularity"])
                        # 신청 생성
                        registration = TestRegistration.objects.create(user=request.user, test=test)
                        # 결제생성
                        payment = Payment.objects.create(
                            user=request.user,
                            amount=amount,
                            original_price=original_price,
                            discounted_price=discount,
                            method=method,
                            target_content_type=ContentType.objects.get_for_model(TestRegistration),
                            target_object_id=registration.id,
                        )

                    elif param.get("target_type") == "course":  # 수업의 경우
                        course = get_object_or_404(Course, id=param.get("target_id"))

                        # 이미 신청한 시험인지 확인
                        course_registration_qs = (
                            CourseRegistration.objects
                            .filter(user=request.user, course=course)
                            .exclude(status=RegistrationBase.STATUS_CANCELED)
                        )
                        if course_registration_qs.exists():
                            raise RegistrationException("이미 응시 신청한 수업입니다.")
                        if course.start_at > timezone.now() or course.end_at < timezone.now():  # 시험 기간 체크
                            raise RegistrationException("수업 수강 기간이 아닙니다.")

                        # 결제 정보 검증
                        original_price = int(param.get("amount", 0))
                        discount = int(original_price * dc / 100)
                        amount = original_price - discount

                        if original_price < 0:
                            raise PaymentException("amount가 필요합니다.")
                        if original_price != course.price:
                            raise PaymentException("결제 금액이 수업 가격과 다릅니다.")

                        course.popularity += 1
                        course.save(update_fields=["popularity"])
                        # 신청 생성
                        registration = CourseRegistration.objects.create(user=request.user, course=course)
                        # 결제생성
                        payment = Payment.objects.create(
                            user=request.user,
                            amount=amount,
                            original_price=original_price,
                            discounted_price=discount,
                            method=method,
                            target_content_type=ContentType.objects.get_for_model(CourseRegistration),
                            target_object_id=registration.id,
                        )

            return Response("신청 완료", status=status.HTTP_201_CREATED)

        except (ValueError, TypeError) as e:
            logger.error(f"수업 신청 중 데이터 오류: {e}")
            raise PaymentException("잘못된 결제 정보입니다.")
        except Exception as e:
            logger.error(f"수업 신청 중 예상치 못한 오류: {e}", exc_info=True)
            raise


# 사용자 수강 수업 태그 기반으로 수업 추천
class RecommendCoursesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer

    def get_queryset(self):
        return Course.objects.all()

    @action(detail=False, methods=["get"], url_path="recommend")
    def recommend(self, request):
        user_taken_course_tags = (Tag.objects.filter(
            courses__courseregistration__user=request.user
        ).exclude(
            courses__courseregistration__status=RegistrationBase.STATUS_CANCELED
        ).values_list('id', flat=True).distinct())

        if not user_taken_course_tags:
            empty_qs = Course.objects.none()
            page = self.paginate_queryset(empty_qs)
            serializer = CourseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        user_taken_course_ids = Course.objects.filter(
            courseregistration__user=request.user
        ).exclude(
            courseregistration__status=RegistrationBase.STATUS_CANCELED
        ).values_list('id', flat=True)

        # 추천 대상 수업들을 필터링하고, 겹치는 태그 수를 계산하여 정렬합니다.
        recommended_courses = Course.objects.exclude(
            id__in=user_taken_course_ids  # 이미 수강한 수업 제외
        ).annotate(
            matching_tags_count=Count('tags', filter=Q(tags__id__in=user_taken_course_tags))
        ).filter(
            matching_tags_count__gt=0  # 겹치는 태그가 하나 이상 있는 수업만 필터링
        ).order_by(
            '-matching_tags_count', '-popularity'  # 겹치는 태그 수 > 인기순으로 정렬
        )

        page = self.paginate_queryset(recommended_courses)
        serializer = CourseSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
