from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    DoctorAvailability,
    DoctorProfile,
    NotificationType,
    Pet,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.appointment import (
    AppointmentCancellation,
    AppointmentCreate,
    AppointmentDecision,
    AppointmentReschedule,
    AppointmentResponse,
)
from app.services.notifications import make_notification, notification_user_for_doctor

router = APIRouter(prefix="/appointments")
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_owned_pet(db: Session, pet_id: str, owner_id: str) -> Pet:
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


def get_open_slot(db: Session, slot_id: str) -> DoctorAvailability:
    slot = db.scalar(
        select(DoctorAvailability)
        .join(DoctorProfile, DoctorProfile.id == DoctorAvailability.doctor_id)
        .where(
            DoctorAvailability.id == slot_id,
            DoctorAvailability.is_booked.is_(False),
            DoctorAvailability.starts_at > datetime.now(UTC),
            DoctorProfile.verification_status == VerificationStatus.VERIFIED,
        )
        .with_for_update()
    )
    if slot is None:
        raise HTTPException(status_code=409, detail="Availability slot is no longer bookable")
    return slot


def get_owner_appointment(db: Session, appointment_id: str, owner_id: str) -> Appointment:
    appointment = db.scalar(
        select(Appointment)
        .join(Pet, Pet.id == Appointment.pet_id)
        .where(Appointment.id == appointment_id, Pet.owner_id == owner_id)
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


def doctor_profile_for_user(db: Session, user_id: str) -> DoctorProfile:
    profile = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return profile


def get_doctor_appointment(
    db: Session, appointment_id: str, doctor_id: str
) -> Appointment:
    appointment = db.scalar(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.doctor_id == doctor_id,
        )
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: AppointmentCreate, owner: OwnerUser, db: DbSession
) -> Appointment:
    get_owned_pet(db, payload.pet_id, owner.id)
    slot = get_open_slot(db, payload.availability_id)
    appointment = Appointment(
        pet_id=payload.pet_id,
        doctor_id=slot.doctor_id,
        availability_id=slot.id,
        scheduled_start=slot.starts_at,
        scheduled_end=slot.ends_at,
        reason=payload.reason.strip(),
        consultation_type=payload.consultation_type,
    )
    slot.is_booked = True
    db.add(appointment)
    doctor_user_id = notification_user_for_doctor(db, slot.doctor_id)
    if doctor_user_id:
        make_notification(
            db,
            doctor_user_id,
            NotificationType.APPOINTMENT,
            "New appointment request",
            f"A consultation was requested for {appointment.scheduled_start}.",
            {"appointment_id": appointment.id, "pet_id": appointment.pet_id},
        )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("", response_model=list[AppointmentResponse])
def list_my_appointments(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Appointment]:
    if user.role == UserRole.OWNER:
        statement = select(Appointment).join(Pet).where(Pet.owner_id == user.id)
    elif user.role == UserRole.DOCTOR:
        profile = doctor_profile_for_user(db, user.id)
        statement = select(Appointment).where(Appointment.doctor_id == profile.id)
    else:
        statement = select(Appointment)
    statement = statement.order_by(Appointment.scheduled_start.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def read_appointment(
    appointment_id: str, user: CurrentUser, db: DbSession
) -> Appointment:
    if user.role == UserRole.OWNER:
        return get_owner_appointment(db, appointment_id, user.id)
    if user.role == UserRole.DOCTOR:
        profile = doctor_profile_for_user(db, user.id)
        return get_doctor_appointment(db, appointment_id, profile.id)
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: str,
    payload: AppointmentCancellation,
    owner: OwnerUser,
    db: DbSession,
) -> Appointment:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.status not in {AppointmentStatus.REQUESTED, AppointmentStatus.CONFIRMED}:
        raise HTTPException(status_code=409, detail="Appointment cannot be cancelled")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = payload.reason.strip()
    slot = db.get(DoctorAvailability, appointment.availability_id)
    if slot is not None:
        slot.is_booked = False
    doctor_user_id = notification_user_for_doctor(db, appointment.doctor_id)
    if doctor_user_id:
        make_notification(
            db,
            doctor_user_id,
            NotificationType.APPOINTMENT,
            "Appointment cancelled",
            "The pet owner cancelled an appointment.",
            {"appointment_id": appointment.id},
        )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: str,
    payload: AppointmentReschedule,
    owner: OwnerUser,
    db: DbSession,
) -> Appointment:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.status not in {AppointmentStatus.REQUESTED, AppointmentStatus.CONFIRMED}:
        raise HTTPException(status_code=409, detail="Appointment cannot be rescheduled")
    new_slot = get_open_slot(db, payload.availability_id)
    old_slot = db.get(DoctorAvailability, appointment.availability_id)
    if old_slot is not None:
        old_slot.is_booked = False
    new_slot.is_booked = True
    appointment.doctor_id = new_slot.doctor_id
    appointment.availability_id = new_slot.id
    appointment.scheduled_start = new_slot.starts_at
    appointment.scheduled_end = new_slot.ends_at
    appointment.status = AppointmentStatus.REQUESTED
    appointment.cancellation_reason = None
    new_doctor_user_id = notification_user_for_doctor(db, new_slot.doctor_id)
    if new_doctor_user_id:
        make_notification(
            db,
            new_doctor_user_id,
            NotificationType.APPOINTMENT,
            "Appointment rescheduled",
            f"An appointment request moved to {new_slot.starts_at}.",
            {"appointment_id": appointment.id},
        )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment(
    appointment_id: str, _: AppointmentDecision, doctor: DoctorUser, db: DbSession
) -> Appointment:
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    if appointment.status != AppointmentStatus.REQUESTED:
        raise HTTPException(status_code=409, detail="Only requested appointments can be confirmed")
    appointment.status = AppointmentStatus.CONFIRMED
    pet = db.get(Pet, appointment.pet_id)
    if pet is not None:
        make_notification(
            db,
            pet.owner_id,
            NotificationType.APPOINTMENT,
            "Appointment confirmed",
            f"Your appointment for {pet.name} has been confirmed.",
            {"appointment_id": appointment.id, "pet_id": pet.id},
        )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/reject", response_model=AppointmentResponse)
def reject_appointment(
    appointment_id: str,
    payload: AppointmentDecision,
    doctor: DoctorUser,
    db: DbSession,
) -> Appointment:
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    if appointment.status != AppointmentStatus.REQUESTED:
        raise HTTPException(status_code=409, detail="Only requested appointments can be rejected")
    appointment.status = AppointmentStatus.REJECTED
    appointment.cancellation_reason = payload.reason
    slot = db.get(DoctorAvailability, appointment.availability_id)
    if slot is not None:
        slot.is_booked = False
    pet = db.get(Pet, appointment.pet_id)
    if pet is not None:
        make_notification(
            db,
            pet.owner_id,
            NotificationType.APPOINTMENT,
            "Appointment declined",
            payload.reason or "The veterinarian declined the appointment request.",
            {"appointment_id": appointment.id, "pet_id": pet.id},
        )
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    appointment_id: str, doctor: DoctorUser, db: DbSession
) -> Appointment:
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed appointments can be completed")
    if as_utc(appointment.scheduled_start) > datetime.now(UTC):
        raise HTTPException(status_code=409, detail="Appointment has not started yet")
    appointment.status = AppointmentStatus.COMPLETED
    db.commit()
    db.refresh(appointment)
    return appointment
