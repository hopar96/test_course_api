from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework.exceptions import APIException, PermissionDenied, NotFound
import logging

logger = logging.getLogger(__name__)


class BusinessLogicException(APIException):
    """비즈니스 로직 예외"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "비즈니스 로직 오류가 발생했습니다."
    default_code = "business_logic_error"


class PaymentException(APIException):
    """결제 관련 예외"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "결제 처리 중 오류가 발생했습니다."
    default_code = "payment_error"


class RegistrationException(APIException):
    """신청 관련 예외"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "신청 처리 중 오류가 발생했습니다."
    default_code = "registration_error"


def custom_exception_handler(exc, context):
    """전역 예외 처리 핸들러"""
    
    # DRF 기본 예외 처리 먼저 실행
    response = exception_handler(exc, context)
    
    if response is not None:
        # DRF가 처리한 예외는 그대로 반환
        return response
    
    # Django 예외들을 DRF 예외로 변환
    if isinstance(exc, ValidationError):
        logger.warning(f"ValidationError: {exc}")
        return Response({
            'detail': '입력 데이터가 유효하지 않습니다.',
            'errors': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exc, IntegrityError):
        logger.error(f"IntegrityError: {exc}")
        return Response({
            'detail': '데이터 무결성 오류가 발생했습니다.',
            'code': 'integrity_error'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    elif isinstance(exc, Http404):
        logger.warning(f"Http404: {exc}")
        return Response({
            'detail': '요청한 리소스를 찾을 수 없습니다.',
            'code': 'not_found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    elif isinstance(exc, PermissionDenied):
        logger.warning(f"PermissionDenied: {exc}")
        return Response({
            'detail': '권한이 없습니다.',
            'code': 'permission_denied'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # 예상치 못한 예외는 로그 기록 후 일반적인 오류 메시지 반환
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return Response({
        'detail': '서버 내부 오류가 발생했습니다.',
        'code': 'internal_server_error'
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
