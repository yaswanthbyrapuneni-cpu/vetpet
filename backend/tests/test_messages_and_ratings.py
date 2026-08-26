import hashlib
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import (
    Appointment,
    AppointmentStatus,
    DoctorProfile,
    PaymentStatus,
    Pet,
    PetSpecies,
    User,
    UserRole,
)
from tests.conftest import otp_login_headers


def mobile_number_for(prefix: str, suffix: str) -> str:
    digits = str(int(hashlib.sha256(suffix.encode()).hexdigest(), 16) % 100000).zfill(5)
    return f"+91{prefix}{digits}"


def setup_appointment(
    client: TestClient,
    db: Session,
    suffix: str,
    appointment_status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    payment_status: PaymentStatus = PaymentStatus.PAID,
) -> tuple[dict[str, str], dict[str, str], str]:
    owner = User(
        mobile_number=mobile_number_for("9876915", suffix),
        full_name="Chat Owner",
        role=UserRole.OWNER,
    )
    doctor_user = User(
        mobile_number=mobile_number_for("9876916", suffix),
        full_name="Dr Chat",
        role=UserRole.DOCTOR,
    )
    doctor = DoctorProfile(
        user=doctor_user,
        license_number=f"CHAT-{suffix.upper()}",
        qualification="BVSc & AH",
    )
    pet = Pet(owner=owner, name="Rex", species=PetSpecies.DOG, weight_kg=18)
    db.add_all([owner, doctor_user, doctor, pet])
    db.flush()
    now = datetime.now(UTC)
    appointment = Appointment(
        pet_id=pet.id,
        doctor_id=doctor.id,
        scheduled_start=now - timedelta(minutes=15),
        reason="Limping on left leg",
        status=appointment_status,
        payment_status=payment_status,
    )
    db.add(appointment)
    db.commit()
    return (
        otp_login_headers(client, owner.mobile_number),
        otp_login_headers(client, doctor_user.mobile_number),
        appointment.id,
    )


def test_owner_and_doctor_can_exchange_messages(client: TestClient, db_session: Session) -> None:
    owner_headers, doctor_headers, appointment_id = setup_appointment(client, db_session, "00001")

    sent = client.post(
        f"/api/v1/appointments/{appointment_id}/messages",
        json={"body": "The limp started this morning."},
        headers=owner_headers,
    )
    assert sent.status_code == 201
    assert sent.json()["body"] == "The limp started this morning."

    reply = client.post(
        f"/api/v1/appointments/{appointment_id}/messages",
        json={"body": "Please share a photo of the leg."},
        headers=doctor_headers,
    )
    assert reply.status_code == 201

    thread = client.get(f"/api/v1/appointments/{appointment_id}/messages", headers=owner_headers)
    assert thread.status_code == 200
    assert [item["body"] for item in thread.json()] == [
        "The limp started this morning.",
        "Please share a photo of the leg.",
    ]


def test_unpaid_appointment_blocks_chat(client: TestClient, db_session: Session) -> None:
    owner_headers, doctor_headers, appointment_id = setup_appointment(
        client, db_session, "00006", payment_status=PaymentStatus.PENDING
    )

    sent = client.post(
        f"/api/v1/appointments/{appointment_id}/messages",
        json={"body": "trying to chat before paying"},
        headers=owner_headers,
    )
    assert sent.status_code == 402

    read = client.get(f"/api/v1/appointments/{appointment_id}/messages", headers=doctor_headers)
    assert read.status_code == 402


def test_other_doctor_cannot_read_or_send_messages(client: TestClient, db_session: Session) -> None:
    _, _, appointment_id = setup_appointment(client, db_session, "00002")
    _, other_doctor_headers, _ = setup_appointment(client, db_session, "00003")

    assert (
        client.get(
            f"/api/v1/appointments/{appointment_id}/messages", headers=other_doctor_headers
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/appointments/{appointment_id}/messages",
            json={"body": "snooping"},
            headers=other_doctor_headers,
        ).status_code
        == 404
    )


def test_owner_rates_completed_appointment_once(client: TestClient, db_session: Session) -> None:
    owner_headers, _, appointment_id = setup_appointment(
        client, db_session, "00004", AppointmentStatus.COMPLETED
    )

    rated = client.post(
        f"/api/v1/appointments/{appointment_id}/rating",
        json={"stars": 5, "tags": ["On time", "Explained clearly"], "comment": "Great vet"},
        headers=owner_headers,
    )
    assert rated.status_code == 201
    assert rated.json()["stars"] == 5

    fetched = client.get(f"/api/v1/appointments/{appointment_id}/rating", headers=owner_headers)
    assert fetched.status_code == 200
    assert fetched.json()["comment"] == "Great vet"

    duplicate = client.post(
        f"/api/v1/appointments/{appointment_id}/rating",
        json={"stars": 3, "tags": [], "comment": None},
        headers=owner_headers,
    )
    assert duplicate.status_code == 409


def test_cannot_rate_appointment_before_completion(client: TestClient, db_session: Session) -> None:
    owner_headers, _, appointment_id = setup_appointment(client, db_session, "00005")

    response = client.post(
        f"/api/v1/appointments/{appointment_id}/rating",
        json={"stars": 4, "tags": [], "comment": None},
        headers=owner_headers,
    )
    assert response.status_code == 409
