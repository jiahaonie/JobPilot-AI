"""与核心服务层分离的 MCP 适配器。"""

from typing import Any


def create_mcp_server(name: str = "jobpilot-ai") -> Any:
    """安装可选 SDK 后创建 MCP 服务器。"""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("MCP support is optional. Install the project mcp extra first.") from exc
    return FastMCP(name)
