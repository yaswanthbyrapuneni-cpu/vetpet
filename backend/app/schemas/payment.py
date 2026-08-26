from pydantic import BaseModel, Field

from app.models.domain import PaymentStatus


class PaymentOrderResponse(BaseModel):
    order_id: str
    amount_paise: int
    currency: str = "INR"
    key_id: str


class PaymentVerification(BaseModel):
    razorpay_order_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    razorpay_signature: str = Field(min_length=1)


class PaymentStatusResponse(BaseModel):
    appointment_id: str
    payment_status: PaymentStatus
    payment_amount_paise: int
