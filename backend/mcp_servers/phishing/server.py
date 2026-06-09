"""Phishing MCP server: Gophish campaign management (1 tool)."""
import asyncio

from shared.mcp_protocol import MCPServer

from phishing.tools.gophish_tool import TOOL as GOPHISH, gophish_campaign


class PhishingServer(MCPServer):
    SERVER_NAME = "fulkro-phishing"

    def _register_tools(self):
        self.register_tool(GOPHISH, gophish_campaign)


if __name__ == "__main__":
    asyncio.run(PhishingServer().run())
