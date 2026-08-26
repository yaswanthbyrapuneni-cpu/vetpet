from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import DoctorProfile, Pet, User, UserRole, VerificationStatus
from tests.conftest import otp_login_headers


def create_owner(client: TestClient, suffix: str) -> dict[str, str]:
    mobile_number = f"+9198765{suffix.zfill(5)}"
    return otp_login_headers(client, mobile_number, full_name="Appointment Owner")


def create_doctor(
    client: TestClient, db_session: Session, suffix: str, verified: bool = True
) -> tuple[dict[str, str], str]:
    mobile_number = f"+9198766{suffix.zfill(5)}"
    doctor_user = User(mobile_number=mobile_number, full_name="Dr Appointment", role=UserRole.DOCTOR)
    profile = DoctorProfile(
        user=doctor_user,
        license_number=f"APPT-{suffix.upper()}",
        qualification="BVSc",
        verification_status=(
            VerificationStatus.VERIFIED if verified else VerificationStatus.PENDING
        ),
    )
    db_session.add_all([doctor_user, profile])
    db_session.commit()
    headers = otp_login_headers(client, mobile_number)
    profile = db_session.scalar(select(DoctorProfile).where(DoctorProfile.user_id == doctor_user.id))
    assert profile is not None
    return headers, profile.id


def book(
    client: TestClient,
    headers: dict[str, str],
    pet_name: str = "Milo",
    species: str = "dog",
    reason: str = "Persistent cough",
):
    return client.post(
        "/api/v1/appointments",
        json={"pet_name": pet_name, "species": species, "reason": reason},
        headers=headers,
    )


class FakeRazorpayClient:
    """Stubs the parts of the razorpay SDK the payment routes call, so tests
    can exercise the pay -> auto-confirm flow without a real gateway."""

    def __init__(self, link_signature_valid: bool = True) -> None:
        self.order = SimpleNamespace(create=lambda payload: {"id": f"order_{payload['receipt']}"})
        self.payment_link = SimpleNamespace(
            create=lambda payload: {"short_url": f"https://rzp.io/i/{payload['reference_id']}"}
        )

        def verify_payment_link_signature(payload: dict) -> None:
            if not link_signature_valid:
                import razorpay

                raise razorpay.errors.SignatureVerificationError("bad signature")

        self.utility = SimpleNamespace(
            verify_payment_signature=lambda payload: None,
            verify_payment_link_signature=verify_payment_link_signature,
        )


def pay(client: TestClient, headers: dict[str, str], appointment_id: str, monkeypatch) -> None:
    import app.api.routes.payments as payments_module

    monkeypatch.setattr(payments_module, "razorpay_client", lambda: FakeRazorpayClient())
    order = client.post(f"/api/v1/appointments/{appointment_id}/payment/order", headers=headers)
    assert order.status_code == 200
    verify = client.post(
        f"/api/v1/appointments/{appointment_id}/payment/verify",
        json={
            "razorpay_order_id": order.json()["order_id"],
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "signature_test123",
        },
        headers=headers,
    )
    assert verify.status_code == 200


