from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AttachmentCreateView, AttachmentDeleteView, AttachmentDownloadView, SubmissionViewSet

router = DefaultRouter()
router.register("submissions", SubmissionViewSet, basename="submission")

urlpatterns = [
    path("", include(router.urls)),
    path("attachments/", AttachmentCreateView.as_view(), name="attachment-create"),
    path("attachments/<int:pk>/", AttachmentDeleteView.as_view(), name="attachment-delete"),
    path("attachments/<int:pk>/download/", AttachmentDownloadView.as_view(), name="attachment-download"),
]
