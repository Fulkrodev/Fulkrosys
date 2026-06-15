"""Tool: metasploit_post — Run post-exploitation module on an existing session."""
from shared.mcp_protocol import MCPTool
from shared.utils import reject_unsafe_args, run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="metasploit_post",
    description="Run an MSF post-exploitation module. Requires an active session. Approval required.",
    input_schema={
        "properties": {
            "module": {"type": "string"},
            "session": {"type": "integer"},
        },
        "required": ["module", "session"],
    },
    timeout_seconds=1200,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def metasploit_post(module: str, session: int) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    if (e := reject_unsafe_args(module)):
        return e
    cmd = [
        "msfconsole", "-qx",
        f"use {module}; set SESSION {session}; run; exit",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "module": module, "session": session,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
