"""Tool: openscap_audit — OpenSCAP compliance audit (CIS, STIG, PCI)."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="openscap_audit",
    description="Run OpenSCAP xccdf evaluation against a system with the selected profile.",
    input_schema={
        "properties": {
            "profile": {"type": "string", "default": "xccdf_org.ssgproject.content_profile_cis"},
            "datastream": {"type": "string"},
        },
        "required": ["datastream"],
    },
    timeout_seconds=1800,
    risk_level="low",
    ens_measures=["op.exp.2", "mp.si.2"],
)


async def openscap_audit(
    datastream: str,
    profile: str = "xccdf_org.ssgproject.content_profile_cis",
) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = [
        "oscap", "xccdf", "eval",
        "--profile", profile,
        "--results-arf", "/tmp/oscap_arf.xml",
        datastream,
    ]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "profile": profile, "datastream": datastream,
        "command": result["command"],
        "stdout": result["stdout"][:8000],
        "returncode": result["returncode"],
    }
