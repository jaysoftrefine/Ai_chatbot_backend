from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.generators.schemas import (
    ExcelWorkbookContent,
    ExcelSheetSpec,
    ExcelFormulaSpec,
)
from app.integrations.google_docs_mcp.client import GoogleDocsMCPClient
from app.services.llm.base import IntentClassificationResult
from app.services.llm.factory import get_llm_provider
from app.services.llm.fake import FakeLLMProvider
from app.services.llm.gemini import GeminiLLMProvider


def test_provider_selection_fake():
    """
    Tests that the fake provider is selected when LLM_PROVIDER is 'fake'.
    """
    with patch.object(settings, "LLM_PROVIDER", "fake"):
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)


def test_provider_selection_google_missing_key():
    """
    Tests that a missing Gemini API key produces a clear configuration error.
    """
    with patch.object(settings, "LLM_PROVIDER", "google"), patch.object(settings, "GEMINI_API_KEY", ""), patch.object(settings, "LLM_API_KEY", ""):
        with pytest.raises(ValueError) as excinfo:
            get_llm_provider()
        assert "Gemini API key is not configured" in str(excinfo.value)


def test_provider_selection_google_with_key():
    """
    Tests that GeminiLLMProvider is instantiated when LLM_PROVIDER is 'google' and key is present.
    """
    with patch.object(settings, "LLM_PROVIDER", "google"), patch.object(settings, "GEMINI_API_KEY", "test-key-123"):
        with patch("app.services.llm.gemini.genai.Client"):
            provider = get_llm_provider()
            assert isinstance(provider, GeminiLLMProvider)
            assert provider.model_name == settings.LLM_MODEL


def test_gemini_chat_mocked():
    """
    Tests Gemini chat completion with mocked API responses.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "FastAPI is a modern, fast web framework for building APIs with Python."
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.llm.gemini.genai.Client", return_value=mock_client):
        provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")
        reply = provider.chat([{"role": "user", "content": "Explain FastAPI"}])
        assert reply == mock_response.text
        assert mock_client.models.generate_content.called


def test_gemini_intent_classification_structured():
    """
    Tests Gemini intent classification parsing structured JSON output.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"intent": "generate_document", "format": "excel", "subject": "monthly budget", '
        '"clarification_question": null, "explicit_preference": null}'
    )
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.llm.gemini.genai.Client", return_value=mock_client):
        provider = GeminiLLMProvider(api_key="mock-key", model_name="gemini-2.5-flash")
        result = provider.classify_intent("Create an Excel sheet for my monthly budget")
        assert isinstance(result, IntentClassificationResult)
        assert result.intent == "generate_document"
        assert result.format == "excel"
        assert result.subject == "monthly budget"


def test_gemini_excel_generation_structured():
    """
    Tests Gemini structured output validation for Excel content.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    sample_excel = ExcelWorkbookContent(
        title="Q1 Expenses",
        sheets=[
            ExcelSheetSpec(
                name="Summary",
                headers=["Department", "Amount"],
                rows=[["Engineering", 15000], ["Sales", 8000]],
                formulas=[ExcelFormulaSpec(cell="B4", formula="=SUM(B2:B3)")],
            )
        ],
    )
    mock_response.text = sample_excel.model_dump_json()
    mock_client.models.generate_content.return_value = mock_response

    with patch("app.services.llm.gemini.genai.Client", return_value=mock_client):
        provider = GeminiLLMProvider(api_key="mock-key")
        content = provider.generate_excel_content("Create Q1 expense report")
        assert isinstance(content, ExcelWorkbookContent)
        assert content.title == "Q1 Expenses"
        assert len(content.sheets) == 1
        assert content.sheets[0].rows[0][0] == "Engineering"


def test_gemini_error_handling_no_silent_fallback():
    """
    Tests that when Gemini API raises an error, an exception is raised
    and the system does NOT silently switch to fake LLM.
    """
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("503 Service Unavailable")

    with patch("app.services.llm.gemini.genai.Client", return_value=mock_client):
        provider = GeminiLLMProvider(api_key="mock-key")
        with pytest.raises(RuntimeError) as excinfo:
            provider.chat([{"role": "user", "content": "Hello"}])
        assert "Gemini API error during chat completion" in str(excinfo.value)
        # Ensure secret API key is NOT leaked into the error string
        assert "mock-key" not in str(excinfo.value)


def test_google_docs_mcp_client_disabled():
    """
    Tests that Google Docs MCP client respects the disabled configuration by default.
    """
    with patch.object(settings, "GOOGLE_DOCS_MCP_ENABLED", False):
        client = GoogleDocsMCPClient()
        assert client.is_enabled() is False


@pytest.mark.asyncio
async def test_google_docs_mcp_unauthenticated_call_raises():
    """
    Tests that calling Google Docs MCP tool without an OAuth token raises PermissionError.
    """
    with patch.object(settings, "GOOGLE_DOCS_MCP_ENABLED", True):
        client = GoogleDocsMCPClient(oauth_access_token=None)
        with pytest.raises(PermissionError) as excinfo:
            await client.call_tool("read_doc", {"documentId": "abc"})
        assert "requires an active Google OAuth" in str(excinfo.value)


def test_google_docs_status_endpoint(client, auth_user_a):
    """
    Tests the GET /api/v1/integrations/google-docs/status endpoint.
    """
    res = client.get("/api/v1/integrations/google-docs/status", headers=auth_user_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data
    assert data["enabled"] is False
    assert data["server_url"] == "https://docsmcp.googleapis.com/mcp/v1"
    assert data["preview_program_required"] is True

