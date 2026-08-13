from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicalRecordType(StrEnum):
    VACCINATION = "vaccination"
    LAB_REPORT = "lab_report"
    CONSULTATION = "consultation"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    SURGERY = "surgery"
    OTHER = "other"


class MedicalRecordCreate(BaseModel):
    record_type: MedicalRecordType
    title: str = Field(min_length=2, max_length=200)
    details: str | None = Field(default=None, max_length=10000)
    occurred_on: date

    @field_validator("occurred_on")
    @classmethod
    def occurrence_cannot_be_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Medical record date cannot be in the future")
        return value


class MedicalRecordUpdate(BaseModel):
    record_type: MedicalRecordType | None = None
    title: str | None = Field(default=None, min_length=2, max_length=200)
    details: str | None = Field(default=None, max_length=10000)
    occurred_on: date | None = None

    @field_validator("occurred_on")
    @classmethod
    def occurrence_cannot_be_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("Medical record date cannot be in the future")
        return value


class MedicalDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    medical_record_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


class MedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pet_id: str
    recorded_by_user_id: str
    record_type: str
    title: str
    details: str | None
    occurred_on: date
    created_at: datetime
    updated_at: datetime
    documents: list[MedicalDocumentResponse]

