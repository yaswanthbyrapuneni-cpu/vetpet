from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser, DbSession, require_roles
from app.core.pricing import SPECIES_FEE_PAISE
from app.models.domain import (
    Appointment,
    AppointmentRating,
    AppointmentStatus,
    DoctorProfile,
    NotificationType,
    PaymentStatus,
    Pet,
    PetSpecies,
    User,
    UserRole,
    VerificationStatus,
    utc_now,
)
from app.schemas.appointment import (
    AppointmentCancellation,
    AppointmentCreate,
    AppointmentResponse,
)
from app.schemas.rating import RatingCreate, RatingResponse
from app.services.notifications import make_notification, notification_user_for_doctor
from app.services.realtime import event_hub

router = APIRouter(prefix="/appointments")
OwnerUser = Annotated[User, Depends(require_roles(UserRole.OWNER))]
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]


def find_or_create_pet(db: Session, owner_id: str, name: str, species: PetSpecies) -> Pet:
    normalized_name = name.strip()
    pet = db.scalar(
        select(Pet).where(
            Pet.owner_id == owner_id,
            Pet.is_archived.is_(False),
            Pet.species == species,
            func.lower(Pet.name) == normalized_name.lower(),
        )
    )
    if pet is not None:
        return pet
    pet = Pet(owner_id=owner_id, name=normalized_name, species=species)
    db.add(pet)
    db.flush()
    return pet


def find_primary_doctor(db: Session) -> DoctorProfile | None:
    return db.scalar(
        select(DoctorProfile)
        .where(DoctorProfile.verification_status == VerificationStatus.VERIFIED)
        .order_by(DoctorProfile.created_at)
    )


def get_primary_doctor(db: Session) -> DoctorProfile:
    profile = find_primary_doctor(db)
    if profile is None:
        raise HTTPException(status_code=409, detail="No verified doctor is available right now")
    return profile


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
    pet = find_or_create_pet(db, owner.id, payload.pet_name, payload.species)
    doctor = get_primary_doctor(db)
    appointment = Appointment(
        pet_id=pet.id,
        doctor_id=doctor.id,
        scheduled_start=utc_now(),
        reason=(payload.reason or "").strip() or "General consultation",
        consultation_type="video",
        payment_amount_paise=SPECIES_FEE_PAISE[pet.species],
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def scoped_appointments(db: Session, user: User) -> Select:
    """Appointments this user may see: their own bookings, their patients, or all for admins."""
    if user.role == UserRole.OWNER:
        return select(Appointment).join(Pet).where(Pet.owner_id == user.id)
    if user.role == UserRole.DOCTOR:
        profile = doctor_profile_for_user(db, user.id)
        return select(Appointment).where(Appointment.doctor_id == profile.id)
    return select(Appointment)


NEVER_HAPPENED_STATUSES = {
    AppointmentStatus.CANCELLED,
    AppointmentStatus.REJECTED,
    AppointmentStatus.NO_SHOW,
}


@router.get("", response_model=list[AppointmentResponse])
def list_my_appointments(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    status_in: Annotated[list[AppointmentStatus] | None, Query()] = None,
) -> list[Appointment]:
    statement = scoped_appointments(db, user).options(
        selectinload(Appointment.pet).selectinload(Pet.owner)
    )
    # An appointment cancelled/rejected/no-show before ever being paid is abandoned
    # booking debris, not a real historical record -- never list it for anyone.
    statement = statement.where(
        ~(
            Appointment.status.in_(NEVER_HAPPENED_STATUSES)
            & (Appointment.payment_status != PaymentStatus.PAID)
        )
    )
    if status_in:
        statement = statement.where(Appointment.status.in_(status_in))
    statement = statement.order_by(Appointment.scheduled_start.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement))


def ensure_paid_appointment(appointment: Appointment, user: User) -> None:
    """Chat/attachments only unlock after payment — enforce the advertised rule server-side too."""
    if user.role == UserRole.ADMIN:
        return
    if appointment.payment_status != PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Payment is required before chat or attachments unlock for this consultation",
        )


def accessible_appointment(db: Session, appointment_id: str, user: User) -> Appointment:
    if user.role == UserRole.OWNER:
        return get_owner_appointment(db, appointment_id, user.id)
    if user.role == UserRole.DOCTOR:
        profile = doctor_profile_for_user(db, user.id)
        return get_doctor_appointment(db, appointment_id, profile.id)
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def read_appointment(
    appointment_id: str, user: CurrentUser, db: DbSession
) -> Appointment:
    return accessible_appointment(db, appointment_id, user)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
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
    doctor_user_id = notification_user_for_doctor(db, appointment.doctor_id)
    if doctor_user_id:
        make_notification(
            db,
            doctor_user_id,
            NotificationType.APPOINTMENT,
            "Appointment cancelled",
            "A pet owner cancelled a consultation.",
            {"appointment_id": appointment.id},
        )
    db.commit()
    db.refresh(appointment)
    if doctor_user_id:
        await event_hub.send_to_user(
            doctor_user_id, {"type": "appointment_cancelled", "appointment_id": appointment.id}
        )
        await event_hub.send_to_user(doctor_user_id, {"type": "notification"})
    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: str, doctor: DoctorUser, db: DbSession
) -> Appointment:
    profile = doctor_profile_for_user(db, doctor.id)
    appointment = get_doctor_appointment(db, appointment_id, profile.id)
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=409, detail="Only confirmed appointments can be completed")
    appointment.status = AppointmentStatus.COMPLETED
    owner_user_id = db.scalar(select(Pet.owner_id).where(Pet.id == appointment.pet_id))
    if owner_user_id:
        make_notification(
            db,
            owner_user_id,
            NotificationType.APPOINTMENT,
            "Consultation completed",
            "Your consultation is complete. You can now rate your experience.",
            {"appointment_id": appointment.id},
        )
    db.commit()
    db.refresh(appointment)
    if owner_user_id:
        await event_hub.send_to_user(owner_user_id, {"type": "notification"})
        await event_hub.send_to_user(
            owner_user_id, {"type": "appointment_completed", "appointment_id": appointment.id}
        )
    return appointment


@router.post(
    "/{appointment_id}/rating", response_model=RatingResponse, status_code=status.HTTP_201_CREATED
)
def rate_appointment(
    appointment_id: str, payload: RatingCreate, owner: OwnerUser, db: DbSession
) -> AppointmentRating:
    appointment = get_owner_appointment(db, appointment_id, owner.id)
    if appointment.status != AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Only completed appointments can be rated")
    if db.scalar(select(AppointmentRating.id).where(AppointmentRating.appointment_id == appointment.id)):
        raise HTTPException(status_code=409, detail="This appointment has already been rated")
    rating = AppointmentRating(
        appointment_id=appointment.id,
        rated_by_user_id=owner.id,
        stars=payload.stars,
        tags=payload.tags,
        comment=payload.comment,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


@router.get("/{appointment_id}/rating", response_model=RatingResponse)
def read_rating(appointment_id: str, user: CurrentUser, db: DbSession) -> AppointmentRating:
    accessible_appointment(db, appointment_id, user)
    rating = db.scalar(select(AppointmentRating).where(AppointmentRating.appointment_id == appointment_id))
    if rating is None:
        raise HTTPException(status_code=404, detail="Rating not found")
    return rating
