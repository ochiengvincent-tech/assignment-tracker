from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment
from courses.models import Course, Enrollment
from submissions.models import Submission
from users.models import UserProfile


class DashboardApiTests(APITestCase):
	def make_user(self, username, role):
		user = get_user_model().objects.create_user(
			username=username,
			email=f"{username}@example.com",
		)
		user.profile.role = role
		user.profile.save(update_fields=("role",))
		return user

	def make_assignment(self, course, title, due_date):
		return Assignment.objects.create(course=course, title=title, due_date=due_date)

	def setUp(self):
		self.instructor = self.make_user("instructor", UserProfile.Role.INSTRUCTOR)
		self.other_instructor = self.make_user("other-instructor", UserProfile.Role.INSTRUCTOR)
		self.student = self.make_user("student", UserProfile.Role.STUDENT)
		self.other_student = self.make_user("other-student", UserProfile.Role.STUDENT)
		self.course = Course.objects.create(name="Computing", term="Fall 2026", instructor=self.instructor)
		self.other_course = Course.objects.create(
			name="Biology", term="Fall 2026", instructor=self.other_instructor
		)
		Enrollment.objects.create(student=self.student, course=self.course)
		Enrollment.objects.create(student=self.other_student, course=self.other_course)

	def test_dashboard_requires_authentication(self):
		response = self.client.get(reverse("dashboard"))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_student_dashboard_summarizes_only_enrolled_assignments(self):
		now = timezone.now()
		upcoming = self.make_assignment(self.course, "Upcoming", now + timedelta(days=3))
		overdue = self.make_assignment(self.course, "Overdue", now - timedelta(days=3))
		in_progress = self.make_assignment(self.course, "Draft", now + timedelta(days=4))
		graded = self.make_assignment(self.course, "Graded", now + timedelta(days=5))
		foreign = self.make_assignment(self.other_course, "Not enrolled", now + timedelta(days=1))
		Submission.objects.create(assignment=in_progress, student=self.student)
		Submission.objects.create(
			assignment=graded,
			student=self.student,
			status=Submission.Status.GRADED,
			submitted_at=now,
			grade="92.00",
		)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse("dashboard"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["role"], "student")
		self.assertEqual(
			response.data["summary"],
			{
				"total_assignments": 4,
				"upcoming": 2,
				"overdue": 1,
				"in_progress": 1,
				"completed": 1,
			},
		)
		statuses = {item["assignment_id"]: item["status"] for item in response.data["assignments"]}
		self.assertEqual(statuses[upcoming.id], "not_started")
		self.assertEqual(statuses[overdue.id], "overdue")
		self.assertEqual(statuses[in_progress.id], "in_progress")
		self.assertEqual(statuses[graded.id], "graded")
		self.assertNotIn(foreign.id, statuses)

	def test_instructor_dashboard_counts_only_owned_course_activity(self):
		now = timezone.now()
		own_in_progress = self.make_assignment(self.course, "Draft", now + timedelta(days=3))
		own_submitted = self.make_assignment(self.course, "Review", now + timedelta(days=4))
		own_graded = self.make_assignment(self.course, "Graded", now + timedelta(days=5))
		foreign = self.make_assignment(self.other_course, "Foreign", now + timedelta(days=1))
		Submission.objects.create(assignment=own_in_progress, student=self.student)
		Submission.objects.create(
			assignment=own_submitted,
			student=self.student,
			status=Submission.Status.SUBMITTED,
			submitted_at=now,
		)
		Submission.objects.create(
			assignment=own_graded,
			student=self.student,
			status=Submission.Status.GRADED,
			submitted_at=now,
			grade="87.00",
		)
		Submission.objects.create(
			assignment=foreign,
			student=self.other_student,
			status=Submission.Status.SUBMITTED,
			submitted_at=now,
		)
		self.client.force_authenticate(self.instructor)

		response = self.client.get(reverse("dashboard"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["role"], "instructor")
		self.assertEqual(
			response.data["summary"],
			{"courses": 1, "assignments": 3, "in_progress": 1, "awaiting_review": 1, "graded": 1},
		)
		self.assertEqual(response.data["courses"][0]["student_count"], 1)
		self.assertEqual(
			{item["id"] for item in response.data["assignments"]},
			{own_in_progress.id, own_submitted.id, own_graded.id},
		)

	def test_user_without_an_application_role_is_forbidden(self):
		user = self.make_user("unassigned", UserProfile.Role.STUDENT)
		user.profile.role = ""
		user.profile.save(update_fields=("role",))
		self.client.force_authenticate(user)

		response = self.client.get(reverse("dashboard"))

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
