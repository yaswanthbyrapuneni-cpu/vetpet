from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.domain import NotificationType, ReminderType


class ReminderCreate(BaseModel):
    reminder_type: ReminderType
    title: str = Field(min_length=2, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    scheduled_for: datetime
    repeat_interval_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> "ReminderCreate":
        if self.scheduled_for.tzinfo is None:
            raise ValueError("Reminder time must include a timezone")
        if self.scheduled_for.astimezone(UTC) <= datetime.now(UTC):
            raise ValueError("Reminder time must be in the future")
        if self.ends_at is not None:
            if self.ends_at.tzinfo is None:
                raise ValueError("Reminder end must include a timezone")
            if self.ends_at <= self.scheduled_for:
                raise ValueError("Reminder end must be after its first occurrence")
        if self.repeat_interval_hours is None and self.ends_at is not None:
            raise ValueError("A one-time reminder cannot have a recurrence end")
        return self


class ReminderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    scheduled_for: datetime | None = None
    repeat_interval_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    ends_at: datetime | None = None


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    pet_id: str
    reminder_type: ReminderType
    title: str
    message: str | None
    scheduled_for: datetime
    repeat_interval_hours: int | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    notification_type: NotificationType
    title: str
    message: str
    data: dict[str, object]
    created_at: datetime
    read_at: datetime | None

