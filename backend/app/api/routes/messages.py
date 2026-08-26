from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession
from app.api.routes.appointments import (
    accessible_appointment,
    ensure_paid_appointment,
    scoped_appointments,
)
from app.models.domain import (
    AppointmentAttachment,
    AppointmentMessage,
    DoctorProfile,
    Pet,
    PetSpecies,
    User,
)
from app.schemas.message import (
    AppointmentThreadSummary,
    MessageCreate,
    MessageResponse,
    ThreadPreview,
)
from app.services.notifications import appointment_participant_user_ids
from app.services.realtime import event_hub

router = APIRouter()


@router.post(
    "/appointments/{appointment_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    appointment_id: str, payload: MessageCreate, user: CurrentUser, db: DbSession
) -> AppointmentMessage:
    appointment = accessible_appointment(db, appointment_id, user)
    ensure_paid_appointment(appointment, user)
    message = AppointmentMessage(
        appointment_id=appointment.id,
        sender_user_id=user.id,
        body=payload.body.strip(),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    recipients = appointment_participant_user_ids(db, appointment)
    await event_hub.send_to_users(
        recipients,
        {
            "type": "chat_message",
            "appointment_id": appointment.id,
            "message": MessageResponse.model_validate(message).model_dump(mode="json"),
        },
    )
    return message


@router.get(
    "/appointments/{appointment_id}/messages",
    response_model=list[MessageResponse],
)
def list_messages(
    appointment_id: str, user: CurrentUser, db: DbSession
) -> list[AppointmentMessage]:
    appointment = accessible_appointment(db, appointment_id, user)
    ensure_paid_appointment(appointment, user)
    statement = (
        select(AppointmentMessage)
        .where(AppointmentMessage.appointment_id == appointment.id)
        .order_by(AppointmentMessage.created_at)
    )
    return list(db.scalars(statement))


def _latest_by_appointment(db: Session, model, appointment_ids: list[str]) -> dict[str, object]:
    if not appointment_ids:
        return {}
    latest = (
        select(model.appointment_id, func.max(model.created_at).label("max_created"))
        .where(model.appointment_id.in_(appointment_ids))
        .group_by(model.appointment_id)
        .subquery()
    )
    rows = db.scalars(
        select(model).join(
            latest,
            (model.appointment_id == latest.c.appointment_id)
            & (model.created_at == latest.c.max_created),
        )
    )
    return {row.appointment_id: row for row in rows}


@router.get("/messages/threads", response_model=list[AppointmentThreadSummary])
def list_message_threads(user: CurrentUser, db: DbSession) -> list[AppointmentThreadSummary]:
    appointments = list(db.scalars(scoped_appointments(db, user)))
    if not appointments:
        return []
    appointment_ids = [a.id for a in appointments]

    last_messages = _latest_by_appointment(db, AppointmentMessage, appointment_ids)
    last_attachments = _latest_by_appointment(db, AppointmentAttachment, appointment_ids)

    pet_ids = {a.pet_id for a in appointments}
    pets = {p.id: p for p in db.scalars(select(Pet).where(Pet.id.in_(pet_ids)))}
    doctors = {
        d.id: d
        for d in db.scalars(
            select(DoctorProfile).where(DoctorProfile.id.in_({a.doctor_id for a in appointments}))
        )
    }
    user_ids = {p.owner_id for p in pets.values()} | {d.user_id for d in doctors.values()}
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids)))}

    summaries = []
    for appt in appointments:
        pet = pets.get(appt.pet_id)
        doctor = doctors.get(appt.doctor_id)
        owner = users.get(pet.owner_id) if pet else None
        doctor_user = users.get(doctor.user_id) if doctor else None

        last_message = last_messages.get(appt.id)
        last_attachment = last_attachments.get(appt.id)
        preview: ThreadPreview | None = None
        last_activity = appt.created_at
        if last_message is not None and (
            last_attachment is None or last_message.created_at >= last_attachment.created_at
        ):
            preview = ThreadPreview(
                kind="message",
                text=last_message.body,
                created_at=last_message.created_at,
                sender_user_id=last_message.sender_user_id,
            )
            last_activity = last_message.created_at
        elif last_attachment is not None:
            preview = ThreadPreview(
                kind=last_attachment.kind.value,
                text=None,
                created_at=last_attachment.created_at,
                sender_user_id=last_attachment.uploaded_by_user_id,
            )
            last_activity = last_attachment.created_at

        summaries.append(
            AppointmentThreadSummary(
                appointment_id=appt.id,
                pet_name=pet.name if pet else "Pet",
                species=pet.species if pet else PetSpecies.OTHER,
                owner_name=owner.full_name if owner else "Pet owner",
                doctor_name=doctor_user.full_name if doctor_user else "Veterinarian",
                status=appt.status,
                payment_status=appt.payment_status,
                consultation_type=appt.consultation_type,
                last_activity_at=last_activity,
                preview=preview,
            )
        )
    summaries.sort(key=lambda s: s.last_activity_at, reverse=True)
    return summaries
