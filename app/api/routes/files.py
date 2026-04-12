"""Routes pour l'upload et la gestion des fichiers financiers."""
import os
import shutil
import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

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
    db: Session = Depends(get_db),
):
    """Upload un fichier financier (CSV, XLSX, PDF)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nom de fichier manquant")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté. Formats acceptés : {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Créer le répertoire d'upload
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    # Nom unique
    unique_name = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(upload_dir, unique_name)

    # Lire et sauvegarder
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    record = UploadedFile(
        filename=unique_name,
        original_name=file.filename,
        file_type=ext,
        file_size=len(content),
        file_path=file_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=List[FileOut])
def list_files(db: Session = Depends(get_db)):
    """Liste tous les fichiers uploadés."""
    files = db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()
    return files


@router.delete("/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    """Supprime un fichier uploadé."""
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    # Supprimer le fichier physique
    try:
        if os.path.exists(record.file_path):
            os.remove(record.file_path)
    except OSError:
        pass

    db.delete(record)
    db.commit()
    return {"message": "Fichier supprimé"}
