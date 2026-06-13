"""Diagnostic Gap Engine · deterministic R1 (sub-atom 1.D.X.H v3.12).

Pipeline puro deterministic · LLM enrichment SOLO explanation_es.

Input:
  - project_id + categoría ENS (BASICA/MEDIA/ALTA · desde projects.dimensions)
  - lista CloudResource detectadas (cualquier provider · pre-sincronizado)

Process:
  1. rules_for_category(categoria) → reglas aplicables
  2. Per regla · detector(resources) → list[GapFinding]
  3. UPSERT idempotente CloudGap por (project_id, ens_measure_code)
     · si existing y resuelto → re-abrir si findings vuelven a emitir
     · si existing y abierto → actualizar raw_evidence + explanation_es
     · si no existing → crear
  4. (opcional) LLM enrichment explanation_es via CopilotPersonaService admin

Auto-trigger:
  - On sync completion (hook m_cloud_connectors.service.trigger_sync · sub-fase L)
  - On categoría change (m01 project update)
  - Manual: POST /admin/projects/{id}/cloud-connectors/run-diagnosis

R1 INVIOLABLE sostener: decisión detected/missing/severity es DETERMINISTIC.
LLM SOLO redacta `explanation_es` cuando cliente solicita más contexto.
ADR-031 ENAC-ready trazabilidad · raw_evidence JSONB persiste qué resource
justificó el hallazgo.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import and_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m_cloud_connectors.base_connector import now_utc
from backend.app.motors.m_cloud_connectors.gap_rules import (
    GapFinding,
    rules_for_category,
)
from backend.app.motors.m_cloud_connectors.models import (
    CloudGap,
    CloudResource,
)


logger = logging.getLogger(__name__)


# Normalización categoría · projects.categoria_objetivo puede venir como
# "BASICA"/"basica"/"Básica"/"B"/"M"/"A" según source · centralizado aquí.
_CATEGORY_ALIASES: dict[str, str] = {
    "B": "BASICA", "BASICA": "BASICA", "BÁSICA": "BASICA",
    "M": "MEDIA", "MEDIA": "MEDIA",
    "A": "ALTA", "ALTA": "ALTA",
}


def _normalize_category(value: str) -> str | None:
    return _CATEGORY_ALIASES.get(value.strip().upper())


# ==================================================================
# Reporting DTOs
# ==================================================================


@dataclass
class DiagnosisReport:
    """Resumen ejecutivo · response endpoint POST run-diagnosis."""

    project_id: uuid.UUID
    category: str | None
    rules_evaluated: int
    findings_emitted: int
    gaps_created: int = 0
    gaps_updated: int = 0
    gaps_resolved: int = 0
    """Gaps existing que ya NO emiten finding · marcados resolved automatic."""
    gap_codes: list[str] = field(default_factory=list)
    """Lista ENS measure codes con gap abierto post-diagnóstico."""
    no_cloud_data: bool = False
    """True si project NO tiene CloudResources · cliente debe conectar primero."""


# ==================================================================
# DiagnosticGapEngine
# ==================================================================


class DiagnosticGapEngine:
    """Engine deterministic · evalúa reglas + persiste gaps."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_diagnosis(
        self,
        *,
        project_id: uuid.UUID,
        category: str | None = None,
    ) -> DiagnosisReport:
        """Ejecuta diagnóstico completo · idempotent UPSERT gaps + auto-resolve.

        Si ``category`` no se pasa → lookup desde projects.dimensions (fallback
        BASICA si no determinable).
        """
        if category is None:
            category = await self._resolve_project_category(project_id)

        rules = rules_for_category(category)
        report = DiagnosisReport(
            project_id=project_id,
            category=category,
            rules_evaluated=len(rules),
            findings_emitted=0,
        )

        if not rules:
            return report

        # Cargar resources del project (across all connectors)
        resources = await self._load_project_resources(project_id)
        if not resources:
            # Forzamos al menos las reglas documentales (no requieren cloud
            # data · org.1 + op.exp.1 emiten su finding documental).
            report.no_cloud_data = True

        # Ejecutar reglas (pure functions · NO DB)
        all_findings: list[GapFinding] = []
        for rule in rules:
            try:
                findings = rule.detector(resources)
                all_findings.extend(findings)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "rule %s detector failed · project=%s · err=%s",
                    rule.rule_id, project_id, exc,
                )

        report.findings_emitted = len(all_findings)

        # UPSERT gaps + auto-resolve los que ya no emiten
        await self._upsert_findings(
            project_id=project_id,
            findings=all_findings,
            evaluated_measures={r.ens_measure_code for r in rules},
            report=report,
        )

        report.gap_codes = sorted({f.ens_measure_code for f in all_findings})
        return report

    # ----------------------------------------------------------
    # Internals
    # ----------------------------------------------------------

    async def _resolve_project_category(
        self, project_id: uuid.UUID,
    ) -> str | None:
        """Lookup ENS category desde projects.categoria_objetivo (B/M/A).

        Fallback None si project no tiene categoría asignada todavía (early
        onboarding · usuario aún no respondió cuestionario M01).
        """
        try:
            row = (await self.db.execute(
                text(
                    "SELECT categoria_objetivo FROM projects "
                    "WHERE id = :pid AND deleted_at IS NULL"
                ),
                {"pid": str(project_id)},
            )).fetchone()
            if row and row[0]:
                return _normalize_category(str(row[0]))
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "projects.categoria_objetivo lookup failed for %s · %s",
                project_id, exc,
            )
        return None

    async def _load_project_resources(
        self, project_id: uuid.UUID,
    ) -> list[CloudResource]:
        stmt = (
            select(CloudResource)
            .where(CloudResource.project_id == project_id)
            .order_by(CloudResource.detected_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def _upsert_findings(
        self,
        *,
        project_id: uuid.UUID,
        findings: list[GapFinding],
        evaluated_measures: set[str],
        report: DiagnosisReport,
    ) -> None:
        """UPSERT gaps · auto-resolve los que dejaron de emitir.

        Estrategia 1-row-per-(project_id, ens_measure_code): re-evaluación
        re-emite o auto-resuelve.
        """
        # Lookup gaps existing OPEN del project para auto-resolve / actualizar
        existing_q = await self.db.execute(
            select(CloudGap).where(
                and_(
                    CloudGap.project_id == project_id,
                    CloudGap.resolved_at.is_(None),
                ),
            )
        )
        existing_open: dict[str, CloudGap] = {
            g.ens_measure_code: g for g in existing_q.scalars().all()
        }

        emitted_codes = {f.ens_measure_code for f in findings}

        # UPSERT findings
        for finding in findings:
            existing = existing_open.get(finding.ens_measure_code)
            if existing is not None:
                # Update raw evidence + explanation (re-eval keep gap abierto)
                existing.severity = finding.severity
                existing.gap_type = finding.gap_type
                existing.title = finding.title
                existing.suggested_action = finding.suggested_action
                existing.explanation_es = self._render_explanation(finding)
                existing.estimated_effort_days = finding.estimated_effort_days
                existing.auto_fixable = finding.auto_fixable
                existing.cliente_can_see = finding.cliente_can_see
                existing.raw_evidence = finding.raw_evidence
                existing.detected_at = now_utc()
                report.gaps_updated += 1
            else:
                gap = CloudGap(
                    project_id=project_id,
                    gap_type=finding.gap_type,
                    severity=finding.severity,
                    ens_measure_code=finding.ens_measure_code,
                    title=finding.title,
                    suggested_action=finding.suggested_action,
                    explanation_es=self._render_explanation(finding),
                    estimated_effort_days=finding.estimated_effort_days,
                    auto_fixable=finding.auto_fixable,
                    cliente_can_see=finding.cliente_can_see,
                    raw_evidence=finding.raw_evidence,
                )
                self.db.add(gap)
                report.gaps_created += 1

        # Auto-resolve: gaps existing de medidas evaluadas que ya NO emiten
        for code, gap in existing_open.items():
            if code in evaluated_measures and code not in emitted_codes:
                gap.resolved_at = now_utc()
                gap.resolution_note = (
                    "Auto-resuelto · re-diagnóstico no detectó el hallazgo."
                )
                report.gaps_resolved += 1

        await self.db.flush()

    def _render_explanation(self, finding: GapFinding) -> str:
        """Renderiza template con placeholders desde raw_evidence.

        Deterministic Python formatting · NO LLM (R1 sostener).
        LLM enrichment SOLO se ejecuta por petición explícita admin
        (endpoint dedicado o copilot interaction · NO en pipeline base).
        """
        ev = finding.raw_evidence or {}
        # FIX: construir UN solo dict de kwargs. Antes se hacía
        # ``.format(**ev, n_privileged=..., n_total=..., pct_privileged=...)``;
        # como el raw_evidence de op.acc.2 YA contiene n_privileged/n_total/
        # pct_privileged, str.format() recibía el kwarg DUPLICADO →
        # TypeError NO capturado (el except solo cubría KeyError/IndexError/
        # ValueError) → CRASH de todo el pipeline de diagnóstico cloud al
        # detectar exceso de usuarios privilegiados. Merge con override + se
        # añade TypeError al fallback.
        fmt_kwargs = {
            **ev,
            "n_users_no_mfa": ev.get("users_no_mfa_count", 0),
            "n_privileged": ev.get("n_privileged", 0),
            "n_total": ev.get("n_total", 0),
            "pct_privileged": ev.get("pct_privileged", 0.0),
            "n_storage_unencrypted": ev.get("storage_unencrypted_count", 0),
            "n_public_buckets": ev.get("public_buckets_count", 0),
        }
        try:
            return finding.explanation_es_template.format(**fmt_kwargs)
        except (KeyError, IndexError, ValueError, TypeError):
            # Fallback al template sin formatear (no rompe pipeline)
            return finding.explanation_es_template
