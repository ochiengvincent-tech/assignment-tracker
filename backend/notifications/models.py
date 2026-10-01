from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        ASSIGNMENT_REMINDER = "assignment_reminder", "Assignment reminder"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    assignment = models.ForeignKey(
        "assignments.Assignment", on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    type = models.CharField(max_length=40, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    title = models.CharField(max_length=200)
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("user", "assignment", "type"),
                condition=models.Q(assignment__isnull=False),
                name="unique_assignment_notification_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.user}"
