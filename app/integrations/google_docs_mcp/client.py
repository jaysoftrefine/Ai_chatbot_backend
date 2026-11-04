import logging
import time
from typing import Any
import httpx
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleDocsMCPTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = {}
    read_only: bool = False


class GoogleDocsMCPClient:
    def __init__(
        self,
        server_url: str | None = None,
        oauth_access_token: str | None = None,
    ):
        self.server_url = server_url or settings.GOOGLE_DOCS_MCP_SERVER_URL
        self.oauth_access_token = oauth_access_token

    def is_enabled(self) -> bool:
        return bool(settings.GOOGLE_DOCS_MCP_ENABLED)

    def is_authenticated(self) -> bool:
        return bool(self.oauth_access_token or (settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET))

    async def list_tools(self) -> list[GoogleDocsMCPTool]:
        """
        Discovers tools at runtime via JSON-RPC 'tools/list' from the official Google Docs MCP server.
        """
        if not self.is_enabled():
            logger.info("Google Docs MCP is disabled in configuration.")
            return []

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.oauth_access_token:
            headers["Authorization"] = f"Bearer {self.oauth_access_token}"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(self.server_url, json=payload, headers=headers)
                if res.status_code != 200:
                    logger.warning(
                        "Google Docs MCP server responded with HTTP %d: %s",
                        res.status_code,
                        res.text[:200],
                    )
                    return []
                data = res.json()
                tools_data = data.get("result", {}).get("tools", [])
                tools = []
                for t in tools_data:
                    annotations = t.get("annotations", {})
                    tools.append(
                        GoogleDocsMCPTool(
                            name=t.get("name", ""),
                            description=t.get("description", ""),
                            input_schema=t.get("inputSchema", {}),
                            read_only=annotations.get("readOnlyHint", False),
                        )
                    )
                return tools
        except Exception as e:
            logger.warning("Error discovering tools from Google Docs MCP: %s", e)
            return []

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Invokes a tool via JSON-RPC 'tools/call'.
        """
        if not self.is_enabled():
            raise RuntimeError("Google Docs MCP server is not enabled in settings")

        token = access_token or self.oauth_access_token
        if not token:
            raise PermissionError(
                "Google Docs MCP call requires an active Google OAuth 2.0 access token with Docs API scopes"
            )

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(self.server_url, json=payload, headers=headers)
            if res.status_code == 401:
                raise PermissionError(
                    "Google Docs MCP authentication failed: OAuth access token missing, expired, or lacking docs scope."
                )
            if res.status_code != 200:
                raise RuntimeError(
                    f"Google Docs MCP server error HTTP {res.status_code}: {res.text}"
                )
            data = res.json()
            if "error" in data:
                raise RuntimeError(f"Google Docs MCP tool error: {data['error']}")
            return data.get("result", {})

