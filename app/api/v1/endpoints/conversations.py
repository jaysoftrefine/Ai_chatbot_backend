import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.conversation import Conversation
from app.db.models.generated_file import GeneratedFile
from app.db.models.message import Message
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.chat import (
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
)
from app.schemas.files import GeneratedFileOut
from app.services.memory_manager import memory_manager

router = APIRouter()


def _build_messages_out(messages: list[Message], db: Session) -> list[MessageOut]:
    parsed_metas = []
    file_ids = []
    for m in messages:
        meta = None
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
                if isinstance(meta, dict) and meta.get("file_id"):
                    file_ids.append(meta["file_id"])
            except Exception:
                pass
        parsed_metas.append(meta)

    files_by_id: dict[str, GeneratedFileOut] = {}
    if file_ids:
        records = db.query(GeneratedFile).filter(GeneratedFile.id.in_(file_ids)).all()
        for f in records:
            files_by_id[f.id] = GeneratedFileOut(
                id=f.id,
                file_name=f.file_name,
                format=f.format,
                mime_type=f.mime_type,
                size_bytes=f.size_bytes,
                sha256=f.sha256,
                download_url=f"{settings.API_V1_STR}/files/{f.id}/download",
                status=f.status,
                created_at=f.created_at,
            )

    out = []
    for m, meta in zip(messages, parsed_metas):
        file_out = None
        if meta and isinstance(meta, dict) and meta.get("file_id"):
            file_out = files_by_id.get(meta["file_id"])

        out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                created_at=m.created_at,
                metadata=meta,
                file=file_out,
            )
        )
    return out


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [ConversationOut.model_validate(c) for c in convs]


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages_out = _build_messages_out(conv.messages, db)

    summary = memory_manager.get_conversation_summary(db, conv.id, current_user.id)

    return ConversationDetailOut(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages_out,
        summary=summary,
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return _build_messages_out(messages, db)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return None

