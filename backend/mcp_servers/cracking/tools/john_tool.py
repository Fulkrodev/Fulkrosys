"""Tool: john_crack — John the Ripper cracking."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="john_crack",
    description="John the Ripper: CPU-based hash cracking with custom rules and formats.",
    input_schema={
        "properties": {
            "hash_file": {"type": "string"},
            "format": {"type": "string"},
            "wordlist": {"type": "string", "default": "/opt/wordlists/rockyou.txt"},
        },
        "required": ["hash_file"],
    },
    timeout_seconds=3600,
    risk_level="medium",
    requires_approval=True,
    ens_measures=["op.acc.6"],
)


async def john_crack(
    hash_file: str,
    format: str | None = None,
    wordlist: str = "/opt/wordlists/rockyou.txt",
) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["john", f"--wordlist={wordlist}"]
    if format:
        cmd.append(f"--format={format}")
    cmd.append(hash_file)
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "hash_file": hash_file,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
