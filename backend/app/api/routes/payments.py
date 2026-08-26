import ssl
from functools import lru_cache
from typing import Annotated

import razorpay
import truststore
from fastapi import APIRouter, Depends, HTTPException, status
from requests.adapters import HTTPAdapter

from app.api.dependencies import DbSession, require_roles
from app.api.routes.appointments import get_owner_appointment
from app.core.config import get_settings
from app.models.domain import (
    AppointmentStatus,
    NotificationType,
    PaymentStatus,
    User,
    UserRole,
    utc_now,
)
from app.schemas.payment import PaymentOrderResponse, PaymentStatusResponse, PaymentVerification
from app.services.notifications import make_notification, notification_user_for_doctor
from app.services.realtime import event_hub

router = APIRouter(prefix="/appointments")
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]

UNCONFIRMABLE_STATUSES = {AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED}


@lru_cache
def razorpay_client() -> razorpay.Client:
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured yet",
        )
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    # Some environments (corporate networks, security software doing TLS
    # inspection) install a root certificate the OS trusts but that
    # razorpay's bundled CA file doesn't know about. Verify against the OS
    # trust store instead: mount an adapter with a truststore-backed SSL
    # context, and clear cert_path so the SDK stops passing an explicit CA
    # file per request (which would otherwise override the adapter's context).
    client.cert_path = True
    adapter = HTTPAdapter()
    adapter.init_poolmanager(
        connections=10, maxsize=10, ssl_context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    )
    client.session.mount("https://", adapter)
    return client


@router.post("/{appointment_id}/payment/order", response_model=PaymentOrderResponse)
def create_payment_order(
    appointment_id: str, owner: OwnerUser, db: DbSession
) -> PaymentOrderResponse:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=409, detail="Appointment is already paid")
    if appointment.status in UNCONFIRMABLE_STATUSES:
        raise HTTPException(status_code=409, detail="This appointment is no longer active")

    client = razorpay_client()
    order = client.order.create(
        {
            "amount": appointment.payment_amount_paise,
            "currency": "INR",
            "receipt": appointment.id,
            "notes": {"appointment_id": appointment.id},
        }
    )
    appointment.razorpay_order_id = order["id"]
    db.commit()

    return PaymentOrderResponse(
        order_id=order["id"],
        amount_paise=appointment.payment_amount_paise,
        key_id=get_settings().razorpay_key_id,
    )


@router.post("/{appointment_id}/payment/verify", response_model=PaymentStatusResponse)
async def verify_payment(
    appointment_id: str, payload: PaymentVerification, owner: OwnerUser, db: DbSession
) -> PaymentStatusResponse:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.status in UNCONFIRMABLE_STATUSES:
        # The owner cancelled (or the doctor rejected) this appointment after the Razorpay
        # checkout was already open elsewhere. Refuse to resurrect it — reconciling the
        # payment itself (refund) is a manual/ops step until a webhook-driven flow exists.
        raise HTTPException(
            status_code=409, detail="This appointment was cancelled and cannot be confirmed"
        )
    if appointment.razorpay_order_id != payload.razorpay_order_id:
        raise HTTPException(status_code=409, detail="Order does not match this appointment")

    client = razorpay_client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }
        )
    except razorpay.errors.SignatureVerificationError as error:
        appointment.payment_status = PaymentStatus.FAILED
        db.commit()
        raise HTTPException(status_code=400, detail="Payment signature verification failed") from error

    appointment.payment_status = PaymentStatus.PAID
    appointment.razorpay_payment_id = payload.razorpay_payment_id
    appointment.paid_at = utc_now()
    appointment.status = AppointmentStatus.CONFIRMED
    doctor_user_id = notification_user_for_doctor(db, appointment.doctor_id)
    if doctor_user_id:
        make_notification(
            db,
            doctor_user_id,
            NotificationType.APPOINTMENT,
            "New paid consultation",
            "A pet owner paid for a consultation and is waiting in your queue.",
            {"appointment_id": appointment.id},
        )
    db.commit()
    if doctor_user_id:
        await event_hub.send_to_user(doctor_user_id, {"type": "notification"})
    return PaymentStatusResponse(
        appointment_id=appointment.id,
        payment_status=appointment.payment_status,
        payment_amount_paise=appointment.payment_amount_paise,
    )
