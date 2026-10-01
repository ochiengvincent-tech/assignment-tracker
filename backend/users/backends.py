from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist


class EmailOrUsernameBackend(ModelBackend):
    """Allow sign-in with either the account username or its email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        identity = kwargs.get("email") or username
        if not identity or not password:
            return None

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username__iexact=identity)
        except ObjectDoesNotExist:
            try:
                user = user_model.objects.get(email__iexact=identity)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                return None
        except MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
