# Madina Vet Pet

Madina Vet Pet is an AI-assisted veterinary telehealth platform connecting pet
owners with Dr. Madina Prasadrao. Sign-in is by mobile number + OTP (mocked for
development), consultations are paid via Razorpay, and owners and the doctor can
exchange photos, videos, and voice notes during a consultation.

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
- mobile number + OTP login (OTP is mocked/returned in the response for local
  development; owners are created automatically on first verified OTP)
- a single pre-seeded, always-verified doctor account (no doctor directory or
  self-serve doctor registration)
- Razorpay-based consultation-fee payment at booking time (test mode)
- shared photo/video/voice-note attachments between an owner and the doctor on
  a consultation
- current-user authentication and reusable role authorization

## Authentication endpoints

- `POST /api/v1/auth/otp/request` (returns `dev_otp` when `VETPET_OTP_MOCK_MODE=true`)
- `POST /api/v1/auth/otp/verify` (creates a new owner automatically if `full_name` is supplied for an unknown number; existing accounts just log in)
- `GET /api/v1/auth/me` (Bearer token required)
- `GET /api/v1/doctors/primary` (the single seeded doctor)
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
- `POST/GET /api/v1/consultations/{consultation_id}/attachments` (photo/video/voice, owner or assigned doctor)
- `GET /api/v1/attachments/{attachment_id}/download`
- `POST /api/v1/appointments/{appointment_id}/payment/order` (owner only, creates a Razorpay order)
- `POST /api/v1/appointments/{appointment_id}/payment/verify` (owner only, verifies the Razorpay signature)

Medical uploads are limited to PDF, JPEG, and PNG files and default to a 10 MiB
size limit. Local storage is for development only; production will use private
object storage with short-lived signed access links.

Pet-owner consultation responses intentionally exclude internal doctor notes,
raw transcripts, and unapproved AI summary drafts. Prescription PDFs are created
from the structured, veterinarian-authored prescription data.

In development, due reminders are converted to inbox notifications when the user
loads the notification inbox. Production will move this processing to a scheduled
worker and send push notifications through Firebase Cloud Messaging.

Administrator and doctor accounts cannot be created through a public
registration endpoint — only owners can self-register, via first-time OTP
verification.

Create the primary doctor account (Dr. Madina Prasadrao) from the backend directory:

```powershell
python scripts/seed_primary_doctor.py --mobile-number "+919000000001"
```

Create an administrator account:

```powershell
python scripts/create_admin.py --mobile-number "+919000000000" --name "Platform Admin"
```

Razorpay checkout requires `VETPET_RAZORPAY_KEY_ID` / `VETPET_RAZORPAY_KEY_SECRET`
(test-mode keys from your own Razorpay account) to be set in `.env` — without
them, payment order creation returns 503.

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

## Deploy to production

`docker-compose.yml` ships three containers (Postgres, backend, frontend) and
publishes **no ports at all** — by design, since this is meant to sit on a
host that's already running other projects behind their own reverse proxy.

### Deploy on a shared host (already running other Dockerized projects behind Caddy)

This is the actual setup in use for this project: one GCP VM, several
unrelated apps, one shared `caddy` container in front of all of them, routing
by domain name to each app's container over a Docker network. Nothing here
should touch another project's containers, ports, or config. The frontend
container proxies its own `/api/*` requests to the backend internally
(`web/Caddyfile`), so it's a fully self-contained front door either way —
reachable straight over a published port with no domain, or through the
shared Caddy once there is one.

1. Find the shared network Caddy already sits on and the host path to its
   Caddyfile (read-only, changes nothing):
   ```bash
   sudo docker inspect caddy --format '{{json .NetworkSettings.Networks}}'
   sudo docker inspect caddy --format '{{json .Mounts}}'
   ```
   In this deployment that network is called `web` and the Caddyfile lives at
   `/home/pudivineela25/Caddyfile` — `docker-compose.yml` already references
   `web` as an `external` network, so it'll fail loudly if that name is wrong
   on a different host rather than silently creating a duplicate.

2. Copy the env template and fill in real secrets:
   ```bash
   cp .env.production.example .env
   # edit .env: POSTGRES_PASSWORD, VETPET_JWT_SECRET_KEY, live
   # VETPET_RAZORPAY_KEY_ID/SECRET, and the Twilio vars
   ```

3. Build and start — this only creates new containers/volumes, nothing
   existing is restarted or modified:
   ```bash
   docker compose up -d --build
   ```

#### No domain yet

`docker-compose.override.yml` is already in the repo and loads automatically
with the command above — it publishes the app directly on the server's IP at
`http://<server-ip>:18080`, completely bypassing the shared Caddy, so nothing
about other projects' routing is touched. `VETPET_CORS_ORIGINS` doesn't
matter for this path: the browser sees the app and its API as the same
origin either way. Whenever a domain is ready, delete
`docker-compose.override.yml` and continue with the step below instead.

#### Once there's a domain

Set `VETPET_CORS_ORIGINS` in `.env` to `["https://yourdomain.com"]`, then
append a new block to the *existing* Caddyfile (don't touch the blocks
already in it):
```
yourdomain.com, www.yourdomain.com {
    reverse_proxy vetpet-frontend:80
}
```
Then reload Caddy without restarting it (zero downtime for the other
projects it's already serving):
```bash
sudo docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```
This needs your domain's DNS A record already pointed at the server's
external IP, or the automatic Let's Encrypt certificate request fails.

### Deploy on a dedicated host (you own ports 80/443 outright)

If this ever moves to its own VPS with nothing else running on it, add a
Caddy service back into `docker-compose.yml` that publishes `80`/`443` and
reverse-proxies to `backend`/`frontend` itself, the same way the shared one
does above — there's nothing shared-host-specific about the app containers.

Before pointing real users at this, two things still need attention:

- **OTP delivery.** `VETPET_OTP_MOCK_MODE` must be `false` in production, with
  `VETPET_TWILIO_ACCOUNT_SID`/`VETPET_TWILIO_AUTH_TOKEN`/`VETPET_TWILIO_FROM_NUMBER`
  set (see `.env.production.example`). Two things to sort out before real
  users can log in: a trial Twilio account only sends to numbers you've
  manually verified in the console, and India requires DLT sender-ID
  registration for A2P SMS or carriers will silently drop the messages.
- **Single backend worker only.** Chat/call/notification delivery lives in an
  in-process `EventHub` (`app/services/realtime.py`). Running more than one
  worker or container replica will silently drop realtime pushes to sockets
  held by a different process. Scaling past one instance needs a shared
  pub/sub (e.g. Redis) behind `EventHub` first — the Dockerfile pins
  `--workers 1` for this reason.

## Package as an Android APK

The web app is already an installable PWA (`web/public/manifest.webmanifest` +
a registered service worker), so once it's live on a real HTTPS domain, wrap
it with Google's [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
CLI as a Trusted Web Activity — no code changes, no separate app to maintain:

```bash
npm install -g @bubblewrap/cli
bubblewrap init --manifest=https://yourdomain.com/manifest.webmanifest
bubblewrap build
```

This needs the real deployed domain (not localhost) and a
`/.well-known/assetlinks.json` file proving the APK and the site are the same
publisher — `bubblewrap init` generates the exact JSON to publish there.

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
