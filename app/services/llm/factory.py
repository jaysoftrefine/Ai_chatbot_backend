from app.core.config import settings
from app.services.llm.base import BaseLLMProvider
from app.services.llm.fake import FakeLLMProvider
from app.services.llm.gemini import GeminiLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    provider_name = settings.LLM_PROVIDER.lower().strip()
    if provider_name in ("google", "gemini"):
        api_key = settings.effective_gemini_api_key
        if not api_key:
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )
        return GeminiLLMProvider(
            api_key=api_key,
            model_name=settings.LLM_MODEL,
        )

    if provider_name == "fake":
        return FakeLLMProvider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{settings.LLM_PROVIDER}'. Supported providers: 'google', 'fake'"
    )
