"""Tool: coercer_check — Coercer NTLM coercion pre-checks."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="coercer_check",
    description="Coercer: detect RPC methods that allow NTLM coercion (PetitPotam, PrintSpoofer...).",
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "domain": {"type": "string"},
        },
        "required": ["target"],
    },
    timeout_seconds=900,
    risk_level="medium",
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def coercer_check(
    target: str, user: str = "", password: str = "", domain: str = ""
) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["coercer", "scan", "-t", target]
    if user:
        cmd += ["-u", user]
    if password:
        cmd += ["-p", password]
    if domain:
        cmd += ["-d", domain]
    result = await run_command(  # §1.4 · redacta el password de command/stdout/logs
        cmd, timeout=TOOL.timeout_seconds, redact=[password] if password else None,
    )
    return {
        "target": target,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
