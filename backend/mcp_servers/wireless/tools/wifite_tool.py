"""Tool: wifite_auto — Wifite2 automated wireless attack workflow."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="wifite_auto",
    description=(
        "wifite2 automated WiFi attacks (WPS, WPA handshake, PMKID). "
        "Must be used only against authorized BSSIDs."
    ),
    input_schema={
        "properties": {
            "interface": {"type": "string", "default": "wlan0"},
            "bssid": {"type": "string"},
        }
    },
    timeout_seconds=3600,
    risk_level="high",
    requires_approval=True,
    ens_measures=["mp.com.2"],
)


async def wifite_auto(interface: str = "wlan0", bssid: str | None = None) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["wifite", "-i", interface, "--nodeauths"]
    if bssid:
        cmd += ["--bssid", bssid]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "interface": interface, "bssid": bssid,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
