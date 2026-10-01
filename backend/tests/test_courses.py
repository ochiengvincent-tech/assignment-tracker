from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import UserProfile

from courses.models import Course, Enrollment


class CourseAndEnrollmentApiTests(APITestCase):
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

	def test_courses_require_authentication(self):
		response = self.client.get(reverse("course-list"))

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_instructor_lists_only_owned_courses(self):
		self.client.force_authenticate(self.instructor)

		response = self.client.get(reverse("course-list"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["id"] for item in response.data], [self.course.id])

	def test_student_lists_only_enrolled_courses(self):
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse("course-list"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["id"] for item in response.data], [self.course.id])

	def test_instructor_can_create_update_and_delete_empty_course(self):
		self.client.force_authenticate(self.instructor)
		create_response = self.client.post(
			reverse("course-list"), {"name": "Databases", "term": "Fall 2026"}, format="json"
		)

		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(create_response.data["instructor_id"], self.instructor.id)
		course_id = create_response.data["id"]

		update_response = self.client.patch(
			reverse("course-detail", kwargs={"pk": course_id}), {"name": "Database Systems"}, format="json"
		)
		delete_response = self.client.delete(reverse("course-detail", kwargs={"pk": course_id}))

		self.assertEqual(update_response.status_code, status.HTTP_200_OK)
		self.assertEqual(update_response.data["name"], "Database Systems")
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(Course.objects.filter(pk=course_id).exists())

	def test_student_cannot_create_course(self):
		self.client.force_authenticate(self.student)

		response = self.client.post(
			reverse("course-list"), {"name": "Unauthorized", "term": "Fall 2026"}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_instructor_cannot_change_another_instructors_course(self):
		self.client.force_authenticate(self.instructor)

		response = self.client.patch(
			reverse("course-detail", kwargs={"pk": self.other_course.pk}), {"name": "Stolen"}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
		self.other_course.refresh_from_db()
		self.assertEqual(self.other_course.name, "Biology")

	def test_course_with_enrollment_cannot_be_deleted(self):
		Enrollment.objects.create(student=self.student, course=self.course)
		self.client.force_authenticate(self.instructor)

		response = self.client.delete(reverse("course-detail", kwargs={"pk": self.course.pk}))

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

	def test_student_can_enroll_self_once(self):
		self.client.force_authenticate(self.student)
		url = reverse("enrollment-list-create")

		first_response = self.client.post(url, {"course_id": self.course.id}, format="json")
		duplicate_response = self.client.post(url, {"course_id": self.course.id}, format="json")

		self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(first_response.data["student_id"], self.student.id)
		self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(duplicate_response.data["course_id"], "You are already enrolled in the course.")
		self.assertEqual(Enrollment.objects.filter(student=self.student, course=self.course).count(), 1)

	def test_student_cannot_enroll_another_student(self):
		self.client.force_authenticate(self.student)

		response = self.client.post(
			reverse("enrollment-list-create"),
			{"course_id": self.course.id, "student_id": self.other_student.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(Enrollment.objects.exists())

	def test_instructor_can_enroll_students_in_owned_course_only(self):
		self.client.force_authenticate(self.instructor)
		url = reverse("enrollment-list-create")

		own_response = self.client.post(
			url, {"course_id": self.course.id, "student_id": self.student.id}, format="json"
		)
		foreign_response = self.client.post(
			url, {"course_id": self.other_course.id, "student_id": self.other_student.id}, format="json"
		)

		self.assertEqual(own_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(foreign_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(Enrollment.objects.count(), 1)

	def test_student_enrollment_list_is_scoped_to_current_student(self):
		Enrollment.objects.create(student=self.student, course=self.course)
		Enrollment.objects.create(student=self.other_student, course=self.other_course)
		self.client.force_authenticate(self.student)

		response = self.client.get(reverse("enrollment-list-create"))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual([item["student_id"] for item in response.data], [self.student.id])

	def test_instructor_cannot_be_enrolled_as_a_student(self):
		self.client.force_authenticate(self.instructor)

		response = self.client.post(
			reverse("enrollment-list-create"),
			{"course_id": self.course.id, "student_id": self.other_instructor.id},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(Enrollment.objects.exists())
