from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import Course, Enrollment
from .permissions import IsInstructor, user_role
from .serializers import CourseSerializer, EnrollmentCreateSerializer, EnrollmentSerializer


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        if role == "instructor":
            return Course.objects.filter(instructor=self.request.user)
        if role == "student":
            return Course.objects.filter(enrollments__student=self.request.user).distinct()
        return Course.objects.none()

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsInstructor()]
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        if user_role(self.request.user) != "instructor":
            raise PermissionDenied("Only instructors can create courses.")
        serializer.save(instructor=self.request.user)

    def perform_destroy(self, instance):
        if instance.enrollments.exists() or instance.assignments.exists():
            raise ValidationError("A course with assignments or enrollments cannot be deleted.")
        instance.delete()


class EnrollmentListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        enrollments = Enrollment.objects.select_related("course", "student")
        if role == "student":
            enrollments = enrollments.filter(student=self.request.user)
        elif role == "instructor":
            enrollments = enrollments.filter(course__instructor=self.request.user)
        else:
            return Enrollment.objects.none()

        course_id = self.request.query_params.get("course_id")
        if course_id:
            if not course_id.isdecimal():
                raise ValidationError({"course_id": "Course ID must be a number."})
            enrollments = enrollments.filter(course_id=course_id)
        return enrollments

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EnrollmentCreateSerializer
        return EnrollmentSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    def perform_create(self, serializer):
        serializer.save()
