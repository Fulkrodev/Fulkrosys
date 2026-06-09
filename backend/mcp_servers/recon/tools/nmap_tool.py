"""Tool: nmap_scan — Network scanner. Most used tool in reconnaissance."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_nmap_xml, run_command


TOOL = MCPTool(
    name="nmap_scan",
    description=(
        "Nmap network scanner. Modes: quick (top 100 ports -sV), full (-sV -p-),"
        " stealth (-sS), udp (-sU), vuln (--script vuln), custom (free args)."
    ),
    input_schema={
        "properties": {
            "target": {"type": "string"},
            "mode": {"type": "string", "enum": ["quick", "full", "stealth", "udp", "vuln", "custom"], "default": "quick"},
            "ports": {"type": "string"},
            "custom_args": {"type": "string"},
            "timing": {"type": "string", "enum": ["T0", "T1", "T2", "T3", "T4", "T5"], "default": "T4"},
        },
        "required": ["target"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.1", "op.pl.2"],
)


_MODE_ARGS = {
    "quick": ["-sV", "--top-ports", "100"],
    "full": ["-sV", "-p-"],
    "stealth": ["-sS", "-sV", "--top-ports", "1000"],
    "udp": ["-sU", "--top-ports", "100"],
    "vuln": ["-sV", "--script", "vuln", "--top-ports", "1000"],
}


async def nmap_scan(
    target: str,
    mode: str = "quick",
    ports: str | None = None,
    custom_args: str | None = None,
    timing: str = "T4",
) -> dict:
    scope = check_scope(target, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "hosts": []}

    cmd = ["nmap", "-oX", "-", f"-{timing}"]
    if mode == "custom" and custom_args:
        cmd += custom_args.split()
    else:
        cmd += _MODE_ARGS.get(mode, _MODE_ARGS["quick"])

    if ports:
        cmd = [a for a in cmd if not a.startswith("--top-ports") and a != "-p-"]
        cmd += ["-p", ports]

    cmd.append(target)
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)

    if result["returncode"] not in (0, None) and not result["stdout"]:
        return {"error": result["stderr"][:2000], "command": result["command"], "hosts": []}

    parsed = parse_nmap_xml(result["stdout"])
    parsed["command"] = result["command"]
    parsed["scan_mode"] = mode
    open_ports = sum(1 for h in parsed["hosts"] for p in h["ports"] if p["state"] == "open")
    parsed["summary"] = {
        "hosts_up": sum(1 for h in parsed["hosts"] if h["state"] == "up"),
        "total_ports_scanned": sum(len(h["ports"]) for h in parsed["hosts"]),
        "open_ports": open_ports,
    }
    return parsed
