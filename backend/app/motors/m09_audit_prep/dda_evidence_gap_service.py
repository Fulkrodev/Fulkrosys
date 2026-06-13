"""DdA vs Evidence gap detection service · CLUSTER 3 Phase C3.1.

Pure service layer · cross-references DdA entries (M03) against Evidence vault
(M07) per ENS measure · returns DdaEvidenceGapMatrix con classification per
medida (covered · partial · missing · not_applicable).

ARQUITECTURAL DESIGN · REUSABLE:
- Pure functional service · NO HTTP coupling · NO authentication concerns
- Returns dataclass + serializable JSON-ready dict (Pydantic schema-friendly)
- Configurable via GapDetectionOptions (min_required + stale_threshold + etc)
- Reusable by:
    · CLUSTER 3 Phase C3.2 auditor portal + admin API endpoints
    · Sesión 3B-2B.10 future · Audit Simulacro Pre-ENAC engine
    · Cualquier motor que necesite snapshot DdA-evidence coherence
- Single-source-of-truth heuristic config · adjustable per project futuro

Edge cases handled empirical (Phase C3 spec):
1. ALTA-only medidas filtered out BÁSICA/MEDIA projects (categoria_minima check)
2. Stale evidence (>365d default) marks medida partial even si count OK
3. Multiple evidence per medida aggregated (count + most recent date)
4. Medidas no_aplica (DdA explicit) status='not_applicable' · NO gap
5. Medidas sin DdA entry (catalog gap) status='missing' con gap_reason explícito

NO uses ORM models directly · pure SQL via sa_text para reusability cross-context
(e.g. SQLite test mode si futuro · auditor token bypass role context).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# Configuration · empirical defaults (Marcos-validated · per ENS guidance)
# ════════════════════════════════════════════════════════════════════════

# Per ENS RD 311/2022 Anexo III ENAC guidance · most medidas require at least
# 1 documented evidence. Critical medidas (op.acc + mp.s + mp.com) typically
# require 3+ evidences (policy + procedure + execution log).
#
# Override per medida via M_categorias min_required column futuro (Future-X).
DEFAULT_MIN_REQUIRED_PER_MEASURE = 1

CRITICAL_HIGH_REQUIREMENT_PREFIXES = (
    "op.acc.",   # Access control · evidence policy + audit log + review
    "mp.s.",     # Service protection · pentest + monitoring + WAF
    "mp.com.",   # Communications · encryption + key mgmt + rotation
    "org.pl.",   # Planning org · policy + risk acceptance + review minutes
)

# Stale threshold · ENS audit cycle anual (audit ENAC every year)
DEFAULT_STALE_THRESHOLD_DAYS = 365

# Categoría mapping · valid columns per ENS measure
CATEGORIA_TO_COLUMN = {
    "BASICA": "aplica_basica",
    "MEDIA": "aplica_media",
    "ALTA": "aplica_alta",
}

# Medida considered critical if family + categoria audit guidance flags
CRITICAL_SEVERITY_FAMILIES_HIGH = frozenset({"op", "mp"})


@dataclass(frozen=True)
class GapDetectionOptions:
    """Configurable thresholds para gap detection per-project tuning."""

    min_required_per_measure: int = DEFAULT_MIN_REQUIRED_PER_MEASURE
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS
    critical_high_requirement: int = 3  # For mp.* + op.acc.* + mp.com.*
    skip_no_aplica: bool = True  # NO gap si DdA marks as no_aplica
    require_vigente: bool = True  # Only count evidence WHERE vigente=true
    require_clean: bool = True  # FIX P1-6: solo evidencia con scan_status='clean'


# ════════════════════════════════════════════════════════════════════════
# Status enum + status helpers
# ════════════════════════════════════════════════════════════════════════

class GapStatus:
    """Canonical status values · 4 mutually exclusive."""

    COVERED = "covered"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class GapSeverity:
    """Per-medida severity classification para summary rollup."""

    CRITICAL = "critical"   # Missing + family ∈ critical + categoria high requirement
    HIGH = "high"           # Partial + critical family OR missing + medium family
    MEDIUM = "medium"       # Partial + non-critical OR missing + low-impact
    LOW = "low"             # Stale only · OR informational


@dataclass
class EvidenceSummaryItem:
    """Per-evidence summary attached to medida gap row."""

    id: uuid.UUID
    nombre_tipo: str | None
    fichero_nombre_original: str | None
    fecha_evidencia: datetime | None
    vigente: bool


@dataclass
class MedidaGapRow:
    """Per-medida classification + metadata."""

    medida_code: str
    medida_nombre: str | None
    family: str | None
    categoria_minima: str | None
    aplicabilidad_dda: str | None  # null si NO DdA entry exists
    status: str  # GapStatus value
    severity: str  # GapSeverity value
    evidence_count: int
    min_required: int
    last_uploaded_at: datetime | None
    stale: bool
    gap_reason: str | None
    evidences_summary: list[EvidenceSummaryItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "medida_code": self.medida_code,
            "medida_nombre": self.medida_nombre,
            "family": self.family,
            "categoria_minima": self.categoria_minima,
            "aplicabilidad_dda": self.aplicabilidad_dda,
            "status": self.status,
            "severity": self.severity,
            "evidence_count": self.evidence_count,
            "min_required": self.min_required,
            "last_uploaded_at": (
                self.last_uploaded_at.isoformat() if self.last_uploaded_at else None
            ),
            "stale": self.stale,
            "gap_reason": self.gap_reason,
            "evidences_summary": [
                {
                    "id": str(e.id),
                    "nombre_tipo": e.nombre_tipo,
                    "fichero_nombre_original": e.fichero_nombre_original,
                    "fecha_evidencia": (
                        e.fecha_evidencia.isoformat()
                        if e.fecha_evidencia else None
                    ),
                    "vigente": e.vigente,
                }
                for e in self.evidences_summary
            ],
        }


@dataclass
class GapSeveritySummary:
    """Rollup counters para UI severity cards."""

    critical_missing: int
    high_partial: int
    medium_total: int
    low_total: int
    recoverable: int  # Quick-fix actionable (missing/partial single-evidence medidas)

    def to_dict(self) -> dict[str, int]:
        return {
            "critical_missing": self.critical_missing,
            "high_partial": self.high_partial,
            "medium_total": self.medium_total,
            "low_total": self.low_total,
            "recoverable": self.recoverable,
        }


@dataclass
class DdaEvidenceGapMatrix:
    """Top-level result · 73 medidas × per-status."""

    project_id: uuid.UUID
    categoria: str | None
    total_applicable: int
    total_covered: int
    total_partial: int
    total_missing: int
    total_not_applicable: int
    coverage_pct: float  # 0.0 - 100.0
    medidas: list[MedidaGapRow]
    severity_summary: GapSeveritySummary
    options_used: GapDetectionOptions
    computed_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": str(self.project_id),
            "categoria": self.categoria,
            "total_applicable": self.total_applicable,
            "total_covered": self.total_covered,
            "total_partial": self.total_partial,
            "total_missing": self.total_missing,
            "total_not_applicable": self.total_not_applicable,
            "coverage_pct": self.coverage_pct,
            "medidas": [m.to_dict() for m in self.medidas],
            "severity_summary": self.severity_summary.to_dict(),
            "options_used": {
                "min_required_per_measure": (
                    self.options_used.min_required_per_measure
                ),
                "stale_threshold_days": self.options_used.stale_threshold_days,
                "critical_high_requirement": (
                    self.options_used.critical_high_requirement
                ),
                "skip_no_aplica": self.options_used.skip_no_aplica,
                "require_vigente": self.options_used.require_vigente,
                "require_clean": self.options_used.require_clean,
            },
            "computed_at": self.computed_at.isoformat(),
        }


# ════════════════════════════════════════════════════════════════════════
# Classification helpers · pure functions (testable isolation)
# ════════════════════════════════════════════════════════════════════════

def _is_high_requirement_medida(medida_code: str) -> bool:
    """True si medida en categoría high-requirement (op.acc.* · mp.* · etc)."""
    if not medida_code:
        return False
    return any(
        medida_code.startswith(p) for p in CRITICAL_HIGH_REQUIREMENT_PREFIXES
    )


def _medida_applies_to_categoria(
    medida_data: dict, project_categoria: str | None,
) -> bool:
    """True si medida applies per project categoría · uses aplica_X columns."""
    if not project_categoria:
        return True  # Conservative: assume applies si no categoría set
    col = CATEGORIA_TO_COLUMN.get(project_categoria.upper())
    if col is None:
        return True
    return bool(medida_data.get(col, True))


def _classify_status(
    *,
    evidence_count: int,
    min_required: int,
    stale: bool,
    aplicabilidad_dda: str | None,
    options: GapDetectionOptions,
) -> tuple[str, str | None]:
    """Returns (status, gap_reason) tuple."""
    if (
        options.skip_no_aplica
        and aplicabilidad_dda == "no_aplica"
    ):
        return GapStatus.NOT_APPLICABLE, None

    if evidence_count == 0:
        return GapStatus.MISSING, "Sin evidencia documental aportada"

    if evidence_count < min_required:
        return (
            GapStatus.PARTIAL,
            f"Insuficiente: {evidence_count}/{min_required} evidencias mínimas",
        )

    if stale:
        return (
            GapStatus.PARTIAL,
            "Evidencia antigua: revisión anual ENS pendiente",
        )

    return GapStatus.COVERED, None


def _classify_severity(
    *,
    status: str,
    family: str | None,
    is_high_req: bool,
) -> str:
    """Per-medida severity rollup classification."""
    if status == GapStatus.NOT_APPLICABLE:
        return GapSeverity.LOW
    if status == GapStatus.COVERED:
        return GapSeverity.LOW

    family_lower = (family or "").lower()
    # FIX: `family` es el código de 2º nivel del Anexo II (op.acc, mp.s, org…),
    # NUNCA el marco suelto. Comparar contra {"op","mp"} daba SIEMPRE False →
    # toda medida MISSING fuera de los prefijos high-req se clasificaba MEDIUM
    # (en vez de HIGH) y las PARTIAL LOW (en vez de MEDIUM) → high_partial/
    # critical_missing infravalorados → NO se abrían bucles correctivos y GATE-7
    # veía menos NC de las reales. Se compara sobre el marco (primer segmento).
    marco = family_lower.split(".", 1)[0]
    is_critical_family = marco in CRITICAL_SEVERITY_FAMILIES_HIGH

    if status == GapStatus.MISSING:
        if is_high_req or (is_critical_family and marco == "mp"):
            return GapSeverity.CRITICAL
        if is_critical_family:
            return GapSeverity.HIGH
        return GapSeverity.MEDIUM

    # PARTIAL
    if is_high_req:
        return GapSeverity.HIGH
    if is_critical_family:
        return GapSeverity.MEDIUM
    return GapSeverity.LOW


def _is_recoverable(row: MedidaGapRow) -> bool:
    """Medida quick-fix actionable · single evidence upload typically resolves."""
    if row.status == GapStatus.MISSING:
        return row.min_required == 1
    if row.status == GapStatus.PARTIAL and not row.stale:
        # Just need 1-2 more evidences
        return (row.min_required - row.evidence_count) <= 2
    return False


# ════════════════════════════════════════════════════════════════════════
# Main service function · public API (reusable cross-context)
# ════════════════════════════════════════════════════════════════════════

async def compute_dda_evidence_gaps(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    options: Optional[GapDetectionOptions] = None,
) -> DdaEvidenceGapMatrix:
    """Compute gap matrix · per medida ENS applicable cross-reference evidence.

    Reusable signature (Sesión 3B-2B.10 simulacro Pre-ENAC engine target).

    Args:
        db: AsyncSession (cualquier role · service queries are read-only)
        project_id: project scope
        options: tuning thresholds · None uses defaults

    Returns:
        DdaEvidenceGapMatrix con 73 medidas classified + severity rollup
    """
    opts = options or GapDetectionOptions()

    # Project metadata · categoria_objetivo
    project_row = (await db.execute(sa_text(
        "SELECT categoria_objetivo FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    if project_row is None:
        raise ValueError(f"Project {project_id} not found")
    categoria = (project_row[0] or "").upper() if project_row[0] else None

    # ENS measures catalog · pull all + applicability columns
    measures_rows = (await db.execute(sa_text(
        "SELECT codigo, nombre, familia, categoria_minima, "
        "aplica_basica, aplica_media, aplica_alta "
        "FROM ens_measures "
        "WHERE deleted_at IS NULL "
        "ORDER BY codigo"
    ))).all()

    # DdA entries per medida_id (project bound)
    dda_rows = (await db.execute(sa_text(
        "SELECT m.codigo, e.aplicabilidad, e.estado_implementacion "
        "FROM dda_entries e "
        "JOIN ens_measures m ON m.id = e.measure_id "
        "WHERE e.project_id = :pid AND e.deleted_at IS NULL"
    ), {"pid": str(project_id)})).all()
    dda_by_code: dict[str, dict[str, str | None]] = {
        row[0]: {"aplicabilidad": row[1], "estado": row[2]}
        for row in dda_rows
    }

    # Evidence per measure_code (project bound + vigente filter optional)
    vigente_clause = "AND vigente = true" if opts.require_vigente else ""
    # FIX P1-6: evidencia con scan_status != 'clean' (infected/quarantined/
    # scanning/error) NO cuenta como cobertura → antes inflaba el coverage_pct
    # del informe firmado al auditor y ocultaba NC reales (criterio canónico
    # 'clean=validado' · control_status_service + workflow_state_scanner).
    clean_clause = "AND scan_status = 'clean'" if opts.require_clean else ""
    evidence_rows = (await db.execute(sa_text(
        "SELECT measure_code, count(*) AS cnt, "
        "max(coalesce(fecha_evidencia, created_at::date)) AS last_date "
        "FROM evidence "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND measure_code IS NOT NULL "
        f"{vigente_clause} {clean_clause} "
        "GROUP BY measure_code"
    ), {"pid": str(project_id)})).all()
    evidence_summary_by_code: dict[str, dict[str, Any]] = {
        row[0]: {"count": row[1], "last_date": row[2]}
        for row in evidence_rows
    }

    # Per-evidence summary (top 5 most recent per medida · for drawer drill-down)
    evidence_items_rows = (await db.execute(sa_text(
        "SELECT measure_code, id, nombre_tipo, fichero_nombre_original, "
        "fecha_evidencia, vigente "
        "FROM evidence "
        "WHERE project_id = :pid AND deleted_at IS NULL "
        "AND measure_code IS NOT NULL "
        f"{vigente_clause} {clean_clause} "
        "ORDER BY measure_code, fecha_evidencia DESC NULLS LAST, "
        "created_at DESC"
    ), {"pid": str(project_id)})).all()
    evidence_items_by_code: dict[str, list[EvidenceSummaryItem]] = {}
    for row in evidence_items_rows:
        code = row[0]
        items = evidence_items_by_code.setdefault(code, [])
        if len(items) < 5:  # Top 5 per medida
            fecha = row[4]
            if fecha is not None and not isinstance(fecha, datetime):
                fecha = datetime.combine(fecha, datetime.min.time(), tzinfo=timezone.utc)
            items.append(EvidenceSummaryItem(
                id=row[1],
                nombre_tipo=row[2],
                fichero_nombre_original=row[3],
                fecha_evidencia=fecha,
                vigente=bool(row[5]),
            ))

    # Stale threshold cutoff
    now = datetime.now(timezone.utc)
    stale_cutoff_days = opts.stale_threshold_days

    # Iterate medidas + classify
    medidas: list[MedidaGapRow] = []
    counts = {
        GapStatus.COVERED: 0,
        GapStatus.PARTIAL: 0,
        GapStatus.MISSING: 0,
        GapStatus.NOT_APPLICABLE: 0,
    }

    for m_row in measures_rows:
        codigo = m_row[0]
        m_data = {
            "codigo": codigo,
            "nombre": m_row[1],
            "familia": m_row[2],
            "categoria_minima": m_row[3],
            "aplica_basica": m_row[4],
            "aplica_media": m_row[5],
            "aplica_alta": m_row[6],
        }

        applies = _medida_applies_to_categoria(m_data, categoria)
        dda_entry = dda_by_code.get(codigo)
        aplicabilidad_dda = (
            dda_entry["aplicabilidad"] if dda_entry else None
        )

        if not applies:
            # Out of scope per categoria · NOT_APPLICABLE silenced
            counts[GapStatus.NOT_APPLICABLE] += 1
            row = MedidaGapRow(
                medida_code=codigo,
                medida_nombre=m_data["nombre"],
                family=m_data["familia"],
                categoria_minima=m_data["categoria_minima"],
                aplicabilidad_dda=aplicabilidad_dda,
                status=GapStatus.NOT_APPLICABLE,
                severity=GapSeverity.LOW,
                evidence_count=0,
                min_required=0,
                last_uploaded_at=None,
                stale=False,
                gap_reason=None,
                evidences_summary=[],
            )
            medidas.append(row)
            continue

        # Determine min_required per medida (high-requirement override)
        is_high_req = _is_high_requirement_medida(codigo)
        min_req = (
            opts.critical_high_requirement
            if is_high_req
            else opts.min_required_per_measure
        )

        # Evidence aggregates
        ev = evidence_summary_by_code.get(codigo, {"count": 0, "last_date": None})
        evidence_count = ev["count"]
        last_date = ev["last_date"]
        last_uploaded_at: datetime | None = None
        stale = False
        if last_date is not None:
            if not isinstance(last_date, datetime):
                last_uploaded_at = datetime.combine(
                    last_date, datetime.min.time(), tzinfo=timezone.utc,
                )
            else:
                last_uploaded_at = last_date
            age_days = (now - last_uploaded_at).days
            stale = age_days > stale_cutoff_days

        status, gap_reason = _classify_status(
            evidence_count=evidence_count,
            min_required=min_req,
            stale=stale,
            aplicabilidad_dda=aplicabilidad_dda,
            options=opts,
        )
        severity = _classify_severity(
            status=status,
            family=m_data["familia"],
            is_high_req=is_high_req,
        )

        counts[status] += 1
        medidas.append(MedidaGapRow(
            medida_code=codigo,
            medida_nombre=m_data["nombre"],
            family=m_data["familia"],
            categoria_minima=m_data["categoria_minima"],
            aplicabilidad_dda=aplicabilidad_dda,
            status=status,
            severity=severity,
            evidence_count=evidence_count,
            min_required=min_req,
            last_uploaded_at=last_uploaded_at,
            stale=stale,
            gap_reason=gap_reason,
            evidences_summary=evidence_items_by_code.get(codigo, []),
        ))

    # Severity summary rollup
    critical_missing = sum(
        1 for m in medidas
        if m.severity == GapSeverity.CRITICAL
        and m.status == GapStatus.MISSING
    )
    high_partial = sum(
        1 for m in medidas
        if m.severity == GapSeverity.HIGH
        and m.status == GapStatus.PARTIAL
    )
    medium_total = sum(
        1 for m in medidas if m.severity == GapSeverity.MEDIUM
    )
    low_total = sum(
        1 for m in medidas if m.severity == GapSeverity.LOW
        and m.status != GapStatus.NOT_APPLICABLE
    )
    recoverable = sum(1 for m in medidas if _is_recoverable(m))

    severity_summary = GapSeveritySummary(
        critical_missing=critical_missing,
        high_partial=high_partial,
        medium_total=medium_total,
        low_total=low_total,
        recoverable=recoverable,
    )

    total_applicable = (
        counts[GapStatus.COVERED]
        + counts[GapStatus.PARTIAL]
        + counts[GapStatus.MISSING]
    )
    coverage_pct = (
        (counts[GapStatus.COVERED] / total_applicable * 100)
        if total_applicable > 0 else 0.0
    )

    return DdaEvidenceGapMatrix(
        project_id=project_id,
        categoria=categoria,
        total_applicable=total_applicable,
        total_covered=counts[GapStatus.COVERED],
        total_partial=counts[GapStatus.PARTIAL],
        total_missing=counts[GapStatus.MISSING],
        total_not_applicable=counts[GapStatus.NOT_APPLICABLE],
        coverage_pct=round(coverage_pct, 2),
        medidas=medidas,
        severity_summary=severity_summary,
        options_used=opts,
        computed_at=now,
    )


async def compute_medida_detail(
    db: AsyncSession,
    project_id: uuid.UUID,
    medida_code: str,
    *,
    options: Optional[GapDetectionOptions] = None,
) -> Optional[MedidaGapRow]:
    """Drill-down per medida · returns single MedidaGapRow or None."""
    matrix = await compute_dda_evidence_gaps(db, project_id, options=options)
    for m in matrix.medidas:
        if m.medida_code == medida_code:
            return m
    return None
