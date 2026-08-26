import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.models.domain import User, UserRole

MOBILE_NUMBER = "+919876500001"


def request_otp(client: TestClient, mobile_number: str = MOBILE_NUMBER) -> str:
    response = client.post("/api/v1/auth/otp/request", json={"mobile_number": mobile_number})
    assert response.status_code == 200
    dev_otp = response.json()["dev_otp"]
    assert dev_otp is not None
    return dev_otp


def test_new_owner_can_verify_otp_and_read_current_user(client: TestClient) -> None:
    code = request_otp(client)
    verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": MOBILE_NUMBER, "code": code, "full_name": "Pet Owner"},
    )
    assert verify.status_code == 200
    token = verify.json()["access_token"]

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["mobile_number"] == MOBILE_NUMBER
    assert me_response.json()["role"] == "owner"


def test_verify_without_full_name_for_new_number_is_rejected(client: TestClient) -> None:
    mobile_number = "+919876500002"
    code = request_otp(client, mobile_number)
    response = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": code},
    )
    assert response.status_code == 422


def test_missing_full_name_does_not_consume_the_otp(client: TestClient) -> None:
    mobile_number = "+919876500006"
    code = request_otp(client, mobile_number)

    rejected = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": code},
    )
    assert rejected.status_code == 422

    retried = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": code, "full_name": "Pet Owner"},
    )
    assert retried.status_code == 200


def test_incorrect_code_and_missing_token_are_rejected(client: TestClient) -> None:
    mobile_number = "+919876500003"
    request_otp(client, mobile_number)
    response = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": "000000", "full_name": "Pet Owner"},
    )
    assert response.status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_existing_user_can_log_in_again_without_full_name(client: TestClient) -> None:
    mobile_number = "+919876500004"
    code = request_otp(client, mobile_number)
    first = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": code, "full_name": "Pet Owner"},
    )
    assert first.status_code == 200

    code = request_otp(client, mobile_number)
    second = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mobile_number, "code": code},
    )
    assert second.status_code == 200


def _current_user_id(client: TestClient, token: str) -> str:
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    return response.json()["id"]


def test_differently_formatted_numbers_resolve_to_the_same_account(client: TestClient) -> None:
    code = request_otp(client, "9876500007")
    first = client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": "9876500007", "code": code, "full_name": "Same Person"},
    )
    assert first.status_code == 200
    first_id = _current_user_id(client, first.json()["access_token"])
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {first.json()['access_token']}"}
        ).json()["mobile_number"]
        == "+919876500007"
    )

    for variant in ("+919876500007", "09876500007", "+91 98765 00007", "91-9876500007"):
        code = request_otp(client, variant)
        again = client.post(
            "/api/v1/auth/otp/verify",
            json={"mobile_number": variant, "code": code},
        )
        assert again.status_code == 200, variant
        assert _current_user_id(client, again.json()["access_token"]) == first_id, variant


def test_otp_requests_are_rate_limited_per_number(client: TestClient) -> None:
    mobile_number = "+919876500008"
    for _ in range(5):
        response = client.post("/api/v1/auth/otp/request", json={"mobile_number": mobile_number})
        assert response.status_code == 200

    blocked = client.post("/api/v1/auth/otp/request", json={"mobile_number": mobile_number})
    assert blocked.status_code == 429

    # A different number is unaffected by another number's limit.
    other = client.post("/api/v1/auth/otp/request", json={"mobile_number": "+919876500009"})
    assert other.status_code == 200


def test_otp_request_sends_sms_and_hides_dev_otp_when_not_in_mock_mode(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "otp_mock_mode", False)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "app.api.routes.auth.send_otp_sms",
        lambda mobile_number, code: sent.append((mobile_number, code)),
    )

    response = client.post(
        "/api/v1/auth/otp/request", json={"mobile_number": "+919876500010"}
    )
    assert response.status_code == 200
    assert response.json()["dev_otp"] is None
    assert sent == [("+919876500010", sent[0][1])]
    assert len(sent[0][1]) == 6


def test_otp_request_surfaces_an_error_when_sms_delivery_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings
    from app.services.sms import SmsDeliveryError

    monkeypatch.setattr(get_settings(), "otp_mock_mode", False)

    def failing_send(mobile_number: str, code: str) -> None:
        raise SmsDeliveryError("Twilio is down")

    monkeypatch.setattr("app.api.routes.auth.send_otp_sms", failing_send)

    response = client.post(
        "/api/v1/auth/otp/request", json={"mobile_number": "+919876500011"}
    )
    assert response.status_code == 502


def test_role_dependency_denies_wrong_role(db_session: Session) -> None:
    owner = User(
        mobile_number="+919876500005",
        full_name="Role Test",
        role=UserRole.OWNER,
    )
    db_session.add(owner)
    db_session.commit()

    doctor_only = require_roles(UserRole.DOCTOR)
    with pytest.raises(HTTPException) as error:
        doctor_only(owner)
    assert error.value.status_code == 403
