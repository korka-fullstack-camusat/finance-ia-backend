import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer
from database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # csv, xlsx, pdf
    file_size = Column(Integer, default=0)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
