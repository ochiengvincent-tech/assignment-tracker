from datetime import timedelta

from django.utils import timezone

from assignments.models import Assignment
from submissions.models import Submission

from .models import Notification


def create_assignment_reminders(*, enqueue_email=False, now=None):
    """Create idempotent in-app reminders for assignments due within 24 hours."""
    now = now or timezone.now()
    window_end = now + timedelta(hours=24)
    assignments = Assignment.objects.filter(due_date__gt=now, due_date__lte=window_end).select_related("course")
    created_count = 0
    queued_ids = []

    for assignment in assignments:
        submitted_students = Submission.objects.filter(
            assignment=assignment,
            status__in=(Submission.Status.SUBMITTED, Submission.Status.GRADED),
        ).values_list("student", flat=True)
        student_ids = assignment.course.enrollments.exclude(student_id__in=submitted_students).values_list(
            "student_id", flat=True
        )

        for student_id in student_ids:
            notification, created = Notification.objects.get_or_create(
                user_id=student_id,
                assignment=assignment,
                type=Notification.Type.ASSIGNMENT_REMINDER,
                defaults={
                    "title": f"Upcoming assignment: {assignment.title}",
                    "message": f"{assignment.title} for {assignment.course.name} is due within 24 hours.",
                    "scheduled_for": max(now, assignment.due_date - timedelta(hours=24)),
                    "status": Notification.Status.QUEUED if enqueue_email else Notification.Status.SENT,
                    "sent_at": None if enqueue_email else now,
                },
            )

            if not created and not enqueue_email:
                changed = Notification.objects.filter(pk=notification.pk).exclude(
                    status__in=(Notification.Status.SENT, Notification.Status.SKIPPED)
                ).update(status=Notification.Status.SENT, sent_at=now)
                created_count += bool(changed)
                continue

            if not created and enqueue_email:
                claimed = Notification.objects.filter(
                    pk=notification.pk,
                    status__in=(Notification.Status.SCHEDULED, Notification.Status.FAILED),
                ).update(status=Notification.Status.QUEUED)
                if claimed:
                    queued_ids.append(notification.pk)
                continue

            if created:
                created_count += 1
                if enqueue_email:
                    queued_ids.append(notification.pk)

    return created_count, queued_ids
