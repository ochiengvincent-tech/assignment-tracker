import os

from django.urls import reverse
from rest_framework import serializers

from assignments.models import Assignment
from courses.permissions import user_role

from .models import Attachment, Submission


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ("id", "original_name", "mime_type", "size_bytes", "uploaded_at", "download_url")
        read_only_fields = fields

    def get_download_url(self, attachment):
        path = reverse("attachment-download", kwargs={"pk": attachment.pk})
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class SubmissionSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True)
    assignment_due_date = serializers.DateTimeField(source="assignment.due_date", read_only=True)
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_name = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    is_late = serializers.SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            "id",
            "assignment",
            "assignment_title",
            "assignment_due_date",
            "student_id",
            "student_name",
            "status",
            "response_text",
            "grade",
            "instructor_comment",
            "submitted_at",
            "is_late",
            "attachments",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_student_name(self, submission):
        return submission.student.get_full_name() or submission.student.get_username()

    def get_is_late(self, submission):
        return bool(submission.submitted_at and submission.submitted_at > submission.assignment.due_date)


class SubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ("assignment", "response_text")

    def validate_assignment(self, assignment):
        user = self.context["request"].user
        if not assignment.course.enrollments.filter(student=user).exists():
            raise serializers.ValidationError("You can only submit work for a course you are enrolled in.")
        if Submission.objects.filter(assignment=assignment, student=user).exists():
            raise serializers.ValidationError("A submission already exists for this assignment.")
        return assignment

    def create(self, validated_data):
        return Submission.objects.create(student=self.context["request"].user, **validated_data)


class SubmissionDraftUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ("response_text",)


class SubmissionGradeSerializer(serializers.ModelSerializer):
    grade = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)

    class Meta:
        model = Submission
        fields = ("grade", "instructor_comment")
        extra_kwargs = {"instructor_comment": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        if self.instance.status not in (Submission.Status.SUBMITTED, Submission.Status.GRADED):
            raise serializers.ValidationError("Only submitted work can be graded.")
        return attrs

    def update(self, instance, validated_data):
        instance.grade = validated_data["grade"]
        instance.instructor_comment = validated_data.get("instructor_comment", instance.instructor_comment)
        instance.status = Submission.Status.GRADED
        instance.save(update_fields=("grade", "instructor_comment", "status", "updated_at"))
        return instance


class AttachmentUploadSerializer(serializers.Serializer):
    MAX_SIZE_BYTES = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png"}

    assignment_id = serializers.PrimaryKeyRelatedField(
        source="assignment", queryset=Assignment.objects.all(), required=False
    )
    submission_id = serializers.PrimaryKeyRelatedField(
        source="submission", queryset=Submission.objects.all(), required=False
    )
    file = serializers.FileField()

    def validate_file(self, file):
        extension = os.path.splitext(file.name)[1].lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Use a PDF, Word document, text file, JPG, or PNG.")
        if file.size > self.MAX_SIZE_BYTES:
            raise serializers.ValidationError("Files must be 10 MB or smaller.")
        return file

    def validate(self, attrs):
        request = self.context["request"]
        assignment = attrs.get("assignment")
        submission = attrs.get("submission")
        if bool(assignment) == bool(submission):
            raise serializers.ValidationError("Attach a file to one assignment or one submission.")

        if assignment:
            if user_role(request.user) != "instructor" or assignment.course.instructor_id != request.user.id:
                raise serializers.ValidationError({"assignment_id": "You can only attach files to your own assignments."})
        elif (
            user_role(request.user) != "student"
            or submission.student_id != request.user.id
            or submission.status != Submission.Status.IN_PROGRESS
        ):
            raise serializers.ValidationError({"submission_id": "Files can only be added to your own work in progress."})
        return attrs

    def create(self, validated_data):
        upload = validated_data["file"]
        return Attachment.objects.create(
            **{key: value for key, value in validated_data.items() if key != "file"},
            file=upload,
            original_name=os.path.basename(upload.name)[:255],
            mime_type=(upload.content_type or "application/octet-stream")[:255],
            size_bytes=upload.size,
        )
