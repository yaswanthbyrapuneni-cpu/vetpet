from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CallRecordingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    recorded_by_user_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    duration_seconds: int | None
    consent_confirmed_at: datetime
    created_at: datetime
