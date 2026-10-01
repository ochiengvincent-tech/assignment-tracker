from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserProfile

admin.site.unregister(get_user_model())


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(get_user_model())
class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "email", "get_role", "is_staff", "is_active")

    @admin.display(description="Role")
    def get_role(self, user):
        try:
            return user.profile.get_role_display()
        except UserProfile.DoesNotExist:
            return "Student"
