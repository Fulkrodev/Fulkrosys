"""Tool: metasploit_info — Get detailed info on a Metasploit module."""
from shared.mcp_protocol import MCPTool
from shared.utils import reject_unsafe_args, run_command


TOOL = MCPTool(
    name="metasploit_info",
    description="Display detailed info on a specific Metasploit module.",
    input_schema={
        "properties": {"module": {"type": "string"}},
        "required": ["module"],
    },
    timeout_seconds=120,
    risk_level="low",
    ens_measures=["op.exp.4"],
)


async def metasploit_info(module: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    if (e := reject_unsafe_args(module)):
        return e
    cmd = ["msfconsole", "-qx", f"info {module}; exit"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "module": module,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
