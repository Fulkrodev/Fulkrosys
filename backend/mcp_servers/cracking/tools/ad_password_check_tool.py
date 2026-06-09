"""Tool: ad_password_policy_check — Active Directory password policy audit (LDAP).

Pattern replica nmap_tool.py · usa ldap3 lib (graceful degradation si no
instalado · igual que el runner ad_password_checker.py existente).

SAFEGUARD #3 (SAN-B.MB-7.1): ldap3 NO declarado en pyproject.toml ·
mismo pattern que runner existente · graceful degradation runtime.
Si ldap3 no instalado, devuelve finding "tool_not_available" sin crash.

SAN-B.MB-7.1 · cierre wire-up MCP path para AdPasswordChecker existing.
"""
from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="ad_password_policy_check",
    description="Audit Active Directory password policy via LDAP · ENS op.acc.5 baseline.",
    input_schema={
        "properties": {
            "target": {
                "type": "string",
                "description": "LDAP server host:port (ej. dc.cliente.local:389)",
            },
            "bind_user": {"type": "string", "description": "LDAP bind DN (read-only)"},
            "bind_password": {"type": "string"},
            "base_dn": {"type": "string", "description": "ej. DC=cliente,DC=local"},
        },
        "required": ["target", "bind_user", "bind_password", "base_dn"],
    },
    timeout_seconds=30,
    risk_level="low",
    ens_measures=["op.acc.5", "op.acc.6"],
)


# Baseline ENS para password policy (op.acc.5)
ENS_PASSWORD_BASELINE = {
    "min_length": 12,
    "complexity_required": True,
    "max_age_days": 90,
    "lockout_threshold": 5,
}


async def ad_password_policy_check(
    target: str,
    bind_user: str,
    bind_password: str,
    base_dn: str,
) -> dict:
    scope = check_scope(target, "audit")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    try:
        from ldap3 import Server, Connection, ALL
    except ImportError:
        return {
            "target": target,
            "command": "ldap3 (no instalado)",
            "findings": [{
                **normalize_finding(
                    {
                        "title": "AD password check skipped · ldap3 missing",
                        "name": "AD-LDAP3-MISSING",
                        "description": "pip install ldap3 para habilitar AD audit",
                        "severity": "info",
                    },
                    "ad_password_policy", target, "ldap3 missing",
                ),
            }],
        }

    raw_findings: list[dict] = []
    try:
        server = Server(target, get_info=ALL, connect_timeout=10)
        conn = Connection(server, user=bind_user, password=bind_password, auto_bind=True)
        conn.search(
            search_base=base_dn,
            search_filter="(objectClass=domainDNS)",
            attributes=["minPwdLength", "pwdProperties", "lockoutThreshold", "maxPwdAge"],
        )
        if not conn.entries:
            raw_findings.append({
                "title": "AD password policy no encontrada",
                "name": "AD-PWPOL-NOT-FOUND",
                "description": f"LDAP search en {base_dn} sin domainDNS",
                "severity": "medium",
            })
        else:
            entry = conn.entries[0]
            min_pwd_length = int(entry.minPwdLength.value or 0)
            if min_pwd_length < ENS_PASSWORD_BASELINE["min_length"]:
                raw_findings.append({
                    "title": f"minPwdLength={min_pwd_length} < ENS baseline 12",
                    "name": "AD-PWPOL-MIN-LENGTH",
                    "description": "Política contraseñas AD permite < 12 chars",
                    "severity": "high",
                })
            lockout_threshold = int(entry.lockoutThreshold.value or 0)
            if lockout_threshold == 0 or lockout_threshold > ENS_PASSWORD_BASELINE["lockout_threshold"]:
                raw_findings.append({
                    "title": f"lockoutThreshold={lockout_threshold} no cumple ENS",
                    "name": "AD-PWPOL-LOCKOUT",
                    "description": "Lockout threshold ENS recomienda <=5 fallos · 0=ilimitado",
                    "severity": "medium",
                })
        conn.unbind()
    except Exception as exc:
        raw_findings.append({
            "title": "AD password policy lookup failed",
            "name": "AD-LDAP-ERROR",
            "description": str(exc)[:200],
            "severity": "low",
        })

    findings = [normalize_finding(f, "ad_password_policy", target, "ldap search domainDNS") for f in raw_findings]
    return {
        "target": target,
        "command": "ldap3 search domainDNS",
        "findings": findings,
        "summary": {"total": len(findings), "high": sum(1 for f in findings if f["severity"] == "high")},
    }
