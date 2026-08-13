from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import AppointmentStatus


class AppointmentCreate(BaseModel):
    pet_id: str
    availability_id: str
    reason: str = Field(min_length=3, max_length=2000)
    consultation_type: str = Field(default="video", pattern="^(video|audio)$")


class AppointmentReschedule(BaseModel):
    availability_id: str


class AppointmentCancellation(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AppointmentDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pet_id: str
    doctor_id: str
    availability_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str
    consultation_type: str
    status: AppointmentStatus
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime

