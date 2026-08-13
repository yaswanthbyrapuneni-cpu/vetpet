from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, update

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.domain import Notification, Pet, Reminder, User, UserRole
from app.schemas.notification import (
    NotificationResponse,
    ReminderCreate,
    ReminderResponse,
    ReminderUpdate,
)
from app.services.notifications import materialize_due_reminders

router = APIRouter()
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]


def owned_pet(db: DbSession, pet_id: str, owner_id: str) -> Pet:
    pet = db.scalar(
        select(Pet).where(
            Pet.id == pet_id,
            Pet.owner_id == owner_id,
            Pet.is_archived.is_(False),
        )
    )
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def owned_reminder(db: DbSession, reminder_id: str, owner_id: str) -> Reminder:
    reminder = db.scalar(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == owner_id)
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.post(
    "/pets/{pet_id}/reminders",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reminder(
    pet_id: str, payload: ReminderCreate, owner: OwnerUser, db: DbSession
) -> Reminder:
    owned_pet(db, pet_id, owner.id)
    reminder = Reminder(
        user_id=owner.id,
        pet_id=pet_id,
        created_by_user_id=owner.id,
        **payload.model_dump(),
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/reminders", response_model=list[ReminderResponse])
def list_reminders(
    owner: OwnerUser,
    db: DbSession,
    active_only: bool = True,
) -> list[Reminder]:
    statement = select(Reminder).where(Reminder.user_id == owner.id)
    if active_only:
        statement = statement.where(Reminder.is_active.is_(True))
    return list(db.scalars(statement.order_by(Reminder.scheduled_for)))


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: str, payload: ReminderUpdate, owner: OwnerUser, db: DbSession
) -> Reminder:
    reminder = owned_reminder(db, reminder_id, owner.id)
    updates = payload.model_dump(exclude_unset=True)
    if "title" in updates and updates["title"] is None:
        raise HTTPException(status_code=422, detail="Reminder title cannot be null")
    if updates.get("scheduled_for") is not None:
        value = updates["scheduled_for"]
        if value.tzinfo is None or value.astimezone(UTC) <= datetime.now(UTC):
            raise HTTPException(
                status_code=422,
                detail="Reminder time must be future and timezone-aware",
            )
    scheduled_for = updates.get("scheduled_for", reminder.scheduled_for)
    repeat_interval = updates.get("repeat_interval_hours", reminder.repeat_interval_hours)
    ends_at = updates.get("ends_at", reminder.ends_at)
    if ends_at is not None:
        if "ends_at" in updates and ends_at.tzinfo is None:
            raise HTTPException(status_code=422, detail="Reminder end must include a timezone")
        scheduled_utc = (
            scheduled_for.replace(tzinfo=UTC)
            if scheduled_for.tzinfo is None
            else scheduled_for.astimezone(UTC)
        )
        ends_utc = (
            ends_at.replace(tzinfo=UTC)
            if ends_at.tzinfo is None
            else ends_at.astimezone(UTC)
        )
        if ends_utc <= scheduled_utc:
            raise HTTPException(status_code=422, detail="Reminder end must follow its start")
        if repeat_interval is None:
            raise HTTPException(status_code=422, detail="Only repeating reminders can have an end")
    for field, value in updates.items():
        setattr(reminder, field, value)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_reminder(
    reminder_id: str, owner: OwnerUser, db: DbSession
) -> Response:
    reminder = owned_reminder(db, reminder_id, owner.id)
    reminder.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(
    user: CurrentUser,
    db: DbSession,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Notification]:
    materialize_due_reminders(db, user.id)
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    statement = statement.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str, user: CurrentUser, db: DbSession
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(user: CurrentUser, db: DbSession) -> Response:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
