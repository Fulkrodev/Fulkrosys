"""Tool: certipy_adcs — Certipy AD CS enumeration and abuse detection."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="certipy_adcs",
    description="Certipy: enumerate AD CS vulnerabilities (ESC1-ESC11) and misconfigured templates.",
    input_schema={
        "properties": {
            "domain": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "dc_ip": {"type": "string"},
        },
        "required": ["domain", "user"],
    },
    timeout_seconds=900,
    risk_level="medium",
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def certipy_adcs(
    domain: str, user: str, password: str = "", dc_ip: str = ""
) -> dict:
    scope = check_scope(dc_ip or domain, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["certipy", "find", "-u", f"{user}@{domain}"]
    if password:
        cmd += ["-p", password]
    if dc_ip:
        cmd += ["-dc-ip", dc_ip]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "domain": domain, "user": user,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
