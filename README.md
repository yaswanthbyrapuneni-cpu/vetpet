# VetPet Connect

VetPet Connect is an AI-assisted veterinary telehealth platform for pet owners,
veterinarians, and platform administrators.

## Repository layout

- `backend/` — FastAPI REST API and tests
- `mobile/` — archived Flutter client
- `web/` — active React TypeScript progressive web application
- `docs/` — architecture, scope, and domain documentation
- `infrastructure/` — deployment and operations placeholders

## Current milestone

The project currently includes:

- versioned FastAPI routes and health checks
- configuration driven by environment variables
- initial relational domain model
- SQLite for zero-setup development and PostgreSQL-ready configuration
- responsive React PWA with role-aware navigation
- automated backend tests
- owner and doctor registration
- Argon2 password hashing and JWT login
- current-user authentication and reusable role authorization

The web client currently implements authentication, registration, pet profile
management, and the verified-veterinarian directory. Appointment and clinical
screens are the next frontend milestone.

## Authentication endpoints

- `POST /api/v1/auth/register/owner`
- `POST /api/v1/auth/register/doctor`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me` (Bearer token required)
- `POST /api/v1/pets` (owner only)
- `GET /api/v1/pets` (owner only, paginated)
- `GET /api/v1/pets/{pet_id}` (owner only)
- `PATCH /api/v1/pets/{pet_id}` (owner only)
- `DELETE /api/v1/pets/{pet_id}` (owner only, archives the record)
- `GET/PATCH /api/v1/doctors/me` (doctor only)
- `POST/GET /api/v1/doctors/me/availability` (doctor only)
- `DELETE /api/v1/doctors/me/availability/{slot_id}` (doctor only)
- `GET /api/v1/doctors` (public verified-doctor directory)
- `GET /api/v1/doctors/{doctor_id}/availability`
- `GET /api/v1/admin/doctors` (admin only)
- `POST /api/v1/admin/doctors/{doctor_id}/verification` (admin only)
- `POST /api/v1/appointments` (owner books an open slot)
- `GET /api/v1/appointments` (role-scoped appointment list)
- `GET /api/v1/appointments/{appointment_id}`
- `POST /api/v1/appointments/{appointment_id}/cancel` (owner only)
- `POST /api/v1/appointments/{appointment_id}/reschedule` (owner only)
- `POST /api/v1/appointments/{appointment_id}/confirm` (assigned doctor only)
- `POST /api/v1/appointments/{appointment_id}/reject` (assigned doctor only)
- `POST /api/v1/appointments/{appointment_id}/complete` (assigned doctor only)
- `POST/GET /api/v1/pets/{pet_id}/medical-records`
- `GET/PATCH/DELETE /api/v1/medical-records/{record_id}`
- `POST /api/v1/medical-records/{record_id}/documents`
- `GET /api/v1/medical-documents/{document_id}/download`
- `POST/GET /api/v1/appointments/{appointment_id}/consultation`
- `GET/PATCH /api/v1/doctor/consultations/{consultation_id}`
- `PUT /api/v1/doctor/consultations/{consultation_id}/prescription`
- `GET /api/v1/consultations/{consultation_id}/prescription`
- `GET /api/v1/consultations/{consultation_id}/prescription.pdf`
- `POST /api/v1/pets/{pet_id}/reminders`
- `GET /api/v1/reminders`
- `PATCH/DELETE /api/v1/reminders/{reminder_id}`
- `GET /api/v1/notifications`
- `POST /api/v1/notifications/{notification_id}/read`
- `POST /api/v1/notifications/read-all`

Medical uploads are limited to PDF, JPEG, and PNG files and default to a 10 MiB
size limit. Local storage is for development only; production will use private
object storage with short-lived signed access links.

Pet-owner consultation responses intentionally exclude internal doctor notes,
raw transcripts, and unapproved AI summary drafts. Prescription PDFs are created
from the structured, veterinarian-authored prescription data.

In development, due reminders are converted to inbox notifications when the user
loads the notification inbox. Production will move this processing to a scheduled
worker and send push notifications through Firebase Cloud Messaging.

Doctor accounts begin with `pending` verification. Administrator accounts cannot
be created through a public registration endpoint.

Create the first administrator from the backend directory:

```powershell
python scripts/create_admin.py --email admin@example.com --name "Platform Admin" --password "choose-a-long-password"
```

## Run the backend

Requires Python 3.11 or newer.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item ..\.env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. The health
endpoint is `http://127.0.0.1:8000/api/v1/health`.

Run tests:

```powershell
cd backend
python -m pytest
```

## Database migrations

The API does not create or alter tables at startup. Apply committed migrations
before starting it:

```powershell
cd backend
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

Create a migration after changing SQLAlchemy models:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
```

Always inspect generated migrations and test both upgrade and downgrade paths
before using them with shared data.

## Run PostgreSQL (optional)

With Docker installed:

```powershell
docker compose up -d db
```

Then set `VETPET_DATABASE_URL` to the PostgreSQL value shown in `.env.example`.

## Run the web application

The React PWA is the active frontend and does not require Flutter or Android
Studio:

```powershell
cd web
$env:NODE_USE_SYSTEM_CA='1'
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`. Keep the FastAPI backend running on port 8000.

## Archived Flutter client

The earlier Flutter implementation remains under `mobile/` for reference but is
no longer required for development.

```powershell
cd mobile
flutter pub get
flutter run -d chrome
```

The first mobile slice includes secure authentication, role-aware navigation,
pet profile management, and the verified-veterinarian directory. See
`mobile/README.md` for emulator and API URL configuration.

See [docs/architecture.md](docs/architecture.md) and
[docs/mvp-scope.md](docs/mvp-scope.md) before extending the platform.
