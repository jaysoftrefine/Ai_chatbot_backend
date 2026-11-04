import json
import logging
from typing import Any
from google import genai
from google.genai import types

from app.generators.schemas import (
    ExcelWorkbookContent,
    PowerPointPresentationContent,
    WordDocumentContent,
)
from app.services.llm.base import BaseLLMProvider, IntentClassificationResult

logger = logging.getLogger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        if not api_key or not api_key.strip():
            raise ValueError(
                "Gemini API key is missing. Please set GEMINI_API_KEY in your environment or .env file."
            )
        self.model_name = model_name or "gemini-2.5-flash"
        # Never log or expose api_key
        logger.info("Initializing GeminiLLMProvider with model: %s", self.model_name)
        self.client = genai.Client(api_key=api_key.strip())

    def classify_intent(
        self, message: str, context: list[dict[str, str]] | None = None
    ) -> IntentClassificationResult:
        system_instruction = (
            "You are a strict intent classifier for an AI personal productivity assistant.\n"
            "Classification Rules:\n"
            "1. 'conversation': For general questions, explanations, greetings, or questions about how things work. "
            "MERELY MENTIONING Excel, Word, or PowerPoint in a question (e.g. 'How do I create a PowerPoint?') is a conversational question, NOT a document generation request.\n"
            "2. 'generate_document': ONLY when the user explicitly requests generating, creating, exporting, or building an Office document. "
            "Set format strictly to 'excel', 'word', or 'powerpoint'. Extract subject.\n"
            "3. 'clarification': When the user asks to create a document or file but leaves the format completely ambiguous (e.g. 'create a document').\n"
            "4. Check if the user is expressing a stable, long-term preference (e.g. 'Always use concise tone', 'Remember that I prefer minimal layout'). If so, populate explicit_preference with category, key, value."
        )

        prompt = f"User message to classify: {message}"
        if context:
            prompt = f"Recent context: {json.dumps(context[-4:])}\n\n{prompt}"

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=IntentClassificationResult,
                temperature=0.0,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            if not response.text:
                raise ValueError("Empty response received from Gemini intent classifier")
            return IntentClassificationResult.model_validate_json(response.text)
        except Exception as e:
            logger.error("Gemini intent classification error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during intent classification: {str(e)}") from e

    def chat(self, messages: list[dict[str, str]], system_prompt: str | None = None) -> str:
        prompt_parts = []
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}\n")

        for m in messages:
            role = "User" if m.get("role") == "user" else "Assistant"
            prompt_parts.append(f"{role}: {m.get('content')}")

        full_prompt = "\n".join(prompt_parts)

        try:
            config = types.GenerateContentConfig(
                temperature=0.7,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=config,
            )
            return response.text or ""
        except Exception as e:
            logger.error("Gemini chat completion error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during chat completion: {str(e)}") from e

    def generate_excel_content(
        self, prompt: str, persona_hints: dict[str, Any] | None = None
    ) -> ExcelWorkbookContent:
        system_instruction = (
            "You are an expert financial and data analyst. Generate structured spreadsheet content "
            "as a valid ExcelWorkbookContent JSON object.\n"
            "Requirements:\n"
            "- Meaningful sheet names, descriptive column headers, and realistic rows of data.\n"
            "- Include valid Excel formulas for totals/aggregations (e.g. '=SUM(C2:C6)').\n"
            "- Formula cells MUST start with '=' and contain valid formula expressions.\n"
            "- Optionally include chart specifications if relevant data warrants visualization.\n"
            "- Respect user persona hints when provided."
        )
        hints_str = json.dumps(persona_hints) if persona_hints else "None"
        user_prompt = f"User Request: {prompt}\nUser Persona Defaults: {hints_str}"

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ExcelWorkbookContent,
                temperature=0.2,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )
            if not response.text:
                raise ValueError("Empty response received from Gemini for Excel generation")
            return ExcelWorkbookContent.model_validate_json(response.text)
        except Exception as e:
            logger.error("Gemini Excel generation error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during Excel generation: {str(e)}") from e

    def generate_word_content(
        self, prompt: str, persona_hints: dict[str, Any] | None = None
    ) -> WordDocumentContent:
        system_instruction = (
            "You are an expert executive document writer. Generate structured document content "
            "as a valid WordDocumentContent JSON object.\n"
            "Requirements:\n"
            "- Document title and optional subtitle.\n"
            "- Well-structured sections with headings (level 1-3).\n"
            "- Rich body paragraphs and informative bullet points.\n"
            "- Include tables where data comparison or schedules add value.\n"
            "- Respect user persona hints when provided."
        )
        hints_str = json.dumps(persona_hints) if persona_hints else "None"
        user_prompt = f"User Request: {prompt}\nUser Persona Defaults: {hints_str}"

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=WordDocumentContent,
                temperature=0.3,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )
            if not response.text:
                raise ValueError("Empty response received from Gemini for Word generation")
            return WordDocumentContent.model_validate_json(response.text)
        except Exception as e:
            logger.error("Gemini Word generation error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during Word generation: {str(e)}") from e

    def generate_powerpoint_content(
        self, prompt: str, persona_hints: dict[str, Any] | None = None
    ) -> PowerPointPresentationContent:
        system_instruction = (
            "You are a professional presentation designer and storyteller. Generate presentation content "
            "as a valid PowerPointPresentationContent JSON object.\n"
            "Requirements:\n"
            "- Deck title and optional subtitle.\n"
            "- Coherent progression of slides: title slide, key content slides, and conclusion slide.\n"
            "- Concise slide titles and 3-5 punchy bullet points per slide (avoid overcrowding).\n"
            "- Professional speaker notes explaining each slide in depth.\n"
            "- Respect user persona hints when provided."
        )
        hints_str = json.dumps(persona_hints) if persona_hints else "None"
        user_prompt = f"User Request: {prompt}\nUser Persona Defaults: {hints_str}"

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=PowerPointPresentationContent,
                temperature=0.3,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )
            if not response.text:
                raise ValueError("Empty response received from Gemini for PowerPoint generation")
            return PowerPointPresentationContent.model_validate_json(response.text)
        except Exception as e:
            logger.error("Gemini PowerPoint generation error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during PowerPoint generation: {str(e)}") from e

    def summarize_conversation(self, messages: list[dict[str, str]]) -> str:
        prompt = (
            "Provide a concise 1-2 sentence summary of this conversation focusing on key topics, "
            "decisions, and preferences mentioned:\n\n"
            + "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
        )
        try:
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=150,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            return (response.text or "").strip()
        except Exception as e:
            logger.error("Gemini conversation summary error: %s", type(e).__name__)
            raise RuntimeError(f"Gemini API error during summarization: {str(e)}") from e

