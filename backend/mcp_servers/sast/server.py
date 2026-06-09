"""SAST MCP server: 5 static analysis / dependency audit tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from sast.tools.bandit_tool import TOOL as BANDIT, bandit_scan
from sast.tools.checkov_tool import TOOL as CHECKOV, checkov_scan
from sast.tools.depcheck_tool import TOOL as DEPCHECK, dependency_check
from sast.tools.safety_tool import TOOL as SAFETY, safety_audit
from sast.tools.semgrep_tool import TOOL as SEMGREP, semgrep_scan


class SastServer(MCPServer):
    SERVER_NAME = "fulkro-sast"

    def _register_tools(self):
        self.register_tool(SEMGREP, semgrep_scan)
        self.register_tool(BANDIT, bandit_scan)
        self.register_tool(SAFETY, safety_audit)
        self.register_tool(DEPCHECK, dependency_check)
        self.register_tool(CHECKOV, checkov_scan)


if __name__ == "__main__":
    asyncio.run(SastServer().run())
