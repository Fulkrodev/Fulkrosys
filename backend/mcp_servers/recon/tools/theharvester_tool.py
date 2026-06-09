"""Tool: theharvester_recon — Email/subdomain/host harvesting."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="theharvester_recon",
    description="theHarvester OSINT: emails, subdomains, hosts from public sources.",
    input_schema={
        "properties": {
            "domain": {"type": "string"},
            "sources": {"type": "string", "default": "crtsh,hackertarget,rapiddns"},
        },
        "required": ["domain"],
    },
    timeout_seconds=600,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def theharvester_recon(domain: str, sources: str = "crtsh,hackertarget,rapiddns") -> dict:
    scope = check_scope(domain, "enumerate")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["theHarvester", "-d", domain, "-b", sources, "-f", "/tmp/harvester_out"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "domain": domain,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
