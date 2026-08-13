from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsultationCreate(BaseModel):
    diagnosis: str | None = Field(default=None, max_length=10000)
    doctor_notes: str | None = Field(default=None, max_length=20000)
    approved_summary: str | None = Field(default=None, max_length=10000)
    follow_up_date: date | None = None


class ConsultationUpdate(ConsultationCreate):
    pass


class OwnerConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    diagnosis: str | None
    approved_summary: str | None
    follow_up_date: date | None
    created_at: datetime
    updated_at: datetime


class DoctorConsultationResponse(OwnerConsultationResponse):
    doctor_notes: str | None
    transcript: str | None
    ai_summary_draft: str | None


class PrescriptionItemInput(BaseModel):
    medicine_name: str = Field(min_length=1, max_length=200)
    dosage: str = Field(min_length=1, max_length=120)
    frequency: str = Field(min_length=1, max_length=120)
    duration: str = Field(min_length=1, max_length=120)
    route: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)


class PrescriptionWrite(BaseModel):
    instructions: str | None = Field(default=None, max_length=5000)
    recommended_tests: list[str] = Field(default_factory=list, max_length=20)
    items: list[PrescriptionItemInput] = Field(min_length=1, max_length=30)


class PrescriptionItemResponse(PrescriptionItemInput):
    model_config = ConfigDict(from_attributes=True)

    id: str


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    consultation_id: str
    instructions: str | None
    recommended_tests: list[str]
    issued_at: datetime
    items: list[PrescriptionItemResponse]

