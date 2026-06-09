"""APISec MCP server: 4 API-security tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from apisec.tools.arjun_tool import TOOL as ARJUN, arjun_param_discovery
from apisec.tools.auth_bypass_tool import TOOL as AUTH, api_auth_bypass_test
from apisec.tools.graphql_tool import TOOL as GRAPHQL, graphql_introspection
from apisec.tools.kiterunner_tool import TOOL as KITERUNNER, kiterunner_api_fuzz


class ApiSecServer(MCPServer):
    SERVER_NAME = "fulkro-apisec"

    def _register_tools(self):
        self.register_tool(ARJUN, arjun_param_discovery)
        self.register_tool(GRAPHQL, graphql_introspection)
        self.register_tool(KITERUNNER, kiterunner_api_fuzz)
        self.register_tool(AUTH, api_auth_bypass_test)


if __name__ == "__main__":
    asyncio.run(ApiSecServer().run())
