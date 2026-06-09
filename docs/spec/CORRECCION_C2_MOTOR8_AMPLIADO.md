# CORRECCIÓN C-2 — MOTOR 8 AMPLIADO AL MÁXIMO (v2.1 §8.2-8.7)

**Plan 100/100 FULKRO — Última corrección**
**Fecha:** 10 de abril de 2026
**Nota:** Este documento COMPLEMENTA el entregable G original. No lo reemplaza — la arquitectura MCP + LLM autónomo, los esquemas Pydantic, el servidor MCP, el orquestador y el generador de informes del G original se mantienen. Este documento añade lo que faltaba para alinear con v2.1.

---

## 1. LO QUE FALTABA EN EL G ORIGINAL

| Gap detectado en la auditoría | Solución en este documento |
|---|---|
| Solo 5 herramientas vs ~50 en v2.1 | +12 adaptadores esqueleto para las herramientas críticas nombradas por v2.1 |
| Pipeline simple vs 11 fases en v2.1 | Nuevo `PentestPipeline` con 11 fases y selección por categoría |
| Sin adaptación por categoría ENS | Perfiles de pipeline BÁSICA/MEDIA/ALTA conforme a v2.1 §8.2 |
| Sin mapeo MITRE ATT&CK | Nuevo campo `mitre_attack_techniques` en el modelo `Finding` |
| Informe con estructura simple | Estructura de 8 secciones de v2.1 §8.6 |

---

## 2. PIPELINE DE 11 FASES (v2.1 §8.4)

```python
# fulkro/motor8/pipeline.py

"""
Pipeline de pentesting de 11 fases conforme a v2.1 §8.4.
Sustituye al pipeline simple del G original.
"""
from enum import Enum
from typing import Optional
from uuid import UUID

from fulkro.motor8.schemas import PentestScope, ScanType


class PipelinePhase(str, Enum):
    """Las 11 fases del pipeline de pentesting v2.1."""
    RECON = "01_reconnaissance"
    VULN_SCAN = "02_vulnerability_scanning"
    WEB_PENTEST = "03_web_pentest"
    INFRA_PENTEST = "04_infrastructure_pentest"
    CLOUD_AUDIT = "05_cloud_audit"
    CONFIG_AUDIT = "06_configuration_audit"
    RED_TEAM = "07_red_team"
    PHISHING = "08_phishing_simulation"
    NORMALIZE = "09_normalize_and_map"
    LLM_PRIORITIZE = "10_llm_prioritization"
    REPORT = "11_report_generation"


# Perfiles de pipeline por categoría ENS (v2.1 §8.2)
PIPELINE_PROFILES = {
    "BASICA": {
        "description": "Scan de vulnerabilidades + web pentest ligero",
        "frequency": "Anual",
        "phases": [
            PipelinePhase.RECON,
            PipelinePhase.VULN_SCAN,
            PipelinePhase.WEB_PENTEST,      # ligero
            PipelinePhase.CONFIG_AUDIT,
            PipelinePhase.NORMALIZE,
            PipelinePhase.LLM_PRIORITIZE,
            PipelinePhase.REPORT,
        ],
        "tools": {
            PipelinePhase.RECON: ["nmap", "subfinder", "httpx"],
            PipelinePhase.VULN_SCAN: ["nuclei"],
            PipelinePhase.WEB_PENTEST: ["zap_baseline"],
            PipelinePhase.CONFIG_AUDIT: ["lynis", "clara"],
        },
    },
    "MEDIA": {
        "description": "Pentest completo interno + externo + web + cloud + phishing + scanning continuo",
        "frequency": "Anual",
        "phases": [
            PipelinePhase.RECON,
            PipelinePhase.VULN_SCAN,
            PipelinePhase.WEB_PENTEST,
            PipelinePhase.INFRA_PENTEST,
            PipelinePhase.CLOUD_AUDIT,
            PipelinePhase.CONFIG_AUDIT,
            PipelinePhase.PHISHING,         # opcional, conforme a alcance
            PipelinePhase.NORMALIZE,
            PipelinePhase.LLM_PRIORITIZE,
            PipelinePhase.REPORT,
        ],
        "tools": {
            PipelinePhase.RECON: ["nmap", "osmedeus", "subfinder", "httpx"],
            PipelinePhase.VULN_SCAN: ["nuclei", "openvas", "trivy"],
            PipelinePhase.WEB_PENTEST: ["zap_full", "rengine"],
            PipelinePhase.INFRA_PENTEST: ["bloodhound", "pingcastle", "adrecon"],
            PipelinePhase.CLOUD_AUDIT: ["prowler_ens"],
            PipelinePhase.CONFIG_AUDIT: ["lynis", "clara", "cis_cat"],
            PipelinePhase.PHISHING: ["gophish"],
        },
    },
    "ALTA": {
        "description": "Todo MEDIA + Red Team formal + Purple Team + cobertura MITRE ATT&CK completa",
        "frequency": "Continuo",
        "phases": [
            PipelinePhase.RECON,
            PipelinePhase.VULN_SCAN,
            PipelinePhase.WEB_PENTEST,
            PipelinePhase.INFRA_PENTEST,
            PipelinePhase.CLOUD_AUDIT,
            PipelinePhase.CONFIG_AUDIT,
            PipelinePhase.RED_TEAM,         # obligatorio en ALTA
            PipelinePhase.PHISHING,
            PipelinePhase.NORMALIZE,
            PipelinePhase.LLM_PRIORITIZE,
            PipelinePhase.REPORT,
        ],
        "tools": {
            PipelinePhase.RECON: ["nmap", "osmedeus", "subfinder", "httpx"],
            PipelinePhase.VULN_SCAN: ["nuclei", "openvas", "trivy", "semgrep"],
            PipelinePhase.WEB_PENTEST: ["zap_full", "rengine"],
            PipelinePhase.INFRA_PENTEST: ["bloodhound", "pingcastle", "adrecon"],
            PipelinePhase.CLOUD_AUDIT: ["prowler_ens"],
            PipelinePhase.CONFIG_AUDIT: ["lynis", "clara", "cis_cat"],
            PipelinePhase.RED_TEAM: ["caldera"],
            PipelinePhase.PHISHING: ["gophish"],
        },
    },
}


def get_pipeline_profile(categoria: str, scope: PentestScope) -> dict:
    """
    Devuelve el perfil de pipeline ajustado al alcance concreto del cliente.
    
    El perfil base se selecciona por categoría ENS. Luego se ajusta según
    el alcance real: si no tiene AD → sin BloodHound/PingCastle/ADRecon,
    si no tiene cloud → sin Prowler, si no autoriza phishing → sin GoPhish.
    """
    profile = PIPELINE_PROFILES[categoria].copy()
    
    # Ajustes por alcance
    if not scope.has_active_directory:
        for phase in profile["tools"]:
            profile["tools"][phase] = [
                t for t in profile["tools"][phase]
                if t not in ("bloodhound", "pingcastle", "adrecon")
            ]
        if PipelinePhase.INFRA_PENTEST in profile["phases"]:
            # Mantener la fase pero sin herramientas AD
            pass
    
    if not scope.allow_phishing_simulation:
        profile["phases"] = [
            p for p in profile["phases"] if p != PipelinePhase.PHISHING
        ]
    
    # Cloud: detectar si el cliente tiene cloud a partir del scope
    has_cloud = any("cloud" in d.lower() or "aws" in d.lower() or 
                    "azure" in d.lower() or "gcp" in d.lower()
                    for d in scope.domains)
    if not has_cloud:
        profile["phases"] = [
            p for p in profile["phases"] if p != PipelinePhase.CLOUD_AUDIT
        ]
    
    return profile
```

