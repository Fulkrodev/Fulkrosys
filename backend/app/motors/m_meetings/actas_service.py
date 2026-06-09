"""Actas service · SAN-E v3.MB-6 atom 5 · Actas 4 tipos signable cliente.

Reuse-first approach · MinutesService m18 helpers (_next_codigo · _validate_asistentes ·
_hash_sha256 · _ed25519_sign · _convert_to_pdf · build_minutes_docx) consumed via
import. Service envuelve workflow cliente-facing (draft → curated → sent_to_client →
reviewed → signed) sin duplicar infrastructure existing.

7 decisiones Marcos cement:
- Q1 A · extender committee_meetings (28 cols MUY madura)
- Q2 D · reuse acta_comite signable_type + acta_subtype col
- Q3 · 4 lifecycles + Q3-extra uniform 1x post-cert + on-demand admin
- Q4 A · TODOS MixinA (9a aplicacion)
- Q5 A · cliente VE TODAS sent_to_client (transparency)
- Q6 (c) · acta_comite outside chain (pagina /actas propia)
- Q7 · NO widen signable_types

Sub-questions:
- Sub-Q1 · acta_subtype='other' allowed (5 valores)
- Sub-Q2 · firmas jsonb multi-sig (admin Ed25519 + cliente signing_intent linked)
- Sub-Q3 · filter UI chip selector (list_actas_for_client subtype_filter param)
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import and_, select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.governance import CommitteeMeeting
from backend.app.motors.m18_communication.minutes_service import (
    _next_codigo,
    _validate_asistentes,
    MinutesValidationError,
)


# ════════════════════════════════════════════════════════════════════
# Constants
# ════════════════════════════════════════════════════════════════════

ACTA_SUBTYPES: tuple[str, ...] = (
    "kickoff",
    "checkpoint",
    "audit",
    "cierre",
    "other",
)

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

# Mapping acta_subtype → legacy tipo_comite (best-effort coherence con MinutesService).
_SUBTYPE_TO_LEGACY_TIPO: dict[str, str] = {
    "kickoff": "kickoff",
    "checkpoint": "seguimiento_trimestral",
    "audit": "extraordinario",
    "cierre": "cierre",
    "other": "extraordinario",
}


# ════════════════════════════════════════════════════════════════════
# Exceptions
# ════════════════════════════════════════════════════════════════════


class ActasError(Exception):
    """Base error actas service."""


class ActaNotFoundError(ActasError):
    """Acta no existe o deleted."""


class InvalidActaSubtypeError(ActasError):
    """acta_subtype invalido (no in 5 valores enum)."""


class InvalidWorkflowTransitionError(ActasError):
    """Transition admin_curation_status invalida."""


class ActaAlreadySignedError(ActasError):
    """Acta ya firmada por cliente · NO modificable."""


class InvalidReviewActionError(ActasError):
    """Action review invalido."""


# ════════════════════════════════════════════════════════════════════
# Service
# ════════════════════════════════════════════════════════════════════


class ActasService:
    """Service actas 4 tipos signable cliente · workflow admin curate + cliente review."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ----------------------------------------------------------------
    # Create draft (reuse _next_codigo + _validate_asistentes m18)
    # ----------------------------------------------------------------

    async def create_acta_draft(
        self,
        project_id: uuid.UUID,
        acta_subtype: str,
        titulo: str,
        fecha: date,
        presidente: str,
        secretario: str,
        asistentes: list[dict],
        admin_user_id: uuid.UUID,
        orden_del_dia: list[dict] | None = None,
        acuerdos: list[dict] | None = None,
        proximos_pasos: list[dict] | None = None,
        lugar: str | None = None,
        notas_libres: str | None = None,
    ) -> CommitteeMeeting:
        """Crea acta en estado draft · admin_curation_status='draft'."""
        if acta_subtype not in ACTA_SUBTYPES:
            raise InvalidActaSubtypeError(
                f"acta_subtype '{acta_subtype}' invalido · "
                f"esperado uno de {ACTA_SUBTYPES}"
            )

        try:
            _validate_asistentes(asistentes)
        except MinutesValidationError as exc:
            raise ActasError(str(exc)) from exc

        codigo = await _next_codigo(self.db, project_id)
        legacy_tipo = _SUBTYPE_TO_LEGACY_TIPO.get(acta_subtype, "extraordinario")

        meeting = CommitteeMeeting(
            project_id=project_id,
            codigo=codigo,
            tipo_comite=legacy_tipo,
            acta_subtype=acta_subtype,
            admin_curation_status="draft",
            admin_curated_by_user_id=admin_user_id,
            titulo=titulo,
            fecha=fecha,
            lugar=lugar,
            presidente=presidente,
            secretario=secretario,
            asistentes=asistentes,
            orden_del_dia=orden_del_dia or [],
            acuerdos_jsonb=acuerdos or [],
            proximos_pasos=proximos_pasos or [],
            notas_libres=notas_libres,
            firmas=[],
            estado="draft",
        )
        self.db.add(meeting)
        await self.db.flush()
        return meeting

    # ----------------------------------------------------------------
    # Admin curation workflow
    # ----------------------------------------------------------------

    async def admin_curate_acta(
        self,
        meeting_id: uuid.UUID,
        admin_user_id: uuid.UUID,
        content_edits: dict | None = None,
    ) -> CommitteeMeeting:
        """Admin Marcos curates content (orden_dia · acuerdos · proximos_pasos).

        content_edits accepted keys:
          - orden_del_dia (list)
          - acuerdos (list) → maps a acuerdos_jsonb
          - proximos_pasos (list)
          - notas_libres (str)
          - titulo (str)
        """
        meeting = await self._get(meeting_id)
        if meeting.admin_curation_status != "draft":
            raise InvalidWorkflowTransitionError(
                f"Acta status='{meeting.admin_curation_status}' · "
                f"esperado 'draft' para curate"
            )

        if content_edits:
            if "orden_del_dia" in content_edits:
                meeting.orden_del_dia = content_edits["orden_del_dia"]
            if "acuerdos" in content_edits:
                meeting.acuerdos_jsonb = content_edits["acuerdos"]
            if "proximos_pasos" in content_edits:
                meeting.proximos_pasos = content_edits["proximos_pasos"]
            if "notas_libres" in content_edits:
                meeting.notas_libres = content_edits["notas_libres"]
            if "titulo" in content_edits:
                meeting.titulo = content_edits["titulo"]

        meeting.admin_curation_status = "curated_by_admin"
        meeting.admin_curated_at = datetime.now(UTC)
        meeting.admin_curated_by_user_id = admin_user_id
        await self.db.flush()
        return meeting

    async def admin_send_to_client(
        self,
        meeting_id: uuid.UUID,
        admin_user_id: uuid.UUID,
    ) -> CommitteeMeeting:
        """Admin sends curated acta to cliente · status='sent_to_client'."""
        meeting = await self._get(meeting_id)
        if meeting.admin_curation_status != "curated_by_admin":
            raise InvalidWorkflowTransitionError(
                f"Acta status='{meeting.admin_curation_status}' · "
                f"esperado 'curated_by_admin' para sent_to_client"
            )

        meeting.admin_curation_status = "sent_to_client"
        meeting.enviada_at = datetime.now(UTC)
        await self.db.flush()
        return meeting

    # ----------------------------------------------------------------
    # Cliente list visible (Q5 A · transparency TODAS sent_to_client)
    # ----------------------------------------------------------------

    async def list_actas_for_client(
        self,
        project_id: uuid.UUID,
        subtype_filter: str | None = None,
    ) -> list[CommitteeMeeting]:
        """Lista actas visible cliente · admin_curation_status='sent_to_client'.

        sub-Q3 · subtype_filter optional chip selector (None = todas).
        """
        conditions = [
            CommitteeMeeting.project_id == project_id,
            CommitteeMeeting.admin_curation_status == "sent_to_client",
            CommitteeMeeting.deleted_at.is_(None),
        ]
        if subtype_filter is not None:
            if subtype_filter not in ACTA_SUBTYPES:
                raise InvalidActaSubtypeError(
                    f"subtype_filter '{subtype_filter}' invalido"
                )
            conditions.append(CommitteeMeeting.acta_subtype == subtype_filter)

        stmt = (
            select(CommitteeMeeting)
            .where(and_(*conditions))
            .order_by(CommitteeMeeting.fecha.desc().nullslast())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    # ----------------------------------------------------------------
    # Cliente review (MixinA · 9a aplicacion)
    # ----------------------------------------------------------------

    async def mark_client_review(
        self,
        meeting_id: uuid.UUID,
        action: str,
        note: str | None,
        user_id: uuid.UUID,
    ) -> CommitteeMeeting:
        """Cliente review action · MixinA pattern (revisada_ok / con_pregunta / suggest_change).

        Bloquea review hasta admin_curation_status='sent_to_client'.
        """
        if action not in CLIENT_FACING_REVIEW_STATUS:
            raise InvalidReviewActionError(
                f"action '{action}' invalido · esperado "
                f"{sorted(CLIENT_FACING_REVIEW_STATUS)}"
            )
        if action in {"con_pregunta", "suggest_change"} and not (note or "").strip():
            raise InvalidReviewActionError(
                f"action '{action}' requiere note no vacia"
            )

        meeting = await self._get(meeting_id)
        if meeting.admin_curation_status != "sent_to_client":
            raise ActasError(
                f"Acta status='{meeting.admin_curation_status}' · cliente NO "
                f"puede revisar hasta sent_to_client"
            )

        meeting.client_review_status = action
        meeting.client_review_note = (note or "").strip() or None
        meeting.client_reviewed_at = datetime.now(UTC)
        meeting.client_reviewed_by_user_id = user_id
        await self.db.flush()
        return meeting

    # ----------------------------------------------------------------
    # Document hash + signoff (sub-Q2 multi-sig)
    # ----------------------------------------------------------------

    async def compute_acta_hash(
        self, meeting_id: uuid.UUID,
    ) -> tuple[str, int]:
        """SHA256 canonical · input firma M05 · deterministic."""
        meeting = await self._get(meeting_id)

        canonical_parts = [
            f"meeting_id:{meeting.id}",
            f"project_id:{meeting.project_id}",
            f"codigo:{meeting.codigo or ''}",
            f"acta_subtype:{meeting.acta_subtype or ''}",
            f"titulo:{meeting.titulo or ''}",
            f"fecha:{meeting.fecha.isoformat() if meeting.fecha else ''}",
            f"presidente:{meeting.presidente or ''}",
            f"secretario:{meeting.secretario or ''}",
            f"asistentes_count:{len(meeting.asistentes or [])}",
            f"orden_count:{len(meeting.orden_del_dia or [])}",
            f"acuerdos_count:{len(meeting.acuerdos_jsonb or [])}",
            f"client_review_status:{meeting.client_review_status or 'pending'}",
        ]
        canonical = "\n".join(canonical_parts)
        document_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return document_hash, len(canonical)

    async def process_acta_signoff(
        self,
        meeting_id: uuid.UUID,
        signing_intent_id: uuid.UUID,
    ) -> CommitteeMeeting:
        """Post-firma cliente · multi-sig append firmas jsonb + estado transition.

        Sub-Q2 cement · firmas jsonb append-mode (admin Ed25519 ya en signature_ed25519
        si exists · cliente firma se añade a firmas jsonb como entry separada con
        signing_intent_id linked).
        """
        meeting = await self._get(meeting_id)
        if meeting.client_signing_intent_id is not None:
            raise ActaAlreadySignedError(
                f"Acta {meeting_id} ya firmada por cliente"
            )

        meeting.client_signing_intent_id = signing_intent_id

        # Multi-sig · append cliente signature a firmas jsonb (sub-Q2)
        firmas = list(meeting.firmas or [])
        firmas.append({
            "actor": "cliente",
            "signing_intent_id": str(signing_intent_id),
            "firmado_at": datetime.now(UTC).isoformat(),
        })
        meeting.firmas = firmas

        # Workflow transition · fully_signed cuando cliente firma
        meeting.estado = "fully_signed"
        meeting.fully_signed_at = datetime.now(UTC)

        await self.db.flush()

        # MB-6 atom 8 · post-signoff hook cross-motor (M30 + Orchestrator email)
        try:
            from backend.app.notifications.post_signoff_hooks import (
                post_signoff_acta,
            )
            await post_signoff_acta(self.db, meeting=meeting)
        except Exception:
            pass  # silent fail · signoff persists OK

        return meeting

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    async def _get(self, meeting_id: uuid.UUID) -> CommitteeMeeting:
        meeting = await self.db.get(CommitteeMeeting, meeting_id)
        if meeting is None or meeting.deleted_at is not None:
            raise ActaNotFoundError(f"Acta {meeting_id} no encontrada")
        return meeting


# ════════════════════════════════════════════════════════════════════
# F0-4 (Ejecutable 8 Pasada 16 · P10-F07) · Cadencia del Comité de Seguridad
# ════════════════════════════════════════════════════════════════════

# Periodicidad mínima del comité de seguridad por categoría ENS (en meses).
# Fuente: P10-F07 · semestral BÁSICA / trimestral MEDIA+ALTA. CCN-STIC 801.
COMITE_PERIODICIDAD_MESES: dict[str, int] = {
    "BASICA": 6,   # semestral
    "MEDIA": 3,    # trimestral
    "ALTA": 3,     # trimestral
}
_COMITE_PERIODICIDAD_LABEL: dict[int, str] = {6: "semestral", 3: "trimestral"}


async def evaluate_comite_cadence(
    db: AsyncSession, project_id: uuid.UUID,
) -> dict:
    """Evalúa el cumplimiento de la cadencia del Comité de Seguridad.

    Pura/funcional (sin side-effects): lee la categoría del proyecto y las actas
    de comité firmadas (estado=fully_signed) y determina si la periodicidad
    requerida (semestral BÁSICA / trimestral MEDIA+ALTA · P10-F07) se cumple.
    Sirve de alerta pre-auditoría. Reutiliza committee_meetings (ADR-025 · sin
    tabla nueva).
    """
    cat_row = (await db.execute(sa_text(
        "SELECT categoria_objetivo FROM projects WHERE id = :pid"
    ), {"pid": str(project_id)})).first()
    categoria = (cat_row[0] if cat_row and cat_row[0] else "BASICA").upper()
    meses = COMITE_PERIODICIDAD_MESES.get(categoria, 6)

    res = await db.execute(
        select(CommitteeMeeting)
        .where(
            CommitteeMeeting.project_id == project_id,
            CommitteeMeeting.estado == "fully_signed",
            CommitteeMeeting.deleted_at.is_(None),
        )
        .order_by(CommitteeMeeting.fecha.desc())
    )
    actas = list(res.scalars().all())
    total_firmadas = len(actas)
    ultima = actas[0] if actas else None
    ultima_fecha = ultima.fecha if ultima else None

    now = datetime.now(UTC)
    dias_desde = None
    cumple = False
    proxima_obligatoria = None
    if ultima_fecha is not None:
        ref = ultima_fecha
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        dias_desde = (now - ref).days
        cumple = dias_desde <= meses * 31
        # próxima obligatoria ~= última + periodicidad (aprox 31 días/mes)
        from datetime import timedelta
        proxima_obligatoria = (ref + timedelta(days=meses * 31)).date().isoformat()

    return {
        "project_id": str(project_id),
        "categoria": categoria,
        "periodicidad_meses": meses,
        "periodicidad_label": _COMITE_PERIODICIDAD_LABEL.get(meses, f"{meses} meses"),
        "total_actas_firmadas": total_firmadas,
        "ultima_acta_fecha": ultima_fecha.isoformat() if ultima_fecha else None,
        "dias_desde_ultima": dias_desde,
        "cumple_cadencia": cumple,
        "proxima_obligatoria": proxima_obligatoria,
        # Alerta pre-auditoría: sin actas firmadas o fuera de cadencia.
        "alerta_pre_auditoria": (total_firmadas == 0) or (not cumple),
        "norma": "CCN-STIC 801 · RD 311/2022 (P10-F07)",
    }
