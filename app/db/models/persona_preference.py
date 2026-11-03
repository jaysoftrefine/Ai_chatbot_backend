import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PersonaPreference(Base):
    __tablename__ = "persona_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # general, word, excel, powerpoint
    key: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., tone, layout, charts
    value_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded value (string, dict, bool, etc.)
    source: Mapped[str] = mapped_column(String(50), default="explicit", nullable=False)  # explicit, repeated_choice
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "category", "key", name="uq_user_category_key"),
        Index("ix_persona_user_cat", "user_id", "category"),
    )

