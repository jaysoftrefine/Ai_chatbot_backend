from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.files import GeneratedFileOut
from app.services.rag.rag_service import rag_service
from app.services.storage_service import storage_service

router = APIRouter()


def make_file_out(record) -> GeneratedFileOut:
    return GeneratedFileOut(
        id=record.id,
        file_name=record.file_name,
        format=record.format,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        download_url=f"{settings.API_V1_STR}/files/{record.id}/download",
        status=record.status,
        created_at=record.created_at,
    )


@router.get("", response_model=list[GeneratedFileOut])
def list_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = storage_service.list_user_files(db, current_user.id)
    return [make_file_out(f) for f in files]


@router.post("/upload", response_model=GeneratedFileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    record = storage_service.save_uploaded_file(
        db=db,
        user_id=current_user.id,
        filename=file.filename,
        content=content,
    )

    # Index into RAG knowledge base
    try:
        rag_service.index_file(
            db=db,
            user_id=current_user.id,
            file_id=record.id,
            file_name=record.file_name,
            file_path=Path(record.storage_key),
        )
    except Exception as e:
        # Non-fatal to file upload, but logged
        import logging
        logging.getLogger(__name__).warning(f"Could not index uploaded file {record.file_name} into RAG: {e}")

    return make_file_out(record)


@router.get("/{file_id}", response_model=GeneratedFileOut)
def get_file_info(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = storage_service.get_file_record(db, current_user.id, file_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return make_file_out(record)


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = storage_service.get_file_record(db, current_user.id, file_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or permission denied")

    file_path = Path(record.storage_key)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found on server")

    return FileResponse(
        path=str(file_path),
        media_type=record.mime_type,
        filename=record.file_name,
        headers={"Content-Disposition": f'attachment; filename="{record.file_name}"'},
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = storage_service.get_file_record(db, current_user.id, file_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    file_path = Path(record.storage_key)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    db.delete(record)
    db.commit()
    return None

