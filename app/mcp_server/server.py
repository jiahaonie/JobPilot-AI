"""MCP adapter kept separate from the core service layer."""

from typing import Any


def create_mcp_server(name: str = "jobpilot-ai") -> Any:
    """Create an MCP server when the optional SDK is installed."""

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "MCP support is optional. Install the project mcp extra first."
        ) from exc
    return FastMCP(name)
