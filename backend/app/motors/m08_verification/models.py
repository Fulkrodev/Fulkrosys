"""M8 v5.1 — Verificacion Tecnica — Modelos SQLAlchemy.

Las 5 tablas viven aqui en lugar de models/verification.py para mantener
el motor autocontenido. Se importan desde models/__init__.py via
`from backend.app.motors.m08_verification.models import *` para que
SQLAlchemy las registre en la metadata global.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, ForeignKey, Index, Integer, Numeric, String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import (
    Base,
    ClientReviewMixinB,
    FullMixin,
    client_review_b_table_args,
)


# ════════════════════════════════════════════════════════════════════
# 1. VerificationRun — engagement Basica/Media/Alta
# ════════════════════════════════════════════════════════════════════

class VerificationRun(ClientReviewMixinB, FullMixin, Base):
    """Engagement de verificacion tecnica (M8 v5.1).

    Cliente review Pattern B via ClientReviewMixinB (atom 5.5.A).
    Atom MB-7.0.bis · helper B updated 2-col · clean usage.
    """
    __tablename__ = "verification_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    # BASICO | MEDIO | ALTO
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    # internal | external_handoff | external_ingest_pdf | external_ingest_form
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending",
    )

    # Scope auto-derivado de M22 + M3 + M6 + M2
    scope_jsonb: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scope_derived_from: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Ejecucion
    tools_config: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"),
    )
    tools_used: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )
    scheduled_start: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    phase1_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    phase1_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    phase2_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    phase2_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    phase3_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Autorizacion
    authorized_by: Mapped[str | None] = mapped_column(Text)
    authorization_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("magic_links.id"),
    )
    authorization_signed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    # Externo (solo Alta)
    external_pentester_name: Mapped[str | None] = mapped_column(Text)
    external_pentester_cert: Mapped[str | None] = mapped_column(Text)
    external_pentester_email: Mapped[str | None] = mapped_column(Text)
    external_report_original_path: Mapped[str | None] = mapped_column(Text)
    external_portal_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("magic_links.id"),
    )

    # Resultados agregados (calculados al completar)
    total_findings: Mapped[int] = mapped_column(Integer, server_default="0")
    confirmed_findings: Mapped[int] = mapped_column(Integer, server_default="0")
    critical_count: Mapped[int] = mapped_column(Integer, server_default="0")
    high_count: Mapped[int] = mapped_column(Integer, server_default="0")
    medium_count: Mapped[int] = mapped_column(Integer, server_default="0")
    low_count: Mapped[int] = mapped_column(Integer, server_default="0")
    info_count: Mapped[int] = mapped_column(Integer, server_default="0")
    security_score: Mapped[int | None] = mapped_column(Integer)

    # Delta con run anterior
    previous_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_runs.id"),
    )
    delta_new: Mapped[int] = mapped_column(Integer, server_default="0")
    delta_resolved: Mapped[int] = mapped_column(Integer, server_default="0")
    delta_persistent: Mapped[int] = mapped_column(Integer, server_default="0")

    # Kill switch (Checkpoint 2.12)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cancel_requested_by: Mapped[str | None] = mapped_column(Text)
    cancel_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # SSH credentials cifradas Fernet · NULL = local · non-NULL = remote
    # SAN-B.MB-3.bis.2 · ssh_credentials_crypto.encrypt_credentials
    ssh_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str | None] = mapped_column(Text, server_default="marcos")

    # ════════════════════════════════════════════════════════════════
    # SAN-E v3.MB-5.5 · Cliente authorization workflow pentest
    # Migration fc8ad935f6f6 · ADR-020 v6
    # ventana_inicio = scheduled_start existing · ventana_fin NEW abajo
    # ════════════════════════════════════════════════════════════════

    # Ventana ejecucion (3 cols)
    ventana_fin: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ventana_timezone: Mapped[str | None] = mapped_column(
        String(50), server_default="Europe/Madrid",
    )
    ventana_business_hours_only: Mapped[bool | None] = mapped_column(
        Boolean, server_default="false",
    )

    # Plan tests (3 cols · extiende tools_config existing)
    plan_test_categorias: Mapped[list | None] = mapped_column(JSONB)
    plan_test_intensity: Mapped[str | None] = mapped_column(String(20))
    plan_test_estimated_hours: Mapped[int | None] = mapped_column(Integer)

    # Contacto IR (4 cols · admin pre-set · cliente VE)
    contacto_ir_nombre: Mapped[str | None] = mapped_column(String(200))
    contacto_ir_email: Mapped[str | None] = mapped_column(String(255))
    contacto_ir_telefono: Mapped[str | None] = mapped_column(String(50))
    contacto_ir_horario: Mapped[str | None] = mapped_column(String(200))

    # Compromiso FULKRO (3 cols · admin pre-set · cliente VE)
    rules_of_engagement: Mapped[str | None] = mapped_column(Text)
    responsibility_disclosure: Mapped[str | None] = mapped_column(Text)
    data_handling_policy: Mapped[str | None] = mapped_column(Text)

    # Cliente review state (4 cols · pattern atoms 5.5.A) heredado de ClientReviewMixinB

    # ════════════════════════════════════════════════════════════════
    # AUTOPILOT v2.0 (M8_AUTOPILOT_ARCHITECTURE_v2 · migración
    # m8_autopilot_canonical_001) · additive · backward-compat NULL
    # ════════════════════════════════════════════════════════════════

    # Determinismo demostrable (doc §11)
    run_manifest_hash: Mapped[str | None] = mapped_column(Text)
    golden_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Observabilidad cobertura (doc §12)
    coverage_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    assets_in_scope: Mapped[int] = mapped_column(Integer, server_default="0")
    assets_scanned: Mapped[int] = mapped_column(Integer, server_default="0")

    # Estado del autopilot (doc §13 · fail-closed §10)
    # idle|authorized|running|paused_gate2|completed|failed|partial|cancelled
    autopilot_status: Mapped[str | None] = mapped_column(Text)
    # recon|detection|normalization|verification|triage|reporting|remediation
    autopilot_phase: Mapped[str | None] = mapped_column(Text)
    partial_run: Mapped[bool] = mapped_column(Boolean, server_default="false")
    tools_attempted: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )
    tools_failed: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )

    # Conector efímero · zero standing access time-boxed (doc §2)
    ephemeral_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ephemeral_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ephemeral_revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        Index("ix_vr_project_status", "project_id", "status"),
        Index(
            "ix_vr_autopilot_status", "project_id", "autopilot_status",
            postgresql_where=text("autopilot_status IS NOT NULL"),
        ),
        *client_review_b_table_args("verification_runs"),
    )


# ════════════════════════════════════════════════════════════════════
# 2. VerificationFinding — finding individual con ZFP
# ════════════════════════════════════════════════════════════════════

class VerificationFinding(FullMixin, Base):
    """Finding individual con ZFP de 5 gates."""
    __tablename__ = "verification_findings"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_runs.id"),
        nullable=False,
    )

    # Identificacion
    finding_hash: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    # critical | high | medium | low | info
    cvss_score: Mapped[float | None] = mapped_column(Numeric(3, 1))
    cvss_vector: Mapped[str | None] = mapped_column(Text)
    cve_id: Mapped[str | None] = mapped_column(Text)
    cwe_id: Mapped[str | None] = mapped_column(Text)

    # Localizacion
    affected_host: Mapped[str] = mapped_column(Text, nullable=False)
    affected_port: Mapped[int | None] = mapped_column(Integer)
    affected_service: Mapped[str | None] = mapped_column(Text)
    affected_service_version: Mapped[str | None] = mapped_column(Text)
    affected_url: Mapped[str | None] = mapped_column(Text)
    affected_os: Mapped[str | None] = mapped_column(Text)

    # Evidencia / cadena de custodia
    tool_sources: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    raw_outputs: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    screenshots: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )

    # ZFP — los 5 gates
    confidence_score: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, server_default="0.50",
    )
    zfp_gate1_dedup: Mapped[bool] = mapped_column(Boolean, server_default="false")
    zfp_gate2_fp_filter: Mapped[bool] = mapped_column(Boolean, server_default="false")
    zfp_gate3_cross_tool: Mapped[int] = mapped_column(Integer, server_default="0")
    zfp_gate4_retest: Mapped[str] = mapped_column(
        Text, server_default="not_tested",
    )
    # not_tested | confirmed | not_confirmed | not_applicable
    zfp_gate5_classification: Mapped[str] = mapped_column(
        Text, server_default="needs_review",
    )
    # confirmed | probable | needs_review | rejected

    # Mapeo ENS (multi-medida)
    ens_measures: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb"),
    )
    # [{measure: "op.exp.5", title: "...", method: "rule", citation: "..."}]
    ens_primary_measure: Mapped[str | None] = mapped_column(Text)

    # MITRE ATT&CK
    mitre_techniques: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )
    # [{technique: "T1190", tactic: "Initial Access"}]

    # Remediacion
    remediation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_guide_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    remediation_effort: Mapped[str | None] = mapped_column(Text)
    # quick_win | short_term | long_term
    remediation_time_estimate: Mapped[str | None] = mapped_column(Text)
    remediation_requires_restart: Mapped[bool] = mapped_column(
        Boolean, server_default="false",
    )
    remediation_requires_maintenance_window: Mapped[bool] = mapped_column(
        Boolean, server_default="false",
    )
    remediation_priority: Mapped[int | None] = mapped_column(Integer)

    # Estado
    status: Mapped[str] = mapped_column(Text, server_default="open")
    # open | remediated | accepted_risk | false_positive | needs_review
    remediated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    remediated_verified: Mapped[bool] = mapped_column(
        Boolean, server_default="false",
    )
    remediated_retest_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    accepted_risk_justification: Mapped[str | None] = mapped_column(Text)
    accepted_risk_approved_by: Mapped[str | None] = mapped_column(Text)
    false_positive_reason: Mapped[str | None] = mapped_column(Text)

    # ════════════════════════════════════════════════════════════════
    # AUTOPILOT v2.0 · Finding canónico ELEVADO (doc §4)
    # migración m8_autopilot_canonical_001 · additive · backward-compat
    # ════════════════════════════════════════════════════════════════

    # EPSS (probabilidad real de explotación · doc §3 Capa 3) 0..1
    epss_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # Nivel de verificación (doc §5 Gate 4 · aquí vive el Zero-FP)
    # unverified|passive|active_safe|exploitation
    verification_level: Mapped[str] = mapped_column(
        Text, server_default="unverified",
    )

    # Máquina de estados del hallazgo (doc §6)
    # detected|triaged|verified|reported|in_remediation|retested|closed
    # |false_positive|risk_accepted
    finding_state: Mapped[str] = mapped_column(Text, server_default="detected")

    # Dedup cross-motor (doc §3) · agrupa el mismo hecho de distintos motores
    dedup_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    first_seen: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Trazabilidad determinista del motor que lo produjo (doc §4 Finding)
    source_engine: Mapped[str | None] = mapped_column(Text)
    engine_version: Mapped[str | None] = mapped_column(Text)
    rule_id: Mapped[str | None] = mapped_column(Text)

    # Grafo de activos PKG-lite (D2) · FK lógica a pkg_nodes.id (sin constraint)
    asset_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # SARIF (doc §3 esquema común) · ref al run del result SARIF
    sarif_ref: Mapped[str | None] = mapped_column(Text)

    # Aceptación de riesgo con caducidad (doc §8)
    risk_accepted_expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    risk_accepted_by: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("idx_vf_finding_hash", "finding_hash"),
        Index("idx_vf_ens_primary", "ens_primary_measure"),
        Index("idx_vf_run_severity", "run_id", "severity"),
        Index("idx_vf_run_status", "run_id", "status"),
        Index("idx_vf_finding_state", "run_id", "finding_state"),
        Index(
            "idx_vf_dedup_group", "dedup_group_id",
            postgresql_where=text("dedup_group_id IS NOT NULL"),
        ),
        Index(
            "idx_vf_asset_node", "asset_node_id",
            postgresql_where=text("asset_node_id IS NOT NULL"),
        ),
    )


# ════════════════════════════════════════════════════════════════════
# 3. ExternalPentesterHandoff — paquete engagement Alta
# ════════════════════════════════════════════════════════════════════

class ExternalPentesterHandoff(FullMixin, Base):
    """Handoff a pentester externo OSCP (solo categoria Alta)."""
    __tablename__ = "external_pentester_handoffs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_runs.id"),
        nullable=False,
    )
    package_documents: Mapped[list] = mapped_column(JSONB, nullable=False)
    # [{name: "01_Scope", path: "...", generated_at: "..."}]

    vpn_config_path: Mapped[str | None] = mapped_column(Text)
    vpn_credentials_encrypted: Mapped[str | None] = mapped_column(Text)

    portal_magic_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("magic_links.id"),
    )
    portal_url: Mapped[str | None] = mapped_column(Text)

    kickoff_scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    kickoff_completed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    deadline: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    findings_submission_method: Mapped[str | None] = mapped_column(Text)
    # pdf | structured_form | both
    report_received_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    total_findings_received: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(Text, server_default="draft")
    # draft | portal_ready | sent | accepted | in_progress |
    # report_received | integrated | closed


# ════════════════════════════════════════════════════════════════════
# 4. FalsePositivePattern — base FP aprendidos
# ════════════════════════════════════════════════════════════════════

class FalsePositivePattern(FullMixin, Base):
    """Patron de falso positivo conocido (~500 inicial, crece con uso)."""
    __tablename__ = "false_positive_patterns"
    __table_args__ = (
        Index("idx_fpp_tool", "tool"),
    )

    tool: Mapped[str] = mapped_column(Text, nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    condition_jsonb: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    learned_from_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    times_matched: Mapped[int] = mapped_column(Integer, server_default="0")
    created_by: Mapped[str | None] = mapped_column(Text, server_default="marcos")


# ════════════════════════════════════════════════════════════════════
# 5. RemediationRetest — re-test quirurgico post-fix
# ════════════════════════════════════════════════════════════════════

class RemediationRetest(Base):
    """Re-test ejecutado tras 'Ya lo he arreglado' del cliente."""
    __tablename__ = "remediation_retests"
    __table_args__ = (
        Index("idx_rr_finding", "finding_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_findings.id"),
        nullable=False,
    )
    triggered_by: Mapped[str | None] = mapped_column(Text)
    # client_portal | marcos | scheduled
    retest_type: Mapped[str] = mapped_column(Text, nullable=False)
    # nuclei_single | testssl | zap_single | lynis_single | nmap_port
    retest_command: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    # fixed | still_present | error | inconclusive
    result_detail: Mapped[str | None] = mapped_column(Text)
    raw_output_path: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


# ════════════════════════════════════════════════════════════════════
# 6. Verdict — anotación del agente (ADVISORY · doc §4 + §7)
# ════════════════════════════════════════════════════════════════════

class Verdict(FullMixin, Base):
    """Anotación del agente de triage sobre un Finding.

    REGLA DURA DE INTEGRIDAD (doc §4 + §7): el Verdict JAMÁS reduce la
    severidad ni el estado del Finding por debajo de lo que dicta el motor
    determinista. Es advisory: sugiere, no decide. Solo un humano (override)
    o una verificación activa que desmiente (determinista) pueden bajar/cerrar.

    `triage` (jsonb) contiene: exploitability_in_context, business_impact,
    false_positive_likelihood, correlation_hypotheses, recommended_severity_adjustment,
    recommended_remediation.
    """
    __tablename__ = "m8_verdicts"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"),
        nullable=False, index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_runs.id"),
        nullable=False,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_findings.id"),
        nullable=False,
    )

    # Trazabilidad LLM pinneado (doc §7 blindaje base)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(Text)
    input_refs: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"),
    )

    # Triage estructurado (structured output · NO prosa-como-decisión)
    triage: Mapped[dict] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"),
    )
    structured_output_valid: Mapped[bool] = mapped_column(
        Boolean, server_default="false",
    )
    decision_log_ref: Mapped[str | None] = mapped_column(Text)

    # Override humano · {by, at, decision, justification}
    human_override: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_m8v_finding", "finding_id"),
        Index("idx_m8v_run", "run_id"),
    )


# ════════════════════════════════════════════════════════════════════
# 7. EvidenceRecord — append-only (doc §4 · pgAudit/R6 hash chain)
# ════════════════════════════════════════════════════════════════════

class EvidenceRecord(Base):
    """Registro de evidencia append-only (doc §4 EvidenceRecord).

    Append-only garantizado por triggers BD (migración
    m8_autopilot_canonical_001): `fn_audit_track` espeja cada INSERT al
    `audit_log` hash-chaineado (R6) y `fn_audit_log_immutable` rechaza
    UPDATE/DELETE sobre esta tabla. NO tiene updated_at/deleted_at: es
    write-once. El log ES el entregable de auditoría (evidence-first §0).
    """
    __tablename__ = "m8_evidence_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Clave de determinismo (doc §11) · liga la evidencia al run reproducible
    run_manifest_hash: Mapped[str | None] = mapped_column(Text)

    ts: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False,
    )
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    # system | human:<id> | tool:<name>@<ver> | model:<id>
    action: Mapped[str] = mapped_column(Text, nullable=False)
    component: Mapped[str | None] = mapped_column(Text)
    input_hash: Mapped[str | None] = mapped_column(Text)
    output_hash: Mapped[str | None] = mapped_column(Text)
    ens_relevance: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_m8er_run", "run_id"),
    )