def test_booking_is_instant_and_unconfirmed_until_paid(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00001")
    create_doctor(client, db_session, "00001")

    booked = book(client, owner_headers)
    assert booked.status_code == 201
    assert booked.json()["status"] == "requested"
    assert booked.json()["payment_status"] == "pending"
    assert booked.json()["payment_amount_paise"] == 20000


def test_no_verified_doctor_available_returns_409(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00002")
    create_doctor(client, db_session, "00002", verified=False)

    response = book(client, owner_headers)
    assert response.status_code == 409


def test_payment_auto_confirms_appointment_and_notifies_doctor(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    owner_headers = create_owner(client, "00003")
    doctor_headers, _ = create_doctor(client, db_session, "00003")
    booked = book(client, owner_headers)
    appointment_id = booked.json()["id"]

    pay(client, owner_headers, appointment_id, monkeypatch)

    appointment = client.get(f"/api/v1/appointments/{appointment_id}", headers=owner_headers)
    assert appointment.json()["status"] == "confirmed"
    assert appointment.json()["payment_status"] == "paid"
    assert appointment.json()["paid_at"] is not None
    assert appointment.json()["razorpay_payment_id"] == "pay_test123"

    doctor_notifications = client.get("/api/v1/notifications", headers=doctor_headers).json()
    assert doctor_notifications[0]["title"] == "New paid consultation"


def test_other_doctor_cannot_read_appointment(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00005")
    create_doctor(client, db_session, "00005")
    other_headers, _ = create_doctor(client, db_session, "00006")
    appointment = book(client, owner_headers)

    response = client.get(
        f"/api/v1/appointments/{appointment.json()['id']}", headers=other_headers
    )
    assert response.status_code == 404


def test_repeat_booking_for_same_animal_reuses_the_same_pet_record(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00007")
    create_doctor(client, db_session, "00007")

    first = book(client, owner_headers, pet_name="Simba", species="dog")
    second = book(client, owner_headers, pet_name="simba", species="dog")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["pet_id"] == second.json()["pet_id"]
    assert db_session.scalar(select(Pet).where(Pet.name == "Simba")) is not None


def test_consultation_fee_varies_by_species(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00009")
    create_doctor(client, db_session, "00009")

    hen_booking = book(client, owner_headers, pet_name="Kodi", species="country_hen")
    assert hen_booking.json()["payment_amount_paise"] == 2500

    goat_booking = book(client, owner_headers, pet_name="Metha", species="goat")
    assert goat_booking.json()["payment_amount_paise"] == 5000

    cow_booking = book(client, owner_headers, pet_name="Lakshmi", species="cow")
    assert cow_booking.json()["payment_amount_paise"] == 20000


def test_cancel_appointment(client: TestClient, db_session: Session) -> None:
    owner_headers = create_owner(client, "00010")
    create_doctor(client, db_session, "00010")
    booked = book(client, owner_headers)

    cancelled = client.post(
        f"/api/v1/appointments/{booked.json()['id']}/cancel",
        json={"reason": "Pet has recovered"},
        headers=owner_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_unpaid_cancelled_appointment_is_not_listed(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    owner_headers = create_owner(client, "00015")
    doctor_headers, _ = create_doctor(client, db_session, "00015")

    # Never paid, then cancelled -- abandoned booking debris, should vanish from lists.
    abandoned = book(client, owner_headers)
    client.post(
        f"/api/v1/appointments/{abandoned.json()['id']}/cancel",
        json={"reason": "Changed my mind"},
        headers=owner_headers,
    )

    # Paid, confirmed, then cancelled -- a real record, should still be listed.
    paid_then_cancelled = book(client, owner_headers)
    pay(client, owner_headers, paid_then_cancelled.json()["id"], monkeypatch)
    client.post(
        f"/api/v1/appointments/{paid_then_cancelled.json()['id']}/cancel",
        json={"reason": "Emergency came up"},
        headers=owner_headers,
    )

    owner_list = client.get("/api/v1/appointments", headers=owner_headers).json()
    ids = [a["id"] for a in owner_list]
    assert abandoned.json()["id"] not in ids
    assert paid_then_cancelled.json()["id"] in ids

    doctor_list = client.get("/api/v1/appointments", headers=doctor_headers).json()
    doctor_ids = [a["id"] for a in doctor_list]
    assert abandoned.json()["id"] not in doctor_ids
    assert paid_then_cancelled.json()["id"] in doctor_ids


def test_complete_appointment_notifies_the_owner(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    owner_headers = create_owner(client, "00013")
    doctor_headers, _ = create_doctor(client, db_session, "00013")
    booked = book(client, owner_headers)
    appointment_id = booked.json()["id"]
    pay(client, owner_headers, appointment_id, monkeypatch)

    completed = client.post(
        f"/api/v1/appointments/{appointment_id}/complete", headers=doctor_headers
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    owner_notifications = client.get("/api/v1/notifications", headers=owner_headers).json()
    assert owner_notifications[0]["title"] == "Consultation completed"


def test_only_confirmed_appointment_can_be_completed(
    client: TestClient, db_session: Session
) -> None:
    owner_headers = create_owner(client, "00014")
    doctor_headers, _ = create_doctor(client, db_session, "00014")
    booked = book(client, owner_headers)

    response = client.post(
        f"/api/v1/appointments/{booked.json()['id']}/complete", headers=doctor_headers
    )
    assert response.status_code == 409


def test_cancel_appointment_notifies_the_doctor(client: TestClient, db_session: Session) -> None:
    owner_headers = create_owner(client, "00011")
    doctor_headers, _ = create_doctor(client, db_session, "00011")
    booked = book(client, owner_headers)

    client.post(
        f"/api/v1/appointments/{booked.json()['id']}/cancel",
        json={"reason": "Pet has recovered"},
        headers=owner_headers,
    )

    doctor_notifications = client.get("/api/v1/notifications", headers=doctor_headers).json()
    assert doctor_notifications[0]["title"] == "Appointment cancelled"


def test_cannot_confirm_payment_on_a_cancelled_appointment(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    owner_headers = create_owner(client, "00012")
    create_doctor(client, db_session, "00012")
    booked = book(client, owner_headers)
    appointment_id = booked.json()["id"]

    import app.api.routes.payments as payments_module

    monkeypatch.setattr(payments_module, "razorpay_client", lambda: FakeRazorpayClient())
    order = client.post(
        f"/api/v1/appointments/{appointment_id}/payment/order", headers=owner_headers
    )
    assert order.status_code == 200

    cancelled = client.post(
        f"/api/v1/appointments/{appointment_id}/cancel",
        json={"reason": "Changed my mind"},
        headers=owner_headers,
    )
    assert cancelled.status_code == 200

    verify = client.post(
        f"/api/v1/appointments/{appointment_id}/payment/verify",
        json={
            "razorpay_order_id": order.json()["order_id"],
            "razorpay_payment_id": "pay_test123",
            "razorpay_signature": "signature_test123",
        },
        headers=owner_headers,
    )
    assert verify.status_code == 409

    appointment = client.get(f"/api/v1/appointments/{appointment_id}", headers=owner_headers)
    assert appointment.json()["status"] == "cancelled"
    assert appointment.json()["payment_status"] == "pending"


def test_create_payment_link_returns_a_hosted_checkout_url(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.api.routes.payments as payments_module

    owner_headers = create_owner(client, "00013")
    create_doctor(client, db_session, "00013")
    appointment_id = book(client, owner_headers).json()["id"]

    monkeypatch.setattr(payments_module, "razorpay_client", lambda: FakeRazorpayClient())
    response = client.post(
        f"/api/v1/appointments/{appointment_id}/payment/link", headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["payment_link_url"] == f"https://rzp.io/i/{appointment_id}"


def test_payment_link_callback_confirms_appointment_on_valid_signature(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.api.routes.payments as payments_module

    owner_headers = create_owner(client, "00014")
    create_doctor(client, db_session, "00014")
    appointment_id = book(client, owner_headers).json()["id"]

    monkeypatch.setattr(payments_module, "razorpay_client", lambda: FakeRazorpayClient())
    callback = client.get(
        f"/api/v1/appointments/{appointment_id}/payment/link-callback",
        params={
            "razorpay_payment_id": "pay_test123",
            "razorpay_payment_link_id": "plink_test123",
            "razorpay_payment_link_reference_id": appointment_id,
            "razorpay_payment_link_status": "paid",
            "razorpay_signature": "signature_test123",
        },
        follow_redirects=False,
    )
    assert callback.status_code in (302, 307)
    assert callback.headers["location"] == (
        f"madinavetpet://payment-complete?appointment_id={appointment_id}&status=success"
    )

    appointment = client.get(f"/api/v1/appointments/{appointment_id}", headers=owner_headers)
    assert appointment.json()["payment_status"] == "paid"
    assert appointment.json()["status"] == "confirmed"


def test_payment_link_callback_rejects_invalid_signature(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.api.routes.payments as payments_module

    owner_headers = create_owner(client, "00015")
    create_doctor(client, db_session, "00015")
    appointment_id = book(client, owner_headers).json()["id"]

    monkeypatch.setattr(
        payments_module, "razorpay_client", lambda: FakeRazorpayClient(link_signature_valid=False)
    )
    callback = client.get(
        f"/api/v1/appointments/{appointment_id}/payment/link-callback",
        params={
            "razorpay_payment_id": "pay_test123",
            "razorpay_payment_link_id": "plink_test123",
            "razorpay_payment_link_reference_id": appointment_id,
            "razorpay_payment_link_status": "paid",
            "razorpay_signature": "forged",
        },
        follow_redirects=False,
    )
    assert callback.headers["location"] == (
        f"madinavetpet://payment-complete?appointment_id={appointment_id}&status=failed"
    )

    appointment = client.get(f"/api/v1/appointments/{appointment_id}", headers=owner_headers)
    assert appointment.json()["payment_status"] == "pending"


def test_payment_link_callback_rejects_mismatched_reference_id(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    import app.api.routes.payments as payments_module

    owner_headers = create_owner(client, "00016")
    create_doctor(client, db_session, "00016")
    appointment_id = book(client, owner_headers).json()["id"]

    monkeypatch.setattr(payments_module, "razorpay_client", lambda: FakeRazorpayClient())
    callback = client.get(
        f"/api/v1/appointments/{appointment_id}/payment/link-callback",
        params={
            "razorpay_payment_id": "pay_test123",
            "razorpay_payment_link_id": "plink_test123",
            "razorpay_payment_link_reference_id": "some-other-appointment-id",
            "razorpay_payment_link_status": "paid",
            "razorpay_signature": "signature_test123",
        },
        follow_redirects=False,
    )
    assert callback.headers["location"] == (
        f"madinavetpet://payment-complete?appointment_id={appointment_id}&status=failed"
    )

    appointment = client.get(f"/api/v1/appointments/{appointment_id}", headers=owner_headers)
    assert appointment.json()["payment_status"] == "pending"
