from pydantic import BaseModel, ConfigDict, Field

from app.models.domain import UserRole


class OtpRequest(BaseModel):
    mobile_number: str = Field(min_length=6, max_length=20)


class OtpRequestResponse(BaseModel):
    expires_in: int
    dev_otp: str | None = None


class OtpVerify(BaseModel):
    mobile_number: str = Field(min_length=6, max_length=20)
    code: str = Field(min_length=4, max_length=6)
    full_name: str | None = Field(default=None, min_length=2, max_length=160)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mobile_number: str
    full_name: str
    role: UserRole
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

