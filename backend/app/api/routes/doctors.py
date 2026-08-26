from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.api.routes.appointments import find_primary_doctor
from app.models.domain import DoctorProfile, User, UserRole, VerificationStatus
from app.schemas.doctor import (
    DoctorProfileResponse,
    DoctorProfileUpdate,
    DoctorStatusUpdate,
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


@router.get("/primary", response_model=DoctorProfileResponse)
def read_primary_doctor(db: DbSession) -> DoctorProfile:
    profile = find_primary_doctor(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="No verified doctor is configured yet")
    return profile


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


@router.patch("/me/status", response_model=DoctorProfileResponse)
def update_own_status(
    payload: DoctorStatusUpdate, doctor: DoctorUser, db: DbSession
) -> DoctorProfile:
    profile = get_doctor_profile(doctor, db)
    profile.is_online = payload.is_online
    db.commit()
    db.refresh(profile)
    return profile


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
