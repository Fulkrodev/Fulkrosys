"""M8 v5.1 — DNS security checks (SPF / DKIM / DMARC / DNSSEC).

Sin binario externo (usa dnspython). Se queda como ``DnsChecker`` con
la misma forma que los otros runners para integrarse en el pipeline.
"""
from __future__ import annotations

from datetime import datetime, timezone

try:
    import dns.resolver as _dns_resolver
    import dns.dnssec as _dns_dnssec  # noqa: F401 · probe de disponibilidad dnssec
    HAS_DNSPYTHON = True
except ImportError:  # pragma: no cover
    HAS_DNSPYTHON = False

from .base import (
    FindingCandidate,
    RunnerResult,
    RunnerNotInstalled,
    excerpt,
    hash_output,
    normalize_severity,
)


class DnsChecker:
    TOOL = "dns_security"
    DEFAULT_TIMEOUT_SECONDS = 60

    @classmethod
    def is_available(cls) -> bool:
        return HAS_DNSPYTHON

    @classmethod
    def ensure_available(cls) -> None:
        if not cls.is_available():
            raise RunnerNotInstalled(
                "dnspython no esta instalado. pip install dnspython>=2.4"
            )

    @classmethod
    async def run(
        cls,
        targets: list[str],
        *,
        timeout_seconds: int | None = None,
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente
        from backend.app.mcp_client import try_invoke_mcp_or_none
        from backend.app.motors.m08_verification.tools.base import (
            runner_result_from_mcp,
        )
        mcp_resp = await try_invoke_mcp_or_none(
            server="recon", tool="dns_security_check",
            args={"target": targets[0] if targets else ""},
            timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if mcp_resp is not None:
            return runner_result_from_mcp(mcp_resp, cls.TOOL, targets, started)

        cls.ensure_available()
        raw_dump: list[str] = []
        findings: list[FindingCandidate] = []
        for domain in targets:
            domain_findings, domain_raw = cls._check_domain(domain)
            findings.extend(domain_findings)
            raw_dump.append(domain_raw)
        raw_bytes = "\n\n".join(raw_dump).encode("utf-8")
        return RunnerResult(
            tool=cls.TOOL,
            targets=targets,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            return_code=0,
            raw_output=raw_bytes,
            raw_output_hash=hash_output(raw_bytes),
            raw_output_path=None,
            findings=findings,
        )

    @classmethod
    def _check_domain(cls, domain: str) -> tuple[list[FindingCandidate], str]:
        findings: list[FindingCandidate] = []
        raw_lines: list[str] = [f"=== {domain} ==="]

        # 1. SPF
        spf = cls._lookup_txt(domain, prefix="v=spf1")
        raw_lines.append(f"SPF: {spf or 'NOT FOUND'}")
        if not spf:
            findings.append(_dns_finding(
                "DNS: registro SPF ausente",
                f"El dominio {domain} no publica registro SPF. Habilita "
                "envios desde IPs no autorizadas.",
                "high", domain, "spf",
            ))
        elif "+all" in spf:
            findings.append(_dns_finding(
                "DNS: SPF demasiado permisivo (+all)",
                f"El dominio {domain} publica SPF con '+all' que autoriza "
                "cualquier remitente. Cambiar a '~all' o '-all'.",
                "high", domain, "spf",
            ))

        # 2. DMARC
        dmarc = cls._lookup_txt(f"_dmarc.{domain}", prefix="v=DMARC1")
        raw_lines.append(f"DMARC: {dmarc or 'NOT FOUND'}")
        if not dmarc:
            findings.append(_dns_finding(
                "DNS: registro DMARC ausente",
                f"El dominio {domain} no publica DMARC. Sin DMARC los "
                "intentos de spoofing no son detectables.",
                "high", domain, "dmarc",
            ))
        else:
            # Politica "p=none" no protege
            if "p=none" in dmarc.lower():
                findings.append(_dns_finding(
                    "DNS: DMARC con politica 'p=none' (solo monitorizacion)",
                    "DMARC publicado pero con p=none: no rechaza ni "
                    "cuarentena. Subir a 'p=quarantine' o 'p=reject'.",
                    "medium", domain, "dmarc",
                ))

        # 3. DKIM (selector default)
        dkim_default = cls._lookup_txt(f"default._domainkey.{domain}", prefix="v=DKIM1")
        raw_lines.append(f"DKIM (default): {dkim_default or 'NOT FOUND'}")
        if not dkim_default:
            findings.append(_dns_finding(
                "DNS: DKIM 'default' ausente",
                f"No se encontro DKIM en selector 'default' de {domain}. "
                "Verificar selectores reales (google, mail, k1...).",
                "medium", domain, "dkim",
            ))

        # 4. DNSSEC
        dnssec_ok = cls._has_dnssec(domain)
        raw_lines.append(f"DNSSEC: {'enabled' if dnssec_ok else 'disabled'}")
        if not dnssec_ok:
            findings.append(_dns_finding(
                "DNS: DNSSEC no habilitado",
                f"El dominio {domain} no publica registros DNSSEC. "
                "Sin DNSSEC, las respuestas DNS pueden ser falsificadas.",
                "low", domain, "dnssec",
            ))

        return findings, "\n".join(raw_lines)

    @staticmethod
    def _lookup_txt(name: str, prefix: str | None = None) -> str | None:
        if not HAS_DNSPYTHON:
            return None
        try:
            answers = _dns_resolver.resolve(name, "TXT", lifetime=10)
        except Exception:
            return None
        for r in answers:
            text = b"".join(r.strings).decode("utf-8", errors="replace")
            if prefix is None or text.startswith(prefix):
                return text
        return None

    @staticmethod
    def _has_dnssec(domain: str) -> bool:
        if not HAS_DNSPYTHON:
            return False
        try:
            answers = _dns_resolver.resolve(domain, "DNSKEY", lifetime=10)
            return len(list(answers)) > 0
        except Exception:
            return False


def _dns_finding(
    title: str, description: str, severity: str,
    domain: str, kind: str,
) -> FindingCandidate:
    return {
        "title": title,
        "description": description,
        "severity": normalize_severity(severity),
        "cve_id": None,
        "cvss_score": None,
        "cvss_vector": None,
        "cwe_id": None,
        "affected_host": domain,
        "affected_port": 53,
        "affected_service": "dns",
        "affected_service_version": None,
        "affected_url": None,
        "affected_os": None,
        "raw_output_excerpt": excerpt(description),
        "tool": "dns_security",
        "tool_metadata": {"check_type": kind},
    }
