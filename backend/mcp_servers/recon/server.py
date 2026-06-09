"""Recon MCP server: 11 reconnaissance tools (post SAN-B.MB-7.1)."""
import asyncio

from shared.mcp_protocol import MCPServer

from recon.tools.amass_tool import TOOL as AMASS, amass_enum
from recon.tools.dns_checker_tool import TOOL as DNS_CHECK, dns_security_check
from recon.tools.httpx_tool import TOOL as HTTPX, httpx_probe
from recon.tools.masscan_tool import TOOL as MASSCAN, masscan_sweep
from recon.tools.naabu_tool import TOOL as NAABU, naabu_portscan
from recon.tools.nmap_tool import TOOL as NMAP, nmap_scan
from recon.tools.searchsploit_tool import TOOL as SEARCHSPLOIT, searchsploit_query
from recon.tools.shodan_tool import TOOL as SHODAN, shodan_lookup
from recon.tools.spiderfoot_tool import TOOL as SPIDERFOOT, spiderfoot_osint
from recon.tools.subfinder_tool import TOOL as SUBFINDER, subfinder_enum
from recon.tools.theharvester_tool import TOOL as HARVESTER, theharvester_recon


class ReconServer(MCPServer):
    SERVER_NAME = "fulkro-recon"

    def _register_tools(self):
        self.register_tool(NMAP, nmap_scan)
        self.register_tool(MASSCAN, masscan_sweep)
        self.register_tool(AMASS, amass_enum)
        self.register_tool(SUBFINDER, subfinder_enum)
        self.register_tool(HTTPX, httpx_probe)
        self.register_tool(NAABU, naabu_portscan)
        self.register_tool(SHODAN, shodan_lookup)
        self.register_tool(HARVESTER, theharvester_recon)
        self.register_tool(SPIDERFOOT, spiderfoot_osint)
        self.register_tool(SEARCHSPLOIT, searchsploit_query)
        self.register_tool(DNS_CHECK, dns_security_check)


if __name__ == "__main__":
    asyncio.run(ReconServer().run())
