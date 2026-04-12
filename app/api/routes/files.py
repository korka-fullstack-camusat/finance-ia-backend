"""Routes fichiers — 100% async."""
import os
import uuid
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

from database import get_db
from app.models.file import UploadedFile
from app.config import settings

router = APIRouter(prefix="/api/files", tags=["files"])

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class FileOut(BaseModel):
    id: str
    filename: str
    original_name: str
    file_type: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/upload", response_model=FileOut)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté. Acceptés : {', '.join(ALLOWED_EXTENSIONS)}",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # Lecture et écriture asynchrones
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50MB)")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    record = UploadedFile(
        filename=unique_name,
        original_name=file.filename,
        file_type=ext,
        file_size=len(content),
        file_path=file_path,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.get("", response_model=List[FileOut])
async def list_files(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UploadedFile).order_by(UploadedFile.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    try:
        if os.path.exists(record.file_path):
            os.remove(record.file_path)
    except OSError:
        pass

    await db.delete(record)
    await db.commit()
    return {"message": "Fichier supprimé"}
