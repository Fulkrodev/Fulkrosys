"""Tool: dns_security_check — SPF / DKIM / DMARC / DNSSEC verification.

Pattern replica nmap_tool.py · usa dnspython lib (ya instalado en venv).
SAN-B.MB-7.1 · cierre wire-up MCP path para DnsChecker existing.
"""
from shared.mcp_protocol import MCPTool
from shared.output_normalizer import normalize_finding
from shared.scope_check import check_scope


TOOL = MCPTool(
    name="dns_security_check",
    description="Verifica SPF + DKIM + DMARC + DNSSEC para un dominio · email security baseline.",
    input_schema={
        "properties": {
            "target": {"type": "string", "description": "domain (ej. example.com)"},
            "dkim_selectors": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["default", "google", "selector1", "selector2"],
            },
        },
        "required": ["target"],
    },
    timeout_seconds=60,
    risk_level="low",
    ens_measures=["mp.com.4", "op.exp.2", "op.exp.3"],
)


async def dns_security_check(
    target: str,
    dkim_selectors: list[str] | None = None,
) -> dict:
    scope = check_scope(target, "lookup")
    if not scope["allowed"]:
        return {"error": f"SCOPE DENIED: {scope['reason']}", "findings": []}

    try:
        import dns.resolver as _resolver
    except ImportError:
        return {
            "target": target,
            "command": "dns.resolver (dnspython)",
            "findings": [],
            "error": "dnspython no instalado · pip install dnspython>=2.4",
        }

    selectors = dkim_selectors or ["default", "google", "selector1", "selector2"]
    raw_findings: list[dict] = []
    raw_findings.extend(_check_spf(target, _resolver))
    raw_findings.extend(_check_dmarc(target, _resolver))
    raw_findings.extend(_check_dkim(target, selectors, _resolver))
    raw_findings.extend(_check_dnssec(target, _resolver))

    findings = [
        normalize_finding(f, "dns_security", target, "dnspython resolve")
        for f in raw_findings
    ]
    return {
        "target": target,
        "command": "dnspython resolve",
        "findings": findings,
        "summary": {
            "total": len(findings),
            "high": sum(1 for f in findings if f["severity"] == "high"),
        },
    }


def _check_spf(domain: str, resolver) -> list[dict]:
    try:
        answers = resolver.resolve(domain, "TXT")
        spf_records = [
            r.to_text().strip('"') for r in answers
            if r.to_text().strip('"').startswith("v=spf1")
        ]
        if not spf_records:
            return [{
                "title": "SPF record missing",
                "name": "DNS-SPF-MISSING",
                "description": f"{domain} sin TXT v=spf1 · email spoofing risk",
                "severity": "high",
            }]
        if any("~all" not in r and "-all" not in r for r in spf_records):
            return [{
                "title": "SPF record sin policy estricta",
                "name": "DNS-SPF-WEAK",
                "description": "SPF presente pero sin ~all/-all · spoofing parcial",
                "severity": "medium",
            }]
    except Exception as exc:  # pragma: no cover
        return [{
            "title": "DNS SPF lookup failed",
            "name": "DNS-SPF-ERROR",
            "description": str(exc)[:200],
            "severity": "low",
        }]
    return []


def _check_dmarc(domain: str, resolver) -> list[dict]:
    try:
        answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
        records = [r.to_text().strip('"') for r in answers]
        dmarc_records = [r for r in records if r.startswith("v=DMARC1")]
        if not dmarc_records:
            return [{
                "title": "DMARC record missing",
                "name": "DNS-DMARC-MISSING",
                "description": f"_dmarc.{domain} sin policy · spoofing detection ausente",
                "severity": "high",
            }]
        if any("p=none" in r for r in dmarc_records):
            return [{
                "title": "DMARC policy=none",
                "name": "DNS-DMARC-MONITOR",
                "description": "DMARC en monitor mode (p=none) · sin enforcement",
                "severity": "medium",
            }]
    except Exception:
        return [{
            "title": "DMARC record missing",
            "name": "DNS-DMARC-MISSING",
            "description": f"_dmarc.{domain} no resuelve",
            "severity": "high",
        }]
    return []


def _check_dkim(domain: str, selectors: list[str], resolver) -> list[dict]:
    found_any = False
    for sel in selectors:
        try:
            answers = resolver.resolve(f"{sel}._domainkey.{domain}", "TXT")
            if any("v=DKIM1" in r.to_text() for r in answers):
                found_any = True
                break
        except Exception:
            continue
    if not found_any:
        return [{
            "title": "DKIM no detectado en selectores comunes",
            "name": "DNS-DKIM-MISSING",
            "description": f"Probados selectors {selectors} · ninguno con DKIM record",
            "severity": "medium",
        }]
    return []


def _check_dnssec(domain: str, resolver) -> list[dict]:
    try:
        answers = resolver.resolve(domain, "DNSKEY")
        if not answers:
            raise Exception("no DNSKEY records")
    except Exception:
        return [{
            "title": "DNSSEC no habilitado",
            "name": "DNS-DNSSEC-MISSING",
            "description": f"{domain} sin DNSKEY records · DNS spoofing risk",
            "severity": "low",
        }]
    return []
