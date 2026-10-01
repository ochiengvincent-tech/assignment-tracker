from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Assignment


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_date", "category", "updated_at")
    list_filter = ("course__term", "category")
    search_fields = ("title", "description", "course__name")
