"""M8 v5.1 — Verificacion Tecnica — Schemas Pydantic.

Schemas para los 14 endpoints REST + estructuras intermedias del scope,
findings y handoff a pentester externo.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────── Enums (string) ────────────────────────────

VALID_CATEGORIES = ("BASICO", "MEDIO", "ALTO")
VALID_MODES = (
    "internal", "external_handoff",
    "external_ingest_pdf", "external_ingest_form",
)
VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")
VALID_STATUSES = (
    "open", "remediated", "accepted_risk",
    "false_positive", "needs_review",
)
VALID_CLASSIFICATIONS = (
    "confirmed", "probable", "needs_review", "rejected",
)


# ──────────────────────────── Run ────────────────────────────

class RunCreateBody(BaseModel):
    """Body de POST /verification/run."""
    category: str = Field(..., pattern="^(BASICO|MEDIO|ALTO)$")
    mode: str = Field("internal", pattern="^(internal|external_handoff|external_ingest_pdf|external_ingest_form)$")
    schedule_now: bool = Field(
        default=False,
        description="Si True, intenta ejecutar inmediatamente; si False, queda pending hasta ventana nocturna.",
    )
    tools_config: dict[str, Any] | None = Field(
        default=None,
        description="Override de configuracion por herramienta (claves: nuclei, nmap, zap, lynis...).",
    )


class RunSummary(BaseModel):
    """Resumen de un run para el listado."""
    id: UUID
    project_id: UUID
    category: str
    mode: str
    status: str
    scheduled_start: datetime | None
    completed_at: datetime | None
    total_findings: int
    confirmed_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    security_score: int | None
    delta_new: int
    delta_resolved: int
    delta_persistent: int
    created_at: datetime


class RunDetail(RunSummary):
    """Detalle de run con todos los timestamps de fase."""
    scope_jsonb: dict[str, Any]
    scope_derived_from: dict[str, Any] | None
    tools_used: list[Any]
    phase1_started_at: datetime | None
    phase1_completed_at: datetime | None
    phase2_started_at: datetime | None
    phase2_completed_at: datetime | None
    phase3_started_at: datetime | None
    authorized_by: str | None
    authorization_signed_at: datetime | None
    previous_run_id: UUID | None


# ──────────────────────────── Findings ────────────────────────────

class EnsMeasureMapping(BaseModel):
    measure: str
    title: str | None = None
    method: str | None = Field(
        None, description="rule | semantic | llm",
    )
    citation: str | None = None
    confidence: float | None = None


class MitreTechnique(BaseModel):
    technique: str
    tactic: str | None = None


class FindingSummary(BaseModel):
    """Vista resumida del finding (lista, dashboards)."""
    id: UUID
    run_id: UUID
    title: str
    severity: str
    cvss_score: float | None
    cve_id: str | None
    affected_host: str
    affected_port: int | None
    confidence_score: float
    zfp_gate5_classification: str
    ens_primary_measure: str | None
    status: str
    remediation_priority: int | None


class FindingDetail(FindingSummary):
    """Vista completa del finding."""
    finding_hash: str
    description: str
    cvss_vector: str | None
    cwe_id: str | None
    affected_service: str | None
    affected_service_version: str | None
    affected_url: str | None
    affected_os: str | None
    tool_sources: list[str]
    raw_outputs: list[dict[str, Any]]
    screenshots: list[dict[str, Any]]
    zfp_gate1_dedup: bool
    zfp_gate2_fp_filter: bool
    zfp_gate3_cross_tool: int
    zfp_gate4_retest: str
    ens_measures: list[EnsMeasureMapping]
    mitre_techniques: list[MitreTechnique]
    remediation_summary: str
    remediation_guide_jsonb: dict[str, Any] | None
    remediation_effort: str | None
    remediation_time_estimate: str | None
    remediation_requires_restart: bool
    remediation_requires_maintenance_window: bool
    remediated_at: datetime | None
    remediated_verified: bool
    accepted_risk_justification: str | None
    accepted_risk_approved_by: str | None
    false_positive_reason: str | None
    created_at: datetime


class FindingPatchBody(BaseModel):
    """PATCH /findings/{fid}: cambio de estado o anotacion."""
    status: str | None = Field(
        None, pattern="^(open|remediated|accepted_risk|false_positive|needs_review)$",
    )
    false_positive_reason: str | None = Field(None, max_length=2000)
    accepted_risk_justification: str | None = Field(None, max_length=2000)
    accepted_risk_approved_by: str | None = Field(None, max_length=200)


class FindingMappingPatchBody(BaseModel):
    """PATCH /findings/{fid}/mapping: corregir el mapeo ENS manualmente."""
    ens_measures: list[EnsMeasureMapping]
    ens_primary_measure: str | None = None


# ──────────────────────────── Remediation ────────────────────────────

class RetestRequestBody(BaseModel):
    """POST /findings/{fid}/retest."""
    triggered_by: str = Field(
        "marcos", pattern="^(client_portal|marcos|scheduled)$",
    )
    retest_type: str | None = Field(
        None,
        pattern="^(ssl|cve|web|hardening|port)$",
        description="Si no se indica, se escoge automaticamente segun el finding.",
    )


class RetestResult(BaseModel):
    id: UUID
    finding_id: UUID
    retest_type: str
    result: str
    result_detail: str | None
    raw_output_path: str | None
    executed_at: datetime


class RemediationPlanItem(BaseModel):
    priority: int
    finding_id: UUID
    title: str
    severity: str
    affected_host: str
    ens_primary_measure: str | None
    action: str
    effort: str | None
    time_estimate: str | None
    deadline_suggested: str  # ISO date


# ──────────────────────────── External Handoff ────────────────────────────

class HandoffCreateBody(BaseModel):
    """POST /verification/handoff (solo Alta)."""
    run_id: UUID
    pentester_name: str = Field(..., min_length=2, max_length=200)
    pentester_email: EmailStr
    pentester_cert: str = Field(
        ..., max_length=200,
        description="Certificacion del pentester: OSCP, OSEP, GPEN, etc.",
    )
    deadline: datetime | None = None
    findings_submission_method: str = Field(
        "both", pattern="^(pdf|structured_form|both)$",
    )


class HandoffDetail(BaseModel):
    id: UUID
    run_id: UUID
    package_documents: list[dict[str, Any]]
    portal_url: str | None
    deadline: datetime | None
    findings_submission_method: str | None
    status: str


class IngestStructuredFindingBody(BaseModel):
    """Cada finding del formulario estructurado (pentester externo)."""
    title: str = Field(..., min_length=2, max_length=300)
    description: str = Field(..., min_length=2)
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    cvss_score: float | None = Field(None, ge=0.0, le=10.0)
    cvss_vector: str | None = None
    cve_id: str | None = None
    affected_host: str = Field(..., min_length=1)
    affected_port: int | None = Field(None, ge=0, le=65535)
    affected_url: str | None = None
    reproduction_steps: str | None = None
    recommendation: str | None = None


class IngestRequestBody(BaseModel):
    """POST /verification/ingest — pentester externo entrega findings."""
    run_id: UUID
    source: str = Field(..., pattern="^(pdf|structured_form)$")
    pdf_base64: str | None = Field(
        None,
        description="PDF en base64 (obligatorio si source=pdf).",
    )
    original_pdf_path: str | None = Field(
        None, description="Path al PDF original ya persistido en MinIO.",
    )
    findings: list[IngestStructuredFindingBody] | None = Field(
        None,
        description="Lista de findings (obligatorio si source=structured_form).",
    )


# ──────────────────────────── Reports ────────────────────────────

class ReportRequestBody(BaseModel):
    """POST /verification/runs/{rid}/report."""
    template_codigo: str = Field(
        ..., pattern="^(E-702|E-703|E-704)$",
        description="E-702 (Verificacion completa) | E-703 (Resumen ejecutivo) | E-704 (Red Team, solo Alta)",
    )
    generate_pdf: bool = True
    sign: bool = True
    remediation_force_offline: bool = Field(
        False,
        description="Si True, usa templates deterministicos en lugar de Haiku para remediaciones.",
    )


class ReportInfo(BaseModel):
    report_type: str
    docx_path: str
    pdf_path: str | None
    hash_sha256: str
    signature_ed25519: str | None
    pages: int | None
    generated_at: datetime


# ──────────────────────────── Heatmap / Score / Delta ────────────────────────────

class HeatmapMeasureStatus(BaseModel):
    """Estado tecnico verificado de una medida ENS."""
    measure_id: str
    measure_name: str
    family: str
    tech_status: str = Field(
        ..., pattern="^(compliant|partial|non_compliant|not_verified)$",
    )
    open_findings: int
    worst_severity: str | None
    last_verified: datetime | None


class HeatmapResponse(BaseModel):
    project_id: UUID
    total_measures: int
    counts: dict[str, int]  # {compliant, partial, non_compliant, not_verified}
    measures: list[HeatmapMeasureStatus]
    generated_at: datetime


class SecurityScoreResponse(BaseModel):
    project_id: UUID
    current_score: int = Field(..., ge=0, le=100)
    previous_score: int | None
    trend: str | None  # improving | stable | degrading
    history: list[dict[str, Any]]  # [{run_id, score, completed_at}]


class DeltaResponse(BaseModel):
    current_run_id: UUID
    previous_run_id: UUID | None
    new_findings: list[FindingSummary]
    resolved_findings: list[FindingSummary]
    persistent_findings: list[FindingSummary]
    severity_changes: list[dict[str, Any]]
    overall_trend: str  # improving | stable | degrading | first_scan
