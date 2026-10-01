import { expect, test } from "@playwright/test";

test("instructor posts an assignment, student submits it, and instructor grades it", async ({ browser }) => {
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_id: 1, instructor_name: "Taylor Teacher" };
  const assignment = {
    id: 12,
    course: course.id,
    course_name: course.name,
    title: "First lab",
    description: "",
    due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    category: "Lab",
    attachments: [],
  };
  let enrollment = null;
  let submission = null;
  let instructorHasCourse = false;
  let instructorHasAssignment = false;

  async function respond(route, data, status = 200) {
    const origin = route.request().headers().origin || "http://127.0.0.1:5173";
    await route.fulfill({
      status,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": origin,
        "access-control-allow-headers": "authorization,content-type",
        "access-control-allow-methods": "GET,POST,PATCH,DELETE,OPTIONS",
      },
      body: JSON.stringify(data),
    });
  }

  async function stubApi(page) {
    await page.route("**/api/v1/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      const path = url.pathname.replace("/api/v1", "");
      const method = request.method();
      const token = request.headers().authorization;
      const role = token === "Token instructor-token" ? "instructor" : "student";
      const currentUser = role === "instructor"
        ? { id: 1, username: "teacher", first_name: "Taylor", role }
        : { id: 2, username: "learner", first_name: "", role };

      if (method === "OPTIONS") return respond(route, {}, 200);
      if (path === "/auth/me/" && method === "GET") {
        return token ? respond(route, currentUser) : respond(route, { detail: "Authentication credentials were not provided." }, 401);
      }
      if (path === "/auth/login/" && method === "POST") {
        const { username } = request.postDataJSON();
        const instructorLogin = username === "teacher";
        return respond(route, {
          token: instructorLogin ? "instructor-token" : "student-token",
          user: instructorLogin
            ? { id: 1, username: "teacher", first_name: "Taylor", role: "instructor" }
            : { id: 2, username: "learner", first_name: "", role: "student" },
        });
      }
      if (path === "/auth/logout/" && method === "POST") return route.fulfill({ status: 204 });
      if (path === "/dashboard/" && method === "GET") {
        return role === "instructor"
          ? respond(route, {
              role,
              summary: { courses: instructorHasCourse ? 1 : 0, assignments: instructorHasAssignment ? 1 : 0, in_progress: 0, awaiting_review: submission?.status === "submitted" ? 1 : 0, graded: submission?.status === "graded" ? 1 : 0 },
              courses: instructorHasCourse ? [{ id: course.id, name: course.name, term: course.term, assignment_count: instructorHasAssignment ? 1 : 0, student_count: enrollment ? 1 : 0 }] : [],
              assignments: instructorHasAssignment ? [{ id: assignment.id, title: assignment.title, course_name: course.name, due_date: assignment.due_date, awaiting_review_count: submission?.status === "submitted" ? 1 : 0 }] : [],
            })
          : respond(route, {
              role,
              summary: { total_assignments: enrollment && instructorHasAssignment ? 1 : 0, upcoming: enrollment && instructorHasAssignment ? 1 : 0, overdue: 0, in_progress: submission?.status === "in_progress" ? 1 : 0, completed: submission && ["submitted", "graded"].includes(submission.status) ? 1 : 0 },
              assignments: enrollment && instructorHasAssignment ? [{ assignment_id: assignment.id, title: assignment.title, category: assignment.category, course_id: course.id, course_name: course.name, due_date: assignment.due_date, days_until_due: 7, status: submission?.status || "not_started", submission_status: submission?.status || null, submission_id: submission?.id || null, submitted_at: submission?.submitted_at || null, grade: submission?.grade || null, is_late: false }] : [],
            });
      }
      if (path === "/courses/" && method === "GET") {
        return respond(route, role === "instructor" ? (instructorHasCourse ? [course] : []) : (enrollment ? [course] : []));
      }
      if (path === "/courses/" && method === "POST") {
        instructorHasCourse = true;
        Object.assign(course, request.postDataJSON());
        return respond(route, course, 201);
      }
      if (path === "/enrollments/" && method === "GET") {
        return respond(route, enrollment ? [{ id: 1, course: course.id, student_id: 2, student_name: "learner" }] : []);
      }
      if (path === "/enrollments/" && method === "POST") {
        enrollment = { id: 1, course: course.id, student_id: 2, student_name: "learner" };
        return respond(route, enrollment, 201);
      }
      if (path === "/assignments/" && method === "GET") {
        return respond(route, instructorHasAssignment && (role === "instructor" || enrollment) ? [assignment] : []);
      }
      if (path === "/assignments/" && method === "POST") {
        instructorHasAssignment = true;
        Object.assign(assignment, request.postDataJSON());
        return respond(route, assignment, 201);
      }
      if (path === "/submissions/" && method === "GET") {
        return respond(route, submission ? [submission] : []);
      }
      if (path === "/submissions/" && method === "POST") {
        submission = {
          id: 20,
          assignment: assignment.id,
          assignment_title: assignment.title,
          student_id: 2,
          student_name: "learner",
          status: "in_progress",
          response_text: "",
          grade: null,
          submitted_at: null,
          is_late: false,
          attachments: [],
        };
        return respond(route, { assignment: assignment.id, response_text: "" }, 201);
      }
      if (path === "/submissions/20/" && method === "PATCH") {
        const payload = request.postDataJSON();
        if (role === "instructor") {
          submission.grade = payload.grade;
          submission.status = "graded";
          return respond(route, { grade: String(payload.grade) });
        }
        submission.response_text = payload.response_text;
        return respond(route, { response_text: submission.response_text });
      }
      if (path === "/submissions/20/submit/" && method === "POST") {
        submission.status = "submitted";
        submission.submitted_at = new Date().toISOString();
        return respond(route, submission);
      }

      return respond(route, { detail: `Unhandled test API request: ${method} ${path}` }, 404);
    });
  }

  const instructorContext = await browser.newContext();
  const instructorPage = await instructorContext.newPage();
  await stubApi(instructorPage);
  await instructorPage.goto("/");
  await instructorPage.getByLabel("Username or email").fill("teacher");
  await instructorPage.getByLabel("Password").fill("test-password");
  await instructorPage.getByRole("button", { name: "Sign in" }).click();
  await instructorPage.getByLabel("Course name").fill(course.name);
  await instructorPage.getByLabel("Term").fill(course.term);
  await instructorPage.getByRole("button", { name: "Create course" }).click();
  await expect(instructorPage.getByRole("heading", { name: course.name })).toBeVisible();
  await instructorPage.getByRole("button", { name: "Add assignment" }).click();
  await instructorPage.getByLabel("Title").fill(assignment.title);
  await instructorPage.getByLabel("Due date and time").fill("2026-10-30T10:00");
  await instructorPage.getByRole("button", { name: "Add assignment", exact: true }).click();
  await expect(instructorPage.getByRole("heading", { name: assignment.title })).toBeVisible();

  const studentContext = await browser.newContext();
  const studentPage = await studentContext.newPage();
  await stubApi(studentPage);
  await studentPage.goto("/");
  await studentPage.getByLabel("Username or email").fill("learner");
  await studentPage.getByLabel("Password").fill("test-password");
  await studentPage.getByRole("button", { name: "Sign in" }).click();
  await studentPage.getByLabel("Join a course using its ID").fill(String(course.id));
  await studentPage.getByRole("button", { name: "Join course" }).click();
  await expect(studentPage.getByRole("heading", { name: assignment.title })).toBeVisible();
  await studentPage.getByRole("button", { name: "Start submission" }).click();
  await studentPage.getByLabel("Your response").fill("My completed work");
  await studentPage.getByRole("button", { name: "Submit work" }).click();
  await expect(studentPage.getByText("Your work has been submitted.")).toBeVisible();

  await instructorPage.reload();
  await instructorPage.getByLabel("Grade (%)").fill("88");
  await instructorPage.getByRole("button", { name: "Save grade" }).click();
  await expect(instructorPage.getByText("Grade saved for learner.")).toBeVisible();
  await studentPage.reload();
  await expect(studentPage.getByText("Grade: 88%")).toBeVisible();

  await studentContext.close();
  await instructorContext.close();
});