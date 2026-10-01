from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source="assignment.title", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = (
            "id", "assignment", "assignment_title", "type", "status", "title", "message",
            "scheduled_for", "sent_at", "read_at", "created_at",
        )
