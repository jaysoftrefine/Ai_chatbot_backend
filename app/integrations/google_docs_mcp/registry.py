from typing import Any
from app.integrations.google_docs_mcp.client import GoogleDocsMCPClient, GoogleDocsMCPTool


class GoogleDocsMCPRegistry:
    def __init__(self, client: GoogleDocsMCPClient | None = None):
        self.client = client or GoogleDocsMCPClient()
        self.cached_tools: list[GoogleDocsMCPTool] = []

    async def refresh_tools(self) -> list[GoogleDocsMCPTool]:
        self.cached_tools = await self.client.list_tools()
        return self.cached_tools

    def get_capabilities(self) -> dict[str, bool]:
        tool_names = [t.name.lower() for t in self.cached_tools]
        return {
            "read_doc": "read_doc" in tool_names,
            "update_doc": "update_doc" in tool_names,
        }


google_docs_registry = GoogleDocsMCPRegistry()