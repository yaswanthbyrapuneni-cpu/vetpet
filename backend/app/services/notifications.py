from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    Appointment,
    DoctorProfile,
    Notification,
    NotificationType,
    Pet,
    Reminder,
)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def make_notification(
    db: Session,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    message: str,
    data: dict[str, object] | None = None,
    reminder_id: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        reminder_id=reminder_id,
        notification_type=notification_type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notification)
    return notification


def notification_user_for_doctor(db: Session, doctor_id: str) -> str | None:
    return db.scalar(select(DoctorProfile.user_id).where(DoctorProfile.id == doctor_id))


def appointment_participant_user_ids(db: Session, appointment: Appointment) -> list[str]:
    """The pet owner's and assigned doctor's user ids, for pushing live events to both sides."""
    row = db.execute(
        select(Pet.owner_id, DoctorProfile.user_id)
        .select_from(Appointment)
        .join(Pet, Pet.id == Appointment.pet_id)
        .join(DoctorProfile, DoctorProfile.id == Appointment.doctor_id)
        .where(Appointment.id == appointment.id)
    ).one_or_none()
    if row is None:
        return []
    return [uid for uid in row if uid]


def materialize_due_reminders(db: Session, user_id: str) -> int:
    now = datetime.now(UTC)
    reminders = list(
        db.scalars(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.is_active.is_(True),
                Reminder.scheduled_for <= now,
            )
        )
    )
    for reminder in reminders:
        make_notification(
            db,
            reminder.user_id,
            NotificationType.REMINDER,
            reminder.title,
            reminder.message or "A pet-care reminder is due.",
            data={"pet_id": reminder.pet_id, "reminder_type": reminder.reminder_type.value},
            reminder_id=reminder.id,
        )
        if reminder.repeat_interval_hours is None:
            reminder.is_active = False
            continue
        interval = timedelta(hours=reminder.repeat_interval_hours)
        next_time = as_utc(reminder.scheduled_for)
        while next_time <= now:
            next_time += interval
        if reminder.ends_at is not None and next_time > as_utc(reminder.ends_at):
            reminder.is_active = False
        else:
            reminder.scheduled_for = next_time
    if reminders:
        db.commit()
    return len(reminders)
