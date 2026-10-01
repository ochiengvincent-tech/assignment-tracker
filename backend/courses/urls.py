from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CourseViewSet, EnrollmentListCreateView

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="course")

urlpatterns = [
    path("", include(router.urls)),
    path("enrollments/", EnrollmentListCreateView.as_view(), name="enrollment-list-create"),
]
