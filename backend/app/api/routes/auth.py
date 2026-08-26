import re
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, generate_otp_code
from app.models.domain import OtpCode, User, UserRole, utc_now
from app.schemas.auth import OtpRequest, OtpRequestResponse, OtpVerify, TokenResponse, UserResponse
from app.services.notifications import as_utc
from app.services.sms import SmsDeliveryError, send_otp_sms

router = APIRouter(prefix="/auth")

LOGIN_PURPOSE = "login"
MAX_OTP_ATTEMPTS = 5
OTP_REQUEST_WINDOW_MINUTES = 15
MAX_OTP_REQUESTS_PER_WINDOW = 5


def normalized_mobile_number(mobile_number: str) -> str:
    # Same person can type their number as "9876543210", "+919876543210",
    # "09876543210", or with spaces/dashes — without a canonical form each
    # variant used to look up/create a *different* user, silently splitting
    # one owner's pets and history across duplicate accounts.
    digits = re.sub(r"[^\d+]", "", mobile_number.strip())
    had_plus = digits.startswith("+")
    digits = digits.lstrip("+")
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    return f"+{digits}" if had_plus else digits


@router.post("/otp/request", response_model=OtpRequestResponse)
def request_otp(payload: OtpRequest, db: DbSession) -> OtpRequestResponse:
    settings = get_settings()
    mobile_number = normalized_mobile_number(payload.mobile_number)

    # Without this, one caller could spam-generate codes for any number with no
    # limit — an annoyance today, and a way to run up an SMS bill or bomb a
    # stranger's phone once a real SMS gateway is wired in behind this endpoint.
    window_start = utc_now() - timedelta(minutes=OTP_REQUEST_WINDOW_MINUTES)
    recent_request_count = db.scalar(
        select(func.count())
        .select_from(OtpCode)
        .where(
            OtpCode.mobile_number == mobile_number,
            OtpCode.purpose == LOGIN_PURPOSE,
            OtpCode.created_at >= window_start,
        )
    )
    if recent_request_count is not None and recent_request_count >= MAX_OTP_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many codes requested for this number. Please try again later.",
        )

    stale_codes = db.scalars(
        select(OtpCode).where(
            OtpCode.mobile_number == mobile_number,
            OtpCode.purpose == LOGIN_PURPOSE,
            OtpCode.consumed_at.is_(None),
        )
    )
    for stale in stale_codes:
        stale.consumed_at = utc_now()

    code = generate_otp_code()
    otp = OtpCode(
        mobile_number=mobile_number,
        code=code,
        purpose=LOGIN_PURPOSE,
        expires_at=utc_now() + timedelta(seconds=settings.otp_expiry_seconds),
    )
    db.add(otp)
    db.commit()

    if not settings.otp_mock_mode:
        try:
            send_otp_sms(mobile_number, code)
        except SmsDeliveryError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to send the verification code. Please try again.",
            ) from error

    return OtpRequestResponse(
        expires_in=settings.otp_expiry_seconds,
        dev_otp=code if settings.otp_mock_mode else None,
    )


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(payload: OtpVerify, db: DbSession) -> TokenResponse:
    mobile_number = normalized_mobile_number(payload.mobile_number)

    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.mobile_number == mobile_number,
            OtpCode.purpose == LOGIN_PURPOSE,
            OtpCode.consumed_at.is_(None),
        )
        .order_by(OtpCode.created_at.desc())
    )
    invalid_code = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code"
    )
    if otp is None or as_utc(otp.expires_at) < utc_now() or otp.attempts >= MAX_OTP_ATTEMPTS:
        raise invalid_code
    if otp.code != payload.code:
        otp.attempts += 1
        db.commit()
        raise invalid_code

    user = db.scalar(select(User).where(User.mobile_number == mobile_number))
    if user is None and not payload.full_name:
        # Reject before consuming the code: a client-recoverable validation error
        # shouldn't burn a still-valid OTP the user could otherwise retry with.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="full_name is required to create a new account",
        )

    otp.consumed_at = utc_now()

    if user is None:
        user = User(
            mobile_number=mobile_number,
            full_name=payload.full_name.strip(),
            role=UserRole.OWNER,
        )
        db.add(user)
    elif not user.is_active:
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    db.commit()
    db.refresh(user)
    access_token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def read_current_user(user: CurrentUser) -> User:
    return user
