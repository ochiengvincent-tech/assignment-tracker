from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "term", "instructor", "created_at")
    list_filter = ("term",)
    search_fields = ("name", "term", "instructor__username", "instructor__email")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "enrolled_at")
    list_filter = ("course__term",)
    search_fields = ("course__name", "student__username", "student__email")
