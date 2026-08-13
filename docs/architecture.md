# Architecture

## Overview

The system begins as a modular monolith: one FastAPI service, one PostgreSQL
database, and one Flutter application. This keeps transactions and deployment
simple while preserving clear module boundaries for later extraction.

```text
Flutter client
      |
 HTTPS/JSON
      |
FastAPI application
  |-- identity and access
  |-- pets and records
  |-- doctors and availability
  |-- appointments
  |-- consultations and prescriptions
  |-- notifications
      |
 PostgreSQL ---- Object storage (later)
      |
 background jobs / AI providers (later)
```

## Roles

- `owner`: manages owned pets and their appointments and records
- `doctor`: accesses assigned patients and creates clinical documentation
- `admin`: verifies doctors and manages platform operations

Authorization must be checked at the resource level. A valid role alone does
not grant access to every record of that type.

## Initial domain model

- `users`: identity, credentials, contact data, role, and account state
- `doctor_profiles`: professional details and verification state
- `pets`: owner-linked demographic information
- `appointments`: scheduled owner/pet/doctor interaction and status
- `consultations`: clinical record for a completed appointment
- `prescriptions`: doctor-approved prescription header
- `prescription_items`: medicine, dose, route, frequency, and duration
- `medical_records`: typed medical-history entries and document references
- `consents`: versioned proof of consent for sensitive processing
- `audit_events`: actor, action, resource, timestamp, and metadata

## Safety boundaries

- AI output is a draft until a veterinarian reviews and accepts it.
- Recording never starts without explicit, versioned consent.
- Media access uses short-lived signed links; raw storage is private.
- Passwords are hashed, secrets stay outside source control, and production
  traffic uses TLS.
- Audit records cover privileged access and clinical-record changes.

## API conventions

- Routes are versioned under `/api/v1`.
- Errors use stable machine-readable codes in addition to human messages.
- Datetimes are stored in UTC and rendered in the user's timezone.
- Pagination is required for collection endpoints.
- Appointment status changes are explicit commands, not arbitrary field edits.

