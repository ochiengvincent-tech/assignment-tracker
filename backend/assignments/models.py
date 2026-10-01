from django.db import models

from courses.models import Course


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    category = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "id")

    def __str__(self):
        return f"{self.title} — {self.course.name}"
