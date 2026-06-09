"""Control Status compute · CLUSTER 3 Phase 3B false-green prevention.

Sesión 3B-2B.8 CLUSTER 3 Phase 3B · canonical deterministic compute function
para prevenir false-green semaforos en dashboard control compliance.

R1 sostained: pure functional · NO LLM · NO HTTP · NO side-effects · NO mutations.
Returns ControlStatusResult dataclass · deterministic.

Anti-false-green logic: verde SOLO si TODOS pre-requisitos cumplen:
  1. ≥1 documento aplicable (vía control_id OR measure_code)
  2. TODOS documents aplicables estado='approved' + approved_at NOT NULL
  3. TODOS documents aplicables con cliente review (niveles 1-2) tienen
     client_review_status='revisada_ok'
  4. TODOS documents con signing_intent linked tienen status='signed'
  5. NO documents expired (expires_at > NOW())

Si CUALQUIER falla → semaforo='amarillo' o 'rojo' con missing_reasons explicit.

Filosofía cliente-mínimo: cliente RECIBE missing_reasons R29 friendly
traducidos · admin RECIBE technical detail.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.documents import Document, Evidence


Semaforo = Literal["verde", "amarillo", "rojo", "no_aplica"]


@dataclass(frozen=True)
class ControlStatusResult:
    """Canonical control status compute result (deterministic R1)."""

    control_id: Optional[uuid.UUID]
    measure_code: Optional[str]
    semaforo: Semaforo
    documents_count: int
    documents_approved_count: int
    documents_signed_count: int
    cliente_reviewed_count: int
    expired_count: int
    # UX explicit: por qué NO verde (R29 friendly cuando cliente endpoint)
    missing_reasons: list[str] = field(default_factory=list)
    # Explicit pre-req check booleans (debug + audit)
    requirements_met: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "control_id": str(self.control_id) if self.control_id else None,
            "measure_code": self.measure_code,
            "semaforo": self.semaforo,
            "documents_count": self.documents_count,
            "documents_approved_count": self.documents_approved_count,
            "documents_signed_count": self.documents_signed_count,
            "cliente_reviewed_count": self.cliente_reviewed_count,
            "expired_count": self.expired_count,
            "missing_reasons": list(self.missing_reasons),
            "requirements_met": dict(self.requirements_met),
        }


# Niveles 1-2 CCN-STIC 805 → requires cliente review (Pattern A signoff Q1.C)
# Niveles 3-4 (Procedures + IT) → NO requires cliente review (NULL accepted)
_DOCUMENT_TIPOS_REQUIRE_CLIENT_REVIEW = frozenset({
    "politica",   # nivel 1
    "normativa",  # nivel 2
})


async def compute_control_status(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    control_id: Optional[uuid.UUID] = None,
    measure_code: Optional[str] = None,
) -> ControlStatusResult:
    """Canonical deterministic compute · false-green prevention.

    Args:
      project_id: scope (RLS enforced)
      control_id: filter por specific control · None matches all
      measure_code: filter por ENS measure code · None matches all

    At least ONE of (control_id, measure_code) MUST be provided.

    Returns ControlStatusResult con semaforo + missing_reasons explicit.
    """
    if control_id is None and measure_code is None:
        raise ValueError(
            "compute_control_status: control_id OR measure_code required"
        )

    # #20 Ola 4 (2026-06-04) · FIX del filtro por medida. Antes el bloque
    # `if measure_code: ... pass` NO filtraba → se agregaban TODOS los Document
    # del proyecto y CADA medida devolvía el MISMO semáforo (el agregado). Ahora:
    #  - measure_code → semáforo Evidence-based POR MEDIDA (la prueba que
    #    respalda la declaración de la SoA · vía Evidence.measure_code, el
    #    vínculo real · Document NO tiene columna measure_code).
    #  - control_id (measure_code=None) → lógica Document anti-falso-verde
    #    existente, agregado de proyecto (sin cambios · el filtro real por
    #    control_id queda como Future, fuera del alcance de #20).
    if measure_code is not None:
        return await _compute_measure_evidence_status(
            db, project_id=project_id, measure_code=measure_code,
        )

    # 1. Query applicable documents (control_id / agregado · Document-based)
    stmt = select(Document).where(Document.project_id == project_id)
    documents = list((await db.execute(stmt)).scalars().all())

    documents_count = len(documents)
    documents_approved_count = 0
    documents_signed_count = 0
    cliente_reviewed_count = 0
    expired_count = 0

    now = datetime.now(timezone.utc)

    for doc in documents:
        # Approval check: estado='approved' + approved_at NOT NULL
        is_approved = doc.estado == "approved" and doc.approved_at is not None
        if is_approved:
            documents_approved_count += 1

        # Cliente review check (niveles 1-2 CCN-STIC 805 require)
        if (doc.tipo or "").lower() in _DOCUMENT_TIPOS_REQUIRE_CLIENT_REVIEW:
            if doc.client_review_status == "revisada_ok":
                cliente_reviewed_count += 1

        # Signed via signing_intent
        if doc.client_signing_intent_id is not None:
            documents_signed_count += 1

        # Expired check
        if doc.expires_at is not None and doc.expires_at < now:
            expired_count += 1

    # 2. Compute requirements_met booleans (explicit pre-req check)
    requires_client_review_docs = [
        d for d in documents
        if (d.tipo or "").lower() in _DOCUMENT_TIPOS_REQUIRE_CLIENT_REVIEW
    ]
    requires_signature_docs = [
        d for d in documents
        if d.client_signing_intent_id is not None or (
            (d.tipo or "").lower() in _DOCUMENT_TIPOS_REQUIRE_CLIENT_REVIEW
        )
    ]

    req_documents_exist = documents_count > 0
    req_all_approved = (
        documents_count > 0
        and documents_approved_count == documents_count
    )
    req_all_cliente_reviewed = (
        len(requires_client_review_docs) == 0
        or all(
            d.client_review_status == "revisada_ok"
            for d in requires_client_review_docs
        )
    )
    req_all_signed = (
        len(requires_signature_docs) == 0
        or all(
            d.client_signing_intent_id is not None
            for d in requires_signature_docs
        )
    )
    req_no_expired = expired_count == 0

    requirements_met = {
        "documents_exist": req_documents_exist,
        "all_approved": req_all_approved,
        "all_cliente_reviewed": req_all_cliente_reviewed,
        "all_signed": req_all_signed,
        "no_expired": req_no_expired,
    }

    # 3. Compute missing_reasons explicit (admin technical + cliente-friendly)
    missing_reasons: list[str] = []
    if not req_documents_exist:
        missing_reasons.append("Falta documentación aplicable a esta medida.")
    elif not req_all_approved:
        pending = documents_count - documents_approved_count
        missing_reasons.append(
            f"Hay {pending} documento(s) pendiente(s) de aprobación admin."
        )
    if not req_all_cliente_reviewed:
        pending_review = sum(
            1 for d in requires_client_review_docs
            if d.client_review_status != "revisada_ok"
        )
        missing_reasons.append(
            f"Hay {pending_review} documento(s) pendiente(s) de tu revisión."
        )
    if not req_all_signed:
        pending_sign = sum(
            1 for d in requires_signature_docs
            if d.client_signing_intent_id is None
        )
        missing_reasons.append(
            f"Hay {pending_sign} documento(s) pendiente(s) de tu firma."
        )
    if not req_no_expired:
        missing_reasons.append(
            f"Hay {expired_count} documento(s) caducado(s)."
        )

    # 4. Compute semaforo (anti-false-green)
    if documents_count == 0:
        semaforo: Semaforo = "no_aplica"
    elif all(requirements_met.values()):
        semaforo = "verde"
    elif not req_no_expired:
        # Expired docs · CRITICO (caducados sin renovación)
        semaforo = "rojo"
    else:
        semaforo = "amarillo"

    return ControlStatusResult(
        control_id=control_id,
        measure_code=measure_code,
        semaforo=semaforo,
        documents_count=documents_count,
        documents_approved_count=documents_approved_count,
        documents_signed_count=documents_signed_count,
        cliente_reviewed_count=cliente_reviewed_count,
        expired_count=expired_count,
        missing_reasons=missing_reasons,
        requirements_met=requirements_met,
    )


async def _compute_measure_evidence_status(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
) -> ControlStatusResult:
    """#20 · semáforo POR MEDIDA basado en Evidence (la prueba que respalda la
    declaración de la SoA). Anti-falso-verde: verde SOLO si ≥1 evidencia +
    todas vigentes + ninguna caducada + todas validadas (scan_status='clean').

    Nota empírica (el repo manda): Evidence NO tiene columna `estado`; la señal
    de "validada/aprobada" es `scan_status == 'clean'` (pasó antivirus · mp.s.5).
    `infected`/`quarantined` → rojo; `scanning`/`error` → pendiente (amarillo).
    La aplicabilidad (no_aplica) la decide la SoA (estado_implementacion), NO el
    semáforo: una medida aplicable sin evidencia es 'amarillo' (falta), no
    'no_aplica'.
    """
    today = date.today()
    stmt = select(Evidence).where(
        Evidence.project_id == project_id,
        Evidence.measure_code == measure_code,
        Evidence.deleted_at.is_(None),
    )
    evidences = list((await db.execute(stmt)).scalars().all())

    total = len(evidences)
    clean_count = sum(1 for e in evidences if e.scan_status == "clean")
    vigentes_count = sum(1 for e in evidences if e.vigente)
    caducadas_count = sum(
        1 for e in evidences
        if e.fecha_caducidad is not None and e.fecha_caducidad < today
    )
    has_infected = any(
        e.scan_status in ("infected", "quarantined") for e in evidences
    )

    req_evidence_exists = total > 0
    req_all_vigente = total > 0 and all(e.vigente for e in evidences)
    req_none_caducada = caducadas_count == 0
    req_all_clean = total > 0 and all(
        e.scan_status == "clean" for e in evidences
    )

    requirements_met = {
        "evidence_exists": req_evidence_exists,
        "all_vigente": req_all_vigente,
        "none_caducada": req_none_caducada,
        "all_clean": req_all_clean,
    }

    missing_reasons: list[str] = []
    if not req_evidence_exists:
        missing_reasons.append("Falta evidencia que respalde esta medida.")
    else:
        if not req_all_vigente:
            no_vigentes = total - vigentes_count
            missing_reasons.append(
                f"Hay {no_vigentes} evidencia(s) marcada(s) como no vigente."
            )
        if not req_none_caducada:
            missing_reasons.append(
                f"Hay {caducadas_count} evidencia(s) caducada(s)."
            )
        if not req_all_clean:
            pendientes = total - clean_count
            missing_reasons.append(
                f"Hay {pendientes} evidencia(s) sin validar "
                "(análisis antivirus pendiente o con incidencia)."
            )

    if total == 0:
        semaforo: Semaforo = "amarillo"  # aplica pero falta evidencia
    elif not req_none_caducada or has_infected:
        semaforo = "rojo"  # caducada o infectada/cuarentena = crítico
    elif all(requirements_met.values()):
        semaforo = "verde"
    else:
        semaforo = "amarillo"

    return ControlStatusResult(
        control_id=None,
        measure_code=measure_code,
        semaforo=semaforo,
        documents_count=total,                 # nº de evidencias de la medida
        documents_approved_count=clean_count,  # evidencias validadas (clean)
        documents_signed_count=0,              # N/A para evidencia
        cliente_reviewed_count=0,              # N/A para evidencia
        expired_count=caducadas_count,
        missing_reasons=missing_reasons,
        requirements_met=requirements_met,
    )


def translate_missing_reasons_cliente_friendly(
    reasons: list[str],
) -> list[str]:
    """Cliente-friendly translation R29 (NO admin lingo · TooltipENS sugerido).

    Default reasons ya están R29 friendly · esta function permite
    customización future per project branding (ClientBrandingProvider).
    """
    # MVP: reasons ya son R29 friendly · pass-through
    # Future: per project branding override + TooltipENS injection
    return list(reasons)
