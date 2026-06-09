"""Tool: apktool_decompile — apktool APK decompile for manual inspection."""
from shared.mcp_protocol import MCPTool
from shared.utils import run_command
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="apktool_decompile",
    description="Decompile an APK into smali + resources for static review.",
    input_schema={
        "properties": {
            "apk_path": {"type": "string"},
            "output_dir": {"type": "string", "default": "/tmp/apktool_out"},
        },
        "required": ["apk_path"],
    },
    timeout_seconds=1200,
    risk_level="low",
    ens_measures=["mp.sw.1"],
)


async def apktool_decompile(apk_path: str, output_dir: str = "/tmp/apktool_out") -> dict:
    # Validates active engagement window, not target IP
    scope = check_scope("__local__", "config_audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}"}
    cmd = ["apktool", "d", "-f", "-o", output_dir, apk_path]
    result = await run_command(cmd, timeout=TOOL.timeout_seconds)
    return {
        "apk_path": apk_path, "output_dir": output_dir,
        "command": result["command"],
        "stdout": result["stdout"][:5000],
        "returncode": result["returncode"],
    }
