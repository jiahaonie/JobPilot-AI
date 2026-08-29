"""Command-line entry point for the optional MCP server."""

from app.mcp_server.server import create_mcp_server


def main() -> None:
    """Run the MCP server using the SDK's default transport."""

    create_mcp_server().run()


if __name__ == "__main__":
    main()
