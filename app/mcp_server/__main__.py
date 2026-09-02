"""可选 MCP 服务器的命令行入口。"""

from app.mcp_server.server import create_mcp_server


def main() -> None:
    """使用 SDK 默认传输方式运行 MCP 服务器。"""
    create_mcp_server().run()


if __name__ == "__main__":
    main()
