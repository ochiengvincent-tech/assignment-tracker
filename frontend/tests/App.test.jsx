import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../src/App.jsx";
import * as api from "../src/api.js";

jest.mock("../src/api.js", () => ({
  createSubmission: jest.fn(),
  createAssignment: jest.fn(),
  createCourse: jest.fn(),
  deleteAttachment: jest.fn(),
  deleteAssignment: jest.fn(),
  deleteCourse: jest.fn(),
  enrollInCourse: jest.fn(),
  getAssignments: jest.fn(),
  getCourses: jest.fn(),
  getCurrentUser: jest.fn(),
  getDashboard: jest.fn(),
  getEnrollments: jest.fn(),
  getSubmissions: jest.fn(),
  gradeSubmission: jest.fn(),
  downloadAttachment: jest.fn(),
  signIn: jest.fn(),
  signOut: jest.fn(),
  submitSubmission: jest.fn(),
  updateSubmission: jest.fn(),
  updateAssignment: jest.fn(),
  updateCourse: jest.fn(),
  uploadAttachment: jest.fn(),
}));

const student = {
  id: 1,
  username: "sam",
  first_name: "Sam",
  role: "student",
};

function configureWorkspace(role = "student") {
  api.getCourses.mockResolvedValue([]);
  api.getEnrollments.mockResolvedValue([]);
  api.getAssignments.mockResolvedValue([]);
  api.getSubmissions.mockResolvedValue([]);
  api.getDashboard.mockResolvedValue(
    role === "instructor"
      ? {
          role,
          summary: { courses: 0, assignments: 0, in_progress: 0, awaiting_review: 0, graded: 0 },
          courses: [],
          assignments: [],
        }
      : {
          role,
          summary: { total_assignments: 0, upcoming: 0, overdue: 0, in_progress: 0, completed: 0 },
          assignments: [],
        },
  );
}

beforeEach(() => {
  jest.resetAllMocks();
  localStorage.clear();
  api.getCurrentUser.mockRejectedValue(new Error("No active session"));
  configureWorkspace();
});

afterEach(() => {
  jest.restoreAllMocks();
});

test("shows the sign-in form when there is no saved session", async () => {
  render(<App />);

  expect(await screen.findByLabelText("Username or email")).toBeInTheDocument();
  expect(screen.getByLabelText("Password")).toBeInTheDocument();
});

test("shows an authentication error when sign-in fails", async () => {
  const user = userEvent.setup();
  api.signIn.mockRejectedValue(new Error("Invalid username/email or password."));
  render(<App />);

  await user.type(await screen.findByLabelText("Username or email"), "sam");
  await user.type(screen.getByLabelText("Password"), "wrong");
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username/email or password.");
});

test("signs in and renders the student workspace", async () => {
  const user = userEvent.setup();
  api.signIn.mockResolvedValue(student);
  render(<App />);

  await user.type(await screen.findByLabelText("Username or email"), "sam@example.com");
  await user.type(screen.getByLabelText("Password"), "secret");
  await user.click(screen.getByRole("button", { name: "Sign in" }));

  expect(api.signIn).toHaveBeenCalledWith("sam@example.com", "secret");
  expect(await screen.findByText("Welcome, Sam.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Assignment dashboard" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Join course" })).toBeInTheDocument();
});

test("sign-out returns the user to the login form", async () => {
  const user = userEvent.setup();
  api.getCurrentUser.mockResolvedValue(student);
  api.signOut.mockResolvedValue(undefined);
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Sign out" }));

  expect(api.signOut).toHaveBeenCalled();
  expect(await screen.findByLabelText("Username or email")).toBeInTheDocument();
});

test("an instructor can create a course", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses.mockResolvedValueOnce([]).mockResolvedValue([course]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 0, assignments: 0, in_progress: 0, awaiting_review: 0, graded: 0 },
    courses: [],
    assignments: [],
  });
  api.createCourse.mockResolvedValue(course);
  render(<App />);

  await user.type(await screen.findByLabelText("Course name"), "Computing");
  await user.type(screen.getByLabelText("Term"), "Fall 2026");
  await user.click(screen.getByRole("button", { name: "Create course" }));

  expect(api.createCourse).toHaveBeenCalledWith({ name: "Computing", term: "Fall 2026" });
  expect(await screen.findByText("Course created.")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Computing" })).toBeInTheDocument();
});

