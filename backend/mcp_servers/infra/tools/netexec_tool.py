"""Tool: netexec_scan — NetExec (formerly CrackMapExec) network enumeration."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="netexec_scan",
    description="NetExec: SMB/WinRM/LDAP/MSSQL enumeration and credential validation.",
    input_schema={
        "properties": {
            "protocol": {"type": "string", "enum": ["smb", "winrm", "ldap", "mssql", "ssh"]},
            "target": {"type": "string"},
            "user": {"type": "string"},
            "password": {"type": "string"},
        },
        "required": ["protocol", "target"],
    },
    timeout_seconds=900,
    risk_level="medium",
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def netexec_scan(
    protocol: str, target: str, user: str = "", password: str = ""
) -> dict:
    scope = check_scope(target, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["netexec", protocol, target]
    if user:
        cmd += ["-u", user]
    if password:
        cmd += ["-p", password]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "protocol": protocol, "target": target,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
