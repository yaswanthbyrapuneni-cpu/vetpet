import hashlib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    DoctorProfile,
    User,
    UserRole,
)

PASSWORD = "strong-password"


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_owner_and_pet(client: TestClient, suffix: str) -> tuple[dict[str, str], str]:
    email = f"records-owner-{suffix}@example.com"
    response = client.post(
        "/api/v1/auth/register/owner",
        json={"email": email, "password": PASSWORD, "full_name": "Records Owner"},
    )
    assert response.status_code == 201
    headers = login(client, email)
    pet = client.post(
        "/api/v1/pets",
        json={"name": "Luna", "species": "Cat", "weight_kg": 4.2},
        headers=headers,
    )
    assert pet.status_code == 201
    return headers, pet.json()["id"]


def create_record(client: TestClient, headers: dict[str, str], pet_id: str):
    return client.post(
        f"/api/v1/pets/{pet_id}/medical-records",
        json={
            "record_type": "vaccination",
            "title": "Annual vaccination",
            "details": "Core vaccines administered",
            "occurred_on": date.today().isoformat(),
        },
        headers=headers,
    )


def create_doctor_with_appointment(
    db_session: Session, pet_id: str, status: AppointmentStatus, suffix: str
) -> User:
    doctor = User(
        email=f"records-doctor-{suffix}@example.com",
        password_hash=hash_password(PASSWORD),
        full_name="Dr Records",
        role=UserRole.DOCTOR,
    )
    profile = DoctorProfile(
        user=doctor,
        license_number=f"RECORDS-{suffix.upper()}",
        qualification="BVSc",
    )
    db_session.add_all([doctor, profile])
    db_session.flush()
    now = datetime.now(UTC)
    appointment = Appointment(
        pet_id=pet_id,
        doctor_id=profile.id,
        availability_id=f"test-slot-{suffix}",
        scheduled_start=now + timedelta(days=1),
        scheduled_end=now + timedelta(days=1, minutes=30),
        reason="Medical record access",
        status=status,
    )
    db_session.add(appointment)
    db_session.commit()
    return doctor


def test_owner_manages_and_archives_own_medical_record(client: TestClient) -> None:
    headers, pet_id = create_owner_and_pet(client, "crud")
    created = create_record(client, headers, pet_id)
    assert created.status_code == 201
    record_id = created.json()["id"]

    listed = client.get(f"/api/v1/pets/{pet_id}/medical-records", headers=headers)
    assert [record["id"] for record in listed.json()] == [record_id]
    updated = client.patch(
        f"/api/v1/medical-records/{record_id}",
        json={"details": "Updated vaccination details"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["details"] == "Updated vaccination details"

    assert client.delete(f"/api/v1/medical-records/{record_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/medical-records/{record_id}", headers=headers).status_code == 404


def test_another_owner_cannot_discover_records(client: TestClient) -> None:
    first_headers, pet_id = create_owner_and_pet(client, "first")
    second_headers, _ = create_owner_and_pet(client, "second")
    record = create_record(client, first_headers, pet_id)

    assert (
        client.get(f"/api/v1/pets/{pet_id}/medical-records", headers=second_headers).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/medical-records/{record.json()['id']}", headers=second_headers
        ).status_code
        == 404
    )


def test_confirmed_doctor_can_add_record_but_owner_cannot_edit_it(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "doctor-access")
    doctor = create_doctor_with_appointment(
        db_session, pet_id, AppointmentStatus.CONFIRMED, "confirmed"
    )
    doctor_headers = login(client, doctor.email)

    created = create_record(client, doctor_headers, pet_id)
    assert created.status_code == 201
    record_id = created.json()["id"]
    owner_read = client.get(f"/api/v1/medical-records/{record_id}", headers=owner_headers)
    assert owner_read.status_code == 200
    owner_edit = client.patch(
        f"/api/v1/medical-records/{record_id}",
        json={"details": "Owner overwrite"},
        headers=owner_headers,
    )
    assert owner_edit.status_code == 403


def test_requested_appointment_does_not_grant_medical_access(
    client: TestClient, db_session: Session
) -> None:
    _, pet_id = create_owner_and_pet(client, "requested")
    doctor = create_doctor_with_appointment(
        db_session, pet_id, AppointmentStatus.REQUESTED, "requested"
    )
    response = create_record(client, login(client, doctor.email), pet_id)
    assert response.status_code == 404


def test_owner_uploads_and_downloads_document(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    headers, pet_id = create_owner_and_pet(client, "upload")
    record = create_record(client, headers, pet_id)
    record_id = record.json()["id"]
    content = b"%PDF-1.4 test veterinary report"

    uploaded = client.post(
        f"/api/v1/medical-records/{record_id}/documents",
        files={"file": ("report.pdf", content, "application/pdf")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["sha256"] == hashlib.sha256(content).hexdigest()
    assert uploaded.json()["size_bytes"] == len(content)

    downloaded = client.get(
        f"/api/v1/medical-documents/{uploaded.json()['id']}/download", headers=headers
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content


def test_document_upload_rejects_unsupported_type(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    headers, pet_id = create_owner_and_pet(client, "bad-upload")
    record = create_record(client, headers, pet_id)
    response = client.post(
        f"/api/v1/medical-records/{record.json()['id']}/documents",
        files={"file": ("notes.txt", b"not allowed", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 415
