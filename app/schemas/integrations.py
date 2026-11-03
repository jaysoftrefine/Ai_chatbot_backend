from typing import Any
from pydantic import BaseModel


class DiscoveredTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = {}


class MicrosoftIntegrationStatus(BaseModel):
    enabled: bool
    transport: str
    server_url: str | None = None
    authenticated: bool
    connected: bool
    discovered_tools: list[DiscoveredTool] = []
    error: str | None = None
    format_support: dict[str, bool] = {
        "excel": False,
        "word": False,
        "powerpoint": False,
    }
    fallback_active: bool = True

