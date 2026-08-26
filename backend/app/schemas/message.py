from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import AppointmentStatus, PaymentStatus, PetSpecies


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    sender_user_id: str
    body: str
    created_at: datetime


class ThreadPreview(BaseModel):
    kind: Literal["message", "photo", "video", "voice"]
    text: str | None
    created_at: datetime
    sender_user_id: str


class AppointmentThreadSummary(BaseModel):
    appointment_id: str
    pet_name: str
    species: PetSpecies
    owner_name: str
    doctor_name: str
    status: AppointmentStatus
    payment_status: PaymentStatus
    consultation_type: str
    last_activity_at: datetime
    preview: ThreadPreview | None
