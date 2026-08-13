from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.models.domain import DoctorProfile, User, UserRole, VerificationStatus, utc_now
from app.schemas.doctor import (
    DoctorProfileResponse,
    DoctorVerificationRequest,
    VerificationDecision,
)

router = APIRouter(prefix="/admin")
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("/doctors", response_model=list[DoctorProfileResponse])
def list_doctors_for_review(
    _: AdminUser,
    db: DbSession,
    verification_status: Annotated[VerificationStatus | None, Query()] = None,
) -> list[DoctorProfile]:
    statement = select(DoctorProfile)
    if verification_status is not None:
        statement = statement.where(DoctorProfile.verification_status == verification_status)
    return list(db.scalars(statement.order_by(DoctorProfile.created_at)))


@router.post("/doctors/{doctor_id}/verification", response_model=DoctorProfileResponse)
def review_doctor(
    doctor_id: str,
    payload: DoctorVerificationRequest,
    admin: AdminUser,
    db: DbSession,
) -> DoctorProfile:
    profile = db.get(DoctorProfile, doctor_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found")
    profile.verification_status = VerificationStatus(payload.decision.value)
    profile.verification_note = payload.note
    if payload.decision == VerificationDecision.VERIFIED:
        profile.verified_at = utc_now()
        profile.verified_by_user_id = admin.id
    else:
        profile.verified_at = None
        profile.verified_by_user_id = admin.id
    db.commit()
    db.refresh(profile)
    return profile
