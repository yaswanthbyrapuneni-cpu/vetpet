from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.domain import VerificationStatus
from app.schemas.auth import UserResponse


class DoctorProfileUpdate(BaseModel):
    qualification: str | None = Field(default=None, min_length=2, max_length=255)
    specialization: str | None = Field(default=None, max_length=160)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    hospital_name: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=3000)


class DoctorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user: UserResponse
    license_number: str
    qualification: str
    specialization: str | None
    experience_years: int
    hospital_name: str | None
    bio: str | None
    verification_status: VerificationStatus
    verification_note: str | None


class AvailabilityCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "AvailabilityCreate":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Availability times must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("Availability end must be after start")
        return self


class AvailabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    starts_at: datetime
    ends_at: datetime
    is_booked: bool


class VerificationDecision(StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"


class DoctorVerificationRequest(BaseModel):
    decision: VerificationDecision
    note: str | None = Field(default=None, max_length=1000)