test("an instructor can edit and delete an empty course", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  const updatedCourse = { ...course, name: "Computer Science" };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses
    .mockResolvedValueOnce([course])
    .mockResolvedValueOnce([updatedCourse])
    .mockResolvedValueOnce([]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 1, assignments: 0, in_progress: 0, awaiting_review: 0, graded: 0 },
    courses: [{ id: course.id, name: course.name, term: course.term, assignment_count: 0, student_count: 0 }],
    assignments: [],
  });
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);
  render(<App />);

  const courseHeading = await screen.findByRole("heading", { name: course.name });
  const courseCard = courseHeading.closest(".course-card");
  await user.click(within(courseCard).getByRole("button", { name: "Edit", exact: true }));
  await user.clear(within(courseCard).getByLabelText("Course name"));
  await user.type(within(courseCard).getByLabelText("Course name"), updatedCourse.name);
  await user.click(within(courseCard).getByRole("button", { name: "Save", exact: true }));
  expect(api.updateCourse).toHaveBeenCalledWith(course.id, { name: updatedCourse.name, term: course.term });
  expect(await screen.findByText("Course updated.")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Delete", exact: true }));
  expect(confirm).toHaveBeenCalled();
  expect(await screen.findByText("You have not created any courses yet.")).toBeInTheDocument();
  expect(api.deleteCourse).toHaveBeenCalledWith(course.id);
});

test("a student can join a course by its ID", async () => {
  const user = userEvent.setup();
  api.getCurrentUser.mockResolvedValue(student);
  api.enrollInCourse.mockResolvedValue({});
  render(<App />);

  await user.type(await screen.findByLabelText("Join a course using its ID"), "41");
  await user.click(screen.getByRole("button", { name: "Join course" }));

  expect(api.enrollInCourse).toHaveBeenCalledWith("41");
  expect(await screen.findByText("You joined the course.")).toBeInTheDocument();
});

test("a student can filter the dashboard timeline by assignment status", async () => {
  const user = userEvent.setup();
  api.getCurrentUser.mockResolvedValue(student);
  api.getDashboard.mockResolvedValue({
    role: "student",
    summary: { total_assignments: 2, upcoming: 1, overdue: 1, in_progress: 0, completed: 0 },
    assignments: [
      { assignment_id: 1, title: "Upcoming lab", course_name: "Computing", due_date: "2026-10-10T10:00:00Z", days_until_due: 9, status: "not_started", submission_status: null, is_late: false },
      { assignment_id: 2, title: "Missed quiz", course_name: "Computing", due_date: "2026-09-20T10:00:00Z", days_until_due: -11, status: "overdue", submission_status: null, is_late: false },
    ],
  });
  render(<App />);

  expect(await screen.findByText("Upcoming lab")).toBeInTheDocument();
  expect(screen.getByText("Missed quiz")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Overdue" }));

  expect(screen.getByText("Missed quiz")).toBeInTheDocument();
  expect(screen.queryByText("Upcoming lab")).not.toBeInTheDocument();
});

test("an instructor can post an assignment in a course", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  const assignment = {
    id: 12,
    course: course.id,
    title: "First lab",
    description: "",
    due_date: "2026-10-30T10:00:00Z",
    category: "Lab",
    attachments: [],
  };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses.mockResolvedValue([course]);
  api.getAssignments.mockResolvedValueOnce([]).mockResolvedValue([assignment]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 1, assignments: 0, in_progress: 0, awaiting_review: 0, graded: 0 },
    courses: [{ id: course.id, name: course.name, term: course.term, assignment_count: 0, student_count: 0 }],
    assignments: [],
  });
  api.createAssignment.mockResolvedValue(assignment);
  api.uploadAttachment.mockResolvedValue({ id: 14, original_name: "lab-guide.pdf" });
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Add assignment" }));
  await user.type(screen.getByLabelText("Title"), "First lab");
  await user.type(screen.getByLabelText("Due date and time"), "2026-10-30T10:00");
  const file = new File(["Lab instructions"], "lab-guide.pdf", { type: "application/pdf" });
  const attachmentInput = screen.getByLabelText("Assignment file (optional)");
  await user.upload(attachmentInput, file);
  expect(attachmentInput.files[0]).toBe(file);
  await user.click(screen.getByRole("button", { name: "Add assignment", exact: true }));

  expect(api.createAssignment).toHaveBeenCalledWith(
    expect.objectContaining({ course: course.id, title: "First lab", category: "" }),
  );
  expect(api.uploadAttachment).toHaveBeenCalledWith({ assignment_id: assignment.id }, file);
  expect(await screen.findByText("Assignment added.")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "First lab" })).toBeInTheDocument();
});

