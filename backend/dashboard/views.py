from django.db.models import Count, Q
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assignments.models import Assignment
from courses.models import Course
from courses.permissions import user_role
from submissions.models import Submission


class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        role = user_role(request.user)
        if role == "student":
            return Response(self.student_dashboard(request.user))
        if role == "instructor":
            return Response(self.instructor_dashboard(request.user))
        raise PermissionDenied("Your account does not have a student or instructor role.")

    def student_dashboard(self, student):
        now = timezone.now()
        assignments = (
            Assignment.objects.filter(course__enrollments__student=student)
            .select_related("course")
            .prefetch_related(
                Prefetch("submissions", queryset=Submission.objects.filter(student=student))
            )
            .distinct()
        )
        items = []
        for assignment in assignments:
            submission = next(iter(assignment.submissions.all()), None)
            submission_status = submission.status if submission else None
            due_date = assignment.due_date
            if submission_status in (Submission.Status.SUBMITTED, Submission.Status.GRADED):
                progress_status = submission_status
            elif due_date < now:
                progress_status = "overdue"
            elif submission_status == Submission.Status.IN_PROGRESS:
                progress_status = "in_progress"
            else:
                progress_status = "not_started"

            days_until_due = (timezone.localtime(due_date).date() - timezone.localdate()).days
            items.append(
                {
                    "assignment_id": assignment.id,
                    "title": assignment.title,
                    "description": assignment.description,
                    "category": assignment.category,
                    "course_id": assignment.course_id,
                    "course_name": assignment.course.name,
                    "due_date": due_date.isoformat(),
                    "days_until_due": days_until_due,
                    "status": progress_status,
                    "submission_status": submission_status,
                    "submission_id": submission.id if submission else None,
                    "submitted_at": submission.submitted_at.isoformat() if submission and submission.submitted_at else None,
                    "grade": str(submission.grade) if submission and submission.grade is not None else None,
                    "is_late": bool(submission and submission.submitted_at and submission.submitted_at > due_date),
                }
            )

        summary = {
            "total_assignments": len(items),
            "upcoming": sum(item["status"] in ("not_started", "in_progress") for item in items),
            "overdue": sum(item["status"] == "overdue" for item in items),
            "in_progress": sum(item["submission_status"] == Submission.Status.IN_PROGRESS for item in items),
            "completed": sum(item["status"] in (Submission.Status.SUBMITTED, Submission.Status.GRADED) for item in items),
        }
        return {"role": "student", "summary": summary, "assignments": items}

    def instructor_dashboard(self, instructor):
        assignments = list(
            Assignment.objects.filter(course__instructor=instructor)
            .values("id", "title", "category", "due_date", "course_id", "course__name")
            .annotate(
                submission_count=Count("submissions", distinct=True),
                in_progress_count=Count(
                    "submissions",
                    filter=Q(submissions__status=Submission.Status.IN_PROGRESS),
                    distinct=True,
                ),
                awaiting_review_count=Count(
                    "submissions",
                    filter=Q(submissions__status=Submission.Status.SUBMITTED),
                    distinct=True,
                ),
                graded_count=Count(
                    "submissions",
                    filter=Q(submissions__status=Submission.Status.GRADED),
                    distinct=True,
                ),
            )
            .order_by("due_date", "id")
        )
        courses = list(
            Course.objects.filter(instructor=instructor)
            .values("id", "name", "term")
            .annotate(
                assignment_count=Count("assignments", distinct=True),
                student_count=Count("enrollments", distinct=True),
            )
            .order_by("term", "name", "id")
        )
        summary = {
            "courses": len(courses),
            "assignments": len(assignments),
            "in_progress": sum(item["in_progress_count"] for item in assignments),
            "awaiting_review": sum(item["awaiting_review_count"] for item in assignments),
            "graded": sum(item["graded_count"] for item in assignments),
        }
        for item in assignments:
            item["course_name"] = item.pop("course__name")
            item["due_date"] = item["due_date"].isoformat()
        return {"role": "instructor", "summary": summary, "courses": courses, "assignments": assignments}
