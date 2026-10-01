from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from .models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = fields

    role = serializers.SerializerMethodField()

    def get_role(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile.role


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request=request, username=attrs["username"], password=attrs["password"])
        if user is None:
            raise AuthenticationFailed("Invalid username/email or password.")
        attrs["user"] = user
        return attrs
