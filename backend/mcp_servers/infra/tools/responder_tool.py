"""Tool: responder_capture — Responder LLMNR/NBT-NS poisoner (HIGH, approval)."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="responder_capture",
    description=(
        "Responder: LLMNR/NBT-NS/MDNS poisoning to capture NetNTLMv2 hashes. "
        "Intrusive — only usable during authorized internal pentests."
    ),
    input_schema={
        "properties": {
            "interface": {"type": "string", "default": "eth0"},
            "duration_seconds": {"type": "integer", "default": 120},
        },
        "required": ["interface"],
    },
    timeout_seconds=600,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.acc.5", "op.exp.4"],
)


async def responder_capture(interface: str = "eth0", duration_seconds: int = 120) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "timeout", str(duration_seconds),
        "python3", "/opt/responder/Responder.py",
        "-I", interface, "-wrfFP",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "interface": interface, "duration_seconds": duration_seconds,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
