"""Tool: hashcat_crack — Hashcat hash cracking."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command


TOOL = MCPTool(
    name="hashcat_crack",
    description="Hashcat GPU-accelerated cracking for common hash modes.",
    input_schema={
        "properties": {
            "hash_file": {"type": "string"},
            "hash_mode": {"type": "integer", "description": "Hashcat -m mode"},
            "wordlist": {"type": "string", "default": "/opt/wordlists/rockyou.txt"},
            "rules": {"type": "string"},
        },
        "required": ["hash_file", "hash_mode"],
    },
    timeout_seconds=7200,
    risk_level="medium",
    requires_approval=True,
    ens_measures=["op.acc.6"],
)


async def hashcat_crack(
    hash_file: str,
    hash_mode: int,
    wordlist: str = "/opt/wordlists/rockyou.txt",
    rules: str | None = None,
) -> dict:
    """Scope: local audit — no external target, scope check not applicable."""
    cmd = ["hashcat", "-m", str(hash_mode), hash_file, wordlist, "--quiet"]
    if rules:
        cmd += ["-r", rules]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "hash_file": hash_file, "hash_mode": hash_mode,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
