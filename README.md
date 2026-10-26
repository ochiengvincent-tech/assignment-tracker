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

For an HTTPS production deployment, set `DJANGO_DEBUG=false`, generate a unique `DJANGO_SECRET_KEY` of at least 50 characters, and set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CORS_ALLOWED_ORIGINS` to the exact API host and frontend origin. Production settings enable HTTPS redirects, HSTS, secure session and CSRF cookies, content-type protection, and a strict referrer policy. If TLS terminates at a reverse proxy, configure that proxy to forward the original HTTPS scheme before setting `DJANGO_SECURE_SSL_REDIRECT=false`; do not disable the redirect for a directly exposed HTTP deployment. Configure PostgreSQL credentials and email provider settings separately for the deployment.

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

## Vercel deployment preparation

This repository is configured for two Vercel projects connected to the same Git repository:

1. Create the **frontend project** with Root Directory `frontend`, Framework Preset `Vite`, Build Command `npm run build`, and Output Directory `dist`. `frontend/vercel.json` rewrites browser routes to the SPA entry point.
2. Create the **API project** with Root Directory `backend`. Vercel detects the Django project from `manage.py` and `requirements.txt`.
3. In the API project's environment settings, set `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY` of at least 50 characters, `DJANGO_ALLOWED_HOSTS` to the API's Vercel hostname, `DJANGO_CORS_ALLOWED_ORIGINS` to the frontend's production origin, and `DATABASE_URL` to a managed PostgreSQL database. Add the provider's database TLS option when required.
4. In the frontend project's environment settings, set `VITE_API_BASE_URL` to `https://<api-host>/api/v1` and redeploy it.
5. Run Django migrations against the production database before accepting real users. Create the instructor and student demo accounts using the Django admin or a controlled management command.

The application needs persistent object storage for production uploads, plus a host for the Celery worker and Beat scheduler. Vercel request functions do not start persistent worker processes. Until those services are configured and deployed, production attachments and automatic reminders are unavailable.

Provider dashboard work is manual: create both Vercel projects, provision managed PostgreSQL and compatible Redis/worker hosting, enter secrets and origins as environment variables, and perform the initial migration. Never commit production secrets or database URLs.

### Attachments and reminder worker

Production attachment storage is configured for an S3-compatible bucket such as Cloudflare R2. Create a private bucket and an R2 token with object read/write access, then set `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` on the Django API project. The API continues to authorize downloads before reading objects; keep the bucket private. These variables must be present before users upload production attachments. Without them, Django falls back to local storage, which is suitable only for development and is not persistent on Vercel.

`render.yaml` provisions a Render background worker that runs Celery worker and Beat together for this small project. Create the worker from the repository Blueprint and provide its prompted environment values. Set `DATABASE_URL` to the same Neon PostgreSQL connection string, `DJANGO_SECRET_KEY` to the same production Django secret, `DJANGO_ALLOWED_HOSTS` to the API hostname, `DJANGO_CORS_ALLOWED_ORIGINS` to the frontend origin, and `CELERY_BROKER_URL` to the Upstash **Redis TCP connection URL** (`rediss://...`), not its REST URL/token. The worker and API must use the same Neon database and Redis database. The combined worker/Beat process is a single instance; do not start a second copy of Beat against the same schedule.

For real reminder email, configure SMTP variables (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, and `DJANGO_DEFAULT_FROM_EMAIL`) both on the Vercel API project and the Render worker. Use the email provider's verified sender address. If SMTP is not configured, the local console backend only writes messages to logs and cannot deliver external email.

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
