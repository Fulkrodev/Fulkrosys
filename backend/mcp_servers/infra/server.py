"""Infra MCP server: 14 internal/AD/infrastructure tools (post SAN-B.MB-7.1)."""
import asyncio

from shared.mcp_protocol import MCPServer

from infra.tools.bloodhound_analyze_tool import TOOL as BH_ANALYZE, bloodhound_analyze
from infra.tools.bloodhound_collect_tool import TOOL as BH_COLLECT, bloodhound_collect
from infra.tools.certipy_tool import TOOL as CERTIPY, certipy_adcs
from infra.tools.coercer_tool import TOOL as COERCER, coercer_check
from infra.tools.impacket_tool import TOOL as IMPACKET, impacket_tool
from infra.tools.kerbrute_tool import TOOL as KERBRUTE, kerbrute_enum
from infra.tools.lynis_tool import TOOL as LYNIS, lynis_audit
from infra.tools.metasploit_check_tool import TOOL as MSF_CHECK, metasploit_check
from infra.tools.metasploit_exploit_tool import TOOL as MSF_EXPLOIT, metasploit_exploit
from infra.tools.metasploit_info_tool import TOOL as MSF_INFO, metasploit_info
from infra.tools.metasploit_post_tool import TOOL as MSF_POST, metasploit_post
from infra.tools.metasploit_search_tool import TOOL as MSF_SEARCH, metasploit_search
from infra.tools.netexec_tool import TOOL as NETEXEC, netexec_scan
from infra.tools.responder_tool import TOOL as RESPONDER, responder_capture


class InfraServer(MCPServer):
    SERVER_NAME = "fulkro-infra"

    def _register_tools(self):
        self.register_tool(MSF_SEARCH, metasploit_search)
        self.register_tool(MSF_INFO, metasploit_info)
        self.register_tool(MSF_CHECK, metasploit_check)
        self.register_tool(MSF_EXPLOIT, metasploit_exploit)
        self.register_tool(MSF_POST, metasploit_post)
        self.register_tool(IMPACKET, impacket_tool)
        self.register_tool(NETEXEC, netexec_scan)
        self.register_tool(BH_COLLECT, bloodhound_collect)
        self.register_tool(BH_ANALYZE, bloodhound_analyze)
        self.register_tool(RESPONDER, responder_capture)
        self.register_tool(KERBRUTE, kerbrute_enum)
        self.register_tool(CERTIPY, certipy_adcs)
        self.register_tool(COERCER, coercer_check)
        self.register_tool(LYNIS, lynis_audit)


if __name__ == "__main__":
    asyncio.run(InfraServer().run())
