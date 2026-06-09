"""ConformityReadinessService · valida pre-firma conformidad ENS.

SAN-E v3.MB-5.6.C · audit-driven NEW service.

Joins signing_events por project_id · verifica DdA + MAGERIT + Pentest firmados.
Validators adicionales: evidencias 73 medidas (M07) · politicas (M06) segun tier.

Used por portal_api · cliente VE estado pre-firma · firma blocked si NO ready.
Snapshot persistido en BasicDeclarationRow.readiness_snapshot_jsonb al firmar
(audit trail compliance ENAC).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import and_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Project
from backend.app.models.documents import Evidence
from backend.app.motors.m05_signing.models import SigningEvent, SigningIntent


# Tier → min evidence count heuristica audit ENAC.
# BASICA · 25 evidencias (subset 73 medidas)
# MEDIA · 50 evidencias
# ALTA · 73 evidencias (full Anexo II)
_TIER_MIN_EVIDENCE: dict[str, int] = {
    "BASICA": 25,
    "MEDIA": 50,
    "ALTA": 73,
}

# Tier → min politicas linkadas a bulk signing_intent (Q1.C híbrida MB-6 atom 1)
# Pattern: 1 firma bulk única linkea TODOS documents tier-aware (BASICA 10 / MEDIA 18 / ALTA 25).
# El conteo es de Document.client_signing_intent_id NOT NULL (linked post-firma bulk).
# Pre-MB-6 atom 1 estos valores eran (0,0,8) basados en heuristica individual policy_approval.
# Actualizado audit-driven Q2.b · chain orden Q4.A pre-pentest.
_TIER_MIN_POLICIES: dict[str, int] = {
    "BASICA": 10,
    "MEDIA": 18,
    "ALTA": 25,
}


@dataclass(slots=True)
class ConformityReadinessSnapshot:
    """Snapshot estado pre-firma conformidad · audit trail."""

    tier: str
    dda_signed_at: datetime | None = None
    dda_signature_id: uuid.UUID | None = None
    magerit_signed_at: datetime | None = None
    magerit_signature_id: uuid.UUID | None = None
    pentest_signed_at: datetime | None = None
    pentest_signature_id: uuid.UUID | None = None
    evidence_count: int = 0
    policies_signed_count: int = 0
    ready_for_conformity_sign: bool = False
    blockers: list[str] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_jsonb(self) -> dict:
        """Serialize para readiness_snapshot_jsonb column."""
        return {
            "tier": self.tier,
            "dda_signed_at": self.dda_signed_at.isoformat() if self.dda_signed_at else None,
            "dda_signature_id": str(self.dda_signature_id) if self.dda_signature_id else None,
            "magerit_signed_at": self.magerit_signed_at.isoformat() if self.magerit_signed_at else None,
            "magerit_signature_id": str(self.magerit_signature_id) if self.magerit_signature_id else None,
            "pentest_signed_at": self.pentest_signed_at.isoformat() if self.pentest_signed_at else None,
            "pentest_signature_id": str(self.pentest_signature_id) if self.pentest_signature_id else None,
            "evidence_count": self.evidence_count,
            "policies_signed_count": self.policies_signed_count,
            "ready_for_conformity_sign": self.ready_for_conformity_sign,
            "blockers": list(self.blockers),
            "captured_at": self.captured_at.isoformat(),
        }


async def _get_latest_signature(
    db: AsyncSession,
    project_id: uuid.UUID,
    signable_type: str,
) -> SigningEvent | None:
    """Latest signature_generated event for signable_type."""
    stmt = (
        select(SigningEvent)
        .join(SigningIntent, SigningIntent.id == SigningEvent.signing_intent_id)
        .where(
            and_(
                SigningIntent.project_id == project_id,
                SigningIntent.signable_type == signable_type,
                SigningEvent.event_type == "signature_generated",
            )
        )
        .order_by(SigningEvent.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _count_evidences_for_project(
    db: AsyncSession, project_id: uuid.UUID,
) -> int:
    """Count evidence rows vigente=true para el project."""
    row = await db.execute(
        select(sa_text("count(*)"))
        .select_from(Evidence)
        .where(
            and_(
                Evidence.project_id == project_id,
                Evidence.vigente.is_(True),
                Evidence.deleted_at.is_(None),
            )
        )
    )
    return int(row.scalar() or 0)


async def _count_signed_policies_for_project(
    db: AsyncSession, project_id: uuid.UUID,
) -> int:
    """Count documents (policies) linked a bulk signing_intent firmada.

    SAN-E v3.MB-6 atom 1 · Q1.C híbrida: 1 firma bulk única linkea TODOS documents
    via documents.client_signing_intent_id. Count = nº documents con intent_id NOT NULL
    cuyo signing_intent tiene status='signed'.

    Pre-MB-6 atom 1 contaba signing_intents individuales (assumed 1 per policy) ·
    actualizado para reflejar workflow bulk única (audit ENAC + UX Marcos decisión).
    """
    row = await db.execute(
        sa_text(
            "SELECT count(*) FROM documents d "
            "JOIN signing_intents si ON si.id = d.client_signing_intent_id "
            "WHERE d.project_id = :pid "
            "AND si.signable_type = 'policy_approval' "
            "AND si.status = 'signed' "
            "AND d.deleted_at IS NULL"
        ),
        {"pid": str(project_id)},
    )
    return int(row.scalar() or 0)


async def _get_project_tier(
    db: AsyncSession, project_id: uuid.UUID,
) -> str:
    """Read project.categoria_objetivo · BASICA/MEDIA/ALTA · default BASICA."""
    row = await db.execute(
        select(Project.categoria_objetivo).where(Project.id == project_id)
    )
    cat = row.scalar_one_or_none()
    if cat in ("BASICA", "MEDIA", "ALTA"):
        return cat
    return "BASICA"


async def compute_readiness(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> ConformityReadinessSnapshot:
    """Aggregates signing chain + state validation pre-conformidad.

    Returns snapshot · blockers list · ready_for_conformity_sign bool.
    """
    tier = await _get_project_tier(db, project_id)

    dda_sig = await _get_latest_signature(db, project_id, "dda")
    magerit_sig = await _get_latest_signature(db, project_id, "magerit_validation")
    pentest_sig = await _get_latest_signature(db, project_id, "pentest_authorization")

    evidence_count = await _count_evidences_for_project(db, project_id)
    policies_count = await _count_signed_policies_for_project(db, project_id)

    blockers: list[str] = []
    if dda_sig is None:
        blockers.append(
            "DdA NO firmada · revisa 73 medidas y firma en /client-portal/dda"
        )
    if magerit_sig is None:
        blockers.append(
            "MAGERIT NO validado · revisa inventario activos y firma en /client-portal/magerit"
        )
    # #15 Ola 7 · el pentest es obligatorio SOLO en ALTA (CCN-STIC 105/140).
    # En MEDIA es opcional (sin opt-in explícito no es gate) y en BÁSICA nunca
    # aplica (autodeclaración). Sin esta guarda, un Básica jamás llegaba a
    # ready_for_conformity_sign (el blocker se añadía sin mirar el tier).
    if tier == "ALTA" and pentest_sig is None:
        blockers.append(
            "Autorizacion pentest NO firmada · revisa ventana y autoriza en /client-portal/pentest-authorization"
        )

    min_evidence = _TIER_MIN_EVIDENCE.get(tier, _TIER_MIN_EVIDENCE["BASICA"])
    if evidence_count < min_evidence:
        blockers.append(
            f"Evidencias insuficientes ({evidence_count}/{min_evidence} minimo {tier})"
        )

    min_policies = _TIER_MIN_POLICIES.get(tier, 0)
    if min_policies > 0 and policies_count < min_policies:
        blockers.append(
            f"Politicas NO firmadas ({policies_count}/{min_policies} {tier}) · "
            f"revisa y firma en /client-portal/policies"
        )

    return ConformityReadinessSnapshot(
        tier=tier,
        dda_signed_at=dda_sig.created_at if dda_sig else None,
        dda_signature_id=dda_sig.id if dda_sig else None,
        magerit_signed_at=magerit_sig.created_at if magerit_sig else None,
        magerit_signature_id=magerit_sig.id if magerit_sig else None,
        pentest_signed_at=pentest_sig.created_at if pentest_sig else None,
        pentest_signature_id=pentest_sig.id if pentest_sig else None,
        evidence_count=evidence_count,
        policies_signed_count=policies_count,
        ready_for_conformity_sign=(len(blockers) == 0),
        blockers=blockers,
    )


def tier_min_evidence_count(tier: str) -> int:
    """Public · minimum evidence count per tier."""
    return _TIER_MIN_EVIDENCE.get(tier, _TIER_MIN_EVIDENCE["BASICA"])


def tier_min_policies_count(tier: str) -> int:
    """Public · minimum politicas firmadas per tier."""
    return _TIER_MIN_POLICIES.get(tier, 0)
