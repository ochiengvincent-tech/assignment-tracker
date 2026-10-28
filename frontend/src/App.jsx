import React, { useEffect, useRef, useState } from "react";
import {
  createSubmission,
  createAssignment,
  createCourse,
  deleteAttachment,
  deleteAssignment,
  deleteCourse,
  enrollInCourse,
  getAssignments,
  getCourses,
  getCurrentUser,
  getDashboard,
  getNotifications,
  getEnrollments,
  getSubmissions,
  gradeSubmission,
  downloadAttachment,
  signIn,
  signOut,
  markNotificationRead,
  submitSubmission,
  updateSubmission,
  updateAssignment,
  updateCourse,
  uploadAttachment,
} from "./api.js";

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [pathname, setPathname] = useState(() => window.location.pathname);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => localStorage.removeItem("assignment-tracker-token"))
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(() => {
    function handlePopState() {
      setPathname(window.location.pathname);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (checkingSession) return;
    const expectedPath = user ? "/dashboard" : "/login";
    if (pathname !== expectedPath) {
      window.history.replaceState({}, "", expectedPath);
      setPathname(expectedPath);
    }
  }, [checkingSession, pathname, user]);

  function navigate(path) {
    if (window.location.pathname !== path) window.history.pushState({}, "", path);
    setPathname(path);
  }

  async function handleSignIn(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      setUser(await signIn(form.get("username"), form.get("password")));
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Could not sign in. Check that the API is running.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    try {
      await signOut();
    } finally {
      setUser(null);
      navigate("/login");
    }
  }

  if (checkingSession) {
    return <main className="page"><p role="status">Checking your session…</p></main>;
  }

  const displayName = user?.first_name || user?.username;

  return (
    <main className={`page ${user ? "page-authenticated" : "page-login"}`}>
      <div className="app-shell">
        <header className="app-header">
          <a className="brand-lockup" href={user ? "/dashboard" : "/login"} aria-label="Assignment Tracker home">
            <span className="brand-mark" aria-hidden="true">at</span>
            <span className="brand-copy"><strong>Classwork</strong><span>Assignment tracker</span></span>
          </a>
          {user ? (
            <div className="account-menu">
              <span className="account-avatar" aria-hidden="true">{displayName?.slice(0, 1).toUpperCase()}</span>
              <span className="account-copy"><strong>{displayName}</strong><span>{user.role}</span></span>
              <button className="button button-secondary sign-out-button" type="button" onClick={handleSignOut}>Sign out</button>
            </div>
          ) : <p className="header-note">A calmer way to keep coursework moving</p>}
        </header>

        <section className={`welcome${user ? " welcome-wide" : ""}`}>
          {user ? (
            <>
              <div className="workspace-hero">
                <div>
                  <p className="eyebrow">{user.role} workspace</p>
                  <h1>A clearer view of coursework.</h1>
                  <p className="intro">Welcome, {displayName}.</p>
                </div>
                <div className="hero-orbit" aria-hidden="true"><span>01</span><i /><b /></div>
              </div>
              <CourseWorkspace key={user.id} user={user} />
            </>
          ) : (
            <div className="login-layout">
              <div className="login-story">
                <p className="eyebrow">CIS 260 project</p>
                <h1>Student Assignment Tracker</h1>
                <p className="intro">Courses, deadlines, submissions, and feedback together in one clear workspace.</p>
                <div className="login-preview" aria-hidden="true">
                  <div className="preview-top"><span /><span /><span /></div>
                  <div className="preview-label">YOUR WEEK</div>
                  <div className="preview-task"><span className="preview-check">✓</span><span><strong>Keep work on track</strong><small>See what is due and what needs attention</small></span><i /></div>
                  <div className="preview-task preview-task-muted"><span className="preview-dot" /><span><strong>Stay in the loop</strong><small>Find grades and instructor feedback</small></span></div>
                </div>
              </div>
              <div className="login-card">
                <div className="login-card-heading">
                  <span className="login-icon" aria-hidden="true">↗</span>
                  <p className="eyebrow">Your learning space</p>
                  <h2>Welcome back</h2>
                  <p>Sign in with your account to continue.</p>
                </div>
                <form className="sign-in-form" onSubmit={handleSignIn}>
                  <label htmlFor="username">Username or email</label>
                  <input id="username" name="username" autoComplete="username" placeholder="Enter username or email" required />
                  <label htmlFor="password">Password</label>
                  <input id="password" name="password" type="password" autoComplete="current-password" placeholder="Enter password" required />
                  {error && <p className="error" role="alert">{error}</p>}
                  <button className="button sign-in-button" type="submit" disabled={busy}>
                    {busy ? "Signing in…" : "Sign in"}<span aria-hidden="true">→</span>
                  </button>
                </form>
                <p className="login-footnote">Use the account created for you by your instructor.</p>
              </div>
            </div>
          )}
        </section>
        <footer className="app-footer"><span>Classwork</span><span>Stay organized. Keep moving.</span></footer>
      </div>
    </main>
  );
}

