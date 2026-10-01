from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course, Enrollment
from submissions.models import Submission
from users.models import UserProfile

from .models import Assignment


class AssignmentApiTests(APITestCase):
	def make_user(self, username, role):
		user = get_user_model().objects.create_user(
			username=username,
			email=f"{username}@example.com",
			password="test-password",
		)
		user.profile.role = role
		user.profile.save(update_fields=("role",))
		return user

	def setUp(self):
		self.instructor = self.make_user("instructor", UserProfile.Role.INSTRUCTOR)
		self.other_instructor = self.make_user("other-instructor", UserProfile.Role.INSTRUCTOR)
		self.student = self.make_user("student", UserProfile.Role.STUDENT)
		self.other_student = self.make_user("other-student", UserProfile.Role.STUDENT)
		self.course = Course.objects.create(name="Computing", term="Fall 2026", instructor=self.instructor)
		self.other_course = Course.objects.create(
			name="Biology", term="Fall 2026", instructor=self.other_instructor
		)
		self.assignment = Assignment.objects.create(
			course=self.course,
			title="First lab",
			description="Write a short report.",
			due_date=timezone.now() + timedelta(days=3),
			category="Lab",
		)

	def test_assignment_list_requires_authentication(self):
		response = self.client.get(reverse("assignment-list"))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_instructor_sees_only_assignments_in_owned_courses(self):
		foreign_assignment = Assignment.objects.create(
			course=self.other_course,
			title="Other lab",
			due_date=timezone.now() + timedelta(days=2),
		)
		self.client.force_authenticate(self.instructor)

		response = self.client.get(reverse("assignment-list"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["id"] for item in response.data], [self.assignment.id])
		self.assertNotIn(foreign_assignment.id, [item["id"] for item in response.data])

	def test_student_sees_assignments_only_for_enrolled_courses(self):
		foreign_assignment = Assignment.objects.create(
			course=self.other_course,
			title="Other lab",
			due_date=timezone.now() + timedelta(days=2),
		)
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse("assignment-list"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["id"] for item in response.data], [self.assignment.id])
		self.assertNotIn(foreign_assignment.id, [item["id"] for item in response.data])

	def test_instructor_can_create_update_and_delete_assignment(self):
		self.client.force_authenticate(self.instructor)
		url = reverse("assignment-list")
		create_response = self.client.post(
			url,
			{
				"course": self.course.id,
				"title": "  Project  ",
				"description": "Build a small app.",
				"due_date": (timezone.now() + timedelta(days=7)).isoformat(),
				"category": "Project",
			},
			format="json",
		)

		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(create_response.data["title"], "Project")
		assignment_id = create_response.data["id"]
		update_response = self.client.patch(
			reverse("assignment-detail", kwargs={"pk": assignment_id}),
			{"title": "Final project"},
			format="json",
		)
		delete_response = self.client.delete(reverse("assignment-detail", kwargs={"pk": assignment_id}))

		self.assertEqual(update_response.status_code, status.HTTP_200_OK)
		self.assertEqual(update_response.data["title"], "Final project")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

	def test_student_cannot_create_or_change_assignments(self):
		self.client.force_authenticate(self.student)
		create_response = self.client.post(
			reverse("assignment-list"),
			{"course": self.course.id, "title": "Unauthorized", "due_date": timezone.now().isoformat()},
			format="json",
		)
		update_response = self.client.patch(
			reverse("assignment-detail", kwargs={"pk": self.assignment.pk}),
			{"title": "Changed"},
			format="json",
		)

		self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
		self.assignment.refresh_from_db()
		self.assertEqual(self.assignment.title, "First lab")

	def test_instructor_cannot_manage_assignments_for_another_instructors_course(self):
		self.client.force_authenticate(self.instructor)
		create_response = self.client.post(
			reverse("assignment-list"),
			{
				"course": self.other_course.id,
				"title": "Foreign assignment",
				"due_date": timezone.now().isoformat(),
			},
			format="json",
		)
		foreign_assignment = Assignment.objects.create(
			course=self.other_course,
			title="Foreign assignment",
			due_date=timezone.now() + timedelta(days=2),
		)
		update_response = self.client.patch(
			reverse("assignment-detail", kwargs={"pk": foreign_assignment.pk}),
			{"title": "Changed"},
			format="json",
		)

		self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(update_response.status_code, status.HTTP_404_NOT_FOUND)
		foreign_assignment.refresh_from_db()
		self.assertEqual(foreign_assignment.title, "Foreign assignment")

	def test_blank_assignment_title_is_rejected(self):
		self.client.force_authenticate(self.instructor)

		response = self.client.post(
			reverse("assignment-list"),
			{"course": self.course.id, "title": "   ", "due_date": timezone.now().isoformat()},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(Assignment.objects.filter(course=self.course, title="").exists())

	def test_assignment_with_submission_cannot_be_deleted(self):
		Enrollment.objects.create(student=self.student, course=self.course)
		Submission.objects.create(assignment=self.assignment, student=self.student)
		self.client.force_authenticate(self.instructor)

		response = self.client.delete(reverse("assignment-detail", kwargs={"pk": self.assignment.pk}))

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertTrue(Assignment.objects.filter(pk=self.assignment.pk).exists())
