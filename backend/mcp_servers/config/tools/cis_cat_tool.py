"""Tool: cis_cat_audit — CIS-CAT benchmark assessment."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="cis_cat_audit",
    description="CIS-CAT Pro/Lite benchmark assessment — runs selected CIS profile on target.",
    input_schema={
        "properties": {
            "benchmark": {"type": "string"},
            "profile": {"type": "string", "default": "Level 1"},
        },
        "required": ["benchmark"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.si.2"],
)


async def cis_cat_audit(benchmark: str, profile: str = "Level 1") -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["CIS-CAT.sh", "-b", benchmark, "-p", profile]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "benchmark": benchmark, "profile": profile,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
