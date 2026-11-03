import time
from typing import Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models.mcp_tool_run import McpToolRun
from app.integrations.mcp.client import MCPClient, MCPTool
from app.integrations.mcp.registry import tool_registry


class MCPExecutor:
    def __init__(self, client: MCPClient | None = None):
        self.client = client or tool_registry.client

    def validate_arguments(self, tool: MCPTool, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        schema = tool.input_schema or {}
        required = schema.get("required", [])
        for req_field in required:
            if req_field not in arguments:
                return False, f"Missing required parameter: {req_field}"
        return True, None

    async def execute_tool(
        self,
        db: Session,
        user_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        start_time = time.time()
        status = "error"
        error_code = None

        try:
            # Check schema validation
            tool = next((t for t in tool_registry.cached_tools if t.name == tool_name), None)
            if tool:
                is_valid, validation_err = self.validate_arguments(tool, arguments)
                if not is_valid:
                    error_code = "VALIDATION_ERROR"
                    raise ValueError(validation_err)

            result = await self.client.call_tool(tool_name, arguments)
            status = "success"
            return result
        except Exception as e:
            error_code = type(e).__name__
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            # Log run safely without secrets or full document body
            run_record = McpToolRun(
                user_id=user_id,
                server_name=settings.MICROSOFT_MCP_SERVER_URL or "microsoft_mcp",
                tool_name=tool_name,
                status=status,
                duration_ms=duration_ms,
                error_code=error_code,
            )
            db.add(run_record)
            db.commit()


mcp_executor = MCPExecutor()

