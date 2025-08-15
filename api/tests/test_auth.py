from __future__ import annotations
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_and_login(self):
        # signup
        resp = self.client.post(
            "/api/signup",
            {"username": "tester", "email": "tester@example.com", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.data)

        # login
        resp = self.client.post(
            "/api/login",
            {"email": "tester@example.com", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)


