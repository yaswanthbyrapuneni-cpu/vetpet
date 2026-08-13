from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.domain import UserRole, VerificationStatus


class OwnerRegistration(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=32)


class DoctorRegistration(OwnerRegistration):
    license_number: str = Field(min_length=3, max_length=100)
    qualification: str = Field(min_length=2, max_length=255)
    specialization: str | None = Field(default=None, max_length=160)
    experience_years: int = Field(default=0, ge=0, le=80)
    hospital_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    is_email_verified: bool


class DoctorRegistrationResponse(BaseModel):
    user: UserResponse
    verification_status: VerificationStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

