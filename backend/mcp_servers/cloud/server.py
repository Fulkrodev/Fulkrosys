"""Cloud MCP server: 4 cloud-security tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from cloud.tools.kube_security_tool import TOOL as KUBE, kube_security_scan
from cloud.tools.pacu_tool import TOOL as PACU, pacu_attack
from cloud.tools.prowler_tool import TOOL as PROWLER, prowler_audit
from cloud.tools.scoutsuite_tool import TOOL as SCOUT, scoutsuite_audit


class CloudServer(MCPServer):
    SERVER_NAME = "fulkro-cloud"

    def _register_tools(self):
        self.register_tool(PROWLER, prowler_audit)
        self.register_tool(SCOUT, scoutsuite_audit)
        self.register_tool(PACU, pacu_attack)
        self.register_tool(KUBE, kube_security_scan)


if __name__ == "__main__":
    asyncio.run(CloudServer().run())
