"""Tool: lynis_audit — Lynis Linux hardening audit."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="lynis_audit",
    description="Lynis: in-depth Linux/Unix hardening audit with report file.",
    input_schema={
        "properties": {
            "target": {"type": "string", "default": "localhost"},
        }
    },
    timeout_seconds=1200,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.si.2"],
)


async def lynis_audit(target: str = "localhost") -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["lynis", "audit", "system", "--quiet", "--no-colors"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "target": target,
        "command": result["command"],
        "stdout": result["stdout"][:10000],
        "returncode": result["returncode"],
    }
