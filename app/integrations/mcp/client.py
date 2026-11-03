import json
import logging
import time
from typing import Any
import httpx
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class MCPTool(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = {}


class MCPClient:
    def __init__(
        self,
        server_url: str | None = None,
        transport: str = "streamable_http",
        auth_token: str | None = None,
    ):
        self.server_url = server_url or settings.MICROSOFT_MCP_SERVER_URL
        self.transport = transport or settings.MICROSOFT_MCP_TRANSPORT
        self.auth_token = auth_token

    def is_configured(self) -> bool:
        return bool(settings.MICROSOFT_MCP_ENABLED and (self.server_url or settings.MICROSOFT_MCP_COMMAND))

    async def list_tools(self) -> list[MCPTool]:
        """
        Discovers tools at runtime via JSON-RPC 'tools/list'.
        """
        if not self.is_configured():
            logger.info("Microsoft MCP is not configured or disabled.")
            return []

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.server_url, json=payload, headers=headers)
                if res.status_code != 200:
                    logger.warning(f"MCP server responded with status {res.status_code}")
                    return []
                data = res.json()
                tools_data = data.get("result", {}).get("tools", [])
                tools = []
                for t in tools_data:
                    tools.append(
                        MCPTool(
                            name=t.get("name", ""),
                            description=t.get("description", ""),
                            input_schema=t.get("inputSchema", {}),
                        )
                    )
                return tools
        except Exception as e:
            logger.warning(f"Failed to discover tools from MCP server: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Invokes a tool via JSON-RPC 'tools/call'.
        """
        if not self.is_configured():
            raise RuntimeError("MCP server is not configured or disabled")

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(self.server_url, json=payload, headers=headers)
            if res.status_code != 200:
                raise RuntimeError(f"MCP server error HTTP {res.status_code}: {res.text}")
            data = res.json()
            if "error" in data:
                raise RuntimeError(f"MCP tool error: {data['error']}")
            return data.get("result", {})

