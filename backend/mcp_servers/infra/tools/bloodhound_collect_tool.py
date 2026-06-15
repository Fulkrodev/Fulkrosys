"""Tool: bloodhound_collect — Gather Active Directory data for BloodHound."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="bloodhound_collect",
    description="Run bloodhound-python ingestor to collect AD objects and relationships.",
    input_schema={
        "properties": {
            "domain": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
            "dc": {"type": "string"},
        },
        "required": ["domain", "user"],
    },
    timeout_seconds=1800,
    risk_level="medium",
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def bloodhound_collect(
    domain: str, user: str, password: str = "", dc: str = ""
) -> dict:
    scope = check_scope(domain, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "python3", "-m", "bloodhound",
        "-d", domain, "-u", user, "-c", "All",
    ]
    if password:
        cmd += ["-p", password]
    if dc:
        cmd += ["-dc", dc]
    result = await run_command(  # §1.4 · redacta el password de command/stdout/logs
        cmd, timeout=TOOL.timeout_seconds, redact=[password] if password else None,
    )
    return {
        "domain": domain, "user": user,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
