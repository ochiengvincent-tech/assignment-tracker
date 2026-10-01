from rest_framework import serializers

from courses.models import Course
from courses.permissions import user_role
from submissions.serializers import AttachmentSerializer

from .models import Assignment


class AssignmentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = (
            "id",
            "course",
            "course_name",
            "title",
            "description",
            "due_date",
            "category",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "course_name", "created_at", "updated_at")

    def validate_course(self, course):
        request = self.context["request"]
        if user_role(request.user) != "instructor":
            raise serializers.ValidationError("Only instructors can create or change assignments.")
        if course.instructor_id != request.user.id:
            raise serializers.ValidationError("You can only manage assignments in your own courses.")
        return course

    def validate_title(self, title):
        title = title.strip()
        if not title:
            raise serializers.ValidationError("Assignment title cannot be blank.")
        return title
