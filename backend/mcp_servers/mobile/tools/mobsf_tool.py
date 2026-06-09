"""Tool: mobsf_scan — Mobile Security Framework static analysis."""
import json
import os
import urllib.request

from shared.mcp_protocol import MCPTool
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="mobsf_scan",
    description="MobSF static scan of an APK/IPA file, returning vulnerabilities and score.",
    input_schema={
        "properties": {
            "file_path": {"type": "string", "description": "Local path to APK/IPA"},
        },
        "required": ["file_path"],
    },
    timeout_seconds=3600,
    risk_level="low",
    ens_measures=["mp.sw.1", "mp.sw.2"],
)


async def mobsf_scan(file_path: str) -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    host = os.environ.get("MOBSF_HOST", "http://mobsf:8000")
    api_key = os.environ.get("MOBSF_API_KEY", "")
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    if not api_key:
        return {"error": "MOBSF_API_KEY not configured"}
    req = urllib.request.Request(
        f"{host}/api/v1/scan",
        data=json.dumps({"scan_type": "apk", "file_name": os.path.basename(file_path)}).encode(),
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode()
        return {"file_path": file_path, "response": body[:5000]}
    except Exception as exc:
        return {"error": str(exc)[:500], "file_path": file_path}
