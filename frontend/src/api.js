const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
const tokenKey = "assignment-tracker-token";

async function request(path, options = {}) {
  const token = localStorage.getItem(tokenKey);
  const multipart = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      ...(options.body && !multipart ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail || Object.values(data).flat(Infinity).find((value) => typeof value === "string");
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}

export function getApiHealth() {
  return request("/health/");
}

export async function signIn(username, password) {
  const data = await request("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  localStorage.setItem(tokenKey, data.token);
  return data.user;
}

export function getCurrentUser() {
  return request("/auth/me/");
}

export function getDashboard() {
  return request("/dashboard/");
}

export function getNotifications() {
  return request("/notifications/");
}

export function markNotificationRead(notificationId) {
  return request(`/notifications/${notificationId}/read/`, { method: "POST" });
}

export function getCourses() {
  return request("/courses/");
}

export function createCourse(course) {
  return request("/courses/", { method: "POST", body: JSON.stringify(course) });
}

export function updateCourse(courseId, course) {
  return request(`/courses/${courseId}/`, { method: "PATCH", body: JSON.stringify(course) });
}

export function deleteCourse(courseId) {
  return request(`/courses/${courseId}/`, { method: "DELETE" });
}

export function getEnrollments(courseId) {
  const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
  return request(`/enrollments/${query}`);
}

export function enrollInCourse(courseId) {
  return request("/enrollments/", {
    method: "POST",
    body: JSON.stringify({ course_id: Number(courseId) }),
  });
}

export function getAssignments(courseId) {
  const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
  return request(`/assignments/${query}`);
}

export function createAssignment(assignment) {
  return request("/assignments/", { method: "POST", body: JSON.stringify(assignment) });
}

export function updateAssignment(assignmentId, assignment) {
  return request(`/assignments/${assignmentId}/`, { method: "PATCH", body: JSON.stringify(assignment) });
}

export function deleteAssignment(assignmentId) {
  return request(`/assignments/${assignmentId}/`, { method: "DELETE" });
}

export function getSubmissions(assignmentId) {
  return request(`/submissions/?assignment_id=${encodeURIComponent(assignmentId)}`);
}

export function createSubmission(assignmentId) {
  return request("/submissions/", {
    method: "POST",
    body: JSON.stringify({ assignment: assignmentId }),
  });
}

export function updateSubmission(submissionId, responseText) {
  return request(`/submissions/${submissionId}/`, {
    method: "PATCH",
    body: JSON.stringify({ response_text: responseText }),
  });
}

export function submitSubmission(submissionId) {
  return request(`/submissions/${submissionId}/submit/`, { method: "POST" });
}

export function gradeSubmission(submissionId, grade, instructorComment) {
  return request(`/submissions/${submissionId}/`, {
    method: "PATCH",
    body: JSON.stringify({ grade: Number(grade), instructor_comment: instructorComment }),
  });
}

export function uploadAttachment(target, file) {
  const form = new FormData();
  if (target.assignment_id) form.append("assignment_id", target.assignment_id);
  if (target.submission_id) form.append("submission_id", target.submission_id);
  form.append("file", file);
  return request("/attachments/", { method: "POST", body: form });
}

export function deleteAttachment(attachmentId) {
  return request(`/attachments/${attachmentId}/`, { method: "DELETE" });
}

export async function downloadAttachment(attachment) {
  const token = localStorage.getItem(tokenKey);
  const response = await fetch(`${apiBaseUrl}/attachments/${attachment.id}/download/`, {
    headers: token ? { Authorization: `Token ${token}` } : {},
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Download failed (${response.status}).`);
  }

  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = attachment.original_name;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function signOut() {
  try {
    await request("/auth/logout/", { method: "POST" });
  } finally {
    localStorage.removeItem(tokenKey);
  }
}
