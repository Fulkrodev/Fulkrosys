"""Tool: cewl_wordlist — CeWL wordlist generator from website content."""
from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import run_command


TOOL = MCPTool(
    name="cewl_wordlist",
    description="CeWL crawls a website and builds a custom wordlist from its content.",
    input_schema={
        "properties": {
            "url": {"type": "string"},
            "depth": {"type": "integer", "default": 2},
            "min_length": {"type": "integer", "default": 5},
        },
        "required": ["url"],
    },
    timeout_seconds=1200,
    risk_level="low",
    ens_measures=["op.acc.6"],
)


async def cewl_wordlist(url: str, depth: int = 2, min_length: int = 5) -> dict:
    scope = check_scope(url, "scan")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["cewl", url, "-d", str(depth), "-m", str(min_length)]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "url": url, "depth": depth, "min_length": min_length,
        "command": result["command"],
        "wordlist": result["stdout"][:10000],
        "returncode": result["returncode"],
    }
