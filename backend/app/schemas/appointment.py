from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import AppointmentStatus, PaymentStatus, PetSpecies


class AppointmentCreate(BaseModel):
    pet_name: str = Field(min_length=1, max_length=120)
    species: PetSpecies
    reason: str | None = Field(default=None, max_length=2000)


class AppointmentCancellation(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pet_id: str
    doctor_id: str
    species: PetSpecies
    owner_name: str
    owner_mobile_number: str
    scheduled_start: datetime
    reason: str
    consultation_type: str
    status: AppointmentStatus
    cancellation_reason: str | None
    payment_status: PaymentStatus
    payment_amount_paise: int
    paid_at: datetime | None
    razorpay_payment_id: str | None
    created_at: datetime
    updated_at: datetime
