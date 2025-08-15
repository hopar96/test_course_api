from __future__ import annotations
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import User, Test, Course, Payment, TestRegistration, CourseRegistration

class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        if not validated_data.get("username"):
            validated_data["username"] = validated_data["email"].split("@")[0]
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ["id", "title", "description", "start_at", "end_at", "popularity", "created_at", "price"]


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "description", "start_at", "end_at", "popularity", "created_at", "price"]


class PaymentSerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["id", "amount", "method", "status", "created_at", "canceled_at", "target_type"]

    def get_target_type(self, obj) -> str:
        if isinstance(obj.target, TestRegistration):
            return "test"
        if isinstance(obj.target, CourseRegistration):
            return "course"
        return "unknown"

class PaymentDetailSerializer(serializers.Serializer):
    payment_id = serializers.IntegerField()
    amount = serializers.IntegerField()
    method = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    canceled_at = serializers.DateTimeField()
    target_type = serializers.CharField()
    target_registration_id = serializers.IntegerField()
    target_title = serializers.CharField()
    target_start_at = serializers.DateTimeField()
    target_end_at = serializers.DateTimeField()

class ActivitySerializer(serializers.Serializer):
    """수업/시험 단일 객체를 위한 시리얼라이저"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
