# Student Assignment Tracker

A no-cost student project for tracking course assignments. The initial setup is a React/Vite frontend and a Django REST Framework API. Local development uses SQLite; production can use PostgreSQL through `DATABASE_URL`.

## Requirements

- Python 3.12 or newer
- Node.js 20 or newer and npm

## Start the backend

```sh
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

When `DATABASE_URL` is unset, Django uses the local `backend/db.sqlite3` file. To use PostgreSQL, install the requirements, create a PostgreSQL database and user, then set `DATABASE_URL` in `backend/.env` before running migrations. For example:

```dotenv
DATABASE_URL=postgresql://assignment_tracker:your-password@127.0.0.1:5432/assignment_tracker
```

If the database requires TLS, add `?sslmode=require` to the URL. Run `python manage.py migrate` after selecting the database. Migrations create the schema; they do not copy existing SQLite records into PostgreSQL.

Phase 7 reminders use Celery and a local Redis server. Redis is free and runs on your computer; there is no subscription or account. Install Redis using your operating system's package instructions, then start it before the worker. The Python requirements include Celery with its Redis support.

On Ubuntu, install and start Redis with:

```sh
sudo apt install redis-server
sudo systemctl enable --now redis-server
```

The API health endpoint is `http://127.0.0.1:8000/api/v1/health/`.

## Start the frontend

In a second terminal:

```sh
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Sign in with an account created by the instructor.

The frontend routes signed-out users to `/login` and signed-in users to `/dashboard`. Opening another path redirects to the route for the current sign-in state. Assignment links use a dashboard fragment (for example, `/dashboard#assignment-12`) to scroll to that assignment.

## Phase 1: foundation

Project structure, local environment configuration, SQLite for local development, PostgreSQL connection configuration for production, API health endpoint, and frontend-to-API configuration. Django models and ORM querysets persist and retrieve the application data; raw SQL is not used by the application code.

## Phase 2: identity and access

The backend uses Django's built-in user accounts, with a related profile for the `student` or `instructor` role. Sign-in accepts either username or email and returns a DRF token. The API provides `/api/v1/auth/login/`, `/api/v1/auth/logout/`, and `/api/v1/auth/me/`.

To create the administrator account:

```sh
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
```

Open `http://127.0.0.1:8000/admin/` to create student and instructor accounts. A new account defaults to student. Open its profile in admin to change the role to instructor. Public self-registration is not included in this phase.

## Phase 3: courses and enrollment

Instructors can create, edit, and delete their courses. A course with enrolled students cannot be deleted, so student enrollment records are preserved. Course IDs appear on instructor cards and can be shared with students. Students join by entering that ID. Instructors see the enrolled student names; students see the courses they joined and each instructor's name.

The API exposes `GET/POST /api/v1/courses/`, course detail at `/api/v1/courses/{id}/`, and `GET/POST /api/v1/enrollments/`. Course and enrollment results are scoped to the authenticated instructor or student.

## Phase 4: assignments

Instructors can add, edit, and delete assignments inside their courses. Each assignment has a title, description, due date and time, and optional category. Students see assignments only for courses they joined. Course assignments can be listed at `GET /api/v1/assignments/?course_id={id}`; instructor create and update requests use the same assignment endpoint and must reference one of their own courses.

## Phase 5: submissions and grading

Students can start a draft, save a written response, attach files, and submit their work. Submitted work cannot be edited in the MVP. Instructors can review work for their own courses and enter a grade from 0 to 100. Late submissions are accepted and marked late in the interface.

Assignment and submission files are stored in the local `backend/media/` directory. PDF, Word, text, JPG, and PNG files up to 10 MB each are accepted; downloads require sign-in and course access. The API supports draft creation and updates, `POST /api/v1/submissions/{id}/submit/`, instructor grade updates through `PATCH /api/v1/submissions/{id}/`, and multipart uploads at `POST /api/v1/attachments/`.

## Phase 6: dashboard and timeline

`GET /api/v1/dashboard/` returns dashboard data scoped to the signed-in user's role. Students get upcoming, overdue, in-progress, submitted, and graded assignment states with days-until-due values. Instructors get course and assignment totals, submissions awaiting review, and deadlines. The frontend groups student assignments by due date and supports status filters; all date calculations use the configured local timezone.

## Phase 7: reminders and notifications

Celery Beat checks every minute for assignments due within 24 hours and creates one reminder per enrolled student who has not submitted. Reminder creation is idempotent. Notifications are stored in the app, students can mark them as read, and the list refreshes every minute. The default email backend prints reminder messages in the Celery worker terminal; it does not send email externally. Sending real email would require an SMTP account or email provider, so it is not enabled by default. Push notifications are not included.

Keep Django running, then open separate backend terminals for Redis, the Celery worker, and Celery Beat. If Redis is already installed as a service, start the service instead of launching another Redis process:

```sh
redis-server
```

```sh
cd backend
source .venv/bin/activate
celery -A config worker --loglevel=INFO
```

```sh
cd backend
source .venv/bin/activate
celery -A config beat --loglevel=INFO
```

The API exposes `GET /api/v1/notifications/` and `POST /api/v1/notifications/{id}/read/`. Set `CELERY_BROKER_URL` in `backend/.env` only if your local Redis uses a different address.

## Testing

Tests are kept in root-level test folders: `backend/tests/` for Django API integration tests and `frontend/tests/` for React component and Playwright end-to-end tests.

Run the backend suite:

```sh
cd backend
source .venv/bin/activate
python manage.py test tests
```

Run the frontend component tests and production build:

```sh
cd frontend
npm test
npm run build
```

Playwright uses Chromium. Install its browser once, then run the browser workflow:

```sh
cd frontend
npx playwright install chromium
npm run test:e2e
```

If the Playwright browser download is unavailable but Google Chrome is installed, set its executable path for the run:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
```
