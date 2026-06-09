"""VulnScan MCP server: 4 vulnerability-assessment tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from vulnscan.tools.grype_tool import TOOL as GRYPE, grype_sbom_scan
from vulnscan.tools.nuclei_tool import TOOL as NUCLEI, nuclei_scan
from vulnscan.tools.openvas_tool import TOOL as OPENVAS, openvas_scan
from vulnscan.tools.trivy_tool import TOOL as TRIVY, trivy_scan


class VulnScanServer(MCPServer):
    SERVER_NAME = "fulkro-vulnscan"

    def _register_tools(self):
        self.register_tool(NUCLEI, nuclei_scan)
        self.register_tool(OPENVAS, openvas_scan)
        self.register_tool(TRIVY, trivy_scan)
        self.register_tool(GRYPE, grype_sbom_scan)


if __name__ == "__main__":
    asyncio.run(VulnScanServer().run())
