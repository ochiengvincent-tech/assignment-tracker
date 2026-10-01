from django.contrib import admin
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.urls import include, path


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "service": "student-assignment-tracker-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="api-health"),
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/", include("courses.urls")),
    path("api/v1/", include("assignments.urls")),
    path("api/v1/", include("submissions.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),
    path("api/v1/", include("notifications.urls")),
]