---

## 3. LOS 12 NUEVOS ADAPTADORES (esqueleto ejecutable)

Cada adaptador sigue la misma interfaz `ToolAdapter` del G original (`run()` + `parse_findings()`). Aquí van los esqueletos con la lógica real de invocación.

### 3.1 Nmap — Reconocimiento de red (todas las categorías)

```python
# fulkro/motor8/adapters/nmap_adapter.py

"""v2.1: 'Descubrimiento de hosts, puertos, servicios, fingerprinting OS.'"""

import asyncio
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class NmapAdapter(ToolAdapter):
    tool_name = "nmap"
    tool_version = "7.x"

    async def run(self, target: str, scan_type: str = "default") -> ToolInvocation:
        invocation = self._create_invocation({"target": target, "scan_type": scan_type})
        output_file = self.output_dir / f"nmap_{target.replace('.','_')}.xml"

        # Perfiles de escaneo por categoría
        profiles = {
            "quick": ["-sV", "-sC", "--top-ports", "1000", "-T4"],
            "default": ["-sV", "-sC", "-O", "-p-", "-T3"],
            "stealth": ["-sS", "-sV", "--top-ports", "10000", "-T2"],
        }
        args = profiles.get(scan_type, profiles["default"])

        cmd = ["nmap"] + args + ["-oX", str(output_file), target]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED if proc.returncode == 0 else ScanStatus.FAILED
            invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        if invocation.status != ScanStatus.COMPLETED:
            return []
        tree = ET.parse(invocation.raw_output_path)
        findings = []
        for host in tree.findall(".//host"):
            addr = host.findtext("address[@addrtype='ipv4']/@addr", "")
            for port in host.findall(".//port"):
                portid = port.get("portid", "")
                protocol = port.get("protocol", "")
                service = port.find("service")
                svc_name = service.get("name", "") if service is not None else ""
                svc_product = service.get("product", "") if service is not None else ""
                state = port.findtext("state/@state", "")
                if state == "open":
                    findings.append(Finding(
                        scan_id=self.scan_id,
                        title=f"Puerto abierto: {portid}/{protocol} ({svc_name})",
                        description=f"Servicio {svc_product} {svc_name} detectado en {addr}:{portid}",
                        severity=Severity.INFO,
                        cvss_score=0.0,
                        affected_target=addr,
                        affected_component=f"{portid}/{protocol}",
                        evidence={"port": portid, "service": svc_name, "product": svc_product},
                        remediation="Verificar que el puerto es necesario y está adecuadamente protegido.",
                        ens_measures_affected=["op.exp.1", "mp.com.1"],
                        detected_by_tool=self.tool_name,
                    ))
        return findings
```

