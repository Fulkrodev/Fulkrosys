"""DPC anual service · SAN-E v3.MB-6 atom 2.

Declaración Protección Continuidad (DPC) anual · art.25 RD 311/2022 · CCN-STIC 806.

Workflow Q1.A anniversary-based:
  1. Celery task daily 08:30 escanea conformidad inicial firmadas
  2. 30 días antes anniversary_date (signed_at + 12m) crea DPC draft idempotent
  3. AlertService trigger category 'dpc_due' · cliente recibe alert inbox
  4. Cliente abre /client-portal/dpc-anual · revisa 4 secciones contexto
  5. Firma única OTP step-up · linked Conformidad parent via readiness_snapshot

Q2.A · 1 firma única por año (UNIQUE partial constraint).
Q3.A · 4 secciones contexto: SLA + Recuperación + Incidents + Roadmap.
Q5.A · TODOS tiers (BASICA + MEDIA + ALTA).

Pattern ClientReviewMixinB 5ª aplicación + BasicDeclarationRow reuse.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.conformity_lifecycle import BasicDeclarationRow


# ════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════

DPC_DECLARATION_TYPE = "dpc_anual"

# Cuántos días antes del anniversary_date el Celery task crea draft + alert
ALERT_LEAD_DAYS = 30

# Cuántos días antes del anniversary_date severity escala critical
CRITICAL_LEAD_DAYS = 7

VALID_REVIEW_STATUS: frozenset[str] = frozenset({
    "revisada_ok",
    "con_pregunta",
    "suggest_change",
})


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class DpcAnualError(Exception):
    """Base error DPC anual service."""


class ConformidadNotSignedError(DpcAnualError):
    """Project NO tiene conformidad inicial firmada · pre-requisito DPC."""


class DpcDeclarationNotFoundError(DpcAnualError):
    """DPC declaration row no existe."""


class InvalidReviewActionError(DpcAnualError):
    """Action review inválido."""


class DpcAlreadySignedError(DpcAnualError):
    """DPC anniversary_year ya firmado."""


# ════════════════════════════════════════════════════════════════════
# Data transfer objects
# ════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DpcContextSnapshot:
    """4 secciones contexto pre-firma cliente (Q3.A)."""

    sla_section: dict
    recovery_section: dict
    incidents_section: dict
    roadmap_section: dict


@dataclass(frozen=True)
class DpcDeclarationView:
    """Vista cliente single DPC anual declaration.

    BasicDeclarationRow usa ClientReviewMixinB · client_concerns_note + reviewed_at
    + signing_intent_id (NO client_review_status enum · pattern B sin status).
    """

    id: uuid.UUID
    project_id: uuid.UUID
    anniversary_year: int
    status: str
    client_concerns_note: str | None
    client_reviewed_at: datetime | None
    client_signing_intent_id: uuid.UUID | None
    signed_at: datetime | None
    conformidad_signature_id: str | None  # FK lógica via readiness_snapshot
    created_at: datetime
    anniversary_date: date  # signed_at conformidad + 12m * anniversary_year_offset
    days_until_anniversary: int | None


# ════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════


class DpcAnualService:
    """Service DPC anual cliente workflow."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Anniversary calculation
    # ----------------------------------------------------------------

    async def get_conformidad_initial_signed_at(
        self, project_id: uuid.UUID,
    ) -> tuple[datetime, uuid.UUID] | None:
        """Returns (signed_at, declaration_id) de conformidad inicial firmada.

        Conformidad inicial = declaration_type IN ('initial', 'commitment_pre_certification')
        + signed_at IS NOT NULL.
        Toma la MÁS ANTIGUA (anniversary base date · Q1.A).
        """
        row = await self.db.execute(
            sa_text(
                "SELECT signed_at, id FROM basic_declarations "
                "WHERE project_id = :pid "
                "AND declaration_type IN ('initial', 'commitment_pre_certification') "
                "AND signed_at IS NOT NULL "
                "ORDER BY signed_at ASC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )
        hit = row.first()
        if hit is None:
            return None
        return hit[0], hit[1]

    def compute_anniversary_date(
        self, conformidad_signed_at: datetime, year_offset: int,
    ) -> date:
        """signed_at + (12 * year_offset) meses (Q1.A anniversary-based)."""
        target = conformidad_signed_at.date().replace(
            year=conformidad_signed_at.date().year + year_offset
        )
        return target

    # ----------------------------------------------------------------
    # Draft creation (idempotent)
    # ----------------------------------------------------------------

    async def create_dpc_anual_draft(
        self,
        project_id: uuid.UUID,
        anniversary_year: int,
    ) -> BasicDeclarationRow:
        """Crea DPC anual draft idempotent · skip si existe (UNIQUE partial).

        anniversary_year es el AÑO CALENDARIO del aniversario
        (ej. conformidad firmada 2026-05-01 → anniversary_year=2027 para primera DPC).
        """
        # Pre-requisito · conformidad inicial debe estar firmada
        conformidad = await self.get_conformidad_initial_signed_at(project_id)
        if conformidad is None:
            raise ConformidadNotSignedError(
                f"Project {project_id} NO tiene conformidad inicial firmada · "
                "DPC anual requiere art.25 RD 311/2022 conformidad pre-existente"
            )
        conformidad_signed_at, conformidad_id = conformidad

        # Idempotent check
        existing = await self.db.execute(
            sa_text(
                "SELECT id FROM basic_declarations "
                "WHERE project_id = :pid "
                "AND declaration_type = 'dpc_anual' "
                "AND anniversary_year = :year"
            ),
            {"pid": str(project_id), "year": anniversary_year},
        )
        hit = existing.first()
        if hit is not None:
            existing_doc = await self.db.get(BasicDeclarationRow, hit[0])
            return existing_doc  # type: ignore[return-value]

        # Capture context snapshot (Q3.A 4 secciones)
        context = await self.aggregate_dpc_context_snapshot(project_id)
        readiness_jsonb = {
            "conformidad_signature_id": str(conformidad_id),
            "conformidad_signed_at": conformidad_signed_at.isoformat(),
            "anniversary_year": anniversary_year,
            "captured_at": datetime.now(UTC).isoformat(),
            "sla_section": context.sla_section,
            "recovery_section": context.recovery_section,
            "incidents_section": context.incidents_section,
            "roadmap_section": context.roadmap_section,
        }

        decl_id = uuid.uuid4()
        await self.db.execute(
            sa_text(
                "INSERT INTO basic_declarations "
                "(id, project_id, declaration_type, anniversary_year, "
                " status, readiness_snapshot_jsonb, created_at) "
                "VALUES (:id, :pid, 'dpc_anual', :year, 'draft', "
                " CAST(:snap AS jsonb), now())"
            ),
            {
                "id": str(decl_id),
                "pid": str(project_id),
                "year": anniversary_year,
                "snap": _jsonify(readiness_jsonb),
            },
        )
        await self.db.flush()
        decl = await self.db.get(BasicDeclarationRow, decl_id)
        assert decl is not None
        return decl

    # ----------------------------------------------------------------
    # Context aggregation (4 secciones · Q3.A)
    # ----------------------------------------------------------------

    async def aggregate_dpc_context_snapshot(
        self, project_id: uuid.UUID,
    ) -> DpcContextSnapshot:
        """Aggregate SLA + Recovery + Incidents + Roadmap last 12 months.

        Q3.A · cliente firma con contexto completo audit ENAC compliance.
        Aggregator lightweight · counters + summaries (NO full data dump).
        """
        twelve_months_ago = datetime.now(UTC) - timedelta(days=365)

        # SLA section · M19 BIA + M23 retainer SLA fields
        sla_row = await self.db.execute(
            sa_text(
                "SELECT count(*) AS bia_count, "
                "max(updated_at) AS last_bia_update "
                "FROM bia_analyses "
                "WHERE project_id = :pid"
            ),
            {"pid": str(project_id)},
        )
        sla_hit = sla_row.first()
        sla_section = {
            "bia_analyses_count": int(sla_hit[0] or 0) if sla_hit else 0,
            "last_bia_update": (
                sla_hit[1].isoformat() if sla_hit and sla_hit[1] else None
            ),
            "uptime_committed_pct": 99.5,  # default · placeholder M23 retainer SLA
        }

        # Recovery section · M26 backup + M25 lifecycle
        # Note: backup_jobs no tiene project_id (es global cluster) · count total
        recovery_row = await self.db.execute(
            sa_text(
                "SELECT count(*) AS backup_jobs_count, "
                "max(created_at) AS last_backup "
                "FROM backup_jobs"
            )
        )
        recovery_hit = recovery_row.first()
        recovery_section = {
            "backup_jobs_last_12m": int(recovery_hit[0] or 0) if recovery_hit else 0,
            "last_backup_at": (
                recovery_hit[1].isoformat()
                if recovery_hit and recovery_hit[1] else None
            ),
            "rto_documented_hours": 24,
            "rpo_documented_hours": 4,
        }

        # Incidents section · M19 incidents últimos 12m
        incidents_row = await self.db.execute(
            sa_text(
                "SELECT severidad, count(*) FROM incidents "
                "WHERE project_id = :pid "
                "AND fecha >= :since "
                "AND deleted_at IS NULL "
                "GROUP BY severidad"
            ),
            {"pid": str(project_id), "since": twelve_months_ago},
        )
        severity_histogram: dict[str, int] = {}
        total_incidents = 0
        for sev, cnt in incidents_row:
            severity_histogram[sev or "unknown"] = int(cnt)
            total_incidents += int(cnt)
        incidents_section = {
            "total_incidents_last_12m": total_incidents,
            "severity_histogram": severity_histogram,
            "lessons_learned_count": 0,  # placeholder · M19 lessons_learned TBD
        }

        # Roadmap section · M28 change_governance + M07 evidence recientes
        roadmap_row = await self.db.execute(
            sa_text(
                "SELECT count(*) FROM evidence "
                "WHERE project_id = :pid "
                "AND created_at >= :since "
                "AND deleted_at IS NULL"
            ),
            {"pid": str(project_id), "since": twelve_months_ago},
        )
        roadmap_hit = roadmap_row.first()
        roadmap_section = {
            "new_evidences_last_12m": int(roadmap_hit[0] or 0) if roadmap_hit else 0,
            "improvements_planned_next_year": [],
        }

        return DpcContextSnapshot(
            sla_section=sla_section,
            recovery_section=recovery_section,
            incidents_section=incidents_section,
            roadmap_section=roadmap_section,
        )

    # ----------------------------------------------------------------
    # List / detail
    # ----------------------------------------------------------------

    async def list_declarations_for_project(
        self, project_id: uuid.UUID,
    ) -> list[DpcDeclarationView]:
        """Lista DPC anual declarations project (current + history)."""
        conformidad = await self.get_conformidad_initial_signed_at(project_id)
        rows = await self.db.execute(
            sa_text(
                "SELECT id, project_id, anniversary_year, status, "
                "client_concerns_note, "
                "client_reviewed_at, client_signing_intent_id, "
                "signed_at, readiness_snapshot_jsonb, created_at "
                "FROM basic_declarations "
                "WHERE project_id = :pid AND declaration_type = 'dpc_anual' "
                "ORDER BY anniversary_year DESC"
            ),
            {"pid": str(project_id)},
        )
        result: list[DpcDeclarationView] = []
        for r in rows:
            anniversary_date = self._anniversary_date_from_year(
                conformidad, r[2],
            )
            days_until = (
                (anniversary_date - date.today()).days
                if anniversary_date else None
            )
            readiness = r[8] or {}
            conformidad_sig = readiness.get("conformidad_signature_id")
            result.append(DpcDeclarationView(
                id=r[0],
                project_id=r[1],
                anniversary_year=r[2],
                status=r[3] or "draft",
                client_concerns_note=r[4],
                client_reviewed_at=r[5],
                client_signing_intent_id=r[6],
                signed_at=r[7],
                conformidad_signature_id=conformidad_sig,
                created_at=r[9],
                anniversary_date=anniversary_date or date.today(),
                days_until_anniversary=days_until,
            ))
        return result

    def _anniversary_date_from_year(
        self,
        conformidad: tuple[datetime, uuid.UUID] | None,
        anniversary_year: int,
    ) -> date | None:
        if conformidad is None:
            return None
        conformidad_signed_at = conformidad[0]
        year_offset = anniversary_year - conformidad_signed_at.year
        if year_offset <= 0:
            return None
        return self.compute_anniversary_date(conformidad_signed_at, year_offset)

    # ----------------------------------------------------------------
    # Review action
    # ----------------------------------------------------------------

    async def mark_dpc_reviewed(
        self,
        declaration_id: uuid.UUID,
        action: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> BasicDeclarationRow:
        """Cliente review action · revisada_ok / con_pregunta / suggest_change."""
        if action not in VALID_REVIEW_STATUS:
            raise InvalidReviewActionError(
                f"action '{action}' inválido · esperado "
                f"{sorted(VALID_REVIEW_STATUS)}"
            )
        if action in {"con_pregunta", "suggest_change"} and not (note or "").strip():
            raise InvalidReviewActionError(
                f"action '{action}' requiere note no vacía"
            )

        decl = await self.db.get(BasicDeclarationRow, declaration_id)
        if decl is None or decl.declaration_type != "dpc_anual":
            raise DpcDeclarationNotFoundError(
                f"DPC declaration {declaration_id} no existe"
            )

        # Pattern B usa concerns_note (no review_status) · adaptamos a nuestro caso
        # · status NO existe en MixinB · usamos client_concerns_note + reviewed_at
        decl.client_concerns_note = (note or "").strip() or None
        decl.client_reviewed_at = datetime.now(UTC)
        decl.client_reviewed_by_user_id = user_id
        await self.db.flush()
        return decl

    # ----------------------------------------------------------------
    # Document hash · canonical bulk para firma
    # ----------------------------------------------------------------

    async def compute_dpc_document_hash(
        self,
        declaration_id: uuid.UUID,
    ) -> tuple[str, int]:
        """SHA256 deterministic hash DPC declaration state · input firma M05."""
        decl = await self.db.get(BasicDeclarationRow, declaration_id)
        if decl is None or decl.declaration_type != "dpc_anual":
            raise DpcDeclarationNotFoundError(
                f"DPC declaration {declaration_id} no existe"
            )

        readiness = decl.readiness_snapshot_jsonb or {}
        canonical_parts: list[str] = [
            f"project_id:{decl.project_id}",
            "declaration_type:dpc_anual",
            f"anniversary_year:{decl.anniversary_year}",
            f"conformidad_signature_id:{readiness.get('conformidad_signature_id', '')}",
            f"sla_bia_count:{readiness.get('sla_section', {}).get('bia_analyses_count', 0)}",
            f"recovery_backup_count:{readiness.get('recovery_section', {}).get('backup_jobs_last_12m', 0)}",
            f"incidents_total:{readiness.get('incidents_section', {}).get('total_incidents_last_12m', 0)}",
            f"roadmap_new_evidences:{readiness.get('roadmap_section', {}).get('new_evidences_last_12m', 0)}",
            f"client_reviewed_at:{decl.client_reviewed_at.isoformat() if decl.client_reviewed_at else ''}",
        ]
        canonical = "\n".join(canonical_parts)
        document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return document_hash, len(canonical)

    # ----------------------------------------------------------------
    # Finalize signoff
    # ----------------------------------------------------------------

    async def process_dpc_signoff(
        self,
        declaration_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
    ) -> BasicDeclarationRow:
        """Marca DPC anual signed post-firma M05 · link signing_intent_id."""
        decl = await self.db.get(BasicDeclarationRow, declaration_id)
        if decl is None or decl.declaration_type != "dpc_anual":
            raise DpcDeclarationNotFoundError(
                f"DPC declaration {declaration_id} no existe"
            )
        if decl.signed_at is not None:
            raise DpcAlreadySignedError(
                f"DPC anniversary_year {decl.anniversary_year} ya firmado"
            )

        decl.client_signing_intent_id = signing_intent_id
        decl.signed_at = datetime.now(UTC)
        decl.status = "signed"

        # Compute signed_hash (input firma · audit trail)
        doc_hash, _ = await self.compute_dpc_document_hash(declaration_id)
        decl.signed_hash = doc_hash

        await self.db.flush()
        return decl


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


def _jsonify(d: dict) -> str:
    """Serialize dict to JSON string for SQL CAST AS jsonb."""
    import json
    return json.dumps(d, default=str)
