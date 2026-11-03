from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.orchestrator import orchestrator

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    chat_req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = await orchestrator.handle_chat(
        db=db,
        user_id=current_user.id,
        message_text=chat_req.message,
        conversation_id=chat_req.conversation_id,
    )
    return response

