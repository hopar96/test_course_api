from __future__ import annotations
from datetime import timedelta, timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenViewBase
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken


class EmailTokenObtainPairSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.check_password(password):
            raise AuthenticationFailed("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_active:
            raise AuthenticationFailed("비활성화된 사용자입니다.")
        access_token = AccessToken.for_user(user)

        return {
            "access": str(access_token),
        }


class EmailTokenObtainPairView(TokenViewBase):
    serializer_class = EmailTokenObtainPairSerializer
