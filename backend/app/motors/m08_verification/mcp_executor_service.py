"""Sub-atom 1.D.E v3.11 · MCP Executor Service project-scoped.

Orquesta la ejecución de las 13 tools MCP (vulnscan + cloud + config +
phishing) per-project con:
  - Estado in-memory por execution_id (NO new DB table · ADR-025 sostener)
  - Async background runner via ``try_invoke_mcp_or_none`` (USE_MCP_REAL flag)
  - SSE progress events vía asyncio.Queue por execution
  - Auto-attach del reporte JSON al folder IDMS "13_Informes_Tecnicos"
    (clasificacion=informe · pattern m24_idms intake_document reuse)

R23 sostener firmísimo · todo project-scoped (auth require_owner).
R1 sostener · MCP determinista · NO LLM en la pipeline de ejecución.
OPS-045 19ª aplicación: backend MCP infrastructure (mcp_client + servers
+ tools + SSE pattern + m24_idms intake) production-grade existing ·
POLISH añade orquestador project-scoped.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.mcp_client import try_invoke_mcp_or_none

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# 13 tools catalog (vulnscan 4 · cloud 4 · config 4 · phishing 1)
# ════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MCPToolParamSpec:
    name: str
    type: str  # string · integer · enum · etc
    description: str
    required: bool = False
    default: Any = None
    enum: tuple[str, ...] | None = None
    placeholder: str | None = None


@dataclass(frozen=True)
class MCPToolDescriptor:
    mcp_name: str  # vulnscan, cloud, config, phishing
    tool_name: str  # nuclei_scan, prowler_scan, etc.
    label: str
    description: str
    risk_level: str  # low, medium, high
    estimated_duration_s: int
    params: tuple[MCPToolParamSpec, ...]


# Catálogo UI-facing para ejecución MANUAL de tools desde /mcps (el autopilot vive
# en autopilot/orchestrator.py · independiente). S12 fix campaña auditoría: los
# tool_name y params de cloud/* y config/* se ALINEARON con los MCPTool.name reales
# de cada server.py (prowler_audit, scoutsuite_audit, pacu_attack, clara_ccn_audit,
# cis_cat_audit, openscap_audit) y con su input_schema (provider/mode/...), de modo
# que con USE_MCP_REAL la ejecución manual ya NO cae siempre a _simulated_result por
# nombre/params inválidos. El ciclo ENS (autopilot → dossier ENAC) no depende de
# este catálogo.
MCP_TOOLS_CATALOG: dict[str, dict[str, MCPToolDescriptor]] = {
    "vulnscan": {
        "nuclei_scan": MCPToolDescriptor(
            mcp_name="vulnscan",
            tool_name="nuclei_scan",
            label="Nuclei",
            description=(
                "Template-driven vulnerability scanner con 8000+ CVE/misconfig "
                "checks (ProjectDiscovery)."
            ),
            risk_level="medium",
            estimated_duration_s=1800,
            params=(
                MCPToolParamSpec(
                    name="target", type="string", description="URL o IP objetivo",
                    required=True, placeholder="https://example.com",
                ),
                MCPToolParamSpec(
                    name="severity", type="string",
                    description="Severidades a incluir (csv)",
                    default="critical,high,medium",
                ),
                MCPToolParamSpec(
                    name="tags", type="string",
                    description="Categorías de templates Nuclei",
                    default="cve,misconfig",
                ),
                MCPToolParamSpec(
                    name="rate_limit", type="integer",
                    description="Requests por segundo", default=150,
                ),
            ),
        ),
        "openvas_scan": MCPToolDescriptor(
            mcp_name="vulnscan",
            tool_name="openvas_scan",
            label="OpenVAS",
            description="Scanner de vulnerabilidades de red (Greenbone).",
            risk_level="medium",
            estimated_duration_s=3600,
            params=(
                MCPToolParamSpec(
                    name="target_ip", type="string",
                    description="IP o rango CIDR del target",
                    required=True, placeholder="10.0.0.0/24",
                ),
                MCPToolParamSpec(
                    name="scan_config", type="enum",
                    description="Perfil de escaneo",
                    default="full_and_fast",
                    enum=("full_and_fast", "discovery", "full_deep"),
                ),
                MCPToolParamSpec(
                    name="port_range", type="string",
                    description="Rango de puertos",
                    default="1-65535",
                ),
            ),
        ),
        "trivy_scan": MCPToolDescriptor(
            mcp_name="vulnscan",
            tool_name="trivy_scan",
            label="Trivy",
            description=(
                "Escaneo de vulnerabilidades en imágenes Docker y SBOMs."
            ),
            risk_level="low",
            estimated_duration_s=600,
            params=(
                MCPToolParamSpec(
                    name="target_image", type="string",
                    description="Imagen Docker o ruta SBOM",
                    required=True, placeholder="alpine:3.18",
                ),
                MCPToolParamSpec(
                    name="severity_threshold", type="enum",
                    description="Umbral mínimo",
                    default="HIGH",
                    enum=("CRITICAL", "HIGH", "MEDIUM", "LOW"),
                ),
            ),
        ),
        "grype_sbom_scan": MCPToolDescriptor(
            mcp_name="vulnscan",
            tool_name="grype_sbom_scan",
            label="Grype",
            description="Escaneo SBOM (CycloneDX/SPDX) con base CVE Anchore.",
            risk_level="low",
            estimated_duration_s=300,
            params=(
                MCPToolParamSpec(
                    name="target_artifact", type="string",
                    description="Ruta al SBOM o imagen",
                    required=True, placeholder="./sbom.json",
                ),
                MCPToolParamSpec(
                    name="vuln_database", type="enum",
                    description="Base CVE a consultar",
                    default="nvd",
                    enum=("nvd", "github", "anchore"),
                ),
            ),
        ),
    },
    "cloud": {
        "prowler_audit": MCPToolDescriptor(
            mcp_name="cloud",
            tool_name="prowler_audit",
            label="Prowler",
            description=(
                "Auditoría cloud (AWS/Azure/GCP/K8s) · CIS · ENS · 600+ checks."
            ),
            risk_level="low",
            estimated_duration_s=1800,
            params=(
                MCPToolParamSpec(
                    name="provider", type="enum",
                    description="Proveedor cloud",
                    required=True, default="aws",
                    enum=("aws", "azure", "gcp", "kubernetes"),
                ),
                MCPToolParamSpec(
                    name="mode", type="enum",
                    description="Modo de ejecución (real requiere credenciales)",
                    default="real",
                    enum=("fixture", "mock", "real"),
                ),
                MCPToolParamSpec(
                    name="fixture_name", type="string",
                    description="Nombre de fixture (solo modo fixture)",
                    default="",
                ),
                MCPToolParamSpec(
                    name="timeout_seconds", type="integer",
                    description="Timeout en segundos", default=3600,
                ),
            ),
        ),
        "scoutsuite_audit": MCPToolDescriptor(
            mcp_name="cloud",
            tool_name="scoutsuite_audit",
            label="ScoutSuite",
            description="Auditoría multi-cloud (AWS · Azure · GCP · Aliyun · OCI).",
            risk_level="low",
            estimated_duration_s=1200,
            params=(
                MCPToolParamSpec(
                    name="provider", type="enum",
                    description="Proveedor cloud",
                    required=True, default="aws",
                    enum=("aws", "azure", "gcp", "aliyun", "oracle"),
                ),
                MCPToolParamSpec(
                    name="mode", type="enum",
                    description="Modo de ejecución (real requiere credenciales)",
                    default="real",
                    enum=("fixture", "mock", "real"),
                ),
                MCPToolParamSpec(
                    name="fixture_name", type="string",
                    description="Nombre de fixture (solo modo fixture)",
                    default="",
                ),
                MCPToolParamSpec(
                    name="timeout_seconds", type="integer",
                    description="Timeout en segundos", default=3600,
                ),
            ),
        ),
        "pacu_attack": MCPToolDescriptor(
            mcp_name="cloud",
            tool_name="pacu_attack",
            label="Pacu",
            description="Exploitation framework AWS (Rhino Security · módulos).",
            risk_level="high",
            estimated_duration_s=1800,
            params=(
                MCPToolParamSpec(
                    name="module", type="string",
                    description="Módulo Pacu a ejecutar",
                    required=True,
                    placeholder="iam__enum_users_roles_policies_groups",
                ),
                MCPToolParamSpec(
                    name="aws_account_id", type="string",
                    description="ID cuenta AWS objetivo",
                    required=True, placeholder="123456789012",
                ),
            ),
        ),
        "kube_security_scan": MCPToolDescriptor(
            mcp_name="cloud",
            tool_name="kube_security_scan",
            label="Kubernetes Security",
            description="Auditoría clúster K8s (kube-bench · kube-hunter · CIS).",
            risk_level="medium",
            estimated_duration_s=900,
            params=(
                MCPToolParamSpec(
                    name="kube_context", type="string",
                    description="Contexto kubectl",
                    required=True, placeholder="prod-cluster",
                ),
                MCPToolParamSpec(
                    name="namespace", type="string",
                    description="Namespace objetivo (vacío = todos)",
                    default="",
                ),
            ),
        ),
    },
    "config": {
        "clara_ccn_audit": MCPToolDescriptor(
            mcp_name="config",
            tool_name="clara_ccn_audit",
            label="CLARA",
            description="Auditor CCN-CERT CLARA · ingiere informe XML de CLARA.",
            risk_level="low",
            estimated_duration_s=600,
            params=(
                MCPToolParamSpec(
                    name="report_path", type="string",
                    description="Ruta al informe XML de CLARA",
                    required=True, placeholder="/path/to/clara_report.xml",
                ),
            ),
        ),
        "cis_cat_audit": MCPToolDescriptor(
            mcp_name="config",
            tool_name="cis_cat_audit",
            label="CIS-CAT",
            description="Auditor configuración CIS Benchmarks.",
            risk_level="low",
            estimated_duration_s=600,
            params=(
                MCPToolParamSpec(
                    name="benchmark", type="string",
                    description="CIS Benchmark a evaluar",
                    required=True, placeholder="CIS_Ubuntu_Linux_22.04_LTS",
                ),
                MCPToolParamSpec(
                    name="profile", type="string",
                    description="Perfil del benchmark",
                    default="Level 1",
                ),
            ),
        ),
        "lynis_audit": MCPToolDescriptor(
            mcp_name="config",
            tool_name="lynis_audit",
            label="Lynis",
            description="Auditoría hardening Linux/macOS.",
            risk_level="low",
            estimated_duration_s=300,
            params=(
                MCPToolParamSpec(
                    name="target_system", type="string",
                    description="Host objetivo (localhost si vacío)",
                    default="localhost",
                ),
                MCPToolParamSpec(
                    name="profile", type="enum",
                    description="Profile Lynis",
                    default="server",
                    enum=("workstation", "server", "developer"),
                ),
            ),
        ),
        "openscap_audit": MCPToolDescriptor(
            mcp_name="config",
            tool_name="openscap_audit",
            label="OpenSCAP",
            description="Compliance SCAP (DISA STIG · USGCB · ANSSI · CIS).",
            risk_level="low",
            estimated_duration_s=900,
            params=(
                MCPToolParamSpec(
                    name="datastream", type="string",
                    description="Ruta al datastream SCAP (SSG)",
                    required=True,
                    placeholder="/usr/share/xml/scap/ssg/.../ssg-ubuntu2204-ds.xml",
                ),
                MCPToolParamSpec(
                    name="profile", type="string",
                    description="Perfil XCCDF",
                    default="xccdf_org.ssgproject.content_profile_cis",
                ),
            ),
        ),
    },
    "phishing": {
        "gophish_campaign": MCPToolDescriptor(
            mcp_name="phishing",
            tool_name="gophish_campaign",
            label="GoPhish",
            description=(
                "Simulacro phishing controlado · campaña templated."
            ),
            risk_level="high",
            estimated_duration_s=86400,
            params=(
                MCPToolParamSpec(
                    name="campaign_name", type="string",
                    description="Nombre de la campaña",
                    required=True, placeholder="Q2 2026 awareness",
                ),
                MCPToolParamSpec(
                    name="template", type="enum",
                    description="Template phishing",
                    default="office365_reauth",
                    enum=(
                        "office365_reauth",
                        "google_workspace_alert",
                        "shipping_notification",
                        "internal_hr_form",
                    ),
                ),
                MCPToolParamSpec(
                    name="target_users", type="string",
                    description="Usuarios target (csv emails)",
                    required=True,
                    placeholder="user1@empresa.es,user2@empresa.es",
                ),
                MCPToolParamSpec(
                    name="landing_page", type="enum",
                    description="Landing page del clic",
                    default="awareness_education",
                    enum=("awareness_education", "credentials_collector"),
                ),
            ),
        ),
    },
}


def get_tool_descriptor(
    mcp_name: str, tool_name: str,
) -> MCPToolDescriptor | None:
    return MCP_TOOLS_CATALOG.get(mcp_name, {}).get(tool_name)


def list_all_tools() -> list[MCPToolDescriptor]:
    out: list[MCPToolDescriptor] = []
    for tools in MCP_TOOLS_CATALOG.values():
        out.extend(tools.values())
    return out


# ════════════════════════════════════════════════════════════════════
# Execution state in-memory
# ════════════════════════════════════════════════════════════════════


VALID_STATES = ("pending", "running", "completed", "failed")


@dataclass
class MCPExecution:
    execution_id: uuid.UUID
    project_id: uuid.UUID
    mcp_name: str
    tool_name: str
    params: dict[str, Any]
    triggered_by: str = "marcos"
    status: str = "pending"
    progress: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    evidence_document_id: uuid.UUID | None = None
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class MCPExecutorError(Exception):
    pass


class MCPExecutorService:
    """Singleton in-memory MCP executor project-scoped.

    Estado per-process · NO DB table T1 (ADR-025 sostener). Ejecuciones
    persisten via Evidence Vault auto-attach (m24_idms intake · folder
    código "13_Informes_Tecnicos"). History rehidratada desde m24_idms.
    """

    def __init__(self) -> None:
        self._executions: dict[uuid.UUID, MCPExecution] = {}
        # Refs fuertes a los background tasks · evita que el GC los recoja a
        # media ejecución (antipatrón asyncio documentado) y permite drenarlos
        # en shutdown/tests (un task cancelado a media op DB envenena la conexión
        # del pool · InterfaceError "another operation in progress").
        self._tasks: set[asyncio.Task] = set()

    def get_execution(self, execution_id: uuid.UUID) -> MCPExecution | None:
        return self._executions.get(execution_id)

    def list_executions_by_project(
        self, project_id: uuid.UUID,
    ) -> list[MCPExecution]:
        return [
            e for e in self._executions.values()
            if e.project_id == project_id
        ]

    async def execute_tool(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        mcp_name: str,
        tool_name: str,
        params: dict[str, Any],
        triggered_by: str = "marcos",
    ) -> MCPExecution:
        descriptor = get_tool_descriptor(mcp_name, tool_name)
        if not descriptor:
            raise MCPExecutorError(
                f"MCP tool {mcp_name}/{tool_name} desconocido. "
                f"Catálogo: {sorted(MCP_TOOLS_CATALOG)}",
            )

        # Validación parámetros requeridos
        for spec in descriptor.params:
            if spec.required and not params.get(spec.name):
                raise MCPExecutorError(
                    f"Parámetro {spec.name!r} obligatorio para "
                    f"{mcp_name}/{tool_name}",
                )

        execution = MCPExecution(
            execution_id=uuid.uuid4(),
            project_id=project_id,
            mcp_name=mcp_name,
            tool_name=tool_name,
            params=params,
            triggered_by=triggered_by,
            status="pending",
        )
        self._executions[execution.execution_id] = execution

        # Background task · NO bloquear endpoint.
        # NO se le pasa `db`: la sesión del request se cierra al devolver el 201
        # y el task seguiría vivo · usar esa sesión cerrada envenenaba la conexión
        # del pool (asyncpg single-conn · ops concurrentes en teardown → conexión
        # "deassociated" → fallos cruzados en tests/prod). El task abre su PROPIA
        # sesión vía async_session(). Ejecutable 8 Pasada 16.
        task = asyncio.create_task(self._run_execution(execution))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return execution

    async def wait_pending_tasks(self, timeout: float = 10.0) -> None:
        """Espera a que terminen los background tasks en vuelo.

        Para shutdown limpio y aislamiento de tests: garantiza que ningún task
        quede a media operación DB cuando se cierra el event loop (lo que
        devolvería conexiones envenenadas al pool global).
        """
        pending = [t for t in self._tasks if not t.done()]
        if pending:
            await asyncio.wait(pending, timeout=timeout)

    async def _run_execution(
        self, execution: MCPExecution,
    ) -> None:
        try:
            execution.status = "running"
            execution.started_at = datetime.now(timezone.utc)
            await self._publish_event(
                execution, "started",
                {"mcp": execution.mcp_name, "tool": execution.tool_name},
            )

            execution.progress = 20
            await self._publish_event(
                execution, "progress",
                {"progress": 20, "message": "Iniciando MCP server…"},
            )

            mcp_result = await try_invoke_mcp_or_none(
                server=execution.mcp_name,
                tool=execution.tool_name,
                args=execution.params,
            )

            if mcp_result is None:
                mcp_result = self._simulated_result(execution)

            execution.progress = 70
            await self._publish_event(
                execution, "progress",
                {"progress": 70, "message": "Procesando hallazgos…"},
            )

            execution.result = mcp_result
            execution.progress = 85
            await self._publish_event(
                execution, "progress",
                {"progress": 85, "message": "Adjuntando evidencia IDMS…"},
            )

            try:
                # Sesión propia del background task (NO la del request, ya cerrada).
                async with async_session() as bg_db:
                    doc_id = await self._auto_attach_evidence(bg_db, execution)
                    await bg_db.commit()
                execution.evidence_document_id = doc_id
            except Exception as exc:
                logger.warning(
                    "auto_attach_evidence falló %s/%s: %s",
                    execution.mcp_name, execution.tool_name, exc,
                )

            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.progress = 100
            await self._publish_event(
                execution, "completed",
                {
                    "execution_id": str(execution.execution_id),
                    "evidence_document_id": (
                        str(execution.evidence_document_id)
                        if execution.evidence_document_id else None
                    ),
                    "summary": (mcp_result or {}).get("summary", {}),
                },
            )
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)
            execution.completed_at = datetime.now(timezone.utc)
            logger.exception("MCP execution falló: %s", exc)
            await self._publish_event(
                execution, "failed", {"error": str(exc)},
            )
        finally:
            await execution.event_queue.put(None)

    async def _publish_event(
        self,
        execution: MCPExecution,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        await execution.event_queue.put({
            "type": event_type,
            "data": {
                **data,
                "execution_id": str(execution.execution_id),
                "status": execution.status,
                "progress": execution.progress,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _simulated_result(self, execution: MCPExecution) -> dict[str, Any]:
        """Fallback simulado cuando USE_MCP_REAL=false (dev / CI).

        Permite probar la pipeline UI completa sin spawn de servers
        Docker. Refleja schema realista por tool con findings de muestra.
        """
        descriptor = get_tool_descriptor(
            execution.mcp_name, execution.tool_name,
        )
        return {
            "_simulated": True,
            "execution_id": str(execution.execution_id),
            "mcp": execution.mcp_name,
            "tool": execution.tool_name,
            "params": execution.params,
            "findings": [],
            "summary": {
                "total": 0,
                "note": (
                    "Resultado simulado · USE_MCP_REAL=false. "
                    "En producción el MCP server real ejecuta el binario."
                ),
                "risk_level": (descriptor.risk_level if descriptor else "low"),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _auto_attach_evidence(
        self, db: AsyncSession, execution: MCPExecution,
    ) -> uuid.UUID | None:
        from backend.app.motors.m24_idms.idms_service import IDMSService

        idms = IDMSService()
        folders = await idms.list_folders(
            db, execution.project_id, standard_only=True,
        )
        folder_13 = next(
            (f for f in folders if f.standard_code == "13"), None,
        )
        if folder_13 is None:
            await idms.initialize_standard_folders(db, execution.project_id)
            folders = await idms.list_folders(
                db, execution.project_id, standard_only=True,
            )
            folder_13 = next(
                (f for f in folders if f.standard_code == "13"), None,
            )

        report_payload = {
            "execution_id": str(execution.execution_id),
            "project_id": str(execution.project_id),
            "mcp_name": execution.mcp_name,
            "tool_name": execution.tool_name,
            "params": execution.params,
            "status": execution.status,
            "started_at": (
                execution.started_at.isoformat() if execution.started_at else None
            ),
            "completed_at": (
                execution.completed_at.isoformat()
                if execution.completed_at else None
            ),
            "triggered_by": execution.triggered_by,
            "result": execution.result,
        }
        report_bytes = json.dumps(
            report_payload, indent=2, default=str,
        ).encode("utf-8")
        nombre = (
            f"MCP_{execution.mcp_name}_{execution.tool_name}_"
            f"{execution.execution_id.hex[:8]}.json"
        )

        intake = await idms.intake_document(
            db,
            project_id=execution.project_id,
            nombre=nombre,
            contenido=report_bytes,
            tipo_mime="application/json",
            folder_id=folder_13.id if folder_13 else None,
            clasificacion="informe",
            tags=[
                {
                    "type": "mcp", "value": execution.mcp_name,
                    "source": "auto", "confidence": 1.0,
                },
                {
                    "type": "tool", "value": execution.tool_name,
                    "source": "auto", "confidence": 1.0,
                },
                {
                    "type": "execution_id",
                    "value": str(execution.execution_id),
                    "source": "auto", "confidence": 1.0,
                },
            ],
            subido_por=execution.triggered_by,
            full_text_content=json.dumps(
                report_payload, indent=2, default=str,
            ),
        )
        await db.commit()
        doc = intake.get("document")
        return doc.id if doc else None


# Singleton helper
_executor: MCPExecutorService | None = None


def get_mcp_executor() -> MCPExecutorService:
    global _executor
    if _executor is None:
        _executor = MCPExecutorService()
    return _executor


def reset_executor_for_tests() -> None:
    """Helper for tests · clears in-memory state."""
    global _executor
    _executor = MCPExecutorService()


__all__ = [
    "MCP_TOOLS_CATALOG",
    "MCPExecution",
    "MCPExecutorError",
    "MCPExecutorService",
    "MCPToolDescriptor",
    "MCPToolParamSpec",
    "get_mcp_executor",
    "get_tool_descriptor",
    "list_all_tools",
    "reset_executor_for_tests",
]
