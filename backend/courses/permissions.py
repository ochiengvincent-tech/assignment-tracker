from rest_framework.permissions import BasePermission


def user_role(user):
    try:
        return user.profile.role
    except AttributeError:
        return None


class IsInstructor(BasePermission):
    message = "Only instructors can perform this action."

    def has_permission(self, request, view):
        return user_role(request.user) == "instructor"


class IsStudent(BasePermission):
    message = "Only students can perform this action."

    def has_permission(self, request, view):
        return user_role(request.user) == "student"


class IsCourseMember(BasePermission):
    def has_object_permission(self, request, view, obj):
        if user_role(request.user) == "instructor":
            return obj.instructor_id == request.user.id
        return obj.enrollments.filter(student=request.user).exists()
