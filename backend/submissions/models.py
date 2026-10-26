from django.db import models

# Create your models here.
import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from assignments.models import Assignment


def attachment_upload_path(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return f"attachments/{uuid.uuid4().hex}{extension}"


class Submission(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        GRADED = "graded", "Graded"

    assignment = models.ForeignKey(Assignment, on_delete=models.PROTECT, related_name="submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    response_text = models.TextField(blank=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    instructor_comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.UniqueConstraint(fields=("assignment", "student"), name="unique_student_assignment_submission"),
            models.CheckConstraint(
                condition=Q(grade__isnull=True) | Q(grade__gte=0, grade__lte=100),
                name="submission_grade_between_0_and_100",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="in_progress", submitted_at__isnull=True)
                    | Q(status__in=("submitted", "graded"), submitted_at__isnull=False)
                ),
                name="submission_status_matches_submitted_at",
            ),
        ]

    def __str__(self):
        return f"{self.student} — {self.assignment.title}"


class Attachment(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to=attachment_upload_path)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255, blank=True)
    size_bytes = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("uploaded_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(assignment__isnull=False, submission__isnull=True)
                    | Q(assignment__isnull=True, submission__isnull=False)
                ),
                name="attachment_has_exactly_one_target",
            ),
        ]

    def __str__(self):
        return self.original_name
