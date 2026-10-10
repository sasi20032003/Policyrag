"""
File validation, sanitization, and storage helpers for uploaded PDFs.
"""
import logging
import os
import re
import uuid

from fastapi import UploadFile, HTTPException

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_CONTENT_TYPES = {"application/pdf"}
FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(filename: str) -> str:
    base = os.path.basename(filename)
    base = FILENAME_SAFE_RE.sub("_", base)
    return base[:150] or "upload.pdf"


async def save_upload(file: UploadFile) -> str:
    """Validate type/size, sanitize filename, and persist the upload. Returns file path."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{sanitize_filename(file.filename or 'upload.pdf')}"
    dest_path = os.path.join(settings.upload_dir, safe_name)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    with open(dest_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(dest_path)
                raise HTTPException(status_code=400, detail=f"File exceeds {settings.max_upload_mb}MB limit.")
            out.write(chunk)

    logger.info("Saved upload to %s (%d bytes)", dest_path, size)
    return dest_path
