"""Tool: impacket_tool — Run an Impacket SMB/RPC script against a target."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import reject_unsafe_args, run_command


TOOL = MCPTool(
    name="impacket_tool",
    description=(
        "Run an Impacket script (e.g. secretsdump, psexec, smbexec) with the given credentials. "
        "High impact, requires approval."
    ),
    input_schema={
        "properties": {
            "tool": {"type": "string", "description": "Impacket module name"},
            "domain": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "target": {"type": "string"},
        },
        "required": ["tool", "target"],
    },
    timeout_seconds=900,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def impacket_tool(
    tool: str,
    target: str,
    domain: str = "",
    user: str = "",
    password: str = "",
) -> dict:
    scope = check_scope(target, "exploit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    # `tool` se interpola en el módulo `impacket.{tool}` → validar (los args van
    # por exec en lista, sin shell, pero el nombre de módulo no debe llevar
    # metacaracteres). creds/password NO se validan (pueden ser legítimos y van
    # como un único arg de lista, sin shell).
    if (e := reject_unsafe_args(tool)):
        return e
    creds = f"{domain}/{user}:{password}@{target}" if user else target
    cmd = ["python3", "-m", f"impacket.{tool}", creds]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "tool": tool, "target": target,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
