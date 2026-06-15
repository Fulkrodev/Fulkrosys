"""Tool: atomic_red_team_test — Run an Atomic Red Team technique."""
from shared.mcp_protocol import MCPTool
from shared.utils import reject_unsafe_args, run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="atomic_red_team_test",
    description=(
        "Execute an Atomic Red Team technique (e.g. T1059.001) on the local host. "
        "Intended for validating EDR detections."
    ),
    input_schema={
        "properties": {
            "technique": {"type": "string", "description": "MITRE ATT&CK ID, e.g. T1059.001"},
            "test_index": {"type": "integer", "default": 1},
        },
        "required": ["technique"],
    },
    timeout_seconds=300,
    risk_level="high",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def atomic_red_team_test(technique: str, test_index: int = 1) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    if (e := reject_unsafe_args(technique)):
        return e
    cmd = [
        "powershell", "-Command",
        f"Invoke-AtomicTest {technique} -TestNumbers {test_index}",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "technique": technique, "test_index": test_index,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
