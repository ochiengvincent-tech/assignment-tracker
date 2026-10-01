from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Course, Enrollment
from .permissions import user_role


class CourseSerializer(serializers.ModelSerializer):
    instructor_id = serializers.IntegerField(source="instructor.id", read_only=True)
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ("id", "name", "term", "instructor_id", "instructor_name", "created_at", "updated_at")
        read_only_fields = ("id", "instructor_id", "instructor_name", "created_at", "updated_at")

    def get_instructor_name(self, course):
        return course.instructor.get_full_name() or course.instructor.get_username()


class EnrollmentSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.name", read_only=True)
    course_term = serializers.CharField(source="course.term", read_only=True)
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "course",
            "course_name",
            "course_term",
            "student_id",
            "student_name",
            "enrolled_at",
        )
        read_only_fields = fields

    def get_student_name(self, enrollment):
        return enrollment.student.get_full_name() or enrollment.student.get_username()


class EnrollmentCreateSerializer(serializers.Serializer):
    course_id = serializers.PrimaryKeyRelatedField(source="course", queryset=Course.objects.all())
    student_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        request = self.context["request"]
        role = user_role(request.user)
        course = attrs["course"]

        if role == "student":
            if "student_id" in attrs:
                raise serializers.ValidationError({"student_id": "Students can only enroll themselves."})
            student = request.user
        elif role == "instructor":
            if course.instructor_id != request.user.id:
                raise serializers.ValidationError({"course_id": "You can only enroll students in your own courses."})
            if "student_id" not in attrs:
                raise serializers.ValidationError({"student_id": "Choose a student to enroll."})
            try:
                student = get_user_model().objects.get(pk=attrs["student_id"])
            except get_user_model().DoesNotExist as exc:
                raise serializers.ValidationError({"student_id": "Student account not found."}) from exc
            if user_role(student) != "student":
                raise serializers.ValidationError({"student_id": "The selected account is not a student."})
        else:
            raise serializers.ValidationError("Your account does not have a student or instructor role.")

        attrs["student"] = student
        return attrs

    def create(self, validated_data):
        enrollment, created = Enrollment.objects.get_or_create(
            student=validated_data["student"],
            course=validated_data["course"],
        )
        if not created:
            raise serializers.ValidationError({"course_id": "You are already enrolled in the course."})
        return enrollment