test("an instructor can edit and delete an assignment", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  const assignment = {
    id: 12,
    course: course.id,
    title: "First lab",
    description: "",
    due_date: "2026-10-30T10:00:00Z",
    category: "Lab",
    attachments: [],
  };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses.mockResolvedValue([course]);
  api.getAssignments.mockResolvedValueOnce([assignment]).mockResolvedValueOnce([{ ...assignment, title: "Revised lab" }]).mockResolvedValue([]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 1, assignments: 1, in_progress: 0, awaiting_review: 0, graded: 0 },
    courses: [{ id: course.id, name: course.name, term: course.term, assignment_count: 1, student_count: 0 }],
    assignments: [{ id: assignment.id, title: assignment.title, course_name: course.name, due_date: assignment.due_date, awaiting_review_count: 0 }],
  });
  const confirm = jest.spyOn(window, "confirm").mockReturnValue(true);
  render(<App />);

  const assignmentHeading = await screen.findByRole("heading", { name: assignment.title });
  const assignmentCard = assignmentHeading.closest(".assignment-card");
  await user.click(within(assignmentCard).getByRole("button", { name: "Edit", exact: true }));
  await user.clear(within(assignmentCard).getByLabelText("Title"));
  await user.type(within(assignmentCard).getByLabelText("Title"), "Revised lab");
  await user.click(within(assignmentCard).getByRole("button", { name: "Save changes" }));

  expect(api.updateAssignment).toHaveBeenCalledWith(
    assignment.id,
    expect.objectContaining({ title: "Revised lab", course: course.id }),
  );
  expect(await screen.findByText("Assignment updated.")).toBeInTheDocument();

  await user.click(within(assignmentCard).getByRole("button", { name: "Delete", exact: true }));
  expect(confirm).toHaveBeenCalled();
  expect(api.deleteAssignment).toHaveBeenCalledWith(assignment.id);
  expect(await screen.findByText("No assignments have been posted for this course.")).toBeInTheDocument();
});

test("an instructor can download and remove an assignment attachment", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  const attachment = { id: 33, original_name: "lab-guide.pdf", mime_type: "application/pdf", size_bytes: 2048, download_url: "/download/" };
  const assignment = {
    id: 12,
    course: course.id,
    title: "First lab",
    description: "",
    due_date: "2026-10-30T10:00:00Z",
    category: "Lab",
    attachments: [attachment],
  };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses.mockResolvedValue([course]);
  api.getAssignments.mockResolvedValueOnce([assignment]).mockResolvedValueOnce([{ ...assignment, attachments: [] }]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 1, assignments: 1, in_progress: 0, awaiting_review: 0, graded: 0 },
    courses: [{ id: course.id, name: course.name, term: course.term, assignment_count: 1, student_count: 0 }],
    assignments: [{ id: assignment.id, title: assignment.title, course_name: course.name, due_date: assignment.due_date, awaiting_review_count: 0 }],
  });
  api.downloadAttachment.mockResolvedValue(undefined);
  api.deleteAttachment.mockResolvedValue(undefined);
  render(<App />);

  await user.click(await screen.findByRole("button", { name: attachment.original_name }));
  expect(api.downloadAttachment).toHaveBeenCalledWith(attachment);
  await user.click(screen.getByRole("button", { name: "Remove" }));
  expect(api.deleteAttachment).toHaveBeenCalledWith(attachment.id);
  expect(await screen.queryByRole("button", { name: attachment.original_name })).not.toBeInTheDocument();
});

