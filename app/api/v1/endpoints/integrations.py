from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.integrations.google_docs_mcp.registry import google_docs_registry
from app.integrations.mcp.registry import tool_registry
from app.schemas.integrations import (
    DiscoveredTool,
    GoogleDocsIntegrationStatus,
    MicrosoftIntegrationStatus,
)

router = APIRouter()


@router.get("/microsoft/status", response_model=MicrosoftIntegrationStatus)
async def get_microsoft_status(current_user: User = Depends(get_current_user)):
    is_enabled = settings.MICROSOFT_MCP_ENABLED
    transport = settings.MICROSOFT_MCP_TRANSPORT
    server_url = settings.MICROSOFT_MCP_SERVER_URL if is_enabled else None

    # Discover/refresh tools if enabled
    tools = []
    error = None
    connected = False
    format_support = {"excel": False, "word": False, "powerpoint": False}

    if is_enabled:
        try:
            discovered = await tool_registry.refresh_tools()
            connected = len(discovered) > 0 or bool(server_url)
            tools = [
                DiscoveredTool(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in discovered
            ]
            format_support = tool_registry.get_format_support()
        except Exception as e:
            error = str(e)
    else:
        error = "Microsoft MCP integration is not enabled in environment configuration (MICROSOFT_MCP_ENABLED=false)"

    return MicrosoftIntegrationStatus(
        enabled=is_enabled,
        transport=transport,
        server_url=server_url,
        authenticated=bool(settings.MICROSOFT_CLIENT_ID and settings.MICROSOFT_CLIENT_SECRET),
        connected=connected,
        discovered_tools=tools,
        error=error,
        format_support=format_support,
        fallback_active=True,  # Local generation fallback is always active and functional
    )


@router.get("/google-docs/status", response_model=GoogleDocsIntegrationStatus)
async def get_google_docs_status(current_user: User = Depends(get_current_user)):
    is_enabled = settings.GOOGLE_DOCS_MCP_ENABLED
    server_url = settings.GOOGLE_DOCS_MCP_SERVER_URL

    tools = []
    error = None
    connected = False
    capabilities = {"read_doc": False, "update_doc": False}
    is_authenticated = bool(
        settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
    )

    if is_enabled:
        try:
            discovered = await google_docs_registry.refresh_tools()
            connected = len(discovered) > 0
            tools = [
                DiscoveredTool(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                    read_only=t.read_only,
                )
                for t in discovered
            ]
            capabilities = google_docs_registry.get_capabilities()
            if not is_authenticated:
                error = "Google Docs MCP server reachable; OAuth 2.0 credentials not yet configured for tool execution."
        except Exception as e:
            error = f"Failed to connect to Google Docs MCP server: {str(e)}"
    else:
        error = "Google Docs MCP integration is disabled (GOOGLE_DOCS_MCP_ENABLED=false). Local Word (.docx) generation remains active."

    return GoogleDocsIntegrationStatus(
        enabled=is_enabled,
        server_url=server_url,
        transport="streamable_http",
        connected=connected,
        authenticated=is_authenticated,
        discovered_tools=tools,
        capabilities=capabilities,
        preview_program_required=True,
        error=error,
    )
