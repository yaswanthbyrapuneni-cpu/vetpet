import hashlib
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.domain import (
    Appointment,
    AppointmentStatus,
    DoctorProfile,
    MedicalDocument,
    MedicalRecord,
    Pet,
    User,
    UserRole,
    utc_now,
)
from app.schemas.medical_record import (
    MedicalDocumentResponse,
    MedicalRecordCreate,
    MedicalRecordResponse,
    MedicalRecordUpdate,
)

router = APIRouter()
allowed_content_types = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def get_pet(db: Session, pet_id: str) -> Pet:
    pet = db.scalar(select(Pet).where(Pet.id == pet_id, Pet.is_archived.is_(False)))
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet


def doctor_has_clinical_access(db: Session, user_id: str, pet_id: str) -> bool:
    appointment_id = db.scalar(
        select(Appointment.id)
        .join(DoctorProfile, DoctorProfile.id == Appointment.doctor_id)
        .where(
            DoctorProfile.user_id == user_id,
            Appointment.pet_id == pet_id,
            Appointment.status.in_(
                [AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED]
            ),
        )
        .limit(1)
    )
    return appointment_id is not None


def ensure_pet_access(db: Session, user: User, pet: Pet) -> None:
    if user.role == UserRole.ADMIN or pet.owner_id == user.id:
        return
    if user.role == UserRole.DOCTOR and doctor_has_clinical_access(db, user.id, pet.id):
        return
    raise HTTPException(status_code=404, detail="Pet not found")


def get_accessible_record(
    db: Session, record_id: str, user: User, include_archived: bool = False
) -> MedicalRecord:
    statement = select(MedicalRecord).where(MedicalRecord.id == record_id)
    if not include_archived:
        statement = statement.where(MedicalRecord.is_archived.is_(False))
    record = db.scalar(statement)
    if record is None:
        raise HTTPException(status_code=404, detail="Medical record not found")
    pet = get_pet(db, record.pet_id)
    ensure_pet_access(db, user, pet)
    return record


def ensure_record_author(user: User, record: MedicalRecord) -> None:
    if user.role != UserRole.ADMIN and record.recorded_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the record author can modify it")


@router.post(
    "/pets/{pet_id}/medical-records",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_medical_record(
    pet_id: str, payload: MedicalRecordCreate, user: CurrentUser, db: DbSession
) -> MedicalRecord:
    pet = get_pet(db, pet_id)
    ensure_pet_access(db, user, pet)
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Administrators cannot create clinical records")
    record = MedicalRecord(
        pet_id=pet.id,
        recorded_by_user_id=user.id,
        record_type=payload.record_type.value,
        title=payload.title.strip(),
        details=payload.details,
        occurred_on=payload.occurred_on,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/pets/{pet_id}/medical-records", response_model=list[MedicalRecordResponse])
def list_medical_records(
    pet_id: str,
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MedicalRecord]:
    pet = get_pet(db, pet_id)
    ensure_pet_access(db, user, pet)
    statement = (
        select(MedicalRecord)
        .where(MedicalRecord.pet_id == pet.id, MedicalRecord.is_archived.is_(False))
        .order_by(MedicalRecord.occurred_on.desc(), MedicalRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement))


@router.get("/medical-records/{record_id}", response_model=MedicalRecordResponse)
def read_medical_record(record_id: str, user: CurrentUser, db: DbSession) -> MedicalRecord:
    return get_accessible_record(db, record_id, user)


@router.patch("/medical-records/{record_id}", response_model=MedicalRecordResponse)
def update_medical_record(
    record_id: str, payload: MedicalRecordUpdate, user: CurrentUser, db: DbSession
) -> MedicalRecord:
    record = get_accessible_record(db, record_id, user)
    ensure_record_author(user, record)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in {"title", "record_type"} and value is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        setattr(record, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/medical-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_medical_record(record_id: str, user: CurrentUser, db: DbSession) -> Response:
    record = get_accessible_record(db, record_id, user)
    ensure_record_author(user, record)
    record.is_archived = True
    record.archived_at = utc_now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/medical-records/{record_id}/documents",
    response_model=MedicalDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_medical_document(
    record_id: str,
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File(description="PDF, JPEG, or PNG medical document")],
) -> MedicalDocument:
    record = get_accessible_record(db, record_id, user)
    ensure_record_author(user, record)
    if file.content_type not in allowed_content_types:
        raise HTTPException(status_code=415, detail="Only PDF, JPEG, and PNG files are allowed")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid.uuid4()}{allowed_content_types[file.content_type]}"
    destination = upload_dir / storage_key
    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Document exceeds upload size limit",
                    )
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    original_filename = Path(file.filename or "document").name[:255]
    document = MedicalDocument(
        medical_record_id=record.id,
        uploaded_by_user_id=user.id,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=file.content_type,
        size_bytes=size,
        sha256=digest.hexdigest(),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/medical-documents/{document_id}/download")
def download_medical_document(
    document_id: str, user: CurrentUser, db: DbSession
) -> FileResponse:
    document = db.get(MedicalDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    get_accessible_record(db, document.medical_record_id, user)
    path = Path(get_settings().upload_dir).resolve() / document.storage_key
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Document file not found")
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)
