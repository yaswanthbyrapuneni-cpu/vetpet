from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    Consultation,
    DoctorProfile,
    NotificationType,
    Pet,
    Prescription,
    PrescriptionItem,
    Reminder,
    ReminderType,
    User,
    UserRole,
)
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationUpdate,
    DoctorConsultationResponse,
    OwnerConsultationResponse,
    PrescriptionResponse,
    PrescriptionWrite,
)
from app.services.notifications import make_notification

router = APIRouter()
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]


def doctor_profile(db: Session, user_id: str) -> DoctorProfile:
    profile = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return profile


def assigned_appointment(db: Session, appointment_id: str, user_id: str) -> Appointment:
    profile = doctor_profile(db, user_id)
    appointment = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.doctor_id == profile.id,
        )
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def assigned_consultation(db: Session, consultation_id: str, user_id: str) -> Consultation:
    profile = doctor_profile(db, user_id)
    consultation = db.scalar(
        select(Consultation)
        .join(Appointment, Appointment.id == Consultation.appointment_id)
        .where(Consultation.id == consultation_id, Appointment.doctor_id == profile.id)
    )
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


def accessible_consultation(
    db: Session, consultation_id: str, user: User
) -> Consultation:
    statement = (
        select(Consultation)
        .join(Appointment, Appointment.id == Consultation.appointment_id)
        .join(Pet, Pet.id == Appointment.pet_id)
        .where(Consultation.id == consultation_id)
    )
    if user.role == UserRole.OWNER:
        statement = statement.where(Pet.owner_id == user.id)
    elif user.role == UserRole.DOCTOR:
        profile = doctor_profile(db, user.id)
        statement = statement.where(Appointment.doctor_id == profile.id)
    consultation = db.scalar(statement)
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


def validate_follow_up(value: date | None) -> None:
    if value is not None and value < date.today():
        raise HTTPException(status_code=422, detail="Follow-up date cannot be in the past")


def sync_follow_up_reminder(
    db: Session, consultation: Consultation, created_by_user_id: str
) -> None:
    appointment = db.get(Appointment, consultation.appointment_id)
    if appointment is None:
        return
    pet = db.get(Pet, appointment.pet_id)
    if pet is None:
        return
    reminder = db.scalar(
        select(Reminder).where(Reminder.source_consultation_id == consultation.id)
    )
    if consultation.follow_up_date is None:
        if reminder is not None:
            reminder.is_active = False
        return
    scheduled_for = datetime.combine(consultation.follow_up_date, time(hour=9), UTC)
    if scheduled_for <= datetime.now(UTC):
        scheduled_for = datetime.now(UTC) + timedelta(minutes=5)
    if reminder is None:
        reminder = Reminder(
            user_id=pet.owner_id,
            pet_id=pet.id,
            source_consultation_id=consultation.id,
            created_by_user_id=created_by_user_id,
            reminder_type=ReminderType.FOLLOW_UP,
            title=f"Follow-up for {pet.name}",
            message="A veterinarian-recommended follow-up is due.",
            scheduled_for=scheduled_for,
        )
        db.add(reminder)
    else:
        reminder.scheduled_for = scheduled_for
        reminder.is_active = True


