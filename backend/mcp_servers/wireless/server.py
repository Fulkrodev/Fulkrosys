"""Wireless MCP server: 3 WiFi security tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from wireless.tools.aircrack_attack_tool import TOOL as AIRCRACK_ATTACK, aircrack_attack
from wireless.tools.aircrack_scan_tool import TOOL as AIRCRACK_SCAN, aircrack_scan
from wireless.tools.wifite_tool import TOOL as WIFITE, wifite_auto


class WirelessServer(MCPServer):
    SERVER_NAME = "fulkro-wireless"

    def _register_tools(self):
        self.register_tool(AIRCRACK_SCAN, aircrack_scan)
        self.register_tool(AIRCRACK_ATTACK, aircrack_attack)
        self.register_tool(WIFITE, wifite_auto)


if __name__ == "__main__":
    asyncio.run(WirelessServer().run())
