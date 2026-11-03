from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class PersonaPreferenceCreate(BaseModel):
    category: str = Field(description="general, word, excel, or powerpoint")
    key: str = Field(min_length=1, max_length=100)
    value: Any = Field(description="Scalar, string, or structured preference value")
    source: str = Field(default="explicit")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PersonaPreferenceUpdate(BaseModel):
    value: Any
    confidence: float | None = None


class PersonaPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    key: str
    value: Any
    source: str
    confidence: float
    created_at: datetime
    updated_at: datetime


class PersonaGroupedOut(BaseModel):
    general: dict[str, Any] = {}
    word: dict[str, Any] = {}
    excel: dict[str, Any] = {}
    powerpoint: dict[str, Any] = {}
    items: list[PersonaPreferenceOut] = []
