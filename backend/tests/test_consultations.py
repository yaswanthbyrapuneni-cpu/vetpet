from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    DoctorProfile,
    Pet,
    User,
    UserRole,
)

PASSWORD = "strong-password"


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_appointment(
    client: TestClient,
    db: Session,
    suffix: str,
    appointment_status: AppointmentStatus = AppointmentStatus.CONFIRMED,
) -> tuple[dict[str, str], dict[str, str], str]:
    owner = User(
        email=f"consult-owner-{suffix}@example.com",
        password_hash=hash_password(PASSWORD),
        full_name="Consultation Owner",
        role=UserRole.OWNER,
    )
    doctor_user = User(
        email=f"consult-doctor-{suffix}@example.com",
        password_hash=hash_password(PASSWORD),
        full_name="Dr Consultation",
        role=UserRole.DOCTOR,
    )
    doctor = DoctorProfile(
        user=doctor_user,
        license_number=f"CONSULT-{suffix.upper()}",
        qualification="BVSc & AH",
    )
    pet = Pet(owner=owner, name="Bruno", species="Dog", weight_kg=22)
    db.add_all([owner, doctor_user, doctor, pet])
    db.flush()
    now = datetime.now(UTC)
    appointment = Appointment(
        pet_id=pet.id,
        doctor_id=doctor.id,
        availability_id=f"consult-slot-{suffix}",
        scheduled_start=now - timedelta(minutes=15),
        scheduled_end=now + timedelta(minutes=15),
        reason="Skin irritation",
        status=appointment_status,
    )
    db.add(appointment)
    db.commit()
    return login(client, owner.email), login(client, doctor_user.email), appointment.id


def create_consultation(
    client: TestClient, doctor_headers: dict[str, str], appointment_id: str
):
    return client.post(
        f"/api/v1/appointments/{appointment_id}/consultation",
        json={
            "diagnosis": "Allergic dermatitis",
            "doctor_notes": "Internal differential diagnosis notes",
            "approved_summary": "Likely allergy; begin prescribed treatment.",
            "follow_up_date": (date.today() + timedelta(days=7)).isoformat(),
        },
        headers=doctor_headers,
    )


def prescription_payload(medicine: str = "Cetirizine") -> dict[str, object]:
    return {
        "instructions": "Give after food and monitor for drowsiness.",
        "recommended_tests": ["Allergy panel"],
        "items": [
            {
                "medicine_name": medicine,
                "dosage": "5 mg",
                "frequency": "Once daily",
                "duration": "7 days",
                "route": "oral",
            }
        ],
    }


def test_doctor_creates_notes_but_owner_response_hides_internal_fields(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, doctor_headers, appointment_id = setup_appointment(
        client, db_session, "privacy"
    )
    created = create_consultation(client, doctor_headers, appointment_id)
    assert created.status_code == 201
    assert created.json()["doctor_notes"] == "Internal differential diagnosis notes"

    owner_view = client.get(
        f"/api/v1/appointments/{appointment_id}/consultation", headers=owner_headers
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["diagnosis"] == "Allergic dermatitis"
    assert "doctor_notes" not in owner_view.json()
    assert "ai_summary_draft" not in owner_view.json()
    assert "transcript" not in owner_view.json()


def test_wrong_doctor_cannot_read_or_update_consultation(
    client: TestClient, db_session: Session
) -> None:
    _, assigned_headers, appointment_id = setup_appointment(client, db_session, "assigned")
    _, other_headers, _ = setup_appointment(client, db_session, "other")
    consultation = create_consultation(client, assigned_headers, appointment_id)
    consultation_id = consultation.json()["id"]

    assert (
        client.get(
            f"/api/v1/doctor/consultations/{consultation_id}", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/doctor/consultations/{consultation_id}",
            json={"diagnosis": "Unauthorized change"},
            headers=other_headers,
        ).status_code
        == 404
    )


def test_requested_appointment_cannot_start_consultation(
    client: TestClient, db_session: Session
) -> None:
    _, doctor_headers, appointment_id = setup_appointment(
        client, db_session, "requested", AppointmentStatus.REQUESTED
    )
    assert create_consultation(client, doctor_headers, appointment_id).status_code == 409


def test_doctor_writes_owner_reads_and_downloads_prescription_pdf(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, doctor_headers, appointment_id = setup_appointment(
        client, db_session, "prescription"
    )
    consultation = create_consultation(client, doctor_headers, appointment_id)
    consultation_id = consultation.json()["id"]

    written = client.put(
        f"/api/v1/doctor/consultations/{consultation_id}/prescription",
        json=prescription_payload(),
        headers=doctor_headers,
    )
    assert written.status_code == 200
    assert written.json()["items"][0]["medicine_name"] == "Cetirizine"

    owner_view = client.get(
        f"/api/v1/consultations/{consultation_id}/prescription", headers=owner_headers
    )
    assert owner_view.status_code == 200
    assert owner_view.json()["recommended_tests"] == ["Allergy panel"]
    assert client.get("/api/v1/reminders", headers=owner_headers).json()[0][
        "reminder_type"
    ] == "follow_up"
    assert client.get("/api/v1/notifications", headers=owner_headers).json()[0][
        "title"
    ] == "Prescription available"
    pdf = client.get(
        f"/api/v1/consultations/{consultation_id}/prescription.pdf", headers=owner_headers
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_rewriting_prescription_replaces_old_items(
    client: TestClient, db_session: Session
) -> None:
    _, doctor_headers, appointment_id = setup_appointment(client, db_session, "replace")
    consultation_id = create_consultation(
        client, doctor_headers, appointment_id
    ).json()["id"]
    url = f"/api/v1/doctor/consultations/{consultation_id}/prescription"
    assert client.put(url, json=prescription_payload(), headers=doctor_headers).status_code == 200
    replaced = client.put(
        url, json=prescription_payload("Prednisolone"), headers=doctor_headers
    )
    assert replaced.status_code == 200
    assert len(replaced.json()["items"]) == 1
    assert replaced.json()["items"][0]["medicine_name"] == "Prednisolone"


def test_prescription_requires_at_least_one_medicine(
    client: TestClient, db_session: Session
) -> None:
    _, doctor_headers, appointment_id = setup_appointment(client, db_session, "validation")
    consultation_id = create_consultation(
        client, doctor_headers, appointment_id
    ).json()["id"]
    response = client.put(
        f"/api/v1/doctor/consultations/{consultation_id}/prescription",
        json={"items": []},
        headers=doctor_headers,
    )
    assert response.status_code == 422