function CourseWorkspace({ user }) {
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingCourseId, setEditingCourseId] = useState(null);

  async function refresh() {
    const [courseList, enrollmentList, assignmentList, dashboardData] = await Promise.all([
      getCourses(),
      getEnrollments(),
      getAssignments(),
      getDashboard(),
    ]);
    setCourses(courseList);
    setEnrollments(enrollmentList);
    setAssignments(assignmentList);
    setDashboard(dashboardData);
  }

  useEffect(() => {
    refresh()
      .catch((err) => setError(err.message || "Could not load courses."))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateCourse(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await createCourse({ name: form.get("name"), term: form.get("term") });
      formElement.reset();
      await refresh();
      setNotice("Course created.");
    } catch (err) {
      setError(err.message || "Could not create the course.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEnroll(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await enrollInCourse(form.get("course_id"));
      formElement.reset();
      await refresh();
      setNotice("You joined the course.");
    } catch (err) {
      setError(err.message || "Could not join the course.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateCourse(event, courseId) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    setBusy(true);
    setError("");
    try {
      await updateCourse(courseId, { name: form.get("name"), term: form.get("term") });
      setEditingCourseId(null);
      await refresh();
      setNotice("Course updated.");
    } catch (err) {
      setError(err.message || "Could not update the course.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteCourse(course) {
    if (!window.confirm(`Delete ${course.name}? Courses with assignments or enrolled students cannot be deleted.`)) return;
    setBusy(true);
    setError("");
    try {
      await deleteCourse(course.id);
      await refresh();
      setNotice("Course deleted.");
    } catch (err) {
      setError(err.message || "Could not delete the course.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="course-workspace" aria-labelledby="courses-heading">
      {dashboard && <DashboardOverview dashboard={dashboard} user={user} />}
      {user.role === "student" && <NotificationCenter />}
      <div className="section-heading">
        <div>
          <p className="eyebrow">{user.role}</p>
          <h2 id="courses-heading">Your courses</h2>
        </div>
        <span className="count-badge">{courses.length}</span>
      </div>

      {user.role === "instructor" ? (
        <form className="course-form" onSubmit={handleCreateCourse}>
          <h3>Create a course</h3>
          <label htmlFor="course-name">Course name</label>
          <input id="course-name" name="name" maxLength="200" placeholder="e.g. Introduction to Computing" required />
          <label htmlFor="course-term">Term</label>
          <input id="course-term" name="term" maxLength="50" placeholder="e.g. Fall 2026" required />
          <button className="button" type="submit" disabled={busy}>{busy ? "Saving…" : "Create course"}</button>
        </form>
      ) : (
        <form className="join-form" onSubmit={handleEnroll}>
          <label htmlFor="course-id">Join a course using its ID</label>
          <div className="join-controls">
            <input id="course-id" name="course_id" type="number" min="1" placeholder="Course ID" required />
            <button className="button" type="submit" disabled={busy}>{busy ? "Joining…" : "Join course"}</button>
          </div>
          <p className="hint">Ask your instructor for the course ID.</p>
        </form>
      )}

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {loading ? <p role="status">Loading courses…</p> : courses.length === 0 ? (
        <p className="empty-state">{user.role === "instructor" ? "You have not created any courses yet." : "You have not joined any courses yet."}</p>
      ) : (
        <div className="course-list">
          {courses.map((course) => {
            const students = enrollments.filter((enrollment) => enrollment.course === course.id);
            return (
              <article className="course-card" key={course.id}>
                <div className="course-card-top">
                  <div>
                    <h3>{course.name}</h3>
                    <p>{course.term}</p>
                  </div>
                  <span className="course-id">ID {course.id}</span>
                </div>
                {user.role === "instructor" ? (
                  editingCourseId === course.id ? (
                    <form className="edit-course-form" onSubmit={(event) => handleUpdateCourse(event, course.id)}>
                      <label htmlFor={`edit-name-${course.id}`}>Course name</label>
                      <input id={`edit-name-${course.id}`} name="name" maxLength="200" defaultValue={course.name} required />
                      <label htmlFor={`edit-term-${course.id}`}>Term</label>
                      <input id={`edit-term-${course.id}`} name="term" maxLength="50" defaultValue={course.term} required />
                      <div className="course-actions">
                        <button className="button" type="submit" disabled={busy}>Save</button>
                        <button className="text-button" type="button" onClick={() => setEditingCourseId(null)}>Cancel</button>
                      </div>
                    </form>
                  ) : (
                    <>
                      <div className="roster">
                        <p className="hint">{students.length} enrolled student{students.length === 1 ? "" : "s"}</p>
                        {students.length > 0 && (
                          <ul>{students.map((enrollment) => <li key={enrollment.id}>{enrollment.student_name}</li>)}</ul>
                        )}
                      </div>
                      <div className="course-actions">
                        <button className="text-button" type="button" onClick={() => setEditingCourseId(course.id)}>Edit</button>
                        <button className="text-button text-button-danger" type="button" disabled={busy} onClick={() => handleDeleteCourse(course)}>Delete</button>
                      </div>
                    </>
                  )
                ) : (
                  <p className="hint">Instructor: {course.instructor_name}</p>
                )}
                <AssignmentPanel
                  user={user}
                  course={course}
                  assignments={assignments.filter((assignment) => assignment.course === course.id)}
                  onChanged={refresh}
                />
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function NotificationCenter() {
  const [data, setData] = useState({ unread_count: 0, notifications: [] });
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const refresh = () => Promise.resolve().then(() => getNotifications())
      .then((result) => { if (active) { setData(result); setError(""); } })
      .catch((err) => { if (active) setError(err.message || "Could not load notifications."); });
    refresh();
    const timer = window.setInterval(refresh, 60000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  async function markRead(notification) {
    try {
      await markNotificationRead(notification.id);
      setData((current) => ({
        ...current,
        unread_count: Math.max(0, current.unread_count - (notification.read_at ? 0 : 1)),
        notifications: current.notifications.map((item) => item.id === notification.id
          ? { ...item, read_at: new Date().toISOString() }
          : item),
      }));
    } catch (err) {
      setError(err.message || "Could not mark notification as read.");
    }
  }

  return (
    <section className="notification-center" aria-labelledby="notifications-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Reminders</p><h2 id="notifications-heading">Notifications</h2></div>
        <span className="count-badge">{data.unread_count} unread</span>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {data.notifications.length === 0 ? <p className="empty-state">No reminders yet. Assignment reminders appear here within 24 hours of a deadline.</p> : (
        <ul className="notification-list">
          {data.notifications.map((notification) => (
            <li className={`notification-item${notification.read_at ? " is-read" : ""}`} key={notification.id}>
              <div><strong>{notification.title}</strong><p>{notification.message}</p><time dateTime={notification.created_at}>{new Date(notification.created_at).toLocaleString()}</time></div>
              {!notification.read_at && <button className="text-button" type="button" onClick={() => markRead(notification)}>Mark read</button>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DashboardOverview({ dashboard, user }) {
  if (user.role === "instructor") {
    const metrics = [
      ["Courses", dashboard.summary.courses],
      ["Assignments", dashboard.summary.assignments],
      ["Awaiting review", dashboard.summary.awaiting_review],
      ["Graded", dashboard.summary.graded],
    ];
    const assignments = [...dashboard.assignments].sort((left, right) => new Date(left.due_date) - new Date(right.due_date));

    return (
      <section className="dashboard-overview" aria-labelledby="dashboard-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Instructor overview</p><h2 id="dashboard-heading">Course activity</h2></div>
        </div>
        <div className="metric-grid">
          {metrics.map(([label, value]) => <MetricCard key={label} label={label} value={value} />)}
        </div>
        <div className="instructor-timeline">
          <h3>Assignment deadlines and review</h3>
          {assignments.length === 0 ? <p className="hint">Create a course and post an assignment to get started.</p> : (
            <ul>
              {assignments.map((assignment) => (
                <li key={assignment.id}>
                  <a href={`#assignment-${assignment.id}`}>
                    <strong>{assignment.title}</strong><span>{assignment.course_name}</span>
                  </a>
                  <span className="review-count">{assignment.awaiting_review_count} to review</span>
                  <time dateTime={assignment.due_date}>{new Date(assignment.due_date).toLocaleDateString()}</time>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    );
  }

  return <StudentDashboard assignments={dashboard.assignments} summary={dashboard.summary} />;
}

function StudentDashboard({ assignments, summary }) {
  const [filter, setFilter] = useState("all");
  const filters = [
    { id: "all", label: "All" },
    { id: "upcoming", label: "Upcoming" },
    { id: "overdue", label: "Overdue" },
    { id: "in_progress", label: "In progress" },
    { id: "completed", label: "Submitted / graded" },
  ];
  const metrics = [
    ["Total", summary.total_assignments],
    ["Upcoming", summary.upcoming],
    ["Overdue", summary.overdue],
    ["In progress", summary.in_progress],
    ["Submitted / graded", summary.completed],
  ];

  const visible = assignments.filter((item) => {
    if (filter === "all") return true;
    if (filter === "upcoming") return ["not_started", "in_progress"].includes(item.status);
    if (filter === "overdue") return item.status === "overdue";
    if (filter === "in_progress") return item.submission_status === "in_progress";
    return ["submitted", "graded"].includes(item.status);
  });
  const days = new Map();
  for (const item of visible) {
    const key = new Date(item.due_date).toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric", year: "numeric",
    });
    days.set(key, [...(days.get(key) || []), item]);
  }

  return (
    <section className="dashboard-overview" aria-labelledby="dashboard-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Student overview</p><h2 id="dashboard-heading">Assignment dashboard</h2></div>
      </div>
      <div className="metric-grid student-metrics">
        {metrics.map(([label, value]) => <MetricCard key={label} label={label} value={value} />)}
      </div>
      <div className="timeline-heading">
        <div><h3>Due date timeline</h3><p className="hint">Select an assignment to open its course and submission details.</p></div>
      </div>
      <div className="timeline-filters" aria-label="Filter assignments">
        {filters.map((option) => (
          <button
            className={`filter-button${filter === option.id ? " is-active" : ""}`}
            type="button"
            key={option.id}
            aria-pressed={filter === option.id}
            onClick={() => setFilter(option.id)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p className="empty-state">{assignments.length === 0 ? "Join a course to see its assignments here." : "No assignments match this filter."}</p>
      ) : (
        <div className="timeline-list">
          {[...days.entries()].map(([day, items]) => (
            <section className="timeline-day" key={day}>
              <h4>{day}</h4>
              <div className="timeline-day-items">
                {items.map((item) => (
                  <a className="timeline-item" href={`#assignment-${item.assignment_id}`} key={item.assignment_id}>
                    <span className={`status-pill status-${item.status}`}>{formatStatus(item.status)}</span>
                    <span className="timeline-item-main">
                      <strong>{item.title}</strong>
                      <span>{item.course_name}{item.category ? ` · ${item.category}` : ""}</span>
                    </span>
                    <span className="timeline-due">{formatDue(item)}</span>
                  </a>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}

function MetricCard({ label, value }) {
  return <div className="metric-card"><span>{label}</span><strong>{value}</strong></div>;
}

function formatStatus(status) {
  return status.replaceAll("_", " ");
}

function formatDue(item) {
  if (item.status === "overdue") return "Past due";
  if (["submitted", "graded"].includes(item.status)) return item.is_late ? "Submitted late" : "Submitted";
  if (item.days_until_due === 0) return "Due today";
  if (item.days_until_due === 1) return "Due tomorrow";
  return `Due in ${item.days_until_due} days`;
}

function AssignmentPanel({ user, course, assignments, onChanged }) {
  const [showForm, setShowForm] = useState(false);
  const [editingAssignmentId, setEditingAssignmentId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function saveAssignment(event, assignmentId = null) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const attachmentFile = form.get("attachment");
    const values = {
      course: course.id,
      title: form.get("title"),
      description: form.get("description"),
      due_date: new Date(form.get("due_date")).toISOString(),
      category: form.get("category"),
    };
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const savedAssignment = assignmentId
        ? await updateAssignment(assignmentId, values)
        : await createAssignment(values);
      if (attachmentFile?.name) {
        await uploadAttachment({ assignment_id: savedAssignment.id }, attachmentFile);
      }
      setShowForm(false);
      setEditingAssignmentId(null);
      await onChanged();
      setNotice(assignmentId ? "Assignment updated." : "Assignment added.");
    } catch (err) {
      setError(err.message || "Could not save the assignment.");
    } finally {
      setBusy(false);
    }
  }

  async function removeAssignment(assignment) {
    if (!window.confirm(`Delete ${assignment.title}?`)) return;
    setBusy(true);
    setError("");
    try {
      await deleteAssignment(assignment.id);
      await onChanged();
      setNotice("Assignment deleted.");
    } catch (err) {
      setError(err.message || "Could not delete the assignment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="assignment-panel" aria-label={`Assignments for ${course.name}`}>
      <div className="assignment-panel-heading">
        <h4>Assignments</h4>
        {user.role === "instructor" && (
          <button className="text-button" type="button" onClick={() => { setShowForm(!showForm); setEditingAssignmentId(null); }}>
            {showForm ? "Cancel" : "Add assignment"}
          </button>
        )}
      </div>

      {showForm && user.role === "instructor" && (
        <AssignmentForm onSubmit={(event) => saveAssignment(event)} busy={busy} submitLabel="Add assignment" />
      )}

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {assignments.length === 0 ? (
        <p className="hint">No assignments have been posted for this course.</p>
      ) : (
        <div className="assignment-list">
          {assignments.map((assignment) => (
            <article className="assignment-card" id={`assignment-${assignment.id}`} key={assignment.id}>
              {editingAssignmentId === assignment.id ? (
                <AssignmentForm
                  assignment={assignment}
                  onSubmit={(event) => saveAssignment(event, assignment.id)}
                  busy={busy}
                  submitLabel="Save changes"
                />
              ) : (
                <>
                  <div className="assignment-title-row">
                    <h5>{assignment.title}</h5>
                    {assignment.category && <span className="category-tag">{assignment.category}</span>}
                  </div>
                  <p className="due-date">Due {new Date(assignment.due_date).toLocaleString()}</p>
                  {assignment.description && <p className="assignment-description">{assignment.description}</p>}
                  <AttachmentList
                    attachments={assignment.attachments}
                    canDelete={user.role === "instructor"}
                    onDelete={deleteAttachment}
                    onChange={onChanged}
                  />
                  {user.role === "instructor" && (
                    <div className="course-actions">
                      <button className="text-button" type="button" onClick={() => setEditingAssignmentId(assignment.id)}>Edit</button>
                      <button className="text-button text-button-danger" type="button" disabled={busy} onClick={() => removeAssignment(assignment)}>Delete</button>
                    </div>
                  )}
                </>
              )}
              {editingAssignmentId !== assignment.id && (
                <SubmissionPanel user={user} assignment={assignment} />
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function AssignmentForm({ assignment, onSubmit, busy, submitLabel }) {
  return (
    <form className="assignment-form" onSubmit={onSubmit}>
      <label>Title<input name="title" maxLength="200" defaultValue={assignment?.title || ""} required /></label>
      <label>Description<textarea name="description" rows="3" defaultValue={assignment?.description || ""} /></label>
      <label>Due date and time<input name="due_date" type="datetime-local" defaultValue={assignment ? toLocalDateTime(assignment.due_date) : ""} required /></label>
      <label>Category (optional)<input name="category" maxLength="80" defaultValue={assignment?.category || ""} placeholder="e.g. Homework" /></label>
      <label>Assignment file (optional)<input name="attachment" type="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png" /></label>
      <div className="course-actions">
        <button className="button" type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}

function AttachmentList({ attachments = [], canDelete, onDelete, onChange }) {
  const [error, setError] = useState("");
  if (attachments.length === 0) return null;

  async function handleDownload(attachment) {
    setError("");
    try {
      await downloadAttachment(attachment);
    } catch (err) {
      setError(err.message || "Could not download this file.");
    }
  }

  async function handleDelete(attachment) {
    try {
      await onDelete(attachment.id);
      await onChange();
    } catch (err) {
      setError(err.message || "Could not remove this file.");
    }
  }

  return (
    <div className="attachment-list">
      <p className="hint">Files</p>
      {error && <p className="error" role="alert">{error}</p>}
      <ul>
        {attachments.map((attachment) => (
          <li key={attachment.id}>
            <button className="text-button" type="button" onClick={() => handleDownload(attachment)}>
              {attachment.original_name}
            </button>
            <span className="file-size">{formatFileSize(attachment.size_bytes)}</span>
            {canDelete && <button className="text-button text-button-danger" type="button" onClick={() => handleDelete(attachment)}>Remove</button>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SubmissionPanel({ user, assignment }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const draftForm = useRef(null);

  async function refresh() {
    setSubmissions(await getSubmissions(assignment.id));
  }

  useEffect(() => {
    refresh()
      .catch((err) => setError(err.message || "Could not load submissions."))
      .finally(() => setLoading(false));
  }, [assignment.id]);

  async function startSubmission() {
    setBusy(true);
    setError("");
    try {
      await createSubmission(assignment.id);
      await refresh();
      setNotice("Draft started.");
    } catch (err) {
      setError(err.message || "Could not start a submission.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(submission, shouldSubmit) {
    const form = new FormData(draftForm.current);
    const file = form.get("submission_file");
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await updateSubmission(submission.id, form.get("response_text"));
      if (file?.name) await uploadAttachment({ submission_id: submission.id }, file);
      if (shouldSubmit) await submitSubmission(submission.id);
      draftForm.current.reset();
      await refresh();
      setNotice(shouldSubmit ? "Your work has been submitted." : "Draft saved.");
    } catch (err) {
      setError(err.message || "Could not save the submission.");
    } finally {
      setBusy(false);
    }
  }

  async function handleGrade(event, submission) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await gradeSubmission(submission.id, form.get("grade"), form.get("instructor_comment"));
      await refresh();
      setNotice(`Grade saved for ${submission.student_name}.`);
    } catch (err) {
      setError(err.message || "Could not save the grade.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="hint">Loading submissions…</p>;
  const ownSubmission = submissions[0];

  return (
    <section className="submission-panel" aria-label={`Submissions for ${assignment.title}`}>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {user.role === "student" ? (
        ownSubmission ? (
          <div className="student-submission">
            <p className={`status-pill status-${ownSubmission.status}`}>{ownSubmission.status.replace("_", " ")}</p>
            {ownSubmission.submitted_at && (
              <p className="hint">Submitted {new Date(ownSubmission.submitted_at).toLocaleString()}{ownSubmission.is_late ? " · late" : ""}</p>
            )}
            {ownSubmission.grade !== null && <p className="grade-display">Grade: {ownSubmission.grade}%</p>}
            {ownSubmission.instructor_comment && (
              <div className="instructor-feedback">
                <h5>Instructor feedback</h5>
                <p>{ownSubmission.instructor_comment}</p>
              </div>
            )}
            {ownSubmission.status === "in_progress" ? (
              <form className="submission-form" ref={draftForm}>
                <label>Your response<textarea name="response_text" rows="4" defaultValue={ownSubmission.response_text} /></label>
                <label>Attach a file (optional)<input name="submission_file" type="file" accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png" /></label>
                <p className="hint">PDF, Word, text, JPG, or PNG · up to 10 MB per file.</p>
                <AttachmentList
                  attachments={ownSubmission.attachments}
                  canDelete
                  onDelete={deleteAttachment}
                  onChange={refresh}
                />
                <div className="course-actions">
                  <button className="button button-secondary" type="button" disabled={busy} onClick={() => saveDraft(ownSubmission, false)}>Save draft</button>
                  <button className="button" type="button" disabled={busy} onClick={() => saveDraft(ownSubmission, true)}>Submit work</button>
                </div>
              </form>
            ) : (
              <>
                {ownSubmission.response_text && <p className="assignment-description">{ownSubmission.response_text}</p>}
                <AttachmentList attachments={ownSubmission.attachments} canDelete={false} />
              </>
            )}
          </div>
        ) : (
          <button className="text-button" type="button" disabled={busy} onClick={startSubmission}>Start submission</button>
        )
      ) : (
        submissions.length === 0 ? <p className="hint">No student submissions yet.</p> : (
          <div className="instructor-submissions">
            <h5>Student submissions</h5>
            {submissions.map((submission) => (
              <article className="student-submission" key={submission.id}>
                <div className="assignment-title-row">
                  <strong>{submission.student_name}</strong>
                  <span className={`status-pill status-${submission.status}`}>{submission.status.replace("_", " ")}</span>
                </div>
                {submission.submitted_at && (
                  <p className="hint">Submitted {new Date(submission.submitted_at).toLocaleString()}{submission.is_late ? " · late" : ""}</p>
                )}
                {submission.response_text && <p className="assignment-description">{submission.response_text}</p>}
                {submission.instructor_comment && (
                  <div className="instructor-feedback">
                    <h6>Previous feedback</h6>
                    <p>{submission.instructor_comment}</p>
                  </div>
                )}
                <AttachmentList attachments={submission.attachments} canDelete={false} />
                {submission.status !== "in_progress" && (
                  <form className="grade-form" onSubmit={(event) => handleGrade(event, submission)}>
                    <label>Grade (%)<input name="grade" type="number" min="0" max="100" step="0.01" defaultValue={submission.grade ?? ""} required /></label>
                    <label>Feedback for student<textarea name="instructor_comment" rows="3" defaultValue={submission.instructor_comment || ""} placeholder="Add comments about the submission (optional)" /></label>
                    <button className="text-button" type="submit" disabled={busy}>{submission.grade === null ? "Save grade" : "Update grade"}</button>
                  </form>
                )}
              </article>
            ))}
          </div>
        )
      )}
    </section>
  );
}

function formatFileSize(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function toLocalDateTime(value) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}
