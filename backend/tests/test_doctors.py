from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import DoctorProfile, User, UserRole
from tests.conftest import otp_login_headers


def register_and_login_doctor(
    client: TestClient, db_session: Session, suffix: str = "00001"
) -> tuple[dict[str, str], str]:
    mobile_number = f"+9198768{suffix.zfill(5)}"
    doctor_user = User(
        mobile_number=mobile_number, full_name=f"Dr {suffix.title()}", role=UserRole.DOCTOR
    )
    profile = DoctorProfile(
        user=doctor_user,
        license_number=f"VET-{suffix.upper()}",
        qualification="BVSc",
        specialization="Small animals",
        experience_years=5,
    )
    db_session.add_all([doctor_user, profile])
    db_session.commit()
    headers = otp_login_headers(client, mobile_number)
    return headers, doctor_user.id


def create_admin_and_login(client: TestClient, db_session: Session) -> dict[str, str]:
    mobile_number = "+919876899999"
    admin = User(
        mobile_number=mobile_number,
        full_name="Platform Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    return otp_login_headers(client, mobile_number)


def test_doctor_can_read_and_update_own_profile(
    client: TestClient, db_session: Session
) -> None:
    headers, _ = register_and_login_doctor(client, db_session, "00001")

    profile = client.get("/api/v1/doctors/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["verification_status"] == "pending"

    updated = client.patch(
        "/api/v1/doctors/me",
        json={"hospital_name": "City Pet Hospital", "experience_years": 6},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["hospital_name"] == "City Pet Hospital"


def test_pending_doctor_is_hidden_until_admin_verifies(
    client: TestClient, db_session: Session
) -> None:
    register_and_login_doctor(client, db_session, "00003")
    assert client.get("/api/v1/doctors").json() == []

    admin_headers = create_admin_and_login(client, db_session)
    pending = client.get(
        "/api/v1/admin/doctors?verification_status=pending", headers=admin_headers
    )
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    profile_id = pending.json()[0]["id"]

    verified = client.post(
        f"/api/v1/admin/doctors/{profile_id}/verification",
        json={"decision": "verified", "note": "License checked"},
        headers=admin_headers,
    )
    assert verified.status_code == 200
    assert verified.json()["verification_status"] == "verified"
    assert client.get("/api/v1/doctors").json()[0]["id"] == profile_id


def test_non_admin_cannot_review_doctors(client: TestClient, db_session: Session) -> None:
    doctor_headers, _ = register_and_login_doctor(client, db_session, "00004")
    response = client.get("/api/v1/admin/doctors", headers=doctor_headers)
    assert response.status_code == 403


def test_doctor_can_toggle_online_status(client: TestClient, db_session: Session) -> None:
    headers, _ = register_and_login_doctor(client, db_session, "00005")

    online = client.patch("/api/v1/doctors/me/status", json={"is_online": True}, headers=headers)
    assert online.status_code == 200
    assert online.json()["is_online"] is True

    offline = client.patch("/api/v1/doctors/me/status", json={"is_online": False}, headers=headers)
    assert offline.status_code == 200
    assert offline.json()["is_online"] is False
