from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from app.generators.schemas import (
    ExcelWorkbookContent,
    WordDocumentContent,
    PowerPointPresentationContent,
)


class ExplicitPreferenceSpec(BaseModel):
    category: str
    key: str
    value: str | bool | int | float

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class IntentClassificationResult(BaseModel):
    intent: str  # "conversation" | "generate_document" | "clarification"
    format: str | None = None  # "excel" | "word" | "powerpoint"
    subject: str | None = None
    clarification_question: str | None = None
    explicit_preference: ExplicitPreferenceSpec | None = None


class BaseLLMProvider(ABC):
    @abstractmethod
    def classify_intent(self, message: str, context: list[dict[str, str]] | None = None) -> IntentClassificationResult:
        pass

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        pass

    @abstractmethod
    def generate_excel_content(self, prompt: str, persona_hints: dict[str, Any] | None = None) -> ExcelWorkbookContent:
        pass

    @abstractmethod
    def generate_word_content(self, prompt: str, persona_hints: dict[str, Any] | None = None) -> WordDocumentContent:
        pass

    @abstractmethod
    def generate_powerpoint_content(
        self, prompt: str, persona_hints: dict[str, Any] | None = None
    ) -> PowerPointPresentationContent:
        pass

    @abstractmethod
    def summarize_conversation(self, messages: list[dict[str, str]]) -> str:
        pass

