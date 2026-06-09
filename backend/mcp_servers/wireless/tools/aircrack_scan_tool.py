"""Tool: aircrack_scan — Scan surrounding WiFi networks with airodump-ng."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="aircrack_scan",
    description=(
        "Passive WiFi scan with airodump-ng for N seconds. Requires a monitor-mode interface."
    ),
    input_schema={
        "properties": {
            "interface": {"type": "string", "default": "wlan0mon"},
            "duration_seconds": {"type": "integer", "default": 60},
        }
    },
    timeout_seconds=600,
    risk_level="low",
    ens_measures=["mp.com.1", "mp.com.2"],
)


async def aircrack_scan(
    interface: str = "wlan0mon", duration_seconds: int = 60
) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "timeout", str(duration_seconds),
        "airodump-ng", interface, "--output-format", "csv", "-w", "/tmp/airodump",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "interface": interface, "duration_seconds": duration_seconds,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