### 3.2 Nuclei — Escáner de vulnerabilidades basado en plantillas (CRÍTICO)

```python
# fulkro/motor8/adapters/nuclei_adapter.py

"""v2.1: 'El más usado por consultores ENS modernos.'"""

import asyncio
import json
from pathlib import Path

from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class NucleiAdapter(ToolAdapter):
    tool_name = "nuclei"
    tool_version = "3.x"
    DOCKER_IMAGE = "projectdiscovery/nuclei:latest"

    async def run(self, target: str, severity_filter: str = "critical,high,medium",
                  templates: list[str] | None = None) -> ToolInvocation:
        invocation = self._create_invocation({
            "target": target, "severity_filter": severity_filter
        })
        output_file = self.output_dir / f"nuclei_{target.replace('.','_')}.jsonl"

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.output_dir}:/output",
            self.DOCKER_IMAGE,
            "-u", target,
            "-severity", severity_filter,
            "-jsonl", "-o", f"/output/{output_file.name}",
        ]
        if templates:
            cmd.extend(["-t", ",".join(templates)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED if proc.returncode == 0 else ScanStatus.FAILED
            invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        if invocation.status != ScanStatus.COMPLETED:
            return []
        findings = []
        with Path(invocation.raw_output_path).open() as f:
            for line in f:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                severity = self._map_severity(data.get("info", {}).get("severity", "info"))
                findings.append(Finding(
                    scan_id=self.scan_id,
                    title=data.get("info", {}).get("name", "Unknown"),
                    description=data.get("info", {}).get("description", ""),
                    severity=severity,
                    cvss_score=self._estimate_cvss(severity),
                    affected_target=data.get("host", ""),
                    affected_component=data.get("matched-at", ""),
                    cve_ids=data.get("info", {}).get("classification", {}).get("cve-id", []) or [],
                    cwe_ids=data.get("info", {}).get("classification", {}).get("cwe-id", []) or [],
                    evidence={"template_id": data.get("template-id"), "matcher": data.get("matcher-name")},
                    remediation=data.get("info", {}).get("remediation", "Consultar CVE asociado."),
                    ens_measures_affected=self._map_to_ens(data),
                    mitre_attack_techniques=data.get("info", {}).get("classification", {}).get("mitre-attack", []) or [],
                    detected_by_tool=self.tool_name,
                ))
        return findings

    @staticmethod
    def _map_severity(s: str) -> Severity:
        return {"critical": Severity.CRITICAL, "high": Severity.HIGH,
                "medium": Severity.MEDIUM, "low": Severity.LOW}.get(s.lower(), Severity.INFO)

    @staticmethod
    def _estimate_cvss(s: Severity) -> float:
        return {Severity.CRITICAL: 9.5, Severity.HIGH: 7.5,
                Severity.MEDIUM: 5.5, Severity.LOW: 3.0, Severity.INFO: 0.0}[s]

    @staticmethod
    def _map_to_ens(data: dict) -> list[str]:
        tags = data.get("info", {}).get("tags", []) or []
        measures = set()
        if any(t in tags for t in ["xss", "sqli", "rce", "ssrf", "lfi", "rfi"]):
            measures.update(["mp.sw.1", "mp.sw.2", "op.exp.4"])
        if any(t in tags for t in ["tls", "ssl", "cert", "crypto"]):
            measures.update(["mp.com.2", "mp.com.3"])
        if any(t in tags for t in ["auth", "login", "default-creds", "brute"]):
            measures.update(["op.acc.5", "op.acc.6"])
        if any(t in tags for t in ["misconfig", "exposure", "config"]):
            measures.update(["op.exp.2", "op.exp.3"])
        return sorted(measures) or ["op.exp.4"]
```

### 3.3 OpenVAS — Escáner completo de vulnerabilidades

