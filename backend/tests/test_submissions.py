import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from assignments.models import Assignment
from courses.models import Course, Enrollment
from users.models import UserProfile

from submissions.models import Attachment, Submission


class SubmissionAndAttachmentApiTests(APITestCase):
	def make_user(self, username, role):
		user = get_user_model().objects.create_user(
			username=username,
			email=f"{username}@example.com",
		)
		user.profile.role = role
		user.profile.save(update_fields=("role",))
		return user

	def setUp(self):
		self.media = tempfile.TemporaryDirectory()
		self.addCleanup(self.media.cleanup)
		media_settings = override_settings(MEDIA_ROOT=self.media.name)
		media_settings.enable()
		self.addCleanup(media_settings.disable)

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
			due_date=timezone.now() + timedelta(days=2),
		)
		self.other_assignment = Assignment.objects.create(
			course=self.other_course,
			title="Other lab",
			due_date=timezone.now() + timedelta(days=2),
		)
		Enrollment.objects.create(student=self.student, course=self.course)
		Enrollment.objects.create(student=self.other_student, course=self.other_course)

	def upload(self, name="work.txt", content=b"my work", **target):
		return self.client.post(
			reverse("attachment-create"),
			{**target, "file": SimpleUploadedFile(name, content, content_type="text/plain")},
			format="multipart",
		)

	def create_submission(self, assignment=None, student=None, response_text=""):
		return Submission.objects.create(
			assignment=assignment or self.assignment,
			student=student or self.student,
			response_text=response_text,
		)

	def test_student_can_create_and_save_a_draft(self):
		self.client.force_authenticate(self.student)

		create_response = self.client.post(
			reverse("submission-list"),
			{"assignment": self.assignment.id, "response_text": "Initial response"},
			format="json",
		)
		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
		submission = Submission.objects.get(assignment=self.assignment, student=self.student)
		update_response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": submission.pk}),
			{"response_text": "Saved response"},
			format="json",
		)

		self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(submission.status, Submission.Status.IN_PROGRESS)
		self.assertEqual(update_response.status_code, status.HTTP_200_OK)
		self.assertEqual(update_response.data["response_text"], "Saved response")

	def test_only_enrolled_students_can_create_submissions(self):
		self.client.force_authenticate(self.other_student)

		response = self.client.post(
			reverse("submission-list"), {"assignment": self.assignment.id}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(Submission.objects.exists())

	def test_duplicate_submission_is_rejected(self):
		self.create_submission()
		self.client.force_authenticate(self.student)

		response = self.client.post(
			reverse("submission-list"), {"assignment": self.assignment.id}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(Submission.objects.count(), 1)

	def test_instructors_cannot_create_student_submissions(self):
		self.client.force_authenticate(self.instructor)

		response = self.client.post(
			reverse("submission-list"), {"assignment": self.assignment.id}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_student_can_submit_non_empty_draft(self):
		submission = self.create_submission(response_text="Completed work")
		self.client.force_authenticate(self.student)

		response = self.client.post(reverse("submission-submit", kwargs={"pk": submission.pk}))

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], Submission.Status.SUBMITTED)
		self.assertIsNotNone(response.data["submitted_at"])

	def test_empty_draft_cannot_be_submitted(self):
		submission = self.create_submission()
		self.client.force_authenticate(self.student)

		response = self.client.post(reverse("submission-submit", kwargs={"pk": submission.pk}))

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		submission.refresh_from_db()
		self.assertEqual(submission.status, Submission.Status.IN_PROGRESS)

	def test_submitted_work_cannot_be_edited_by_student(self):
		submission = self.create_submission(response_text="Submitted")
		submission.status = Submission.Status.SUBMITTED
		submission.submitted_at = timezone.now()
		submission.save(update_fields=("status", "submitted_at", "updated_at"))
		self.client.force_authenticate(self.student)

		response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": submission.pk}),
			{"response_text": "Changed after submitting"},
			format="json",
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		submission.refresh_from_db()
		self.assertEqual(submission.response_text, "Submitted")

	def test_students_and_instructors_see_only_submissions_in_their_scope(self):
		own_submission = self.create_submission()
		other_submission = self.create_submission(
			assignment=self.other_assignment,
			student=self.other_student,
			response_text="Other work",
		)

		self.client.force_authenticate(self.student)
		student_response = self.client.get(reverse("submission-list"))
		self.assertEqual([item["id"] for item in student_response.data], [own_submission.id])

		self.client.force_authenticate(self.instructor)
		instructor_response = self.client.get(reverse("submission-list"))
		self.assertEqual([item["id"] for item in instructor_response.data], [own_submission.id])
		self.assertNotIn(other_submission.id, [item["id"] for item in instructor_response.data])

	def test_instructor_can_grade_submitted_work(self):
		submission = self.create_submission(response_text="Submitted")
		submission.status = Submission.Status.SUBMITTED
		submission.submitted_at = timezone.now()
		submission.save(update_fields=("status", "submitted_at", "updated_at"))
		self.client.force_authenticate(self.instructor)

		response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": submission.pk}), {"grade": "94.50"}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
		self.assertEqual(response.data["grade"], "94.50")
		submission.refresh_from_db()
		self.assertEqual(submission.status, Submission.Status.GRADED)

	def test_instructor_cannot_grade_draft_or_another_instructors_work(self):
		draft = self.create_submission()
		submitted_other = self.create_submission(
			assignment=self.other_assignment,
			student=self.other_student,
			response_text="Submitted elsewhere",
		)
		submitted_other.status = Submission.Status.SUBMITTED
		submitted_other.submitted_at = timezone.now()
		submitted_other.save(update_fields=("status", "submitted_at", "updated_at"))
		self.client.force_authenticate(self.instructor)

		draft_response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": draft.pk}), {"grade": "80"}, format="json"
		)
		foreign_response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": submitted_other.pk}),
			{"grade": "80"},
			format="json",
		)

		self.assertEqual(draft_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(foreign_response.status_code, status.HTTP_404_NOT_FOUND)

	def test_grade_must_be_between_zero_and_one_hundred(self):
		submission = self.create_submission(response_text="Submitted")
		submission.status = Submission.Status.SUBMITTED
		submission.submitted_at = timezone.now()
		submission.save(update_fields=("status", "submitted_at", "updated_at"))
		self.client.force_authenticate(self.instructor)

		response = self.client.patch(
			reverse("submission-detail", kwargs={"pk": submission.pk}), {"grade": "101"}, format="json"
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		submission.refresh_from_db()
		self.assertIsNone(submission.grade)

	def test_student_can_upload_and_download_own_draft_attachment(self):
		submission = self.create_submission()
		self.client.force_authenticate(self.student)

		upload_response = self.upload(submission_id=submission.id)
		attachment = Attachment.objects.get(pk=upload_response.data["id"])
		download_response = self.client.get(reverse("attachment-download", kwargs={"pk": attachment.pk}))

		self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(upload_response.data["original_name"], "work.txt")
		self.assertEqual(upload_response.data["size_bytes"], len(b"my work"))
		self.assertEqual(download_response.status_code, status.HTTP_200_OK)
		self.assertEqual(b"".join(download_response.streaming_content), b"my work")

	def test_upload_rejects_unsupported_extensions_and_files_over_ten_megabytes(self):
		submission = self.create_submission()
		self.client.force_authenticate(self.student)

		bad_extension_response = self.upload("script.exe", submission_id=submission.id)
		large_file_response = self.upload(
			"large.pdf",
			b"x" * (10 * 1024 * 1024 + 1),
			submission_id=submission.id,
		)

		self.assertEqual(bad_extension_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(large_file_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(Attachment.objects.exists())

	def test_upload_requires_exactly_one_valid_owned_target(self):
		submission = self.create_submission()
		self.client.force_authenticate(self.student)

		no_target = self.upload()
		both_targets = self.upload(assignment_id=self.assignment.id, submission_id=submission.id)
		another_students_submission = self.create_submission(
			assignment=self.other_assignment,
			student=self.other_student,
		)
		foreign_target = self.upload(submission_id=another_students_submission.id)

		self.assertEqual(no_target.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(both_targets.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(foreign_target.status_code, status.HTTP_400_BAD_REQUEST)

	def test_instructor_can_upload_and_remove_own_assignment_attachment(self):
		self.client.force_authenticate(self.instructor)

		upload_response = self.upload(assignment_id=self.assignment.id)
		attachment = Attachment.objects.get(pk=upload_response.data["id"])
		file_path = Path(attachment.file.path)
		delete_response = self.client.delete(reverse("attachment-delete", kwargs={"pk": attachment.pk}))

		self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
		self.assertFalse(file_path.exists())

	def test_users_cannot_upload_files_to_other_users_or_courses(self):
		submission = self.create_submission()
		self.client.force_authenticate(self.other_student)
		foreign_submission_response = self.upload(submission_id=submission.id)

		self.client.force_authenticate(self.instructor)
		foreign_assignment_response = self.upload(assignment_id=self.other_assignment.id)

		self.assertEqual(foreign_submission_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(foreign_assignment_response.status_code, status.HTTP_400_BAD_REQUEST)

	def test_submitted_student_attachment_cannot_be_deleted_by_student(self):
		submission = self.create_submission()
		attachment = Attachment.objects.create(
			submission=submission,
			file=SimpleUploadedFile("work.txt", b"my work"),
			original_name="work.txt",
			size_bytes=7,
		)
		submission.status = Submission.Status.SUBMITTED
		submission.submitted_at = timezone.now()
		submission.save(update_fields=("status", "submitted_at", "updated_at"))
		self.client.force_authenticate(self.student)

		response = self.client.delete(reverse("attachment-delete", kwargs={"pk": attachment.pk}))

		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
		self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())
