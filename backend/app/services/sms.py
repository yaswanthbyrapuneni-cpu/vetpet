from functools import lru_cache

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.core.config import get_settings


class SmsDeliveryError(RuntimeError):
    pass


@lru_cache
def twilio_client() -> Client:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise SmsDeliveryError("Twilio is not configured (missing account SID or auth token).")
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send_otp_sms(mobile_number: str, code: str) -> None:
    settings = get_settings()
    if not settings.twilio_from_number:
        raise SmsDeliveryError("Twilio is not configured (missing sender number).")
    minutes = settings.otp_expiry_seconds // 60
    body = f"Your Madina Vet Pet verification code is {code}. It expires in {minutes} minutes."
    try:
        twilio_client().messages.create(
            to=mobile_number, from_=settings.twilio_from_number, body=body
        )
    except TwilioRestException as error:
        raise SmsDeliveryError(f"Twilio failed to send the verification code: {error}") from error
