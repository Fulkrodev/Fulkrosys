"""Retainer quarterly checkin service · SAN-E v3.MB-6 atom 4.

Trimestral uniforme workflow (Q1+Q4 cement):
  draft (auto-generated Celery) → curated_by_admin (Marcos curates) →
  sent_to_client (Marcos sends) → reviewed (cliente MixinA) → signed (firma)

Cross-motor KPI aggregation cement schema v1.0 (Consideration C):
  - actividades · M23 retainer_activities (3 estados counts)
  - incidents · M19 incidents (detected · resolved · ccn_cert_routed)
  - vulnerabilidades · M07 vulnerabilities (critical · high · medium · mitigated)
  - rag_overall · computed (green/amber/red)
  - bonus stakeholder_changes · M30 client_contact_interactions
  - bonus evidence_freshness · M07 evidence (fresh/stale/expired)

Q5 empty state · si NO retainer activo · empty list + portal redirect retainer_offer.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.retainer import RetainerQuarterlyReport


# ════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════

SCHEMA_VERSION = "1.0"

ADMIN_CURATION_STATUSES: tuple[str, ...] = (
    "draft",
    "curated_by_admin",
    "sent_to_client",
)

CLIENT_FACING_REVIEW_STATUS: frozenset[str] = frozenset({
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
})


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class RetainerCheckinError(Exception):
    """Base error retainer checkin service."""


class NoActiveRetainerError(RetainerCheckinError):
    """Project NO tiene retainer activo · pre-requisito checkin."""


class CheckinReportNotFoundError(RetainerCheckinError):
    """Quarterly report no existe."""


class InvalidWorkflowTransitionError(RetainerCheckinError):
    """Transition admin_curation_status inválida."""


class CheckinAlreadySignedError(RetainerCheckinError):
    """Checkin ya firmado · NO modificable."""


class InvalidReviewActionError(RetainerCheckinError):
    """Action review inválido."""


# ════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════


def compute_quarter_label(d: date) -> str:
    """Returns 'YYYY-QN' format (e.g., 2026-Q2 para April-June 2026)."""
    quarter = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{quarter}"


def quarter_bounds(period_quarter: str) -> tuple[date, date]:
    """Returns (period_start, period_end) for 'YYYY-QN' label."""
    year, qn = period_quarter.split("-Q")
    year_int = int(year)
    quarter = int(qn)
    start_month = (quarter - 1) * 3 + 1
    period_start = date(year_int, start_month, 1)
    end_month = start_month + 2
    if end_month == 12:
        period_end = date(year_int, 12, 31)
    else:
        period_end = date(year_int, end_month + 1, 1) - timedelta(days=1)
    return period_start, period_end


class RetainerCheckinService:
    """Service retainer quarterly checkin workflow."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Active retainer resolution
    # ----------------------------------------------------------------

    async def get_active_retainer(
        self, project_id: uuid.UUID,
    ) -> tuple[uuid.UUID, str] | None:
        """Returns (retainer_contract_id, perfil) si project tiene retainer activo."""
        row = await self.db.execute(
            sa_text(
                "SELECT id, perfil FROM retainer_contracts "
                "WHERE project_id = :pid AND estado = 'active' "
                "AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        hit = row.first()
        if hit is None:
            return None
        return hit[0], hit[1]

    # ----------------------------------------------------------------
    # Cross-motor aggregation (schema v1.0)
    # ----------------------------------------------------------------

    async def aggregate_quarter_data(
        self,
        project_id: uuid.UUID,
        period_start: date,
        period_end: date,
    ) -> dict:
        """5 secciones core + 2 bonus · cement schema v1.0.

        Lightweight aggregator · counters + summaries (NO full data dump).
        """
        # 1. Actividades retainer
        act_row = await self.db.execute(
            sa_text(
                "SELECT estado, count(*) FROM retainer_activities ra "
                "WHERE ra.project_id = :pid "
                "AND ra.fecha_programada BETWEEN :start AND :end "
                "AND ra.deleted_at IS NULL "
                "GROUP BY estado"
            ),
            {"pid": str(project_id), "start": period_start, "end": period_end},
        )
        activities = {"completed": 0, "pending": 0, "overdue": 0, "total": 0}
        # FIX(enum-drift): RetainerActivity.estado se persiste en ESPAÑOL
        # (programada/en_curso/completada/cancelada/vencida · models/retainer.py).
        # Antes se comparaba contra literales en inglés → activities_* SIEMPRE 0 y
        # RAG verde fabricado. 'cancelada' cuenta en total pero en ningún bucket.
        for estado, cnt in act_row:
            count = int(cnt)
            activities["total"] += count
            if estado in ("completada", "completed"):
                activities["completed"] += count
            elif estado in ("programada", "en_curso", "scheduled",
                            "in_progress", "pending"):
                activities["pending"] += count
            elif estado in ("vencida", "overdue", "delayed"):
                activities["overdue"] += count

        # 2. Incidents (M19)
        inc_row = await self.db.execute(
            sa_text(
                "SELECT count(*) FILTER (WHERE workflow_state IN "
                "  ('resolved','closed')) AS resolved, "
                "count(*) AS detected, "
                "count(*) FILTER (WHERE notificado_lucia = true) AS ccn_cert_routed "
                "FROM incidents WHERE project_id = :pid "
                "AND fecha BETWEEN :start AND :end "
                "AND deleted_at IS NULL"
            ),
            {"pid": str(project_id), "start": period_start, "end": period_end},
        )
        inc_hit = inc_row.first()
        incidents = {
            "detected": int(inc_hit[1] or 0) if inc_hit else 0,
            "resolved": int(inc_hit[0] or 0) if inc_hit else 0,
            "ccn_cert_routed": int(inc_hit[2] or 0) if inc_hit else 0,
        }

        # 3. Vulnerabilidades (M07)
        vuln_row = await self.db.execute(
            sa_text(
                "SELECT severidad, count(*), "
                "count(*) FILTER (WHERE estado IN ('resolved','mitigated')) "
                "FROM vulnerabilities "
                "WHERE project_id = :pid "
                "AND fecha_deteccion BETWEEN :start AND :end "
                "AND deleted_at IS NULL "
                "GROUP BY severidad"
            ),
            {"pid": str(project_id), "start": period_start, "end": period_end},
        )
        vulnerabilidades: dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0, "mitigated": 0,
        }
        for sev, total, mitig in vuln_row:
            sev_key = (sev or "low").lower()
            if sev_key in vulnerabilidades:
                vulnerabilidades[sev_key] += int(total)
            vulnerabilidades["mitigated"] += int(mitig or 0)

        # 4. Normativa changes (M10) · counters only (lightweight)
        try:
            norm_row = await self.db.execute(
                sa_text(
                    "SELECT count(*) FROM normativa_alerts "
                    "WHERE created_at BETWEEN :start AND :end"
                ),
                {"start": period_start, "end": period_end},
            )
            norm_count = int(norm_row.scalar() or 0)
        except Exception:
            norm_count = 0
        normativa_changes = {
            "relevant_count": norm_count,
            "summary": f"{norm_count} normativa alerts en trimestre",
        }

        # 5. RAG overall (computed)
        rag_overall = self._compute_rag(activities, incidents, vulnerabilidades)

        # Bonus M30 stakeholder changes (Q3-extra)
        try:
            stake_row = await self.db.execute(
                sa_text(
                    "SELECT count(*) FROM client_contact_interactions "
                    "WHERE created_at BETWEEN :start AND :end"
                ),
                {"start": period_start, "end": period_end},
            )
            stake_count = int(stake_row.scalar() or 0)
        except Exception:
            stake_count = 0
        stakeholder_changes = {
            "count": stake_count,
            "summary": f"{stake_count} interacciones stakeholders",
        }

        # Bonus M07 evidence freshness (Q3-extra)
        try:
            ev_row = await self.db.execute(
                sa_text(
                    "SELECT count(*) FILTER (WHERE vigente = true) AS fresh, "
                    "count(*) FILTER (WHERE vigente = false) AS stale "
                    "FROM evidence WHERE project_id = :pid "
                    "AND deleted_at IS NULL"
                ),
                {"pid": str(project_id)},
            )
            ev_hit = ev_row.first()
            evidence_freshness = {
                "fresh": int(ev_hit[0] or 0) if ev_hit else 0,
                "stale": int(ev_hit[1] or 0) if ev_hit else 0,
            }
        except Exception:
            evidence_freshness = {"fresh": 0, "stale": 0}

        return {
            "schema_version": SCHEMA_VERSION,
            "actividades": activities,
            "incidents": incidents,
            "vulnerabilidades": vulnerabilidades,
            "normativa_changes": normativa_changes,
            "rag_overall": rag_overall,
            "stakeholder_changes": stakeholder_changes,
            "evidence_freshness": evidence_freshness,
            "captured_at": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def _compute_rag(
        activities: dict, incidents: dict, vulns: dict,
    ) -> str:
        """Computed RAG overall · green/amber/red."""
        if vulns.get("critical", 0) > 0:
            return "red"
        if incidents.get("detected", 0) - incidents.get("resolved", 0) > 0:
            return "red"
        if activities.get("overdue", 0) > 0:
            return "amber"
        if vulns.get("high", 0) > 0:
            return "amber"
        return "green"

    # ----------------------------------------------------------------
    # Draft generation (Celery-callable)
    # ----------------------------------------------------------------

    async def generate_quarterly_report_draft(
        self,
        project_id: uuid.UUID,
        period_quarter: str | None = None,
    ) -> RetainerQuarterlyReport:
        """Idempotent draft creation per (project_id, period_quarter)."""
        retainer = await self.get_active_retainer(project_id)
        if retainer is None:
            raise NoActiveRetainerError(
                f"Project {project_id} sin retainer activo · "
                "pre-requisito generar checkin trimestral"
            )
        retainer_contract_id, _perfil = retainer

        if period_quarter is None:
            period_quarter = compute_quarter_label(date.today())

        period_start, period_end = quarter_bounds(period_quarter)

        # Idempotent check
        existing = await self.db.execute(
            sa_text(
                "SELECT id FROM retainer_quarterly_reports "
                "WHERE project_id = :pid AND period_quarter = :pq"
            ),
            {"pid": str(project_id), "pq": period_quarter},
        )
        hit = existing.first()
        if hit is not None:
            existing_doc = await self.db.get(RetainerQuarterlyReport, hit[0])
            assert existing_doc is not None
            return existing_doc

        # Cross-motor aggregation
        summary = await self.aggregate_quarter_data(
            project_id, period_start, period_end,
        )

        report_id = uuid.uuid4()
        await self.db.execute(
            sa_text(
                "INSERT INTO retainer_quarterly_reports "
                "(id, retainer_contract_id, project_id, period_type, "
                "period_start, period_end, period_quarter, "
                "activities_completed, activities_pending, activities_overdue, "
                "incidents_detected, normativa_changes_relevant, vulns_critical, "
                "rag_overall, summary_jsonb, admin_curation_status, "
                "schema_version, created_at, updated_at) "
                "VALUES (:id, :rcid, :pid, 'trimestral', :ps, :pe, :pq, "
                ":ac, :ap, :ao, :id_, :nc, :vc, :rag, "
                "CAST(:summary AS jsonb), 'draft', :sv, now(), now())"
            ),
            {
                "id": str(report_id),
                "rcid": str(retainer_contract_id),
                "pid": str(project_id),
                "ps": period_start,
                "pe": period_end,
                "pq": period_quarter,
                "ac": summary["actividades"]["completed"],
                "ap": summary["actividades"]["pending"],
                "ao": summary["actividades"]["overdue"],
                "id_": summary["incidents"]["detected"],
                "nc": summary["normativa_changes"]["relevant_count"],
                "vc": summary["vulnerabilidades"]["critical"],
                "rag": summary["rag_overall"],
                "summary": _jsonify(summary),
                "sv": SCHEMA_VERSION,
            },
        )
        await self.db.flush()
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        assert report is not None
        return report

    async def generate_annual_report_draft(
        self,
        project_id: uuid.UUID,
        year: int | None = None,
    ) -> RetainerQuarterlyReport:
        """#37 (FRENTE C) · informe ANUAL E-802 idempotente por (project_id, año).

        Mismo patrón que el trimestral (E-801 · ``generate_quarterly_report_draft``)
        pero ``period_type='anual'`` y bounds del año natural. Por defecto el año
        ANTERIOR (el beat lo dispara el 15 de enero). period_quarter usa la
        etiqueta ``YYYY-ANNUAL`` para la idempotencia (misma tabla).
        """
        retainer = await self.get_active_retainer(project_id)
        if retainer is None:
            raise NoActiveRetainerError(
                f"Project {project_id} sin retainer activo · "
                "pre-requisito generar informe anual"
            )
        retainer_contract_id, _perfil = retainer

        if year is None:
            year = date.today().year - 1
        period_label = f"{year}-AN"  # 7 chars · cabe en period_quarter VARCHAR(7)
        period_start = date(year, 1, 1)
        period_end = date(year, 12, 31)

        # Idempotente per (project_id, period_quarter)
        existing = await self.db.execute(
            sa_text(
                "SELECT id FROM retainer_quarterly_reports "
                "WHERE project_id = :pid AND period_quarter = :pq"
            ),
            {"pid": str(project_id), "pq": period_label},
        )
        hit = existing.first()
        if hit is not None:
            existing_doc = await self.db.get(RetainerQuarterlyReport, hit[0])
            assert existing_doc is not None
            return existing_doc

        summary = await self.aggregate_quarter_data(
            project_id, period_start, period_end,
        )

        report_id = uuid.uuid4()
        await self.db.execute(
            sa_text(
                "INSERT INTO retainer_quarterly_reports "
                "(id, retainer_contract_id, project_id, period_type, "
                "period_start, period_end, period_quarter, "
                "activities_completed, activities_pending, activities_overdue, "
                "incidents_detected, normativa_changes_relevant, vulns_critical, "
                "rag_overall, summary_jsonb, admin_curation_status, "
                "schema_version, created_at, updated_at) "
                "VALUES (:id, :rcid, :pid, 'anual', :ps, :pe, :pq, "
                ":ac, :ap, :ao, :id_, :nc, :vc, :rag, "
                "CAST(:summary AS jsonb), 'draft', :sv, now(), now())"
            ),
            {
                "id": str(report_id),
                "rcid": str(retainer_contract_id),
                "pid": str(project_id),
                "ps": period_start,
                "pe": period_end,
                "pq": period_label,
                "ac": summary["actividades"]["completed"],
                "ap": summary["actividades"]["pending"],
                "ao": summary["actividades"]["overdue"],
                "id_": summary["incidents"]["detected"],
                "nc": summary["normativa_changes"]["relevant_count"],
                "vc": summary["vulnerabilidades"]["critical"],
                "rag": summary["rag_overall"],
                "summary": _jsonify(summary),
                "sv": SCHEMA_VERSION,
            },
        )
        await self.db.flush()
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        assert report is not None
        return report

    # ----------------------------------------------------------------
    # Admin curation workflow
    # ----------------------------------------------------------------

    async def admin_curate_report(
        self,
        report_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        summary_edits: dict | None = None,
    ) -> RetainerQuarterlyReport:
        """Marcos admin curates auto-generated draft (Q4-extra obligatorio)."""
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        if report is None:
            raise CheckinReportNotFoundError(f"Report {report_id} no existe")
        if report.admin_curation_status != "draft":
            raise InvalidWorkflowTransitionError(
                f"Report status='{report.admin_curation_status}' · "
                f"esperado 'draft' para curate"
            )

        if summary_edits:
            current = dict(report.summary_jsonb or {})
            current.update(summary_edits)
            report.summary_jsonb = current

        report.admin_curation_status = "curated_by_admin"
        report.admin_curated_at = datetime.now(UTC)
        report.admin_curated_by_user_id = admin_user_id
        await self.db.flush()
        return report

    async def admin_send_to_client(
        self,
        report_id: uuid.UUID,
        admin_user_id: uuid.UUID,
    ) -> RetainerQuarterlyReport:
        """Marcos admin sends curated report to cliente."""
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        if report is None:
            raise CheckinReportNotFoundError(f"Report {report_id} no existe")
        if report.admin_curation_status != "curated_by_admin":
            raise InvalidWorkflowTransitionError(
                f"Report status='{report.admin_curation_status}' · "
                f"esperado 'curated_by_admin' para sent_to_client"
            )

        report.admin_curation_status = "sent_to_client"
        report.sent_at = datetime.now(UTC)
        await self.db.flush()
        return report

    # ----------------------------------------------------------------
    # Cliente review (MixinA · 8ª aplicación)
    # ----------------------------------------------------------------

    async def mark_client_review(
        self,
        report_id: uuid.UUID,
        action: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> RetainerQuarterlyReport:
        """Cliente review action · MixinA pattern."""
        if action not in CLIENT_FACING_REVIEW_STATUS:
            raise InvalidReviewActionError(
                f"action '{action}' inválido · esperado "
                f"{sorted(CLIENT_FACING_REVIEW_STATUS)}"
            )
        if action in {"con_pregunta", "suggest_change"} and not (note or "").strip():
            raise InvalidReviewActionError(
                f"action '{action}' requiere note no vacía"
            )

        report = await self.db.get(RetainerQuarterlyReport, report_id)
        if report is None:
            raise CheckinReportNotFoundError(f"Report {report_id} no existe")
        if report.admin_curation_status != "sent_to_client":
            raise RetainerCheckinError(
                f"Report status='{report.admin_curation_status}' · cliente NO "
                f"puede revisar hasta sent_to_client"
            )

        report.client_review_status = action
        report.client_review_note = (note or "").strip() or None
        report.client_reviewed_at = datetime.now(UTC)
        report.client_reviewed_by_user_id = user_id
        await self.db.flush()
        return report

    # ----------------------------------------------------------------
    # List for cliente
    # ----------------------------------------------------------------

    async def list_for_client(
        self, project_id: uuid.UUID,
    ) -> list[RetainerQuarterlyReport]:
        """Lista reports visible cliente (sent_to_client) · #34 GATE: solo si el
        proyecto está en lifecycle_state='RETAINER'. Un cliente que rechazó o
        terminó el retainer (ENDED_CHURN/ENDED_RENEWAL_OK/…) NO ve los reportes
        aunque conozca los IDs · la RLS por project_id sola no bastaba."""
        from backend.app.models.core import Project

        stmt = (
            select(RetainerQuarterlyReport)
            .join(Project, Project.id == RetainerQuarterlyReport.project_id)
            .where(
                and_(
                    RetainerQuarterlyReport.project_id == project_id,
                    RetainerQuarterlyReport.admin_curation_status == "sent_to_client",
                    RetainerQuarterlyReport.deleted_at.is_(None),
                    Project.lifecycle_state == "RETAINER",
                )
            )
            .order_by(RetainerQuarterlyReport.period_quarter.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # ----------------------------------------------------------------
    # Document hash + signoff
    # ----------------------------------------------------------------

    async def compute_signoff_hash(
        self, report_id: uuid.UUID,
    ) -> tuple[str, int]:
        """SHA256 canonical · input firma M05."""
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        if report is None:
            raise CheckinReportNotFoundError(f"Report {report_id} no existe")

        canonical_parts = [
            f"report_id:{report.id}",
            f"project_id:{report.project_id}",
            f"period_quarter:{report.period_quarter or ''}",
            f"schema_version:{report.schema_version}",
            f"activities_completed:{report.activities_completed}",
            f"activities_overdue:{report.activities_overdue}",
            f"incidents_detected:{report.incidents_detected}",
            f"vulns_critical:{report.vulns_critical}",
            f"rag_overall:{report.rag_overall or ''}",
            f"client_review_status:{report.client_review_status or 'pending'}",
        ]
        canonical = "\n".join(canonical_parts)
        document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return document_hash, len(canonical)

    async def process_quarterly_signoff(
        self,
        report_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
    ) -> RetainerQuarterlyReport:
        """Post-firma · link signing_intent_id."""
        report = await self.db.get(RetainerQuarterlyReport, report_id)
        if report is None:
            raise CheckinReportNotFoundError(f"Report {report_id} no existe")
        if report.client_signing_intent_id is not None:
            raise CheckinAlreadySignedError(
                f"Report {report_id} ya firmado"
            )

        report.client_signing_intent_id = signing_intent_id
        await self.db.flush()

        # MB-6 atom 8 · post-signoff hook cross-motor
        try:
            from backend.app.notifications.post_signoff_hooks import (
                post_signoff_retainer_quarterly,
            )
            await post_signoff_retainer_quarterly(self.db, report=report)
        except Exception:
            pass  # silent fail

        return report


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _jsonify(d: dict) -> str:
    import json
    return json.dumps(d, default=str)
