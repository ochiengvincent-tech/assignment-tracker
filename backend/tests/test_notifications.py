from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assignments.models import Assignment
from courses.models import Course, Enrollment
from notifications.models import Notification
from notifications.reminders import create_assignment_reminders
from submissions.models import Submission


class AssignmentReminderTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.instructor = user_model.objects.create_user(
            username="instructor",
            email="instructor@example.com",
        )
        self.student = user_model.objects.create_user(
            username="student",
            email="student@example.com",
        )
        self.submitted_student = user_model.objects.create_user(
            username="submitted-student",
            email="submitted@example.com",
        )
        self.graded_student = user_model.objects.create_user(
            username="graded-student",
            email="graded@example.com",
        )
        self.unenrolled_student = user_model.objects.create_user(
            username="unenrolled-student",
            email="unenrolled@example.com",
        )
        self.course = Course.objects.create(
            name="Computing",
            term="Fall 2026",
            instructor=self.instructor,
        )
        Enrollment.objects.create(student=self.student, course=self.course)
        self.now = timezone.now()

    def create_assignment(self, title, due_date):
        return Assignment.objects.create(
            course=self.course,
            title=title,
            due_date=due_date,
        )

    def test_creates_reminders_only_for_enrolled_students_without_completed_submissions(self):
        assignment = self.create_assignment("First lab", self.now + timedelta(hours=12))
        Enrollment.objects.create(student=self.submitted_student, course=self.course)
        Enrollment.objects.create(student=self.graded_student, course=self.course)
        Submission.objects.create(
            assignment=assignment,
            student=self.submitted_student,
            status=Submission.Status.SUBMITTED,
            submitted_at=self.now,
        )
        Submission.objects.create(
            assignment=assignment,
            student=self.graded_student,
            status=Submission.Status.GRADED,
            submitted_at=self.now,
        )

        created_count, queued_ids = create_assignment_reminders(now=self.now)

        notification = Notification.objects.get(assignment=assignment)
        self.assertEqual((created_count, queued_ids), (1, []))
        self.assertEqual(notification.user, self.student)
        self.assertEqual(notification.type, Notification.Type.ASSIGNMENT_REMINDER)
        self.assertEqual(notification.status, Notification.Status.SENT)
        self.assertEqual(notification.title, "Upcoming assignment: First lab")
        self.assertEqual(
            notification.message,
            "First lab for Computing is due within 24 hours.",
        )
        self.assertEqual(notification.scheduled_for, self.now)
        self.assertEqual(notification.sent_at, self.now)
        self.assertFalse(Notification.objects.filter(user=self.unenrolled_student).exists())

    def test_due_window_excludes_assignments_due_now_or_after_24_hours(self):
        due_now = self.create_assignment("Due now", self.now)
        within_window = self.create_assignment("Due soon", self.now + timedelta(hours=1))
        at_window_end = self.create_assignment("Due at cutoff", self.now + timedelta(hours=24))
        after_window = self.create_assignment("Due later", self.now + timedelta(hours=24, seconds=1))
        created_count, _ = create_assignment_reminders(now=self.now)

        self.assertEqual(created_count, 2)
        self.assertSetEqual(
            set(Notification.objects.values_list("assignment_id", flat=True)),
            {within_window.id, at_window_end.id},
        )

    def test_reminder_creation_is_idempotent_and_reactivates_failed_reminder(self):
        assignment = self.create_assignment("First lab", self.now + timedelta(hours=12))
        existing = Notification.objects.create(
            user=self.student,
            assignment=assignment,
            type=Notification.Type.ASSIGNMENT_REMINDER,
            status=Notification.Status.FAILED,
            title="Old title",
            message="Old message",
            scheduled_for=self.now,
        )

        first_result = create_assignment_reminders(now=self.now)
        second_result = create_assignment_reminders(now=self.now)

        existing.refresh_from_db()
        self.assertEqual(first_result, (1, []))
        self.assertEqual(second_result, (0, []))
        self.assertEqual(Notification.objects.filter(assignment=assignment).count(), 1)
        self.assertEqual(existing.status, Notification.Status.SENT)
        self.assertEqual(existing.sent_at, self.now)

    def test_email_queue_mode_returns_newly_queued_reminder_ids(self):
        assignment = self.create_assignment("First lab", self.now + timedelta(hours=12))

        created_count, queued_ids = create_assignment_reminders(enqueue_email=True, now=self.now)

        notification = Notification.objects.get(assignment=assignment, user=self.student)
        self.assertEqual(created_count, 1)
        self.assertEqual(queued_ids, [notification.id])
        self.assertEqual(notification.status, Notification.Status.QUEUED)
        self.assertIsNone(notification.sent_at)