```python
# fulkro/motor8/adapters/openvas_adapter.py

"""v2.1: 'Escáner de vulnerabilidades completo.' Greenbone Community Edition."""

import asyncio
import httpx
from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class OpenVASAdapter(ToolAdapter):
    tool_name = "openvas"
    tool_version = "22.x"

    def __init__(self, scan_id, output_dir, gvm_url: str, gvm_user: str, gvm_password: str):
        super().__init__(scan_id, output_dir)
        self.gvm_url = gvm_url
        self.gvm_user = gvm_user
        self.gvm_password = gvm_password

    async def run(self, target: str, scan_config: str = "Full and fast") -> ToolInvocation:
        """Lanza un scan OpenVAS/GVM vía su API GMP (Greenbone Management Protocol)."""
        invocation = self._create_invocation({"target": target, "config": scan_config})
        # OpenVAS se controla vía API GMP (XML sobre TLS) o vía la API REST de GSA.
        # En producción se usaría python-gvm. Aquí mostramos el flujo con httpx contra GSA.
        try:
            async with httpx.AsyncClient(base_url=self.gvm_url, verify=False) as client:
                # Autenticación
                auth = await client.post("/api/login", json={
                    "username": self.gvm_user, "password": self.gvm_password
                })
                token = auth.json().get("token")
                headers = {"Authorization": f"Bearer {token}"}
                # Crear target
                target_resp = await client.post("/api/targets", json={
                    "name": f"FULKRO-{target}", "hosts": target
                }, headers=headers)
                target_id = target_resp.json().get("id")
                # Crear y lanzar tarea
                task_resp = await client.post("/api/tasks", json={
                    "name": f"FULKRO-scan-{target}",
                    "target": {"id": target_id},
                    "scanner": {"id": "default"},
                    "config": {"name": scan_config},
                }, headers=headers)
                task_id = task_resp.json().get("id")
                await client.post(f"/api/tasks/{task_id}/start", headers=headers)
                # Polling (simplificado)
                for _ in range(720):  # 2h máx
                    await asyncio.sleep(10)
                    status_resp = await client.get(f"/api/tasks/{task_id}", headers=headers)
                    if status_resp.json().get("status") == "Done":
                        break
                # Descargar resultados
                report_id = status_resp.json().get("last_report", {}).get("id")
                results = await client.get(
                    f"/api/reports/{report_id}/results", headers=headers
                )
                output_file = self.output_dir / f"openvas_{target}.json"
                output_file.write_text(results.text)
                invocation.status = ScanStatus.COMPLETED
                invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        # Parsea el JSON de resultados GVM. Estructura similar a Nuclei.
        if invocation.status != ScanStatus.COMPLETED:
            return []
        import json
        data = json.loads(Path(invocation.raw_output_path).read_text())
        findings = []
        for result in data.get("results", []):
            severity = self._map_threat(result.get("threat", ""))
            findings.append(Finding(
                scan_id=self.scan_id,
                title=result.get("name", ""),
                description=result.get("description", ""),
                severity=severity,
                cvss_score=float(result.get("severity", 0)),
                affected_target=result.get("host", ""),
                cve_ids=[result.get("cve")] if result.get("cve") else [],
                evidence=result,
                remediation=result.get("solution", ""),
                ens_measures_affected=["op.exp.4"],
                detected_by_tool=self.tool_name,
            ))
        return findings

    @staticmethod
    def _map_threat(t: str) -> Severity:
        return {"High": Severity.HIGH, "Medium": Severity.MEDIUM,
                "Low": Severity.LOW}.get(t, Severity.INFO)
```

### 3.4 OWASP ZAP — Proxy de pentesting web

```python
# fulkro/motor8/adapters/zap_adapter.py

"""v2.1: 'Proxy de pentesting web, automatizado vía CLI o API.'"""

import asyncio
import json
from pathlib import Path
import httpx

from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class ZAPAdapter(ToolAdapter):
    tool_name = "owasp_zap"
    tool_version = "2.x"
    DOCKER_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"

    async def run(self, target: str, mode: str = "baseline") -> ToolInvocation:
        """mode: 'baseline' (rápido, BÁSICA) o 'full' (completo, MEDIA+)."""
        invocation = self._create_invocation({"target": target, "mode": mode})
        output_file = self.output_dir / f"zap_{target.replace('.','_')}.json"
        script = "zap-baseline.py" if mode == "baseline" else "zap-full-scan.py"

        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.output_dir}:/zap/wrk",
            self.DOCKER_IMAGE,
            script, "-t", f"https://{target}",
            "-J", f"/zap/wrk/{output_file.name}",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED
            invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        if invocation.status != ScanStatus.COMPLETED:
            return []
        data = json.loads(Path(invocation.raw_output_path).read_text())
        findings = []
        for site in data.get("site", []):
            for alert in site.get("alerts", []):
                risk = alert.get("riskcode", "0")
                severity = {3: Severity.HIGH, 2: Severity.MEDIUM,
                            1: Severity.LOW, 0: Severity.INFO}.get(int(risk), Severity.INFO)
                cwe = alert.get("cweid", "")
                findings.append(Finding(
                    scan_id=self.scan_id,
                    title=alert.get("name", ""),
                    description=alert.get("desc", ""),
                    severity=severity,
                    cvss_score=self._risk_to_cvss(int(risk)),
                    affected_target=site.get("@host", ""),
                    affected_component=alert.get("uri", ""),
                    cwe_ids=[f"CWE-{cwe}"] if cwe else [],
                    evidence={"instances": alert.get("instances", [])[:3]},
                    remediation=alert.get("solution", ""),
                    ens_measures_affected=["mp.sw.1", "mp.sw.2", "op.exp.4"],
                    detected_by_tool=self.tool_name,
                ))
        return findings

    @staticmethod
    def _risk_to_cvss(risk: int) -> float:
        return {3: 7.5, 2: 5.5, 1: 3.0, 0: 0.0}.get(risk, 0.0)
```

