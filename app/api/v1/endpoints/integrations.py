from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.integrations.mcp.registry import tool_registry
from app.schemas.integrations import DiscoveredTool, MicrosoftIntegrationStatus

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

