import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DbSession
from app.api.routes.appointments import accessible_appointment, ensure_paid_appointment
from app.core.config import get_settings
from app.models.domain import AppointmentAttachment, AttachmentKind
from app.schemas.attachment import AppointmentAttachmentResponse
from app.services.notifications import appointment_participant_user_ids
from app.services.realtime import event_hub

router = APIRouter()

allowed_content_types = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "video/webm": ".webm",
    "video/mp4": ".mp4",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
}


def kind_for_content_type(content_type: str) -> AttachmentKind:
    category = content_type.split("/")[0]
    return {"image": AttachmentKind.PHOTO, "video": AttachmentKind.VIDEO, "audio": AttachmentKind.VOICE}[
        category
    ]


@router.post(
    "/appointments/{appointment_id}/attachments",
    response_model=AppointmentAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    appointment_id: str,
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="Photo, video, or voice note")],
) -> AppointmentAttachment:
    appointment = accessible_appointment(db, appointment_id, user)
    ensure_paid_appointment(appointment, user)

    content_type = (file.content_type or "").split(";")[0]
    if content_type not in allowed_content_types:
        allowed = ", ".join(sorted(allowed_content_types))
        raise HTTPException(status_code=415, detail=f"Only {allowed} files are allowed")

    max_bytes = get_settings().max_recording_bytes
    digest = hashlib.sha256()
    size = 0
    chunks: list[bytes] = []
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=413, detail="File exceeds the size limit")
        digest.update(chunk)
        chunks.append(chunk)
    data = b"".join(chunks)

    attachment = AppointmentAttachment(
        appointment_id=appointment.id,
        uploaded_by_user_id=user.id,
        kind=kind_for_content_type(content_type),
        original_filename=Path(file.filename or "attachment").name[:255],
        data=data,
        content_type=content_type,
        size_bytes=size,
        sha256=digest.hexdigest(),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    recipients = appointment_participant_user_ids(db, appointment)
    await event_hub.send_to_users(
        recipients,
        {
            "type": "chat_attachment",
            "appointment_id": appointment.id,
            "attachment": AppointmentAttachmentResponse.model_validate(attachment).model_dump(
                mode="json"
            ),
        },
    )
    return attachment


@router.get(
    "/appointments/{appointment_id}/attachments",
    response_model=list[AppointmentAttachmentResponse],
)
def list_attachments(
    appointment_id: str, user: CurrentUser, db: DbSession
) -> list[AppointmentAttachment]:
    appointment = accessible_appointment(db, appointment_id, user)
    ensure_paid_appointment(appointment, user)
    statement = (
        select(AppointmentAttachment)
        .where(AppointmentAttachment.appointment_id == appointment.id)
        .order_by(AppointmentAttachment.created_at.desc())
    )
    return list(db.scalars(statement))


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: str, user: CurrentUser, db: DbSession) -> Response:
    attachment = db.get(AppointmentAttachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    appointment = accessible_appointment(db, attachment.appointment_id, user)
    ensure_paid_appointment(appointment, user)
    return Response(
        content=attachment.data,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'inline; filename="{attachment.original_filename}"'},
    )
