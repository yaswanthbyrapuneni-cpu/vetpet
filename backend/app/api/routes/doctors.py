from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.models.domain import (
    DoctorAvailability,
    DoctorProfile,
    User,
    UserRole,
    VerificationStatus,
)
from app.schemas.doctor import (
    AvailabilityCreate,
    AvailabilityResponse,
    DoctorProfileResponse,
    DoctorProfileUpdate,
)

router = APIRouter(prefix="/doctors")
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]


def get_doctor_profile(user: User, db: DbSession) -> DoctorProfile:
    profile = db.scalar(select(DoctorProfile).where(DoctorProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    return profile


@router.get("", response_model=list[DoctorProfileResponse])
def list_verified_doctors(
    db: DbSession,
    specialization: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DoctorProfile]:
    statement = select(DoctorProfile).where(
        DoctorProfile.verification_status == VerificationStatus.VERIFIED
    )
    if specialization:
        statement = statement.where(DoctorProfile.specialization == specialization)
    statement = statement.order_by(DoctorProfile.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement))


@router.get("/me", response_model=DoctorProfileResponse)
def read_own_profile(doctor: DoctorUser, db: DbSession) -> DoctorProfile:
    return get_doctor_profile(doctor, db)


@router.patch("/me", response_model=DoctorProfileResponse)
def update_own_profile(
    payload: DoctorProfileUpdate, doctor: DoctorUser, db: DbSession
) -> DoctorProfile:
    profile = get_doctor_profile(doctor, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/me/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: AvailabilityCreate, doctor: DoctorUser, db: DbSession
) -> DoctorAvailability:
    profile = get_doctor_profile(doctor, db)
    if payload.starts_at.astimezone(UTC) <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Availability must start in the future")
    overlap = db.scalar(
        select(DoctorAvailability).where(
            DoctorAvailability.doctor_id == profile.id,
            DoctorAvailability.starts_at < payload.ends_at,
            DoctorAvailability.ends_at > payload.starts_at,
        )
    )
    if overlap is not None:
        raise HTTPException(status_code=409, detail="Availability overlaps an existing slot")
    slot = DoctorAvailability(
        doctor_id=profile.id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/me/availability", response_model=list[AvailabilityResponse])
def list_own_availability(doctor: DoctorUser, db: DbSession) -> list[DoctorAvailability]:
    profile = get_doctor_profile(doctor, db)
    statement = (
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == profile.id)
        .order_by(DoctorAvailability.starts_at)
    )
    return list(db.scalars(statement))


@router.delete("/me/availability/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    slot_id: str, doctor: DoctorUser, db: DbSession
) -> Response:
    profile = get_doctor_profile(doctor, db)
    slot = db.scalar(
        select(DoctorAvailability).where(
            DoctorAvailability.id == slot_id,
            DoctorAvailability.doctor_id == profile.id,
        )
    )
    if slot is None:
        raise HTTPException(status_code=404, detail="Availability slot not found")
    if slot.is_booked:
        raise HTTPException(status_code=409, detail="Booked availability cannot be deleted")
    db.delete(slot)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{doctor_id}", response_model=DoctorProfileResponse)
def read_verified_doctor(doctor_id: str, db: DbSession) -> DoctorProfile:
    profile = db.scalar(
        select(DoctorProfile).where(
            DoctorProfile.id == doctor_id,
            DoctorProfile.verification_status == VerificationStatus.VERIFIED,
        )
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return profile


@router.get("/{doctor_id}/availability", response_model=list[AvailabilityResponse])
def read_public_availability(doctor_id: str, db: DbSession) -> list[DoctorAvailability]:
    verified = db.scalar(
        select(DoctorProfile.id).where(
            DoctorProfile.id == doctor_id,
            DoctorProfile.verification_status == VerificationStatus.VERIFIED,
        )
    )
    if verified is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    statement = (
        select(DoctorAvailability)
        .where(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.is_booked.is_(False),
            DoctorAvailability.starts_at > datetime.now(UTC),
        )
        .order_by(DoctorAvailability.starts_at)
    )
    return list(db.scalars(statement))

