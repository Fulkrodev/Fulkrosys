"""Tool: httpx_probe — HTTP probe with tech detection."""
import os
import tempfile

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope
from shared.utils import parse_jsonl, run_command


TOOL = MCPTool(
    name="httpx_probe",
    description="HTTP probing: status, title, tech stack, TLS and redirects.",
    input_schema={
        "properties": {
            "targets": {"type": "array", "items": {"type": "string"}},
            "target": {"type": "string"},
        }
    },
    timeout_seconds=900,
    risk_level="low",
    ens_measures=["op.exp.1"],
)


async def httpx_probe(targets: list | None = None, target: str | None = None) -> dict:
    target_list = list(targets or [])
    if target:
        target_list.append(target)
    if not target_list:
        return {"error": "No targets provided", "findings": []}

    for t in target_list:
        scope = check_scope(t, "scan")
        if not scope["allowed"]:
            return {"error": f"SCOPE DENIED for {t}: {scope['reason']}", "findings": []}

    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write("\n".join(target_list))
        cmd = ["httpx", "-l", path, "-json", "-silent"]
        result = await run_command(cmd, timeout=TOOL.timeout_seconds)
        findings = parse_jsonl(result["stdout"])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return {
        "targets": target_list,
        "command": result["command"],
        "findings": findings,
    }
