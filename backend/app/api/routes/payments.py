import ssl
from functools import lru_cache
from typing import Annotated

import razorpay
import truststore
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from requests.adapters import HTTPAdapter
from sqlalchemy.orm import Session

from app.api.dependencies import DbSession, require_roles
from app.api.routes.appointments import get_owner_appointment
from app.core.config import get_settings
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    NotificationType,
    PaymentStatus,
    User,
    UserRole,
    utc_now,
)
from app.schemas.payment import (
    PaymentLinkResponse,
    PaymentOrderResponse,
    PaymentStatusResponse,
    PaymentVerification,
)
from app.services.notifications import make_notification, notification_user_for_doctor
from app.services.realtime import event_hub

router = APIRouter(prefix="/appointments")
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]

UNCONFIRMABLE_STATUSES = {AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED}

# The Android app opens payment in a real system browser tab (Chrome Custom
# Tabs) instead of its own embedded WebView — redirect-based payment methods
# (netbanking, UPI, wallets) proved unreliable inside a generic WebView even
# though they work fine in any normal browser. This scheme is registered in
# AndroidManifest.xml so Android hands the callback straight back to the app.
NATIVE_APP_CALLBACK_SCHEME = "madinavetpet://payment-complete"


async def _mark_appointment_paid(
    db: Session, appointment: Appointment, razorpay_payment_id: str
) -> None:
    appointment.payment_status = PaymentStatus.PAID
    appointment.razorpay_payment_id = razorpay_payment_id
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
        raise HTTPException(
            status_code=400, detail="Payment signature verification failed"
        ) from error

    await _mark_appointment_paid(db, appointment, payload.razorpay_payment_id)
    return PaymentStatusResponse(
        appointment_id=appointment.id,
        payment_status=appointment.payment_status,
        payment_amount_paise=appointment.payment_amount_paise,
    )


@router.post("/{appointment_id}/payment/link", response_model=PaymentLinkResponse)
def create_payment_link(
    appointment_id: str, owner: OwnerUser, db: DbSession, request: Request
) -> PaymentLinkResponse:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=409, detail="Appointment is already paid")
    if appointment.status in UNCONFIRMABLE_STATUSES:
        raise HTTPException(status_code=409, detail="This appointment is no longer active")

    client = razorpay_client()
    # request.base_url reflects whatever Host header the browser actually sent
    # (Caddy forwards it unchanged), so this keeps working unmodified whether
    # that's the bare IP today or a real domain once one exists.
    base_url = str(request.base_url).rstrip("/")
    callback_url = (
        f"{base_url}{get_settings().api_v1_prefix}"
        f"/appointments/{appointment.id}/payment/link-callback"
    )
    link = client.payment_link.create(
        {
            "amount": appointment.payment_amount_paise,
            "currency": "INR",
            "reference_id": appointment.id,
            "description": "Madina Vet Pet consultation fee",
            "callback_url": callback_url,
            "callback_method": "get",
            "notes": {"appointment_id": appointment.id},
        }
    )
    return PaymentLinkResponse(payment_link_url=link["short_url"])


@router.get("/{appointment_id}/payment/link-callback", include_in_schema=False)
async def payment_link_callback(
    appointment_id: str,
    db: DbSession,
    razorpay_payment_id: str,
    razorpay_payment_link_id: str,
    razorpay_payment_link_reference_id: str,
    razorpay_payment_link_status: str,
    razorpay_signature: str,
) -> RedirectResponse:
    # No bearer auth here on purpose: Razorpay's own redirect lands in the
    # user's browser tab, outside the app's authenticated session — the
    # HMAC signature (computable only with our key_secret) is what's
    # actually trusted here, the same as any payment-gateway webhook.
    outcome = "failed"
    appointment = db.get(Appointment, appointment_id)
    if (
        appointment is not None
        and razorpay_payment_link_reference_id == appointment.id
        and appointment.status not in UNCONFIRMABLE_STATUSES
    ):
        client = razorpay_client()
        try:
            client.utility.verify_payment_link_signature(
                {
                    "payment_link_id": razorpay_payment_link_id,
                    "payment_link_reference_id": razorpay_payment_link_reference_id,
                    "payment_link_status": razorpay_payment_link_status,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
            if razorpay_payment_link_status == "paid":
                await _mark_appointment_paid(db, appointment, razorpay_payment_id)
                outcome = "success"
        except razorpay.errors.SignatureVerificationError:
            pass
    return RedirectResponse(
        url=f"{NATIVE_APP_CALLBACK_SCHEME}?appointment_id={appointment_id}&status={outcome}"
    )
