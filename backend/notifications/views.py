from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.permissions import user_role

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if user_role(self.request.user) != "student":
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).exclude(
            status=Notification.Status.SKIPPED
        ).select_related("assignment")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response({
            "unread_count": queryset.filter(read_at__isnull=True).count(),
            "notifications": self.get_serializer(queryset, many=True).data,
        })


class NotificationReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        if user_role(request.user) != "student":
            raise PermissionDenied("Only students can access notifications.")
        notification = Notification.objects.filter(user=request.user, pk=pk).first()
        if notification is None:
            return Response({"detail": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=("read_at",))
        return Response(NotificationSerializer(notification).data)
