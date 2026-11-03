import json
from typing import Any
from sqlalchemy.orm import Session

from app.db.models.conversation_summary import ConversationSummary
from app.db.models.persona_preference import PersonaPreference

CATEGORIES = {"general", "word", "excel", "powerpoint"}


class MemoryManager:
    def get_user_preferences_grouped(self, db: Session, user_id: str) -> dict[str, Any]:
        prefs = db.query(PersonaPreference).filter(
            PersonaPreference.user_id == user_id
        ).all()

        result = {
            "general": {},
            "word": {},
            "excel": {},
            "powerpoint": {},
            "items": [],
        }

        for p in prefs:
            try:
                val = json.loads(p.value_json)
            except Exception:
                val = p.value_json

            cat = p.category.lower()
            if cat in result:
                result[cat][p.key] = val

            result["items"].append(
                {
                    "id": p.id,
                    "category": p.category,
                    "key": p.key,
                    "value": val,
                    "source": p.source,
                    "confidence": p.confidence,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
            )

        return result

    def get_relevant_preferences(self, db: Session, user_id: str, format_type: str | None = None) -> dict[str, Any]:
        """
        Retrieves general preferences plus preferences specific to the requested format.
        """
        categories = ["general"]
        if format_type and format_type.lower() in CATEGORIES:
            categories.append(format_type.lower())

        prefs = db.query(PersonaPreference).filter(
            PersonaPreference.user_id == user_id,
            PersonaPreference.category.in_(categories),
        ).all()

        merged: dict[str, Any] = {}
        for p in prefs:
            try:
                val = json.loads(p.value_json)
            except Exception:
                val = p.value_json
            merged[f"{p.category}.{p.key}"] = val

        return merged

    def set_preference(
        self,
        db: Session,
        user_id: str,
        category: str,
        key: str,
        value: Any,
        source: str = "explicit",
        confidence: float = 1.0,
    ) -> PersonaPreference:
        category = category.lower()
        if category not in CATEGORIES:
            category = "general"

        value_json = json.dumps(value) if not isinstance(value, str) else json.dumps(value)

        existing = db.query(PersonaPreference).filter(
            PersonaPreference.user_id == user_id,
            PersonaPreference.category == category,
            PersonaPreference.key == key,
        ).first()

        if existing:
            existing.value_json = value_json
            existing.source = source
            existing.confidence = confidence
            db.commit()
            db.refresh(existing)
            return existing

        new_pref = PersonaPreference(
            user_id=user_id,
            category=category,
            key=key,
            value_json=value_json,
            source=source,
            confidence=confidence,
        )
        db.add(new_pref)
        db.commit()
        db.refresh(new_pref)
        return new_pref

    def delete_preference(self, db: Session, user_id: str, preference_id: str) -> bool:
        pref = db.query(PersonaPreference).filter(
            PersonaPreference.id == preference_id,
            PersonaPreference.user_id == user_id,
        ).first()
        if not pref:
            return False
        db.delete(pref)
        db.commit()
        return True

    def get_conversation_summary(self, db: Session, conversation_id: str, user_id: str) -> str | None:
        summary_row = db.query(ConversationSummary).filter(
            ConversationSummary.conversation_id == conversation_id,
            ConversationSummary.user_id == user_id,
        ).first()
        return summary_row.summary if summary_row else None

    def save_conversation_summary(self, db: Session, conversation_id: str, user_id: str, summary_text: str):
        existing = db.query(ConversationSummary).filter(
            ConversationSummary.conversation_id == conversation_id,
            ConversationSummary.user_id == user_id,
        ).first()
        if existing:
            existing.summary = summary_text
            db.commit()
            return existing

        new_sum = ConversationSummary(
            conversation_id=conversation_id,
            user_id=user_id,
            summary=summary_text,
        )
        db.add(new_sum)
        db.commit()
        return new_sum


memory_manager = MemoryManager()

