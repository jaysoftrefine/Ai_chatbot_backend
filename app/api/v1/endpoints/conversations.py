import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.chat import (
    ConversationDetailOut,
    ConversationOut,
    MessageOut,
)
from app.services.memory_manager import memory_manager

router = APIRouter()


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

    messages_out = []
    for m in conv.messages:
        meta = None
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except Exception:
                pass
        messages_out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                created_at=m.created_at,
                metadata=meta,
            )
        )

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
    out = []
    for m in messages:
        meta = None
        if m.metadata_json:
            try:
                meta = json.loads(m.metadata_json)
            except Exception:
                pass
        out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                created_at=m.created_at,
                metadata=meta,
            )
        )
    return out


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

