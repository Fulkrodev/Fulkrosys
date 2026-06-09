"""Mobile MCP server: 2 mobile-app security tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from mobile.tools.apktool_tool import TOOL as APKTOOL, apktool_decompile
from mobile.tools.mobsf_tool import TOOL as MOBSF, mobsf_scan


class MobileServer(MCPServer):
    SERVER_NAME = "fulkro-mobile"

    def _register_tools(self):
        self.register_tool(MOBSF, mobsf_scan)
        self.register_tool(APKTOOL, apktool_decompile)


if __name__ == "__main__":
    asyncio.run(MobileServer().run())
