"""LeadService · CRM lifecycle management lead M13 commercial.

SAN-D MB-19.2 · ADR-041.

Cubre:
- create_lead(): crear Lead con dedup idempotent (email + origen).
- transition_estado_contacto(): mover estado workflow comercial v2 con
  audit trail LeadStageHistory + validación VALID_TRANSITIONS dict.
- list_pipeline(): listar leads filtrados por estado/origen/asignado.

Workflow comercial 8 estados FASE 8.5 C2 v2:

    nuevo → enviado → respondio → reunion_agendada → propuesta_enviada
                                                       ↓                ↘
                                                     ganado          no_interesa
                                                       ↑                ↓
                                                       ←—— descartado ←——

Refs:
- backend/app/models/commercial.py:Lead · LeadStageHistory
- ADR-041 (CRM workflow comercial m13 extension)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import Lead, LeadStageHistory


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Workflow comercial 8 estados v2 · transitions válidas per estado
# ──────────────────────────────────────────────────────────────────
# Mapeo: estado_actual → set(estados_posibles_destino).
# Terminal: ganado (no transition out · solo via re-open admin).
# Re-entry permitido: descartado/no_interesa → nuevo (rare lead re-engagement).

VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "nuevo": frozenset({"enviado", "descartado", "no_interesa"}),
    "enviado": frozenset({"respondio", "descartado", "no_interesa"}),
    "respondio": frozenset({
        "reunion_agendada", "descartado", "no_interesa",
    }),
    "reunion_agendada": frozenset({
        "propuesta_enviada", "descartado", "no_interesa",
    }),
    "propuesta_enviada": frozenset({
        "ganado", "descartado", "no_interesa",
        # back-and-forth durante negociación: revisión de propuesta
        # mantiene estado=propuesta_enviada (no transición · ProposalService
        # crea revisión versión nueva).
    }),
    "ganado": frozenset(),  # Terminal · no transitions
    "descartado": frozenset({"nuevo"}),  # Re-engagement raro
    "no_interesa": frozenset({"nuevo"}),  # Re-engagement raro
}


# ──────────────────────────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────────────────────────


class LeadServiceError(Exception):
    """Error genérico LeadService."""


class InvalidTransitionError(LeadServiceError):
    """Transición workflow comercial no permitida."""


class LeadNotFoundError(LeadServiceError):
    """Lead UUID no encontrado en BD."""


# ──────────────────────────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────────────────────────


class LeadService:
    """CRM lead lifecycle management · m13_commercial extension MB-19.2.

    Servicios async · usa AsyncSession existing (NO crea sesión propia).
    Tests usan fixture conftest.db (transactional rollback).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ────────────────────────────────────────────────────────────
    # CREATE
    # ────────────────────────────────────────────────────────────

    async def create_lead(
        self,
        *,
        empresa_nombre: str,
        contacto_email: str | None = None,
        empresa_cif: str | None = None,
        sector: str | None = None,
        origen: str = "manual",
        contacto_telefono: str | None = None,
        contacto_position: str | None = None,
        notas: str | None = None,
        asignado_a: str | None = None,
        temperature_level: int | None = None,
        categoria_objetivo_ens: str | None = None,
        archetype_ens: str | None = None,
        estado_contacto: str = "nuevo",
    ) -> Lead:
        """Crea Lead con dedup idempotent por (contacto_email, origen).

        Si existe lead con mismo email+origen, retorna el existente sin
        modificar (idempotent · auto-import workers reusan sin duplicar).

        Crea audit trail row en lead_stage_history (estado_anterior=NULL,
        estado_nuevo=estado_contacto, metadata={"event":"lead_created"}).
        """
        if estado_contacto not in VALID_TRANSITIONS:
            raise LeadServiceError(
                f"estado_contacto inválido: {estado_contacto!r} · "
                f"valid: {sorted(VALID_TRANSITIONS.keys())}"
            )

        # Dedup check
        if contacto_email:
            existing = await self.db.scalar(
                select(Lead).where(
                    Lead.contacto_email == contacto_email,
                    Lead.origen == origen,
                )
            )
            if existing:
                logger.info(
                    "create_lead idempotent skip · existing lead %s "
                    "email=%s origen=%s",
                    existing.id, contacto_email, origen,
                )
                return existing

        lead = Lead(
            empresa_nombre=empresa_nombre,
            contacto_email=contacto_email,
            empresa_cif=empresa_cif,
            sector=sector,
            origen=origen,
            contacto_telefono=contacto_telefono,
            notas=notas,
            asignado_a=asignado_a,
            temperature_level=temperature_level,
            categoria_objetivo_ens=categoria_objetivo_ens,
            archetype_ens=archetype_ens,
            estado="nuevo",  # estado legacy (string libre)
            estado_contacto=estado_contacto,
            fecha_entrada=datetime.now(timezone.utc),
            fecha_ultima_actualizacion=datetime.now(timezone.utc),
        )
        self.db.add(lead)
        await self.db.flush()

        # Audit trail row
        history = LeadStageHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            estado_anterior=None,
            estado_nuevo=estado_contacto,
            cambiado_por_user_id=None,
            notas=notas,
            metadata_jsonb={"event": "lead_created", "origen": origen},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(history)
        await self.db.flush()

        return lead

    # ────────────────────────────────────────────────────────────
    # TRANSITION
    # ────────────────────────────────────────────────────────────

    async def transition_estado_contacto(
        self,
        *,
        lead_id: uuid.UUID,
        target_estado: str,
        by_user_id: uuid.UUID | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Lead:
        """Mueve lead a target_estado con validación VALID_TRANSITIONS
        + audit trail LeadStageHistory.

        Side effects per estado destino:
        - enviado: si primer_contacto_at IS NULL · set NOW()
        - propuesta_enviada: no side effect (ProposalService maneja
          fecha_aceptacion/superseded).
        - ganado: fecha_conversion = NOW() (CommercialWorkflowService
          completa Project + ClientUser create).
        - descartado/no_interesa: fecha_perdida = NOW() · razon_perdida=notes.

        Args:
            lead_id: UUID del Lead a transicionar.
            target_estado: estado destino (debe estar en VALID_TRANSITIONS
                del estado actual).
            by_user_id: UUID admin user que realiza la transición.
            notes: notas Marcos sobre la transición.
            metadata: dict adicional persistido en lead_stage_history.metadata_jsonb.

        Returns:
            Lead actualizado con estado_contacto + side-effects.

        Raises:
            LeadNotFoundError: lead_id no existe.
            InvalidTransitionError: target_estado no está en
                VALID_TRANSITIONS[lead.estado_contacto].
        """
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            raise LeadNotFoundError(f"Lead {lead_id} no encontrado")

        current = lead.estado_contacto or "nuevo"
        valid_targets = VALID_TRANSITIONS.get(current, frozenset())
        if target_estado not in valid_targets:
            raise InvalidTransitionError(
                f"Transición inválida {current!r} → {target_estado!r} · "
                f"valid: {sorted(valid_targets)}"
            )

        previous = current
        now = datetime.now(timezone.utc)

        lead.estado_contacto = target_estado
        lead.fecha_ultima_actualizacion = now

        # Side effects per estado
        if target_estado == "enviado" and lead.primer_contacto_at is None:
            lead.primer_contacto_at = now
        elif target_estado in ("descartado", "no_interesa"):
            lead.fecha_perdida = now
            if notes:
                lead.razon_perdida = notes[:200]
        elif target_estado == "ganado":
            lead.fecha_conversion = now
            # Project create + ClientUser invite quedan a cargo de
            # CommercialWorkflowService.handle_contract_signed (orquestación
            # completa MB-19.2 separada).

        # Audit trail
        history = LeadStageHistory(
            id=uuid.uuid4(),
            lead_id=lead.id,
            estado_anterior=previous,
            estado_nuevo=target_estado,
            cambiado_por_user_id=by_user_id,
            notas=notes,
            metadata_jsonb=metadata or {},
            created_at=now,
        )
        self.db.add(history)
        await self.db.flush()

        return lead

    # ────────────────────────────────────────────────────────────
    # QUERY
    # ────────────────────────────────────────────────────────────

    async def list_pipeline(
        self,
        *,
        estado_contacto: str | None = None,
        origen: str | None = None,
        asignado_a: str | None = None,
        limit: int = 200,
    ) -> list[Lead]:
        """Lista leads pipeline con filtros opcionales.

        Default order: fecha_ultima_actualizacion DESC (último activity
        primero · útil pipeline kanban).
        """
        query = select(Lead).order_by(
            Lead.fecha_ultima_actualizacion.desc().nulls_last(),
            Lead.created_at.desc(),
        ).limit(limit)
        if estado_contacto:
            query = query.where(Lead.estado_contacto == estado_contacto)
        if origen:
            query = query.where(Lead.origen == origen)
        if asignado_a:
            query = query.where(Lead.asignado_a == asignado_a)

        result = await self.db.scalars(query)
        return list(result)
