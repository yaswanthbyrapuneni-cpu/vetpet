from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.domain import AttachmentKind


class AppointmentAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    uploaded_by_user_id: str
    kind: AttachmentKind
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
