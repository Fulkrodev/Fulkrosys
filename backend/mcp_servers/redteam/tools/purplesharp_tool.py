"""Tool: purplesharp_validate — PurpleSharp Windows adversary simulation."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="purplesharp_validate",
    description="PurpleSharp: execute Windows adversary simulation playbook to validate SIEM rules.",
    input_schema={
        "properties": {
            "playbook": {"type": "string"},
        },
        "required": ["playbook"],
    },
    timeout_seconds=1200,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def purplesharp_validate(playbook: str) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["PurpleSharp.exe", "-p", playbook]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "playbook": playbook,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
