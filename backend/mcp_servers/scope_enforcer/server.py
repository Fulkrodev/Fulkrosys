"""Scope Enforcer MCP server — exposes a single check_scope tool.

The real function of this server is operational: every other MCP server
calls its local ``shared.scope_check`` helper before any tool runs. This
MCP endpoint exists so an orchestrator can audit scope decisions over the
same JSON-RPC bus.
"""
import asyncio
import json
import os

from shared.mcp_protocol import MCPServer, MCPTool
from scope_enforcer.enforcer import ScopeEnforcer


AUTHORIZATION_TOOL = MCPTool(
    name="check_scope",
    description=(
        "Validate whether a target is inside the signed engagement scope. "
        "Returns {allowed, reason}. Fail-closed on any unexpected state."
    ),
    input_schema={
        "properties": {
            "target": {"type": "string", "description": "IP, CIDR or hostname"},
            "test_type": {"type": "string", "default": "scan"},
        },
        "required": ["target"],
    },
    risk_level="low",
    timeout_seconds=10,
)


def _load_auth() -> dict:
    raw = os.environ.get("PENTEST_AUTHORIZATION", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    path = os.environ.get("PENTEST_AUTHORIZATION_FILE", "/app/authorization.json")
    if os.path.exists(path):
        try:
            with open(path) as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}


async def check_scope_handler(target: str, test_type: str = "scan") -> dict:
    enforcer = ScopeEnforcer(_load_auth())
    return enforcer.check(target, test_type)


class ScopeEnforcerServer(MCPServer):
    SERVER_NAME = "fulkro-scope-enforcer"

    def _register_tools(self):
        self.register_tool(AUTHORIZATION_TOOL, check_scope_handler)


if __name__ == "__main__":
    asyncio.run(ScopeEnforcerServer().run())
