"""Tool: metasploit_check — Non-intrusive vulnerability check via MSF `check`."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="metasploit_check",
    description="Run non-intrusive vulnerability `check` for a specific MSF exploit module.",
    input_schema={
        "properties": {
            "module": {"type": "string"},
            "target": {"type": "string"},
        },
        "required": ["module", "target"],
    },
    timeout_seconds=600,
    risk_level="medium",
    ens_measures=["op.exp.4"],
)


async def metasploit_check(module: str, target: str) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "msfconsole", "-qx",
        f"use {module}; set RHOSTS {target}; check; exit",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "module": module, "target": target,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