test("a student can save a draft and submit written work", async () => {
  const user = userEvent.setup();
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Teacher" };
  const assignment = {
    id: 12,
    course: course.id,
    title: "First lab",
    description: "",
    due_date: "2026-10-30T10:00:00Z",
    category: "Lab",
    attachments: [],
  };
  const draft = {
    id: 20,
    assignment: assignment.id,
    assignment_title: assignment.title,
    student_name: "Sam",
    status: "in_progress",
    response_text: "",
    grade: null,
    submitted_at: null,
    is_late: false,
    attachments: [],
  };
  const submitted = { ...draft, status: "submitted", response_text: "My answer", submitted_at: "2026-10-01T10:00:00Z" };
  api.getCurrentUser.mockResolvedValue(student);
  api.getCourses.mockResolvedValue([course]);
  api.getEnrollments.mockResolvedValue([{ id: 1, course: course.id, student_name: "Sam" }]);
  api.getAssignments.mockResolvedValue([assignment]);
  api.getSubmissions.mockResolvedValueOnce([]).mockResolvedValueOnce([draft]).mockResolvedValueOnce([submitted]);
  api.getDashboard.mockResolvedValue({
    role: "student",
    summary: { total_assignments: 1, upcoming: 1, overdue: 0, in_progress: 0, completed: 0 },
    assignments: [{ assignment_id: assignment.id, title: assignment.title, course_name: course.name, due_date: assignment.due_date, status: "not_started", submission_status: null, days_until_due: 20 }],
  });
  api.createSubmission.mockResolvedValue({});
  api.updateSubmission.mockResolvedValue({});
  api.submitSubmission.mockResolvedValue(submitted);
  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Start submission" }));
  const responseField = await screen.findByLabelText("Your response");
  await user.type(responseField, "My answer");
  const file = new File(["Supporting notes"], "notes.txt", { type: "text/plain" });
  await user.upload(screen.getByLabelText("Attach a file (optional)"), file);
  await user.click(screen.getByRole("button", { name: "Submit work" }));

  expect(api.createSubmission).toHaveBeenCalledWith(assignment.id);
  expect(api.updateSubmission).toHaveBeenCalledWith(draft.id, "My answer");
  expect(api.uploadAttachment).toHaveBeenCalledWith({ submission_id: draft.id }, file);
  expect(api.submitSubmission).toHaveBeenCalledWith(draft.id);
  expect(await screen.findByText("Your work has been submitted.")).toBeInTheDocument();
});

test("an instructor can grade submitted student work", async () => {
  const user = userEvent.setup();
  const instructor = { ...student, role: "instructor" };
  const course = { id: 7, name: "Computing", term: "Fall 2026", instructor_name: "Sam" };
  const assignment = {
    id: 12,
    course: course.id,
    title: "First lab",
    description: "",
    due_date: "2026-10-30T10:00:00Z",
    category: "Lab",
    attachments: [],
  };
  const submitted = {
    id: 20,
    assignment: assignment.id,
    assignment_title: assignment.title,
    student_name: "Learner",
    status: "submitted",
    response_text: "My answer",
    grade: null,
    submitted_at: "2026-10-01T10:00:00Z",
    is_late: false,
    attachments: [],
  };
  api.getCurrentUser.mockResolvedValue(instructor);
  api.getCourses.mockResolvedValue([course]);
  api.getAssignments.mockResolvedValue([assignment]);
  api.getSubmissions.mockResolvedValueOnce([submitted]).mockResolvedValue([{ ...submitted, status: "graded", grade: "88.00" }]);
  api.getDashboard.mockResolvedValue({
    role: "instructor",
    summary: { courses: 1, assignments: 1, in_progress: 0, awaiting_review: 1, graded: 0 },
    courses: [{ id: course.id, name: course.name, term: course.term, assignment_count: 1, student_count: 1 }],
    assignments: [{ id: assignment.id, title: assignment.title, course_name: course.name, due_date: assignment.due_date, awaiting_review_count: 1 }],
  });
  api.gradeSubmission.mockResolvedValue({ grade: "88.00" });
  render(<App />);

  await user.type(await screen.findByLabelText("Grade (%)"), "88");
  await user.type(screen.getByLabelText("Feedback for student"), "Clear reasoning.");
  await user.click(screen.getByRole("button", { name: "Save grade" }));

  expect(api.gradeSubmission).toHaveBeenCalledWith(submitted.id, "88", "Clear reasoning.");
  expect(await screen.findByText("Grade saved for Learner.")).toBeInTheDocument();
});