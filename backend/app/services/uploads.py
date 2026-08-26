import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings


async def store_upload(
    file: UploadFile,
    allowed_content_types: dict[str, str],
    max_bytes: int,
    subdir: str = "",
) -> tuple[str, str, int, str]:
    """Validate, stream, and hash an uploaded file to disk.

    Returns (content_type, storage_key, size_bytes, sha256_hex).
    """
    content_type = (file.content_type or "").split(";")[0]
    if content_type not in allowed_content_types:
        allowed = ", ".join(sorted(allowed_content_types))
        raise HTTPException(status_code=415, detail=f"Only {allowed} files are allowed")

    directory = Path(get_settings().upload_dir).resolve()
    if subdir:
        directory = directory / subdir
    directory.mkdir(parents=True, exist_ok=True)
    storage_key = f"{uuid.uuid4()}{allowed_content_types[content_type]}"
    destination = directory / storage_key

    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail="File exceeds the size limit")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return content_type, storage_key, size, digest.hexdigest()


def resolve_upload_path(storage_key: str, subdir: str = "") -> Path:
    directory = Path(get_settings().upload_dir).resolve()
    return (directory / subdir / storage_key) if subdir else (directory / storage_key)
