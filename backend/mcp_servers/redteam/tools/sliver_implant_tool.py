"""Tool: sliver_implant — Generate a Sliver implant (CRITICAL, approval)."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="sliver_implant",
    description=(
        "Generate a Sliver C2 implant binary. Extremely sensitive: only valid inside a signed "
        "red team engagement."
    ),
    input_schema={
        "properties": {
            "name": {"type": "string"},
            "os": {"type": "string", "default": "linux"},
            "arch": {"type": "string", "default": "amd64"},
            "protocol": {"type": "string", "default": "mtls"},
        },
        "required": ["name"],
    },
    timeout_seconds=600,
    risk_level="critical",
    requires_approval=True,
    ens_measures=["op.exp.4"],
)


async def sliver_implant(
    name: str, os: str = "linux", arch: str = "amd64", protocol: str = "mtls"
) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = [
        "sliver-client", "--command",
        f"generate --{protocol} --os {os} --arch {arch} --name {name}",
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "name": name, "os": os, "arch": arch, "protocol": protocol,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