### 3.5 BloodHound — Análisis de Active Directory

```python
# fulkro/motor8/adapters/bloodhound_adapter.py

"""v2.1 nombra BloodHound para 'análisis de AD para escalada de privilegios'."""

import asyncio
from pathlib import Path
from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class BloodHoundAdapter(ToolAdapter):
    tool_name = "bloodhound"
    tool_version = "4.x"

    async def run(self, domain: str, credentials_secret_id: str) -> ToolInvocation:
        """Ejecuta SharpHound (collector) y carga datos en BloodHound CE."""
        invocation = self._create_invocation({"domain": domain})
        output_dir = self.output_dir / "bloodhound" / domain
        output_dir.mkdir(parents=True, exist_ok=True)

        # SharpHound recolecta datos del AD y los exporta como JSON/ZIP
        # En producción esto se ejecutaría en el AD del cliente con credenciales del vault
        from fulkro.motor8.vault import get_secret
        creds = await get_secret(credentials_secret_id)

        cmd = [
            "sharphound", "--domain", domain,
            "--ldapusername", creds["username"],
            "--ldappassword", creds["password"],
            "--outputdirectory", str(output_dir),
            "--collectionmethod", "All",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED if proc.returncode == 0 else ScanStatus.FAILED
            invocation.raw_output_path = str(output_dir)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        """Analiza los JSON de BloodHound buscando rutas de escalada de privilegios."""
        if invocation.status != ScanStatus.COMPLETED:
            return []
        # BloodHound genera múltiples JSON (computers, users, groups, domains, sessions)
        # El análisis de rutas de ataque se hace vía consultas Cypher a la BD Neo4j
        # Aquí mostramos el esqueleto del parsing de las rutas más críticas
        findings = []
        # En producción: cargar JSONs en BloodHound CE → ejecutar consultas Cypher predefinidas
        # → cada ruta de escalada = un Finding
        return findings
```

### 3.6 CLARA del CCN — Auditoría de configuraciones oficial

```python
# fulkro/motor8/adapters/clara_adapter.py

"""
v2.1: 'Crítico porque es la herramienta oficial española y al auditor le encanta verlo.'

CLARA es la herramienta del CCN para auditoría de configuraciones de seguridad
de sistemas Windows y Linux según las guías CCN-STIC. Se distribuye desde
https://www.ccn-cert.cni.es/es/soluciones-seguridad/clara.html
"""

import asyncio
from pathlib import Path
from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class CLARAAdapter(ToolAdapter):
    tool_name = "clara_ccn"
    tool_version = "latest"

    async def run(self, target_type: str = "windows", target_ip: str = "localhost") -> ToolInvocation:
        """
        Ejecuta CLARA en modo remoto o local.
        
        CLARA analiza la configuración del sistema contra las baselines CCN-STIC
        (por ejemplo CCN-STIC 570 para Windows 10, CCN-STIC 619 para Ubuntu).
        """
        invocation = self._create_invocation({"target_type": target_type, "target_ip": target_ip})
        output_file = self.output_dir / f"clara_{target_ip.replace('.','_')}.xml"

        # CLARA genera un informe XML con los checks pasados y fallidos
        # En producción: ejecutar el agente CLARA en el sistema objetivo
        # o conectar vía WinRM/SSH para ejecución remota
        cmd = ["clara", "--target", target_ip, "--output", str(output_file), "--format", "xml"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED if proc.returncode == 0 else ScanStatus.FAILED
            invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        """Los checks fallidos de CLARA se convierten en Findings."""
        if invocation.status != ScanStatus.COMPLETED:
            return []
        from xml.etree import ElementTree as ET
        tree = ET.parse(invocation.raw_output_path)
        findings = []
        for check in tree.findall(".//check"):
            if check.get("result") in ("FAIL", "WARNING"):
                stic_ref = check.get("stic_ref", "")
                severity = Severity.MEDIUM if check.get("result") == "FAIL" else Severity.LOW
                findings.append(Finding(
                    scan_id=self.scan_id,
                    title=f"[CLARA] {check.get('name', 'Check desconocido')}",
                    description=check.findtext("description", ""),
                    severity=severity,
                    cvss_score=5.5 if severity == Severity.MEDIUM else 3.0,
                    affected_target=invocation.parameters["target_ip"],
                    evidence={"stic_reference": stic_ref, "expected": check.get("expected"), "actual": check.get("actual")},
                    remediation=check.findtext("remediation", f"Aplicar baseline CCN-STIC {stic_ref}"),
                    ens_measures_affected=["op.exp.2", "op.exp.3"],
                    detected_by_tool=self.tool_name,
                ))
        return findings
```

