import json
import logging
from typing import Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.generators.excel_generator import generate_excel_file
from app.generators.powerpoint_generator import generate_powerpoint_file
from app.generators.word_generator import generate_word_file
from app.schemas.chat import ChatResponse
from app.schemas.files import GeneratedFileOut
from app.services.llm.factory import get_llm_provider
from app.services.memory_manager import memory_manager
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class AIOrchestrator:
    @property
    def llm(self) -> BaseLLMProvider:
        return get_llm_provider()

    async def handle_chat(
        self,
        db: Session,
        user_id: str,
        message_text: str,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        # 1. Resolve or create conversation
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ).first()
            if not conv:
                conv = Conversation(id=conversation_id, user_id=user_id, title=message_text[:40])
                db.add(conv)
                db.commit()
                db.refresh(conv)
        else:
            conv = Conversation(user_id=user_id, title=message_text[:40])
            db.add(conv)
            db.commit()
            db.refresh(conv)

        # 2. Record user message
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=message_text,
        )
        db.add(user_msg)
        db.commit()

        # 3. Classify intent
        classification = self.llm.classify_intent(message_text)

        # Check explicit preference
        if classification.explicit_preference:
            pref = classification.explicit_preference
            memory_manager.set_preference(
                db=db,
                user_id=user_id,
                category=pref["category"],
                key=pref["key"],
                value=pref["value"],
                source="explicit",
            )

        # 4. Route based on intent
        if classification.intent == "clarification":
            assistant_text = classification.clarification_question or "Could you clarify what kind of document you need?"
            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=assistant_text,
                intent="clarification",
            )
            db.add(asst_msg)
            db.commit()

            return ChatResponse(
                conversation_id=conv.id,
                assistant_message=assistant_text,
                intent="clarification",
                clarification_required=True,
                file=None,
            )

        elif classification.intent == "generate_document" and classification.format:
            fmt = classification.format.lower()
            # Retrieve persona preferences for this format + general
            persona_hints = memory_manager.get_relevant_preferences(db, user_id, format_type=fmt)

            # Precedence rule: check for current-turn override keywords in user message
            # Current turn instruction overrides persona hints dynamically without modifying the DB
            lower_msg = message_text.lower()
            effective_hints = dict(persona_hints)
            if "no chart" in lower_msg or "without chart" in lower_msg:
                effective_hints["excel.include_charts"] = False
            if "no summary" in lower_msg or "without summary" in lower_msg:
                effective_hints["excel.include_summary_sheet"] = False
            if "no table" in lower_msg or "without table" in lower_msg:
                effective_hints["word.use_tables"] = False

            # Allocate storage path
            file_id, dest_path = storage_service.allocate_file_path(user_id, fmt)

            try:
                if fmt == "excel":
                    content = self.llm.generate_excel_content(message_text, effective_hints)
                    generate_excel_file(content, dest_path)
                    original_name = f"{content.title.replace(' ', '_')}.xlsx"
                elif fmt == "word":
                    content = self.llm.generate_word_content(message_text, effective_hints)
                    generate_word_file(content, dest_path)
                    original_name = f"{content.title.replace(' ', '_')}.docx"
                elif fmt == "powerpoint":
                    content = self.llm.generate_powerpoint_content(message_text, effective_hints)
                    generate_powerpoint_file(content, dest_path)
                    original_name = f"{content.deck_title.replace(' ', '_')}.pptx"
                else:
                    raise ValueError(f"Unsupported format: {fmt}")

                # Register file in DB
                file_record = storage_service.register_file(
                    db=db,
                    user_id=user_id,
                    file_id=file_id,
                    file_path=dest_path,
                    original_name=original_name,
                    format_type=fmt,
                )

                file_out = GeneratedFileOut(
                    id=file_record.id,
                    file_name=file_record.file_name,
                    format=file_record.format,
                    mime_type=file_record.mime_type,
                    size_bytes=file_record.size_bytes,
                    sha256=file_record.sha256,
                    download_url=f"{settings.API_V1_STR}/files/{file_record.id}/download",
                    status=file_record.status,
                    created_at=file_record.created_at,
                )

                assistant_text = f"I have generated your requested {fmt.title()} document: **{file_record.file_name}**. You can download it directly below."
                asst_msg = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=assistant_text,
                    intent="generate_document",
                    metadata_json=json.dumps({"file_id": file_record.id, "format": fmt}),
                )
                db.add(asst_msg)
                db.commit()

                return ChatResponse(
                    conversation_id=conv.id,
                    assistant_message=assistant_text,
                    intent="generate_document",
                    clarification_required=False,
                    file=file_out,
                )

            except Exception as e:
                logger.error(f"Error during document generation: {e}", exc_info=True)
                err_text = f"An error occurred while generating the document: {str(e)}"
                asst_msg = Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=err_text,
                    intent="error",
                )
                db.add(asst_msg)
                db.commit()
                return ChatResponse(
                    conversation_id=conv.id,
                    assistant_message=err_text,
                    intent="error",
                    clarification_required=False,
                    file=None,
                )

        else:
            # Normal conversational intent
            # Retrieve recent conversation messages
            recent_msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
                .limit(10)
                .all()
            )
            chat_history = [{"role": m.role, "content": m.content} for m in recent_msgs]

            general_prefs = memory_manager.get_relevant_preferences(db, user_id, format_type=None)
            sys_prompt = "You are a helpful AI personal productivity assistant."
            if general_prefs:
                sys_prompt += f" User preferences: {json.dumps(general_prefs)}"

            assistant_text = self.llm.chat(chat_history, system_prompt=sys_prompt)

            asst_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=assistant_text,
                intent="conversation",
            )
            db.add(asst_msg)
            db.commit()

            # Trigger summary if messages >= 6
            if len(recent_msgs) >= 6:
                summary_text = self.llm.summarize_conversation(chat_history)
                memory_manager.save_conversation_summary(db, conv.id, user_id, summary_text)

            return ChatResponse(
                conversation_id=conv.id,
                assistant_message=assistant_text,
                intent="conversation",
                clarification_required=False,
                file=None,
            )


orchestrator = AIOrchestrator()

