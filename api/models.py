from __future__ import annotations
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import AbstractUser

# 유저
class User(AbstractUser):
    email = models.EmailField(unique=True)

    def __str__(self) -> str:  # pragma: no cover - readability
        return self.email or self.username

# 생성일/수정일 abstract model
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# 시험
class Test(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    popularity = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.title

# 수업 태그
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# 수업
class Course(TimeStampedModel):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    popularity = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)

    tags = models.ManyToManyField(Tag, related_name='courses', blank=True)

    def __str__(self) -> str:
        return self.title

# 신청 기본 정보 abstract model
class RegistrationBase(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_COMPLETED, "completed"),
        (STATUS_CANCELED, "canceled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        abstract = True

# 시험 신청
class TestRegistration(RegistrationBase):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)

# 수업 신청
class CourseRegistration(RegistrationBase):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

class Payment(TimeStampedModel):
    METHOD_CREDIT_CARD = "credit_card"
    METHOD_KAKAOPAY = "kakaopay"
    METHOD_BANK = "bank_transfer"
    METHOD_CHOICES = [
        (METHOD_CREDIT_CARD, "credit_card"),
        (METHOD_KAKAOPAY, "kakaopay"),
        (METHOD_BANK, "bank_transfer"),
    ]

    STATUS_PAID = "paid"
    STATUS_CANCELED = "canceled"
    STATUS_CHOICES = [
        (STATUS_PAID, "paid"),
        (STATUS_CANCELED, "canceled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    original_price = models.PositiveIntegerField(default=0)
    discounted_price = models.PositiveIntegerField(default=0)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PAID)
    canceled_at = models.DateTimeField(null=True, blank=True)

    # Generic relation to registration (test or course)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")

    def cancel(self) -> None:
        # Business rule: cannot cancel if related registration is completed
        if hasattr(self, "target") and self.target:
            if getattr(self.target, "status", None) == RegistrationBase.STATUS_COMPLETED:
                raise ValueError("완료된 항목은 취소할 수 없습니다.")
        self.status = self.STATUS_CANCELED
        self.canceled_at = timezone.now()
        self.save()
        if hasattr(self, "target") and self.target:
            # 인기도 감소
            if self.target_content_type == ContentType.objects.get_for_model(TestRegistration):
                test = Test.objects.get(id = self.target.test.id)
                test.popularity -= 1
                test.save()
            elif self.target_content_type == ContentType.objects.get_for_model(CourseRegistration):
                course = Course.objects.get(id = self.target.course.id)
                course.popularity -= 1
                course.save()
            # 신청 취소 처리
            self.target.status = self.STATUS_CANCELED
            self.target.save()

    def __str__(self) -> str:
        return f"Payment({self.id}) {self.user} {self.amount} {self.status}"
