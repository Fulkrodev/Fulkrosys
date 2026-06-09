"""Tool: metasploit_search — Search Metasploit modules by keyword."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="metasploit_search",
    description="Search Metasploit modules by keyword (CVE, product, platform).",
    input_schema={
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
    timeout_seconds=120,
    risk_level="low",
    ens_measures=["op.exp.4"],
)


async def metasploit_search(query: str) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["msfconsole", "-qx", f"search {query}; exit"]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "query": query,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
