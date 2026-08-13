from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DoctorProfile, VerificationStatus

PASSWORD = "strong-password"


def auth_headers(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def create_owner_and_pet(client: TestClient, suffix: str) -> tuple[dict[str, str], str]:
    email = f"appointment-owner-{suffix}@example.com"
    registration = client.post(
        "/api/v1/auth/register/owner",
        json={"email": email, "password": PASSWORD, "full_name": "Appointment Owner"},
    )
    assert registration.status_code == 201
    headers = auth_headers(client, email)
    pet = client.post(
        "/api/v1/pets",
        json={"name": "Milo", "species": "Dog", "weight_kg": 12.5},
        headers=headers,
    )
    assert pet.status_code == 201
    return headers, pet.json()["id"]


def create_doctor(
    client: TestClient, db_session: Session, suffix: str, verified: bool = True
) -> tuple[dict[str, str], str]:
    email = f"appointment-doctor-{suffix}@example.com"
    registration = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Dr Appointment",
            "license_number": f"APPT-{suffix.upper()}",
            "qualification": "BVSc",
        },
    )
    assert registration.status_code == 201
    headers = auth_headers(client, email)
    profile = db_session.scalar(
        select(DoctorProfile).where(
            DoctorProfile.user_id == registration.json()["user"]["id"]
        )
    )
    assert profile is not None
    if verified:
        profile.verification_status = VerificationStatus.VERIFIED
        db_session.commit()
    return headers, profile.id


def create_slot(client: TestClient, headers: dict[str, str], days: int = 2) -> str:
    starts_at = datetime.now(UTC) + timedelta(days=days)
    response = client.post(
        "/api/v1/doctors/me/availability",
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def book(client: TestClient, headers: dict[str, str], pet_id: str, slot_id: str):
    return client.post(
        "/api/v1/appointments",
        json={
            "pet_id": pet_id,
            "availability_id": slot_id,
            "reason": "Persistent cough",
        },
        headers=headers,
    )


def test_owner_books_and_doctor_confirms_appointment(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "booking")
    doctor_headers, _ = create_doctor(client, db_session, "booking")
    slot_id = create_slot(client, doctor_headers)

    booked = book(client, owner_headers, pet_id, slot_id)
    assert booked.status_code == 201
    assert booked.json()["status"] == "requested"
    appointment_id = booked.json()["id"]

    doctor_list = client.get("/api/v1/appointments", headers=doctor_headers)
    assert [item["id"] for item in doctor_list.json()] == [appointment_id]
    confirmed = client.post(
        f"/api/v1/appointments/{appointment_id}/confirm",
        json={},
        headers=doctor_headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    owner_notifications = client.get("/api/v1/notifications", headers=owner_headers).json()
    assert owner_notifications[0]["title"] == "Appointment confirmed"
    doctor_notifications = client.get("/api/v1/notifications", headers=doctor_headers).json()
    assert doctor_notifications[0]["title"] == "New appointment request"


def test_unverified_doctor_slot_cannot_be_booked(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "pending")
    doctor_headers, _ = create_doctor(client, db_session, "pending", verified=False)
    slot_id = create_slot(client, doctor_headers)

    response = book(client, owner_headers, pet_id, slot_id)
    assert response.status_code == 409


def test_cancel_releases_slot_for_a_new_booking(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "cancel")
    doctor_headers, _ = create_doctor(client, db_session, "cancel")
    slot_id = create_slot(client, doctor_headers)
    first = book(client, owner_headers, pet_id, slot_id)

    cancelled = client.post(
        f"/api/v1/appointments/{first.json()['id']}/cancel",
        json={"reason": "Pet has recovered"},
        headers=owner_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert book(client, owner_headers, pet_id, slot_id).status_code == 201


def test_reschedule_releases_old_slot_and_requires_new_confirmation(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "reschedule")
    doctor_headers, _ = create_doctor(client, db_session, "reschedule")
    first_slot = create_slot(client, doctor_headers, days=2)
    second_slot = create_slot(client, doctor_headers, days=3)
    appointment = book(client, owner_headers, pet_id, first_slot)

    moved = client.post(
        f"/api/v1/appointments/{appointment.json()['id']}/reschedule",
        json={"availability_id": second_slot},
        headers=owner_headers,
    )
    assert moved.status_code == 200
    assert moved.json()["availability_id"] == second_slot
    assert moved.json()["status"] == "requested"
    assert book(client, owner_headers, pet_id, first_slot).status_code == 201


def test_other_doctor_cannot_change_appointment(
    client: TestClient, db_session: Session
) -> None:
    owner_headers, pet_id = create_owner_and_pet(client, "isolation")
    assigned_headers, _ = create_doctor(client, db_session, "assigned")
    other_headers, _ = create_doctor(client, db_session, "other")
    slot_id = create_slot(client, assigned_headers)
    appointment = book(client, owner_headers, pet_id, slot_id)

    response = client.post(
        f"/api/v1/appointments/{appointment.json()['id']}/confirm",
        json={},
        headers=other_headers,
    )
    assert response.status_code == 404


def test_owner_cannot_book_another_owners_pet(
    client: TestClient, db_session: Session
) -> None:
    first_headers, first_pet = create_owner_and_pet(client, "first")
    second_headers, _ = create_owner_and_pet(client, "second")
    doctor_headers, _ = create_doctor(client, db_session, "pet-security")
    slot_id = create_slot(client, doctor_headers)

    assert book(client, second_headers, first_pet, slot_id).status_code == 404
    assert book(client, first_headers, first_pet, slot_id).status_code == 201
