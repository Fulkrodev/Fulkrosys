"""Cracking MCP server: 4 password-cracking + AD policy tools (post SAN-B.MB-7.1)."""
import asyncio

from shared.mcp_protocol import MCPServer

from cracking.tools.ad_password_check_tool import TOOL as AD_PWPOL, ad_password_policy_check
from cracking.tools.cewl_tool import TOOL as CEWL, cewl_wordlist
from cracking.tools.hashcat_tool import TOOL as HASHCAT, hashcat_crack
from cracking.tools.john_tool import TOOL as JOHN, john_crack


class CrackingServer(MCPServer):
    SERVER_NAME = "fulkro-cracking"

    def _register_tools(self):
        self.register_tool(HASHCAT, hashcat_crack)
        self.register_tool(JOHN, john_crack)
        self.register_tool(CEWL, cewl_wordlist)
        self.register_tool(AD_PWPOL, ad_password_policy_check)


if __name__ == "__main__":
    asyncio.run(CrackingServer().run())
