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

For an HTTPS production deployment, set `DJANGO_DEBUG=false`, generate a unique `DJANGO_SECRET_KEY` of at least 50 characters, and set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CORS_ALLOWED_ORIGINS` to the exact API host and frontend origin. Production settings enable HTTPS redirects, HSTS, secure session and CSRF cookies, content-type protection, and a strict referrer policy. If TLS terminates at a reverse proxy, configure that proxy to forward the original HTTPS scheme before setting `DJANGO_SECURE_SSL_REDIRECT=false`; do not disable the redirect for a directly exposed HTTP deployment. Configure PostgreSQL and persistent storage separately for the deployment; email delivery is not required for in-app reminders.

If the database requires TLS, add `?sslmode=require` to the URL. Run `python manage.py migrate` after selecting the database. Migrations create the schema; they do not copy existing SQLite records into PostgreSQL.

The optional local Celery reminder runner uses Redis on your development computer. Production reminders instead use GitHub Actions and do not need Redis. To run the Celery worker locally, install Redis using your operating system's package instructions, then start it. The Python requirements include Celery with Redis support.

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

During local development, assignment and submission files use `backend/media/`. Production files use private Cloudflare R2 object storage. PDF, Word, text, JPG, and PNG files up to 10 MB each are accepted; downloads require sign-in and course access. The API supports draft creation and updates, `POST /api/v1/submissions/{id}/submit/`, instructor grades and comments through `PATCH /api/v1/submissions/{id}/`, and multipart uploads at `POST /api/v1/attachments/`.

## Phase 6: dashboard and timeline

`GET /api/v1/dashboard/` returns dashboard data scoped to the signed-in user's role. Students get upcoming, overdue, in-progress, submitted, and graded assignment states with days-until-due values. Instructors get course and assignment totals, submissions awaiting review, and deadlines. The frontend groups student assignments by due date and supports status filters; all date calculations use the configured local timezone.

## Phase 7: reminders and notifications

The reminder command creates one in-app reminder for each enrolled student with an assignment due within 24 hours and no submitted work. Creation is idempotent. Notifications are stored in the app, students can mark them as read, and the list refreshes every minute. Production runs the command from GitHub Actions every 15 minutes; email and push notifications are not part of the deployed setup. The Celery worker and Beat instructions below are optional local development components only.

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

## Phase 8: hardening

The interface is responsive and supports both student and instructor roles. Production settings disable Django debug mode, enforce HTTPS security headers and cookies, restrict allowed hosts and CORS origins, and use scoped API querysets and permissions. Attachment downloads require authentication and authorization. The instructor can leave written grading feedback that is visible to the student alongside the grade.

Hardening and deployment verification have been completed by the project owner. Re-run the security review and production smoke checks after changes to authentication, authorization, uploads, grading, or deployment configuration.

## Phase 9: testing

The project includes backend Django tests, frontend Jest/React Testing Library tests, and a Playwright end-to-end assignment flow. The project owner reports that the test and hardening pass is complete. Commands for repeating the test suites are in [Testing](#testing).

## Phase 10: deployment

The production application is deployed with the React/Vite frontend and Django API on separate Vercel projects, Neon PostgreSQL for application data, Cloudflare R2 for private attachment storage, and GitHub Actions for scheduled in-app reminders. The production database has been migrated and the application has been smoke-tested.

- Frontend: [assignment-tracker-orpin-xi.vercel.app](https://assignment-tracker-orpin-xi.vercel.app)
- API health: [assignment-tracker-hnh4.vercel.app/api/v1/health/](https://assignment-tracker-hnh4.vercel.app/api/v1/health/)

The frontend Vercel project uses Root Directory `frontend`, Framework Preset `Vite`, Build Command `npm run build`, and Output Directory `dist`. `frontend/vercel.json` rewrites browser routes to the SPA entry point. The API project uses Root Directory `backend` and the Django project detected from `manage.py` and `requirements.txt`.

Keep deployment secrets in Vercel and GitHub repository secrets; never commit production environment files, database URLs, or credentials. The production frontend uses `VITE_API_BASE_URL=https://assignment-tracker-hnh4.vercel.app/api/v1`. The API uses Neon through `DATABASE_URL`, and its CORS and host settings must match the frontend and API hostnames.

### Attachments and reminders

Production attachment storage uses a private Cloudflare R2 bucket. The API project's `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` values point to that bucket. For a new deployment, create a private bucket and an R2 token with object read/write access, then add those variables to the Django API project's environment. The API authorizes downloads before reading objects. Without the R2 variables, Django falls back to local storage, which is suitable only for development and is not persistent on Vercel.

### Production in-app reminder schedule

`.github/workflows/assignment-reminders.yml` runs `python manage.py create_assignment_reminders` at minutes 9, 24, 39, and 54 of every hour (UTC; 12, 27, 42, and 57 in East Africa Time). It can also be started manually from GitHub Actions. The job writes reminders directly to Neon; it does not send email and does not require Redis or a Render worker. Scheduled GitHub Actions can be delayed, so reminders are best-effort rather than real-time.

In GitHub, open the repository's **Settings → Secrets and variables → Actions** and add these repository secrets. Use the same production values already configured for the Django API:

- `DATABASE_URL`: production Neon PostgreSQL connection string.
- `DJANGO_SECRET_KEY`: production Django secret key.
- `DJANGO_ALLOWED_HOSTS`: API hostname, without `https://` or a path.
- `DJANGO_CORS_ALLOWED_ORIGINS`: frontend origin, including `https://`.

Do not place these values in the workflow file. Confirm Actions are enabled and that the workflow file is on the default branch. Use **Actions → Create assignment reminders → Run workflow** to run it manually when needed. Check the run log for the number of reminders created or activated. Neon must allow connections from GitHub-hosted runners; if the database uses an IP allowlist, permit those connections or use a provider-supported secure connection option.


## Testing

Backend tests are in `backend/tests/` and in the Django app test modules (for example, `backend/submissions/tests.py`). Frontend component tests and Playwright end-to-end tests are in `frontend/tests/`.

Run the backend suite:

```sh
cd backend
source .venv/bin/activate
python manage.py test
```

Run the frontend component tests and production build:

```sh
cd frontend
npm test
npm run build
```

Playwright needs its matching Chromium browser binary. From the frontend directory, install the Node dependencies if you have not already, then install Chromium and its Linux system libraries:

```sh
cd frontend
npm install
npx playwright install --with-deps chromium
npm run test:e2e
```

On Linux, Playwright may ask for your `sudo` password to install operating-system packages. On macOS or Windows, install just the browser with `npx playwright install chromium`, then run `npm run test:e2e`. The browser binary is cached for reuse; rerun the install command after updating Playwright because each Playwright version may require a matching browser build. See the [Playwright browser installation guide](https://playwright.dev/docs/browsers).

If the Playwright browser download is unavailable but Google Chrome is installed, set its executable path for the run:

```sh
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/google-chrome npm run test:e2e
```
