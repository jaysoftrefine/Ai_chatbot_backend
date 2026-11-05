import hashlib
import os
import uuid
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.generated_file import GeneratedFile

MIME_TYPES = {
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "powerpoint": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "text": "text/plain",
    "markdown": "text/markdown",
    "csv": "text/csv",
}

EXTENSIONS = {
    "excel": "xlsx",
    "word": "docx",
    "powerpoint": "pptx",
    "pdf": "pdf",
    "text": "txt",
    "markdown": "md",
    "csv": "csv",
}


def sanitize_filename(filename: str, format_type: str) -> str:
    ext = EXTENSIONS.get(format_type, "bin")
    # Strip dangerous characters
    safe = "".join(c for c in filename if c.isalnum() or c in (" ", "-", "_", ".")).strip()
    if not safe:
        safe = f"document.{ext}"
    if not safe.lower().endswith(f".{ext}"):
        safe = f"{safe}.{ext}"
    return safe


class StorageService:
    def __init__(self, base_storage_path: str = settings.STORAGE_PATH):
        self.base_path = Path(base_storage_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_user_storage_dir(self, user_id: str) -> Path:
        user_dir = (self.base_path / user_id).resolve()
        # Security check: ensure path is within base_path
        if not str(user_dir).startswith(str(self.base_path)):
            raise ValueError("Invalid storage path")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def allocate_file_path(self, user_id: str, format_type: str) -> tuple[str, Path]:
        file_id = str(uuid.uuid4())
        ext = EXTENSIONS.get(format_type, "bin")
        user_dir = self.get_user_storage_dir(user_id)
        destination_path = user_dir / f"{file_id}.{ext}"
        return file_id, destination_path

    def register_file(
        self,
        db: Session,
        user_id: str,
        file_id: str,
        file_path: Path,
        original_name: str,
        format_type: str,
    ) -> GeneratedFile:
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise ValueError("Target file does not exist or is empty")

        size_bytes = file_path.stat().st_size

        # Compute SHA256
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        mime = MIME_TYPES.get(format_type, "application/octet-stream")
        safe_name = sanitize_filename(original_name, format_type)

        record = GeneratedFile(
            id=file_id,
            user_id=user_id,
            file_name=safe_name,
            format=format_type,
            mime_type=mime,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            storage_key=str(file_path),
            status="completed",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_file_record(self, db: Session, user_id: str, file_id: str) -> GeneratedFile | None:
        return db.query(GeneratedFile).filter(
            GeneratedFile.id == file_id,
            GeneratedFile.user_id == user_id,
        ).first()

    def list_user_files(self, db: Session, user_id: str) -> list[GeneratedFile]:
        return db.query(GeneratedFile).filter(
            GeneratedFile.user_id == user_id,
        ).order_by(GeneratedFile.created_at.desc()).all()

    def save_uploaded_file(
        self,
        db: Session,
        user_id: str,
        filename: str,
        content: bytes,
    ) -> GeneratedFile:
        lower_name = filename.lower()
        if lower_name.endswith(".xlsx"):
            format_type = "excel"
        elif lower_name.endswith(".docx"):
            format_type = "word"
        elif lower_name.endswith(".pptx"):
            format_type = "powerpoint"
        elif lower_name.endswith(".pdf"):
            format_type = "pdf"
        elif lower_name.endswith(".md"):
            format_type = "markdown"
        elif lower_name.endswith(".csv"):
            format_type = "csv"
        else:
            format_type = "text"

        file_id, file_path = self.allocate_file_path(user_id, format_type)
        with open(file_path, "wb") as f:
            f.write(content)

        return self.register_file(
            db=db,
            user_id=user_id,
            file_id=file_id,
            file_path=file_path,
            original_name=filename,
            format_type=format_type,
        )


storage_service = StorageService()

