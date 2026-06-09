"""Tool: aircrack_attack — WiFi handshake capture + offline crack (approval)."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="aircrack_attack",
    description=(
        "Deauth + capture WPA handshake, then offline crack with aircrack-ng. "
        "Destructive to the connected clients — requires explicit approval."
    ),
    input_schema={
        "properties": {
            "bssid": {"type": "string"},
            "channel": {"type": "integer"},
            "interface": {"type": "string", "default": "wlan0mon"},
            "wordlist": {"type": "string", "default": "/opt/wordlists/rockyou.txt"},
        },
        "required": ["bssid", "channel"],
    },
    timeout_seconds=1800,
    risk_level="high",
    requires_approval=True,
    ens_measures=["mp.com.2"],
)


async def aircrack_attack(
    bssid: str,
    channel: int,
    interface: str = "wlan0mon",
    wordlist: str = "/opt/wordlists/rockyou.txt",
) -> dict:
    scope = check_scope(bssid, "exploit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "aircrack-ng", "-w", wordlist,
        "-b", bssid, "/tmp/capture-01.cap",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "bssid": bssid, "channel": channel, "interface": interface,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
