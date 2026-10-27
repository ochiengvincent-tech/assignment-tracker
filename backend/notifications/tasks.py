from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from submissions.models import Submission

from .models import Notification
from .reminders import create_assignment_reminders


@shared_task
def schedule_assignment_reminders():
    _, notification_ids = create_assignment_reminders(enqueue_email=True)
    queued_count = 0
    for notification_id in notification_ids:
        try:
            deliver_assignment_reminder.delay(notification_id)
        except Exception:
            Notification.objects.filter(pk=notification_id).update(status=Notification.Status.FAILED)
            continue
        queued_count += 1
    return queued_count


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
