"""Tool: kerbrute_enum — Kerberos userenum/bruteforce."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="kerbrute_enum",
    description="Kerberos username enumeration against an AD domain controller.",
    input_schema={
        "properties": {
            "domain": {"type": "string"},
            "dc": {"type": "string"},
            "userlist": {"type": "string", "description": "Path to newline-separated usernames"},
        },
        "required": ["domain", "dc", "userlist"],
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["op.acc.5"],
)


async def kerbrute_enum(domain: str, dc: str, userlist: str) -> dict:
    scope = check_scope(dc, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["kerbrute", "userenum", "--dc", dc, "-d", domain, userlist]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "domain": domain, "dc": dc,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
