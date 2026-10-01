from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from courses.models import Course
from courses.permissions import IsInstructor, user_role

from .models import Assignment
from .serializers import AssignmentSerializer


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        assignments = Assignment.objects.select_related("course", "course__instructor")
        if role == "instructor":
            assignments = assignments.filter(course__instructor=self.request.user)
        elif role == "student":
            assignments = assignments.filter(course__enrollments__student=self.request.user)
        else:
            return Assignment.objects.none()

        course_id = self.request.query_params.get("course_id")
        if course_id:
            if not course_id.isdecimal():
                raise ValidationError({"course_id": "Course ID must be a number."})
            assignments = assignments.filter(course_id=course_id)
        return assignments.distinct()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsInstructor()]
        return [permission() for permission in self.permission_classes]

    def perform_destroy(self, instance):
        if instance.submissions.exists():
            raise ValidationError("An assignment with student submissions cannot be deleted.")
        instance.delete()
