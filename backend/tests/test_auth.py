import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.security import hash_password
from app.models.domain import User, UserRole

OWNER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "strong-password",
    "full_name": "Pet Owner",
    "phone": "+91 9876543210",
}


def register_owner(client: TestClient) -> dict[str, object]:
    response = client.post("/api/v1/auth/register/owner", json=OWNER_PAYLOAD)
    assert response.status_code == 201
    return response.json()


def login_owner(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_PAYLOAD["email"], "password": OWNER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_owner_registration_login_and_current_user(client: TestClient) -> None:
    registered = register_owner(client)
    assert registered["role"] == "owner"
    assert "password" not in registered

    token = login_owner(client)
    me_response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == OWNER_PAYLOAD["email"]


def test_duplicate_email_is_rejected_case_insensitively(client: TestClient) -> None:
    register_owner(client)
    duplicate = {**OWNER_PAYLOAD, "email": "OWNER@example.com"}
    response = client.post("/api/v1/auth/register/owner", json=duplicate)
    assert response.status_code == 409


def test_invalid_login_and_missing_token_are_rejected(client: TestClient) -> None:
    register_owner(client)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_PAYLOAD["email"], "password": "incorrect-password"},
    )
    assert login_response.status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_doctor_registration_starts_pending_verification(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register/doctor",
        json={
            **OWNER_PAYLOAD,
            "email": "doctor@example.com",
            "full_name": "Dr Vet",
            "license_number": "VET-12345",
            "qualification": "BVSc",
            "specialization": "Small animals",
            "experience_years": 6,
        },
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "doctor"
    assert response.json()["verification_status"] == "pending"


def test_role_dependency_denies_wrong_role(db_session: Session) -> None:
    owner = User(
        email="role@example.com",
        password_hash=hash_password("strong-password"),
        full_name="Role Test",
        role=UserRole.OWNER,
    )
    db_session.add(owner)
    db_session.commit()

    doctor_only = require_roles(UserRole.DOCTOR)
    with pytest.raises(HTTPException) as error:
        doctor_only(owner)
    assert error.value.status_code == 403
