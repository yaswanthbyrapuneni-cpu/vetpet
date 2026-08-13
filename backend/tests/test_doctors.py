from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.domain import User, UserRole

PASSWORD = "strong-password"


def register_and_login_doctor(
    client: TestClient, suffix: str = "one"
) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register/doctor",
        json={
            "email": f"doctor-{suffix}@example.com",
            "password": PASSWORD,
            "full_name": f"Dr {suffix.title()}",
            "license_number": f"VET-{suffix.upper()}",
            "qualification": "BVSc",
            "specialization": "Small animals",
            "experience_years": 5,
        },
    )
    assert response.status_code == 201
    doctor_id = response.json()["user"]["id"]
    login = client.post(
        "/api/v1/auth/login",
        json={"email": f"doctor-{suffix}@example.com", "password": PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, doctor_id


def create_admin_and_login(client: TestClient, db_session: Session) -> dict[str, str]:
    admin = User(
        email="admin@example.com",
        password_hash=hash_password("admin-strong-password"),
        full_name="Platform Admin",
        role=UserRole.ADMIN,
        is_email_verified=True,
    )
    db_session.add(admin)
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin-strong-password"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_doctor_can_read_and_update_own_profile(client: TestClient) -> None:
    headers, _ = register_and_login_doctor(client)

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


def test_doctor_availability_rejects_overlaps(client: TestClient) -> None:
    headers, _ = register_and_login_doctor(client, "slots")
    starts_at = datetime.now(UTC) + timedelta(days=2)
    payload = {
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(minutes=30)).isoformat(),
    }
    created = client.post("/api/v1/doctors/me/availability", json=payload, headers=headers)
    assert created.status_code == 201

    overlap = client.post(
        "/api/v1/doctors/me/availability",
        json={
            "starts_at": (starts_at + timedelta(minutes=10)).isoformat(),
            "ends_at": (starts_at + timedelta(minutes=40)).isoformat(),
        },
        headers=headers,
    )
    assert overlap.status_code == 409
    assert len(client.get("/api/v1/doctors/me/availability", headers=headers).json()) == 1


def test_pending_doctor_is_hidden_until_admin_verifies(
    client: TestClient, db_session: Session
) -> None:
    _, _ = register_and_login_doctor(client, "review")
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


def test_non_admin_cannot_review_doctors(client: TestClient) -> None:
    doctor_headers, _ = register_and_login_doctor(client, "not-admin")
    response = client.get("/api/v1/admin/doctors", headers=doctor_headers)
    assert response.status_code == 403


def test_availability_requires_timezone_and_future_time(client: TestClient) -> None:
    headers, _ = register_and_login_doctor(client, "validation")
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    no_timezone = client.post(
        "/api/v1/doctors/me/availability",
        json={
            "starts_at": tomorrow.replace(tzinfo=None).isoformat(),
            "ends_at": (tomorrow + timedelta(hours=1)).replace(tzinfo=None).isoformat(),
        },
        headers=headers,
    )
    past = client.post(
        "/api/v1/doctors/me/availability",
        json={
            "starts_at": (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            "ends_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        },
        headers=headers,
    )
    assert no_timezone.status_code == 422
    assert past.status_code == 422
