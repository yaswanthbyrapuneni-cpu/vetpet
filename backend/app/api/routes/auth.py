from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.domain import DoctorProfile, User, UserRole
from app.schemas.auth import (
    DoctorRegistration,
    DoctorRegistrationResponse,
    LoginRequest,
    OwnerRegistration,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth")


def normalized_email(email: str) -> str:
    return email.strip().lower()


def ensure_email_available(db: DbSession, email: str) -> None:
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )


@router.post(
    "/register/owner",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_owner(payload: OwnerRegistration, db: DbSession) -> User:
    email = normalized_email(str(payload.email))
    ensure_email_available(db, email)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        role=UserRole.OWNER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from error
    db.refresh(user)
    return user


@router.post(
    "/register/doctor",
    response_model=DoctorRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_doctor(payload: DoctorRegistration, db: DbSession) -> DoctorRegistrationResponse:
    email = normalized_email(str(payload.email))
    ensure_email_available(db, email)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        role=UserRole.DOCTOR,
    )
    profile = DoctorProfile(
        user=user,
        license_number=payload.license_number.strip(),
        qualification=payload.qualification.strip(),
        specialization=payload.specialization,
        experience_years=payload.experience_years,
        hospital_name=payload.hospital_name,
    )
    db.add_all([user, profile])
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or license number is already registered",
        ) from error
    db.refresh(user)
    db.refresh(profile)
    return DoctorRegistrationResponse(
        user=UserResponse.model_validate(user),
        verification_status=profile.verification_status,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    email = normalized_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    access_token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def read_current_user(user: CurrentUser) -> User:
    return user
