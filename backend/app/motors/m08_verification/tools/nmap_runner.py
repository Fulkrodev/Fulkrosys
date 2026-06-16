"""M8 v5.1 — Nmap runner.

- Comando default: ``nmap -p- -sC -sV -oX <xml_out> <target>``
- Timeout: 30 minutos por defecto
- Parser: XML (nmap -oX -)
- Severity: ports abiertos = info; servicios obsoletos = medium;
  scripts NSE con CVE detectado = high (mapeado por script id)

NSE script ids que escalan severity (heuristica conservadora):
- ssl-heartbleed, ssl-poodle, ssl-ccs-injection → critical
- smb-vuln-* → high (varias CVE)
- http-vuln-* → high
- ftp-anon, telnet-brute → medium
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .base import (
    BaseRunner,
    FindingCandidate,
    RunnerResult,
    excerpt,
    normalize_severity,
    run_subprocess,
)


# Heuristicas de severity por NSE script id (extensible)
NSE_SEVERITY = {
    "ssl-heartbleed": "critical",
    "ssl-poodle": "critical",
    "ssl-ccs-injection": "critical",
    "smb-vuln-ms17-010": "critical",
    "smb-vuln-cve2009-3103": "high",
    "ftp-anon": "medium",
    "telnet-brute": "medium",
    "http-vuln-cve2017-5638": "critical",
}

OBSOLETE_SERVICE_KEYWORDS = (
    "telnet", "rsh", "rlogin", "tftp",
    # Versiones obsoletas de OpenSSH (toda la rama 5.x y 6.x)
    "openssh 5.", "openssh 6.",
)


class NmapRunner(BaseRunner):
    TOOL = "nmap"
    BINARY = "nmap"
    DEFAULT_TIMEOUT_SECONDS = 30 * 60  # 30 min

    @classmethod
    async def run(
        cls,
        targets: list[str],
        *,
        timeout_seconds: int | None = None,
        ports: str = "-p-",
        scripts: str = "default",
    ) -> RunnerResult:
        started = datetime.now(timezone.utc)

        # SAN-B.MB-7.bis · MCP wire-up · fallback subprocess transparente.
        # Paralelo a los otros runners (nuclei/testssl/openvas...). Si no
        # hay tool MCP nmap disponible (flag off / docker ausente), degrada
        # de forma transparente al subprocess local existente.
        from backend.app.mcp_client import try_invoke_mcp_or_none
        mcp_resp = await try_invoke_mcp_or_none(
            server="recon", tool="nmap_scan",
            args=cls._mcp_args(targets, ports=ports, scripts=scripts),
            timeout_seconds=timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS,
        )
        if mcp_resp is not None:
            return cls.from_mcp_response(mcp_resp, targets, started)

        cls.ensure_available()
        cmd = [
            cls.BINARY, ports, "-sV", "--script", scripts,
            "-oX", "-", *targets,
        ]
        rc, stdout, stderr, timed_out = await run_subprocess(
            cmd, timeout_seconds=(timeout_seconds or cls.DEFAULT_TIMEOUT_SECONDS),
        )
        try:
            findings = cls.parse_output(stdout)
            error = None
        except Exception as exc:  # pragma: no cover — el parser es muy tolerante
            findings = []
            error = f"parse error: {exc}"
        return cls.make_result(
            targets=targets, started_at=started, return_code=rc,
            raw_output=stdout, findings=findings,
            error=error or (stderr.decode(errors="replace") if rc != 0 else None),
            timed_out=timed_out,
        )

    @staticmethod
    def _mcp_args(
        targets: list[str], *, ports: str, scripts: str,
    ) -> dict:
        """Mapea los parámetros del runner al esquema del tool MCP
        ``recon/nmap_scan`` (target + mode + ports opcionales).

        Conservador: deriva ``mode`` de los flags del subprocess local
        (--script vuln → 'vuln'; -p- → 'full'; resto → 'quick') y pasa
        un rango de puertos explícito sólo cuando no es un flag nmap.
        """
        if "vuln" in (scripts or ""):
            mode = "vuln"
        elif ports == "-p-":
            mode = "full"
        else:
            mode = "quick"
        args: dict = {
            "target": targets[0] if targets else "",
            "mode": mode,
        }
        # ports sólo si es un rango/lista explícito (no un flag tipo "-p-").
        if ports and not ports.startswith("-"):
            args["ports"] = ports
        return args

    @classmethod
    def parse_output(cls, raw: bytes) -> list[FindingCandidate]:
        """Parsea XML de nmap (output de -oX -).

        Devuelve un FindingCandidate por puerto abierto + uno extra por
        cada hit de script NSE relevante. Severity heuristica:
        - puerto abierto sin info especial: info
        - servicio obsoleto / inseguro: medium
        - NSE script con vuln conocida: segun NSE_SEVERITY
        """
        if not raw:
            return []
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return []

        findings: list[FindingCandidate] = []
        for host in root.findall("host"):
            addr_el = host.find("address[@addrtype='ipv4']")
            if addr_el is None:
                addr_el = host.find("address")
            host_addr = addr_el.get("addr") if addr_el is not None else "unknown"
            os_el = host.find("os/osmatch")
            os_name = os_el.get("name") if os_el is not None else None

            ports_el = host.find("ports")
            if ports_el is None:
                continue
            for port in ports_el.findall("port"):
                state_el = port.find("state")
                if state_el is None or state_el.get("state") != "open":
                    continue
                portid = int(port.get("portid", "0"))
                protocol = port.get("protocol", "tcp")
                svc = port.find("service")
                svc_name = svc.get("name") if svc is not None else None
                svc_product = svc.get("product") if svc is not None else None
                svc_version = svc.get("version") if svc is not None else None

                product_str = " ".join(filter(None, [svc_product, svc_version])).strip().lower()

                # Severity por defecto: info (puerto abierto)
                sev = "info"
                title = f"Puerto abierto {portid}/{protocol} ({svc_name or 'desconocido'})"
                description = f"Nmap detecto el puerto {portid}/{protocol} abierto en {host_addr}."
                if svc_product:
                    description += f" Servicio: {svc_product} {svc_version or ''}".strip()

                if any(k in product_str for k in OBSOLETE_SERVICE_KEYWORDS):
                    sev = "medium"
                    description += " Servicio considerado obsoleto/inseguro."

                findings.append({
                    "title": title,
                    "description": description,
                    "severity": sev,
                    "cve_id": None,
                    "cvss_score": None,
                    "affected_host": host_addr,
                    "affected_port": portid,
                    "affected_service": svc_name,
                    "affected_service_version": (
                        f"{svc_product} {svc_version}".strip()
                        if svc_product else None
                    ),
                    "affected_url": None,
                    "affected_os": os_name,
                    "raw_output_excerpt": excerpt(ET.tostring(port)),
                    "tool": cls.TOOL,
                    "tool_metadata": {
                        "protocol": protocol,
                        "service_extrainfo": (
                            svc.get("extrainfo") if svc is not None else None
                        ),
                    },
                })

                # NSE scripts relevantes
                for script in port.findall("script"):
                    sid = script.get("id", "")
                    nse_sev = NSE_SEVERITY.get(sid)
                    if not nse_sev:
                        continue
                    output = script.get("output", "")
                    findings.append({
                        "title": f"NSE {sid} en {host_addr}:{portid}",
                        "description": (
                            f"Script Nmap {sid} reporto: {output[:200]}"
                        ),
                        "severity": normalize_severity(nse_sev),
                        "cve_id": _extract_cve(sid),
                        "cvss_score": None,
                        "affected_host": host_addr,
                        "affected_port": portid,
                        "affected_service": svc_name,
                        "affected_service_version": (
                            f"{svc_product} {svc_version}".strip()
                            if svc_product else None
                        ),
                        "affected_url": None,
                        "affected_os": os_name,
                        "raw_output_excerpt": excerpt(output),
                        "tool": cls.TOOL,
                        "tool_metadata": {"nse_script_id": sid},
                    })
        return findings


def _extract_cve(script_id: str) -> str | None:
    """Si el script id tipo 'http-vuln-cve2017-5638', devuelve CVE-2017-5638."""
    s = script_id.lower()
    if "cve" not in s:
        return None
    parts = s.split("cve")
    if len(parts) < 2:
        return None
    rest = parts[1].lstrip("-_")
    digits = rest.replace("-", "_").split("_")
    if len(digits) >= 2 and digits[0].isdigit() and digits[1].isdigit():
        return f"CVE-{digits[0]}-{digits[1]}"
    return None
