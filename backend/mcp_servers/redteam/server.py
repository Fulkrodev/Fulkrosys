"""RedTeam MCP server: 6 adversary-emulation tools."""
import asyncio

from shared.mcp_protocol import MCPServer

from redteam.tools.atomic_red_team_tool import TOOL as ATOMIC, atomic_red_team_test
from redteam.tools.caldera_create_operation_tool import (
    TOOL as CALDERA_CREATE, caldera_create_operation,
)
from redteam.tools.caldera_get_results_tool import (
    TOOL as CALDERA_RESULTS, caldera_get_results,
)
from redteam.tools.infection_monkey_tool import (
    TOOL as MONKEY, infection_monkey_run,
)
from redteam.tools.purplesharp_tool import TOOL as PURPLE, purplesharp_validate
from redteam.tools.sliver_implant_tool import TOOL as SLIVER, sliver_implant


class RedTeamServer(MCPServer):
    SERVER_NAME = "fulkro-redteam"

    def _register_tools(self):
        self.register_tool(CALDERA_CREATE, caldera_create_operation)
        self.register_tool(CALDERA_RESULTS, caldera_get_results)
        self.register_tool(ATOMIC, atomic_red_team_test)
        self.register_tool(SLIVER, sliver_implant)
        self.register_tool(MONKEY, infection_monkey_run)
        self.register_tool(PURPLE, purplesharp_validate)


if __name__ == "__main__":
    asyncio.run(RedTeamServer().run())
