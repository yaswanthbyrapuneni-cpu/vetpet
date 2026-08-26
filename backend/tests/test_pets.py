from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.domain import DoctorProfile, User, UserRole, VerificationStatus
from tests.conftest import otp_login_headers


def register_and_login_owner(client: TestClient, mobile_number: str) -> dict[str, str]:
    return otp_login_headers(client, mobile_number, full_name="Pet Owner")


def valid_pet() -> dict[str, object]:
    return {
        "name": "Milo",
        "species": "dog",
        "breed": "Indie",
        "sex": "male",
        "date_of_birth": "2022-04-10",
        "weight_kg": 18.4,
    }


def test_owner_can_create_list_read_and_update_pet(client: TestClient) -> None:
    headers = register_and_login_owner(client, "+919876510001")
    created = client.post("/api/v1/pets", json=valid_pet(), headers=headers)
    assert created.status_code == 201
    pet_id = created.json()["id"]

    listed = client.get("/api/v1/pets", headers=headers)
    assert listed.status_code == 200
    assert [pet["id"] for pet in listed.json()] == [pet_id]

    read = client.get(f"/api/v1/pets/{pet_id}", headers=headers)
    assert read.status_code == 200
    assert read.json()["name"] == "Milo"

    updated = client.patch(
        f"/api/v1/pets/{pet_id}", json={"weight_kg": 19.2}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["weight_kg"] == 19.2


def test_owner_cannot_access_another_owners_pet(client: TestClient) -> None:
    first_owner = register_and_login_owner(client, "+919876510002")
    second_owner = register_and_login_owner(client, "+919876510003")
    created = client.post("/api/v1/pets", json=valid_pet(), headers=first_owner)
    pet_id = created.json()["id"]

    assert client.get(f"/api/v1/pets/{pet_id}", headers=second_owner).status_code == 404
    assert (
        client.patch(
            f"/api/v1/pets/{pet_id}", json={"name": "Stolen"}, headers=second_owner
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/pets/{pet_id}", headers=second_owner).status_code == 404


def test_archived_pet_disappears_without_being_destroyed(client: TestClient) -> None:
    headers = register_and_login_owner(client, "+919876510004")
    created = client.post("/api/v1/pets", json=valid_pet(), headers=headers)
    pet_id = created.json()["id"]

    archived = client.delete(f"/api/v1/pets/{pet_id}", headers=headers)
    assert archived.status_code == 204
    assert client.get(f"/api/v1/pets/{pet_id}", headers=headers).status_code == 404
    assert client.get("/api/v1/pets", headers=headers).json() == []


def test_pet_validation_rejects_future_birth_date_and_invalid_weight(
    client: TestClient,
) -> None:
    headers = register_and_login_owner(client, "+919876510005")
    future_date = (date.today() + timedelta(days=1)).isoformat()

    future_birth = client.post(
        "/api/v1/pets",
        json={**valid_pet(), "date_of_birth": future_date},
        headers=headers,
    )
    invalid_weight = client.post(
        "/api/v1/pets",
        json={**valid_pet(), "weight_kg": 0},
        headers=headers,
    )
    assert future_birth.status_code == 422
    assert invalid_weight.status_code == 422


def test_doctor_cannot_use_owner_pet_endpoints(
    client: TestClient, db_session: Session
) -> None:
    mobile_number = "+919876510006"
    doctor_user = User(mobile_number=mobile_number, full_name="Dr Access", role=UserRole.DOCTOR)
    profile = DoctorProfile(
        user=doctor_user,
        license_number="ACCESS-123",
        qualification="BVSc",
        verification_status=VerificationStatus.VERIFIED,
    )
    db_session.add_all([doctor_user, profile])
    db_session.commit()

    headers = otp_login_headers(client, mobile_number)
    assert client.get("/api/v1/pets", headers=headers).status_code == 403
