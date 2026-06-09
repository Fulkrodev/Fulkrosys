"""Config MCP server: 4 configuration/hardening audit tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from config.tools.cis_cat_tool import TOOL as CIS, cis_cat_audit
from config.tools.clara_tool import TOOL as CLARA, clara_ccn_audit
from config.tools.lynis_tool import TOOL as LYNIS, lynis_audit
from config.tools.openscap_tool import TOOL as OPENSCAP, openscap_audit


class ConfigServer(MCPServer):
    SERVER_NAME = "fulkro-config"

    def _register_tools(self):
        self.register_tool(CLARA, clara_ccn_audit)
        self.register_tool(OPENSCAP, openscap_audit)
        self.register_tool(LYNIS, lynis_audit)
        self.register_tool(CIS, cis_cat_audit)


if __name__ == "__main__":
    asyncio.run(ConfigServer().run())
