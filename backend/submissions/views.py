from django.shortcuts import render

# Create your views here.
import mimetypes

from django.db.models import Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import DestroyAPIView, GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from courses.permissions import IsStudent, user_role

from .models import Attachment, Submission
from .serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    SubmissionCreateSerializer,
    SubmissionDraftUpdateSerializer,
    SubmissionGradeSerializer,
    SubmissionSerializer,
)


class SubmissionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        submissions = Submission.objects.select_related(
            "assignment", "assignment__course", "student"
        ).prefetch_related("attachments")
        if role == "student":
            submissions = submissions.filter(student=self.request.user)
        elif role == "instructor":
            submissions = submissions.filter(assignment__course__instructor=self.request.user)
        else:
            return Submission.objects.none()

        assignment_id = self.request.query_params.get("assignment_id")
        if assignment_id:
            if not assignment_id.isdecimal():
                raise ValidationError({"assignment_id": "Assignment ID must be a number."})
            submissions = submissions.filter(assignment_id=assignment_id)
        return submissions

    def get_permissions(self):
        if self.action in ("create", "submit"):
            return [IsAuthenticated(), IsStudent()]
        return [permission() for permission in self.permission_classes]

    def get_serializer_class(self):
        if self.action == "create":
            return SubmissionCreateSerializer
        if self.action in ("update", "partial_update"):
            if user_role(self.request.user) == "instructor":
                return SubmissionGradeSerializer
            return SubmissionDraftUpdateSerializer
        return SubmissionSerializer

    @action(detail=True, methods=("post",))
    def submit(self, request, pk=None):
        submission = self.get_object()
        if submission.status != Submission.Status.IN_PROGRESS:
            raise ValidationError("This submission has already been submitted.")
        if not submission.response_text.strip() and not submission.attachments.exists():
            raise ValidationError("Add a written response or attach a file before submitting.")

        submission.status = Submission.Status.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save(update_fields=("status", "submitted_at", "updated_at"))
        return Response(SubmissionSerializer(submission, context=self.get_serializer_context()).data)

    def perform_update(self, serializer):
        submission = self.get_object()
        if user_role(self.request.user) == "student" and submission.status != Submission.Status.IN_PROGRESS:
            raise PermissionDenied("Submitted work can no longer be changed.")
        serializer.save()


class AttachmentCreateView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = AttachmentUploadSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save()
        return Response(
            AttachmentSerializer(attachment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AttachmentDeleteView(DestroyAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AttachmentSerializer

    def get_queryset(self):
        role = user_role(self.request.user)
        attachments = Attachment.objects.select_related(
            "assignment__course", "submission", "submission__assignment__course"
        )
        if role == "instructor":
            return attachments.filter(assignment__course__instructor=self.request.user)
        if role == "student":
            return attachments.filter(
                submission__student=self.request.user,
                submission__status=Submission.Status.IN_PROGRESS,
            )
        return Attachment.objects.none()


class AttachmentDownloadView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        attachments = Attachment.objects.select_related(
            "assignment__course", "submission", "submission__assignment__course"
        )
        if role == "instructor":
            return attachments.filter(
                Q(assignment__course__instructor=self.request.user)
                | Q(submission__assignment__course__instructor=self.request.user)
            )
        if role == "student":
            return attachments.filter(
                Q(assignment__course__enrollments__student=self.request.user)
                | Q(submission__student=self.request.user)
            ).distinct()
        return Attachment.objects.none()

    def get(self, request, pk):
        attachment = self.get_queryset().filter(pk=pk).first()
        if attachment is None:
            raise PermissionDenied("You cannot access this file.")
        guessed_type, _ = mimetypes.guess_type(attachment.original_name)
        return FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
            content_type=guessed_type or "application/octet-stream",
        )
