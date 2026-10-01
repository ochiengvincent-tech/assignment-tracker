from django.conf import settings
from django.db import models


class Course(models.Model):
    name = models.CharField(max_length=200)
    term = models.CharField(max_length=50)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("term", "name", "id")

    def __str__(self):
        return f"{self.name} ({self.term})"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_enrollments",
    )
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("course__name", "student__username")
        constraints = [
            models.UniqueConstraint(fields=("student", "course"), name="unique_student_course_enrollment"),
        ]

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"