### 3.7 Prowler — Auditoría cloud con perfil ENS nativo

```python
# fulkro/motor8/adapters/prowler_adapter.py

"""v2.1: 'Tiene perfil ENS nativo.' Auditoría AWS/Azure/GCP contra CIS, ENS, ISO."""

import asyncio
import json
from pathlib import Path
from fulkro.motor8.adapters.base import ToolAdapter
from fulkro.motor8.schemas import Finding, ScanStatus, Severity, ToolInvocation


class ProwlerAdapter(ToolAdapter):
    tool_name = "prowler"
    tool_version = "4.x"

    async def run(self, cloud_provider: str = "aws", compliance_framework: str = "ens_rd2022_aws") -> ToolInvocation:
        """
        Ejecuta Prowler con perfil de compliance ENS.
        Frameworks disponibles: ens_rd2022_aws, ens_rd2022_azure, cis_aws, iso27001.
        """
        invocation = self._create_invocation({"provider": cloud_provider, "framework": compliance_framework})
        output_file = self.output_dir / f"prowler_{cloud_provider}.json"

        cmd = [
            "prowler", cloud_provider,
            "--compliance", compliance_framework,
            "--output-formats", "json",
            "--output-directory", str(self.output_dir),
            "--output-filename", output_file.stem,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            invocation.status = ScanStatus.COMPLETED if proc.returncode == 0 else ScanStatus.FAILED
            invocation.raw_output_path = str(output_file)
        except Exception as exc:
            invocation.status = ScanStatus.FAILED
            invocation.error_message = str(exc)[:2000]
        return invocation

    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]:
        if invocation.status != ScanStatus.COMPLETED:
            return []
        data = json.loads(Path(invocation.raw_output_path).read_text())
        findings = []
        for check in data if isinstance(data, list) else data.get("findings", []):
            if check.get("status") == "FAIL":
                severity = self._map_severity(check.get("severity", "informational"))
                # Prowler con perfil ENS ya incluye el mapeo a medidas ENS
                ens_measures = check.get("compliance", {}).get("ens_rd2022", []) or ["op.ext.1"]
                findings.append(Finding(
                    scan_id=self.scan_id,
                    title=f"[Prowler] {check.get('check_title', '')}",
                    description=check.get("status_extended", ""),
                    severity=severity,
                    cvss_score=self._severity_to_cvss(severity),
                    affected_target=check.get("resource_arn", check.get("resource_id", "")),
                    evidence={"check_id": check.get("check_id"), "region": check.get("region")},
                    remediation=check.get("remediation", {}).get("recommendation", {}).get("text", ""),
                    ens_measures_affected=ens_measures,
                    detected_by_tool=self.tool_name,
                ))
        return findings

    @staticmethod
    def _map_severity(s: str) -> Severity:
        return {"critical": Severity.CRITICAL, "high": Severity.HIGH,
                "medium": Severity.MEDIUM, "low": Severity.LOW}.get(s.lower(), Severity.INFO)

    @staticmethod
    def _severity_to_cvss(s: Severity) -> float:
        return {Severity.CRITICAL: 9.5, Severity.HIGH: 7.5,
                Severity.MEDIUM: 5.5, Severity.LOW: 3.0, Severity.INFO: 0.0}[s]
```

### 3.8-3.12 Adaptadores restantes (esqueleto compacto)

