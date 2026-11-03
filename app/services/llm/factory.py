from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.fake import FakeLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name == "fake" or not settings.LLM_API_KEY:
        return FakeLLMProvider()

    # In production with live API key, could initialize OpenAILLMProvider, etc.
    # For now, default safe fallback is FakeLLMProvider
    return FakeLLMProvider()

