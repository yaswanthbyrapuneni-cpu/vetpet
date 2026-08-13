import hashlib
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.dependencies import DbSession, require_roles
from app.core.config import get_settings
from app.models.domain import Appointment, CallRecording, DoctorProfile, User, UserRole, utc_now
from app.schemas.recording import CallRecordingResponse

router = APIRouter(prefix="/recordings")
DoctorUser = Annotated[User, Depends(require_roles(UserRole.DOCTOR))]
allowed_types = {"video/webm": ".webm", "audio/webm": ".webm", "audio/ogg": ".ogg"}


def assigned_appointment(db: DbSession, appointment_id: str, doctor: User) -> Appointment:
    appointment = db.scalar(select(Appointment).join(DoctorProfile, DoctorProfile.id == Appointment.doctor_id).where(Appointment.id == appointment_id, DoctorProfile.user_id == doctor.id))
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment


@router.post("/appointments/{appointment_id}", response_model=CallRecordingResponse, status_code=status.HTTP_201_CREATED)
async def upload_recording(
    appointment_id: str,
    doctor: DoctorUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    consent_confirmed: Annotated[bool, Form()],
    duration_seconds: Annotated[int | None, Form()] = None,
) -> CallRecording:
    assigned_appointment(db, appointment_id, doctor)
    if not consent_confirmed:
        raise HTTPException(status_code=422, detail="Owner consent must be confirmed before recording")
    content_type = (file.content_type or "").split(";")[0]
    if content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Only WebM video/audio or OGG audio recordings are allowed")
    directory = (Path(get_settings().upload_dir).resolve() / "call-recordings")
    directory.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid.uuid4()}{allowed_types[content_type]}"
    destination = directory / storage_key
    digest, size = hashlib.sha256(), 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > get_settings().max_recording_bytes:
                    raise HTTPException(status_code=413, detail="Recording exceeds the configured size limit")
                digest.update(chunk); output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True); raise
    finally:
        await file.close()
    recording = CallRecording(appointment_id=appointment_id, recorded_by_user_id=doctor.id, storage_key=storage_key, original_filename=Path(file.filename or "consultation.webm").name[:255], content_type=content_type, size_bytes=size, sha256=digest.hexdigest(), duration_seconds=duration_seconds, consent_confirmed_at=utc_now())
    db.add(recording); db.commit(); db.refresh(recording)
    return recording


@router.get("", response_model=list[CallRecordingResponse])
def list_recordings(doctor: DoctorUser, db: DbSession) -> list[CallRecording]:
    statement = select(CallRecording).join(Appointment, Appointment.id == CallRecording.appointment_id).join(DoctorProfile, DoctorProfile.id == Appointment.doctor_id).where(DoctorProfile.user_id == doctor.id).order_by(CallRecording.created_at.desc())
    return list(db.scalars(statement))


@router.get("/{recording_id}/media")
def stream_recording(recording_id: str, doctor: DoctorUser, db: DbSession) -> FileResponse:
    recording = db.get(CallRecording, recording_id)
    if recording is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    assigned_appointment(db, recording.appointment_id, doctor)
    path = Path(get_settings().upload_dir).resolve() / "call-recordings" / recording.storage_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Recording file not found")
    return FileResponse(path, media_type=recording.content_type, filename=recording.original_filename)