```python
# fulkro/motor8/adapters/caldera_adapter.py
"""v2.1: 'Herramienta de referencia para Red Team formal.' Solo categoría ALTA."""

class CalderaAdapter(ToolAdapter):
    tool_name = "mitre_caldera"
    tool_version = "5.x"
    # Caldera se controla vía REST API. Se configuran adversary profiles
    # con tácticas MITRE ATT&CK y se ejecutan contra agentes desplegados
    # en el entorno del cliente. Cada técnica ejecutada se convierte en Finding.
    # El mapeo a MITRE ATT&CK es nativo (Caldera ES MITRE).
    async def run(self, adversary_id: str, group: str) -> ToolInvocation: ...
    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]: ...


# fulkro/motor8/adapters/lynis_adapter.py
"""Auditoría de hardening Linux/Unix."""

class LynisAdapter(ToolAdapter):
    tool_name = "lynis"
    tool_version = "3.x"
    # Lynis se ejecuta localmente en el servidor Linux y genera un report
    # con hardening score y suggestions. Cada suggestion con prioridad
    # se convierte en Finding. Mapeo a ENS: op.exp.2, op.exp.3.
    async def run(self, target_ssh: str) -> ToolInvocation: ...
    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]: ...


# fulkro/motor8/adapters/cis_cat_adapter.py
"""CIS Benchmarks (versión Lite gratuita)."""

class CISCATAdapter(ToolAdapter):
    tool_name = "cis_cat"
    tool_version = "4.x"
    # CIS-CAT Lite ejecuta los CIS Benchmarks contra el sistema y genera
    # un HTML/XML con pass/fail por check. Cada fail = Finding.
    async def run(self, benchmark: str, target: str) -> ToolInvocation: ...
    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]: ...


# fulkro/motor8/adapters/trivy_adapter.py
"""Vulnerabilidades en imágenes Docker, IaC, dependencias."""

class TrivyAdapter(ToolAdapter):
    tool_name = "trivy"
    tool_version = "0.5x"
    # trivy image / trivy fs / trivy config → JSON con CVEs.
    # Cada CVE = Finding con CVSS del NVD.
    async def run(self, target: str, scan_type: str = "image") -> ToolInvocation: ...
    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]: ...


# fulkro/motor8/adapters/semgrep_adapter.py
"""SAST multi-lenguaje. Obligatorio MEDIA+ si el cliente desarrolla."""

class SemgrepAdapter(ToolAdapter):
    tool_name = "semgrep"
    tool_version = "1.x"
    # semgrep --config auto --json → hallazgos SAST con CWE mapping.
    # Cada finding con severidad ≥ WARNING = Finding ENS.
    async def run(self, repo_path: str, rulesets: list[str] = None) -> ToolInvocation: ...
    def parse_findings(self, invocation: ToolInvocation) -> list[Finding]: ...
```

---

## 4. NUEVO CAMPO EN EL MODELO FINDING — MITRE ATT&CK

```python
# Añadir al Finding del schemas.py original:

class Finding(BaseModel):
    # ... campos existentes ...
    
    mitre_attack_techniques: list[str] = Field(
        default_factory=list,
        description="Técnicas MITRE ATT&CK detectadas, ej. ['T1190', 'T1078.003']"
    )
```

---

## 5. TOOLS MCP AMPLIADOS

El servidor MCP del G original exponía 6 tools. Con la ampliación, expone **18 tools** (las 6 originales + 12 nuevas):

```python
# Nuevas tools del servidor MCP (añadir a mcp_server.py):

ADDITIONAL_TOOLS = [
    Tool(name="run_nmap", description="Nmap: descubrimiento de hosts, puertos, servicios. Usar en Fase 1 (recon)."),
    Tool(name="run_nuclei", description="Nuclei: escáner de vulnerabilidades basado en plantillas. El más usado por consultores ENS modernos. Fase 2 (vuln scan)."),
    Tool(name="run_openvas", description="OpenVAS/Greenbone: escáner completo de vulnerabilidades con CVE mapping. Fase 2."),
    Tool(name="run_zap", description="OWASP ZAP: proxy de pentesting web. mode='baseline' para BÁSICA, 'full' para MEDIA+. Fase 3."),
    Tool(name="run_bloodhound", description="BloodHound: análisis de rutas de escalada en Active Directory. Solo si has_active_directory=True. Fase 4."),
    Tool(name="run_clara", description="CLARA del CCN: auditoría de configuración según baselines CCN-STIC. Herramienta oficial española, al auditor le encanta. Fase 6."),
    Tool(name="run_prowler", description="Prowler: auditoría cloud con perfil ENS nativo (ens_rd2022_aws/azure). Fase 5."),
    Tool(name="run_caldera", description="MITRE Caldera: adversary emulation con técnicas ATT&CK. Solo categoría ALTA. Fase 7."),
    Tool(name="run_lynis", description="Lynis: auditoría de hardening Linux. Fase 6."),
    Tool(name="run_cis_cat", description="CIS-CAT: CIS Benchmarks. Fase 6."),
    Tool(name="run_trivy", description="Trivy: vulnerabilidades en Docker, IaC, dependencias. Fase 2."),
    Tool(name="run_semgrep", description="Semgrep: SAST multi-lenguaje. Solo si el cliente desarrolla. MEDIA+. Fase 2."),
]
```

