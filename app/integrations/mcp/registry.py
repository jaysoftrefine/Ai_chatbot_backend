from typing import Any
from app.integrations.mcp.client import MCPClient, MCPTool


class MCPToolRegistry:
    def __init__(self, client: MCPClient | None = None):
        self.client = client or MCPClient()
        self.cached_tools: list[MCPTool] = []
        self.last_discovered_at: float | None = None

    async def refresh_tools(self) -> list[MCPTool]:
        self.cached_tools = await self.client.list_tools()
        return self.cached_tools

    def get_format_support(self) -> dict[str, bool]:
        """
        Confirms separately whether Excel, Word, and PowerPoint create/edit actions
        are actually exposed by discovered tools.
        """
        tool_names = [t.name.lower() for t in self.cached_tools]
        tool_descriptions = [t.description.lower() for t in self.cached_tools]
        combined = " ".join(tool_names + tool_descriptions)

        return {
            "excel": any("excel" in name or "workbook" in name or "spreadsheet" in name for name in tool_names),
            "word": any("word" in name or "document" in name or "docx" in name for name in tool_names),
            "powerpoint": any("powerpoint" in name or "presentation" in name or "pptx" in name or "slides" in name for name in tool_names),
        }

    def find_tool_for_format(self, format_type: str) -> MCPTool | None:
        target = format_type.lower()
        for tool in self.cached_tools:
            name_lower = tool.name.lower()
            if target == "excel" and ("excel" in name_lower or "spreadsheet" in name_lower):
                return tool
            if target == "word" and ("word" in name_lower or "docx" in name_lower):
                return tool
            if target == "powerpoint" and ("powerpoint" in name_lower or "slide" in name_lower or "presentation" in name_lower):
                return tool
        return None


tool_registry = MCPToolRegistry()