@router.post(
    "/appointments/{appointment_id}/consultation",
    response_model=DoctorConsultationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_consultation(
    appointment_id: str,
    payload: ConsultationCreate,
    doctor: DoctorUser,
    db: DbSession,
) -> Consultation:
    appointment = assigned_appointment(db, appointment_id, doctor.id)
    if appointment.status not in {AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED}:
        raise HTTPException(status_code=409, detail="Appointment is not ready for consultation")
    if db.scalar(select(Consultation.id).where(Consultation.appointment_id == appointment.id)):
        raise HTTPException(status_code=409, detail="Consultation already exists")
    validate_follow_up(payload.follow_up_date)
    consultation = Consultation(appointment_id=appointment.id, **payload.model_dump())
    db.add(consultation)
    db.flush()
    sync_follow_up_reminder(db, consultation, doctor.id)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get(
    "/appointments/{appointment_id}/consultation",
    response_model=OwnerConsultationResponse,
)
def read_appointment_consultation(
    appointment_id: str, user: CurrentUser, db: DbSession
) -> Consultation:
    statement = (
        select(Consultation)
        .join(Appointment, Appointment.id == Consultation.appointment_id)
        .join(Pet, Pet.id == Appointment.pet_id)
        .where(Appointment.id == appointment_id)
    )
    if user.role == UserRole.OWNER:
        statement = statement.where(Pet.owner_id == user.id)
    elif user.role == UserRole.DOCTOR:
        statement = statement.join(
            DoctorProfile, DoctorProfile.id == Appointment.doctor_id
        ).where(DoctorProfile.user_id == user.id)
    consultation = db.scalar(statement)
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")
    return consultation


@router.get("/doctor/consultations/{consultation_id}", response_model=DoctorConsultationResponse)
def read_doctor_consultation(
    consultation_id: str, doctor: DoctorUser, db: DbSession
) -> Consultation:
    return assigned_consultation(db, consultation_id, doctor.id)


@router.patch(
    "/doctor/consultations/{consultation_id}",
    response_model=DoctorConsultationResponse,
)
def update_consultation(
    consultation_id: str,
    payload: ConsultationUpdate,
    doctor: DoctorUser,
    db: DbSession,
) -> Consultation:
    consultation = assigned_consultation(db, consultation_id, doctor.id)
    validate_follow_up(payload.follow_up_date)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(consultation, field, value)
    sync_follow_up_reminder(db, consultation, doctor.id)
    db.commit()
    db.refresh(consultation)
    return consultation


def replace_prescription(
    db: Session, consultation: Consultation, payload: PrescriptionWrite
) -> Prescription:
    prescription = db.scalar(
        select(Prescription).where(Prescription.consultation_id == consultation.id)
    )
    if prescription is None:
        prescription = Prescription(consultation_id=consultation.id)
        db.add(prescription)
        db.flush()
    prescription.instructions = payload.instructions
    prescription.recommended_tests = payload.recommended_tests
    prescription.items.clear()
    prescription.items.extend(
        PrescriptionItem(**item.model_dump()) for item in payload.items
    )
    db.commit()
    db.refresh(prescription)
    return prescription


@router.put(
    "/doctor/consultations/{consultation_id}/prescription",
    response_model=PrescriptionResponse,
)
def write_prescription(
    consultation_id: str,
    payload: PrescriptionWrite,
    doctor: DoctorUser,
    db: DbSession,
) -> Prescription:
    consultation = assigned_consultation(db, consultation_id, doctor.id)
    prescription = replace_prescription(db, consultation, payload)
    appointment = db.get(Appointment, consultation.appointment_id)
    pet = db.get(Pet, appointment.pet_id) if appointment is not None else None
    if pet is not None:
        make_notification(
            db,
            pet.owner_id,
            NotificationType.PRESCRIPTION,
            "Prescription available",
            f"A veterinarian issued a prescription for {pet.name}.",
            {"consultation_id": consultation.id, "prescription_id": prescription.id},
        )
        db.commit()
    return prescription


@router.get(
    "/consultations/{consultation_id}/prescription",
    response_model=PrescriptionResponse,
)
def read_prescription(
    consultation_id: str, user: CurrentUser, db: DbSession
) -> Prescription:
    consultation = accessible_consultation(db, consultation_id, user)
    prescription = db.scalar(
        select(Prescription).where(Prescription.consultation_id == consultation.id)
    )
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription


def pdf_line(canvas: Canvas, text: str, y: float, bold: bool = False) -> float:
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", 10)
    canvas.drawString(50, y, text[:110])
    return y - 16


@router.get("/consultations/{consultation_id}/prescription.pdf")
def download_prescription_pdf(
    consultation_id: str, user: CurrentUser, db: DbSession
) -> Response:
    consultation = accessible_consultation(db, consultation_id, user)
    appointment = db.get(Appointment, consultation.appointment_id)
    prescription = db.scalar(
        select(Prescription).where(Prescription.consultation_id == consultation.id)
    )
    if appointment is None or prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    pet = db.get(Pet, appointment.pet_id)
    doctor = db.get(DoctorProfile, appointment.doctor_id)
    if pet is None or doctor is None:
        raise HTTPException(status_code=404, detail="Prescription details not found")

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    y = pdf_line(canvas, "VetPet Connect - Veterinary Prescription", 800, bold=True)
    y = pdf_line(canvas, f"Pet: {pet.name} ({pet.species})", y)
    y = pdf_line(canvas, f"Veterinarian: {doctor.user.full_name}", y)
    y = pdf_line(canvas, f"Qualification: {doctor.qualification}", y)
    y = pdf_line(canvas, f"Issued: {prescription.issued_at.date().isoformat()}", y)
    y -= 8
    y = pdf_line(canvas, f"Diagnosis: {consultation.diagnosis or 'Not specified'}", y, bold=True)
    for index, item in enumerate(prescription.items, start=1):
        y = pdf_line(canvas, f"{index}. {item.medicine_name} - {item.dosage}", y, bold=True)
        directions = (
            f"   {item.frequency} for {item.duration}; "
            f"route: {item.route or 'as directed'}"
        )
        y = pdf_line(canvas, directions, y)
    if prescription.recommended_tests:
        y = pdf_line(canvas, "Recommended tests: " + ", ".join(prescription.recommended_tests), y)
    if prescription.instructions:
        pdf_line(canvas, "Instructions: " + prescription.instructions, y)
    canvas.save()
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="prescription-{consultation.id}.pdf"'
            )
        },
    )
