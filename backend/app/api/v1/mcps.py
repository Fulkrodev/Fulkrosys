"""MCPs status endpoint - FASE 9.B.

Sub-bloque 9.B: dashboard estado MCPs.

Inventario: 14 MCPs (13 servicios pentest + scope_enforcer fail-closed).
Source-of-truth: backend/mcp_servers/<name>/{server.py, Dockerfile}.

Estados:
- real: MCP integrado y consumido por motor backend (M08, M21, etc.)
- available: server.py + Dockerfile presentes, no integrado en backend (rol 9.C)
- coming_soon: placeholder, sin implementacion
- blocked: deshabilitado por configuracion / licencia / scope

Post-9.C: scope_enforcer + recon + webpentest en `real` (M08 retest_runner
invoca MCP server.py via JSON-RPC stdio cuando USE_MCP_REAL=true; fallback
transparente al runner subprocess legacy si la llamada MCP falla). Resto en
`available` pendiente de migrar (TODO-FASE-13-MCPS-FULL-MIGRATION-001).

scope_enforcer = `real` (efectivamente activo en el docker-compose como gate
fail-closed entre los pentest y el host).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.app.auth.dependencies import require_owner

router = APIRouter(
    prefix="/mcps", tags=["MCPs - Servers Status"],
    # El inventario revela el arsenal ofensivo (14 MCP pentest) → Marcos-only.
    # Antes: cualquier sesión autenticada (incl. cliente) podía listarlo.
    dependencies=[Depends(require_owner)],
)

MCPCategory = Literal[
    "scope",
    "recon",
    "vulnscan",
    "webpentest",
    "infra",
    "redteam",
    "cloud",
    "config",
    "phishing",
    "apisec",
    "mobile",
    "wireless",
    "cracking",
    "sast",
]

MCPState = Literal["real", "available", "coming_soon", "blocked"]


class MCPStatus(BaseModel):
    name: str
    label: str
    description: str
    category: MCPCategory
    state: MCPState
    version: str | None = None
    docker_image: str | None = None
    tools_count: int = 0
    last_health_check: str | None = None  # ISO datetime, null hasta 9.C


class MCPsStatusResponse(BaseModel):
    total: int = Field(..., description="Total MCPs registrados")
    real_count: int
    available_count: int
    coming_soon_count: int
    blocked_count: int
    items: list[MCPStatus]


# Inventario derivado de backend/mcp_servers/. Los tools_count corresponden
# al nombre de cada server.py register_tool calls (auditados manualmente).
_MCP_REGISTRY: list[MCPStatus] = [
    MCPStatus(
        name="scope_enforcer",
        label="Scope Enforcer",
        description="Gate fail-closed para todos los servidores pentest. Bloquea targets fuera de scope antes de que cualquier herramienta pueda ejecutarse.",
        category="scope",
        state="real",
        version="1.0.0",
        docker_image="fulkro-scope-enforcer:latest",
        tools_count=0,
    ),
    MCPStatus(
        name="recon",
        label="Recon",
        description="Reconocimiento pasivo y activo: nmap, masscan, amass, subfinder, httpx, naabu, shodan, theharvester, spiderfoot, searchsploit.",
        category="recon",
        state="real",
        version="0.9.0",
        docker_image="fulkro-recon:latest",
        tools_count=10,
    ),
    MCPStatus(
        name="vulnscan",
        label="Vulnerability Scanner",
        description="Escaneo de vulnerabilidades web/red: nuclei, nikto, testssl, dirb.",
        category="vulnscan",
        state="available",
        version="0.9.0",
        docker_image="fulkro-vulnscan:latest",
        tools_count=4,
    ),
    MCPStatus(
        name="webpentest",
        label="Web Pentest",
        description="Pentesting web: ZAP active scan, sqlmap, wpscan, ffuf, gobuster, wfuzz.",
        category="webpentest",
        state="real",
        version="0.9.0",
        docker_image="fulkro-webpentest:latest",
        tools_count=6,
    ),
    MCPStatus(
        name="infra",
        label="Infrastructure",
        description="Pentesting de infraestructura: metasploit, impacket, responder, crackmapexec, bloodhound, mimikatz wrappers.",
        category="infra",
        state="available",
        version="0.9.0",
        docker_image="fulkro-infra:latest",
        tools_count=13,
    ),
    MCPStatus(
        name="redteam",
        label="Red Team",
        description="Adversary emulation y C2: Caldera, Atomic Red Team, Sliver, Empire, Covenant.",
        category="redteam",
        state="available",
        version="0.9.0",
        docker_image="fulkro-redteam:latest",
        tools_count=6,
    ),
    MCPStatus(
        name="cloud",
        label="Cloud Security",
        description="Auditoria cloud (AWS/Azure/GCP): prowler, scoutsuite, cloudsplaining, pacu.",
        category="cloud",
        state="available",
        version="0.9.0",
        docker_image="fulkro-cloud:latest",
        tools_count=4,
    ),
    MCPStatus(
        name="config",
        label="Config Audit",
        description="Auditoria de configuracion sistemas: lynis, openvas-cli, chkrootkit, rkhunter.",
        category="config",
        state="available",
        version="0.9.0",
        docker_image="fulkro-config:latest",
        tools_count=4,
    ),
    MCPStatus(
        name="phishing",
        label="Phishing Simulation",
        description="Campana phishing controlada (gophish).",
        category="phishing",
        state="available",
        version="0.9.0",
        docker_image="fulkro-phishing:latest",
        tools_count=1,
    ),
    MCPStatus(
        name="apisec",
        label="API Security",
        description="Pentesting APIs REST/GraphQL: apicheck, kiterunner, postman-runner, graphql-cop.",
        category="apisec",
        state="available",
        version="0.9.0",
        docker_image="fulkro-apisec:latest",
        tools_count=4,
    ),
    MCPStatus(
        name="mobile",
        label="Mobile Pentest",
        description="Analisis estatico/dinamico apps moviles: mobsf, frida.",
        category="mobile",
        state="available",
        version="0.9.0",
        docker_image="fulkro-mobile:latest",
        tools_count=2,
    ),
    MCPStatus(
        name="wireless",
        label="Wireless",
        description="Auditoria redes wireless: aircrack-ng, kismet, wifite.",
        category="wireless",
        state="available",
        version="0.9.0",
        docker_image="fulkro-wireless:latest",
        tools_count=3,
    ),
    MCPStatus(
        name="cracking",
        label="Password Cracking",
        description="Cracking de credenciales en muestras controladas: hashcat, john, cewl.",
        category="cracking",
        state="available",
        version="0.9.0",
        docker_image="fulkro-cracking:latest",
        tools_count=3,
    ),
    MCPStatus(
        name="sast",
        label="SAST",
        description="Analisis estatico de codigo: semgrep, bandit, safety, dependency-check, checkov.",
        category="sast",
        state="available",
        version="0.9.0",
        docker_image="fulkro-sast:latest",
        tools_count=5,
    ),
]


@router.get("/status", response_model=MCPsStatusResponse)
async def get_mcps_status() -> MCPsStatusResponse:
    """Devuelve el inventario completo de MCPs y sus estados.

    Read-only, lectura desde registry estatico (no docker inspect aun).
    last_health_check vacio hasta 9.C cuando se anada el ping real.
    """
    items = list(_MCP_REGISTRY)
    return MCPsStatusResponse(
        total=len(items),
        real_count=sum(1 for m in items if m.state == "real"),
        available_count=sum(1 for m in items if m.state == "available"),
        coming_soon_count=sum(1 for m in items if m.state == "coming_soon"),
        blocked_count=sum(1 for m in items if m.state == "blocked"),
        items=items,
    )
