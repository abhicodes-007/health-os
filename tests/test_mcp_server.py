"""The MCP server module imports and registers every tool (catches SDK breaking changes)."""
import asyncio

from mcp_server.server import mcp


def test_server_registers_all_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert len(names) == 26
    assert {"get_health_summary", "stage_lab_panel", "approve_staged_source", "log_meal"} <= names
