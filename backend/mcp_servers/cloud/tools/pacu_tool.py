"""Tool: pacu_attack — Rhino Security Labs Pacu AWS exploitation framework."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="pacu_attack",
    description=(
        "Pacu: run AWS exploitation module (enumeration, privesc, persistence). "
        "Destructive actions require approval."
    ),
    input_schema={
        "properties": {
            "module": {"type": "string"},
            "aws_account_id": {"type": "string"},
        },
        "required": ["module", "aws_account_id"],
    },
    timeout_seconds=1200,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4", "op.nub.1"],
)


async def pacu_attack(module: str, aws_account_id: str) -> dict:
    scope = check_scope(aws_account_id, "exploit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["pacu", "--session", "fulkro", "--exec", f"run {module}"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "module": module, "aws_account_id": aws_account_id,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
