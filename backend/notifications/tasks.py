from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from assignments.models import Assignment
from submissions.models import Submission

from .models import Notification


@shared_task
def schedule_assignment_reminders():
    now = timezone.now()
    window_end = now + timedelta(hours=24)
    assignments = Assignment.objects.filter(due_date__gt=now, due_date__lte=window_end).select_related("course")
    created_count = 0

    for assignment in assignments:
        submitted_students = Submission.objects.filter(
            assignment=assignment,
            status__in=(Submission.Status.SUBMITTED, Submission.Status.GRADED),
        ).values_list("student", flat=True)
        students = assignment.course.enrollments.exclude(student_id__in=submitted_students).values_list(
            "student_id", flat=True
        )
        for student_id in students:
            message = f"{assignment.title} for {assignment.course.name} is due within 24 hours."
            notification, created = Notification.objects.get_or_create(
                user_id=student_id,
                assignment=assignment,
                type=Notification.Type.ASSIGNMENT_REMINDER,
                defaults={
                    "title": f"Upcoming assignment: {assignment.title}",
                    "message": message,
                    "scheduled_for": max(now, assignment.due_date - timedelta(hours=24)),
                },
            )
            if not created:
                claimed = Notification.objects.filter(
                    pk=notification.pk,
                    status__in=(Notification.Status.SCHEDULED, Notification.Status.FAILED),
                ).update(status=Notification.Status.QUEUED)
                if not claimed:
                    continue
            else:
                notification.status = Notification.Status.QUEUED
                notification.save(update_fields=("status",))
            try:
                deliver_assignment_reminder.delay(notification.pk)
            except Exception:
                notification.status = Notification.Status.FAILED
                notification.save(update_fields=("status",))
                continue
            created_count += 1
    return created_count


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_assignment_reminder(self, notification_id):
    notification = Notification.objects.select_related("user", "assignment").filter(pk=notification_id).first()
    if notification is None or notification.status == Notification.Status.SENT:
        return
    if notification.assignment_id is None:
        notification.status = Notification.Status.FAILED
        notification.save(update_fields=("status",))
        return

    if notification.assignment.due_date > timezone.now() + timedelta(hours=24):
        notification.status = Notification.Status.SCHEDULED
        notification.save(update_fields=("status",))
        return

    if Submission.objects.filter(
        assignment_id=notification.assignment_id,
        student=notification.user,
        status__in=(Submission.Status.SUBMITTED, Submission.Status.GRADED),
    ).exists():
        notification.status = Notification.Status.SKIPPED
        notification.save(update_fields=("status",))
        return

    try:
        if notification.user.email:
            send_mail(
                notification.title,
                notification.message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.user.email],
                fail_silently=False,
            )
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            notification.status = Notification.Status.FAILED
            notification.save(update_fields=("status",))
        raise self.retry(exc=exc)

    notification.status = Notification.Status.SENT
    notification.sent_at = timezone.now()
    notification.save(update_fields=("status", "sent_at"))