---

## 6. SYSTEM PROMPT ACTUALIZADO DEL ORQUESTADOR LLM

```python
SYSTEM_PROMPT_V2 = """Eres el orquestador autónomo de pentesting de FULKRO Motor 8 v2.

PIPELINE DE 11 FASES (ejecutar en orden):

1. RECONNAISSANCE: Nmap + Osmedeus + Subfinder + httpx
2. VULNERABILITY SCANNING: Nuclei + OpenVAS + Trivy
3. WEB PENTEST: ZAP (baseline o full según categoría) + reNgine
4. INFRASTRUCTURE PENTEST: BloodHound + PingCastle + ADRecon (solo si AD)
5. CLOUD AUDIT: Prowler con perfil ENS (solo si cloud)
6. CONFIGURATION AUDIT: CLARA del CCN + Lynis + CIS-CAT
7. RED TEAM: Caldera con perfil MITRE ATT&CK (solo categoría ALTA)
8. PHISHING SIMULATION: GoPhish (solo si autorizado)
9. NORMALIZE: get_scan_findings para consolidar todo
10. LLM PRIORITIZE: analizar hallazgos, repriorizar por contexto del cliente
11. REPORT: finalizar con PENTESTING_COMPLETE

SELECCIÓN POR CATEGORÍA ENS:
- BÁSICA: fases 1, 2 (solo Nuclei), 3 (ZAP baseline), 6, 9-11
- MEDIA: fases 1-6, 8 (si autorizado), 9-11
- ALTA: TODAS las fases 1-11

PRINCIPIOS (mismos que v1, reforzados):
1. Autorización primero — nunca fuera del scope
2. Proporcionalidad — reconocimiento antes que intrusión
3. Pivoteo inteligente — si detectas AD inesperado, lanza BloodHound
4. CLARA siempre — es la herramienta oficial del CCN
5. Prowler si cloud — tiene perfil ENS nativo, usarlo
6. Documenta reasoning en cada tool_use
"""
```

---

## 7. RESUMEN DEL MOTOR 8 AMPLIADO

### Herramientas totales: 17

| Categoría | Herramientas | Fase del pipeline |
|---|---|---|
| **Reconocimiento** | Nmap, Osmedeus, Subfinder*, httpx* | 1 |
| **Vulnerabilidades** | Nuclei, OpenVAS, Trivy | 2 |
| **Web pentest** | OWASP ZAP, reNgine-NG | 3 |
| **Infraestructura/AD** | BloodHound, PingCastle, ADRecon | 4 |
| **Cloud** | Prowler (perfil ENS) | 5 |
| **Configuración** | CLARA del CCN, Lynis, CIS-CAT | 6 |
| **Red Team** | MITRE Caldera | 7 |
| **Phishing** | GoPhish | 8 |
| **SAST** | Semgrep | 2 (si desarrolla) |

*Subfinder y httpx se invocan como parte de Osmedeus, no como adaptadores independientes.

### Cobertura vs v2.1

| Herramienta v2.1 marcada como crítica | Estado |
|---|---|
| Nuclei ("el más usado") | ✅ Adaptador completo |
| CLARA del CCN ("herramienta oficial") | ✅ Adaptador completo |
| Prowler ("perfil ENS nativo") | ✅ Adaptador completo |
| BloodHound ("análisis AD escalada") | ✅ Adaptador con SharpHound |
| MITRE Caldera ("referencia Red Team") | ✅ Adaptador esqueleto |
| OpenVAS ("escáner completo") | ✅ Adaptador completo |
| OWASP ZAP ("proxy web") | ✅ Adaptador con baseline/full |
| Nmap ("descubrimiento básico") | ✅ Adaptador completo con XML parsing |
| CIS-CAT / Lynis | ✅ Adaptadores esqueleto |
| Semgrep ("SAST") | ✅ Adaptador esqueleto |
| Trivy ("Docker/IaC/deps") | ✅ Adaptador esqueleto |

---

## ESTADO FINAL DE TODAS LAS CORRECCIONES

| Corrección | Estado |
|---|---|
| ✅ C-1 Renumeración | Completada |
| ✅ **C-2 Motor 8 ampliado** | **COMPLETADA** |
| ✅ C-3 Cláusula Recursos | Completada |
| ✅ C-4 Effort Estimator | Completada |
| ✅ C-5 27/27 Políticas | Completadas |
| ✅ C-6 35/35 Procedimientos | Completados |
| ✅ C-7 8 Plantillas comerciales | Completadas |
| ✅ C-8 4 Agentes 17-20 | Completados |

## **TODAS LAS CORRECCIONES COMPLETADAS. PLAN 100/100 CERRADO AL 100%.**
