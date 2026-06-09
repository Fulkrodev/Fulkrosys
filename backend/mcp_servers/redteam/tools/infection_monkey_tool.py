"""Tool: infection_monkey_run — Guardicore/Akamai Infection Monkey simulation."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="infection_monkey_run",
    description=(
        "Launch Infection Monkey to safely simulate lateral movement across the "
        "authorized network segment."
    ),
    input_schema={
        "properties": {
            "target_network": {"type": "string"},
            "duration_minutes": {"type": "integer", "default": 30},
        },
        "required": ["target_network"],
    },
    timeout_seconds=3600,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def infection_monkey_run(
    target_network: str, duration_minutes: int = 30
) -> dict:
    scope = check_scope(target_network, "exploit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "monkey-island", "run",
        "--network", target_network,
        "--duration", str(duration_minutes * 60),
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "target_network": target_network,
        "duration_minutes": duration_minutes,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
