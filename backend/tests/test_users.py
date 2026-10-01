from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import UserProfile


class AuthenticationApiTests(APITestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="student-one",
			email="student@example.com",
			password="correct horse battery staple",
			first_name="Sam",
		)

	def test_new_users_receive_a_student_profile(self):
		self.assertEqual(self.user.profile.role, UserProfile.Role.STUDENT)

	def test_login_accepts_username_and_returns_token_and_user(self):
		response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "correct horse battery staple"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data["token"])
		self.assertEqual(response.data["user"]["username"], self.user.username)
		self.assertEqual(response.data["user"]["role"], UserProfile.Role.STUDENT)
		self.assertNotIn("password", response.data["user"])

	def test_login_accepts_email_case_insensitively(self):
		response = self.client.post(
			reverse("login"),
			{"username": "STUDENT@EXAMPLE.COM", "password": "correct horse battery staple"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["user"]["id"], self.user.id)

	def test_login_rejects_invalid_credentials(self):
		response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "wrong-password"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_current_user_requires_authentication_and_returns_profile(self):
		anonymous_response = self.client.get(reverse("current-user"))
		self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

		self.client.force_authenticate(self.user)
		response = self.client.get(reverse("current-user"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["id"], self.user.id)
		self.assertEqual(response.data["role"], UserProfile.Role.STUDENT)

	def test_logout_revokes_token(self):
		login_response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "correct horse battery staple"},
			format="json",
		)
		self.client.credentials(HTTP_AUTHORIZATION=f"Token {login_response.data['token']}")

		logout_response = self.client.post(reverse("logout"))
		current_user_response = self.client.get(reverse("current-user"))

		self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertEqual(current_user_response.status_code, status.HTTP_401_UNAUTHORIZED)
