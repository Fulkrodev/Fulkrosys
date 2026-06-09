"""M19 triggers automáticos · genera magic-links M12 en milestones lifecycle.

Mapping milestone → magic-link purpose para 4 transiciones canónicas
del workflow FULKRO (8 fases · ADR-026):

- DIAGNOSTICO → ADECUACION  : APROBACION_PROPUESTA (cliente aprueba propuesta gap)
- ADECUACION → IMPLANTACION : FIRMA_DOCUMENTO (cliente firma DdA)
- IMPLANTACION → VERIFICACION : AUTORIZAR_PENTEST_EXTERNO
- VERIFICACION → CONFORMIDAD : DESCARGA_DOSSIER_FINAL

CONFORMIDAD → RETAINER_CIERRE: NO genera magic-link (ADR-020 v3 IMPLEMENTED
FULLY · MB-4.bis3 commit 89da6e1). Ofrecer retainer cliente in-portal
vía ClientNotification (M21) cuando trigger BD project_lifecycle_events
se active. OFERTA_RETAINER hard-revoked en magic_links cliente.

Listener consume ``project_lifecycle_events`` con ``event_type='phase_changed'``
(emitido por trigger BD MB-6.1 · pendiente audit M04/M07 antes de
implementar). Mientras MB-6.1 no esté activa, este listener queda inert
(no hay events que procesar) · tests mockean events insertados manual
para validar la lógica.

Idempotencia: cada magic-link generado guarda en ``scope.source_event_id``
el UUID del lifecycle event procesado. Re-run sobre el mismo event detecta
el ML existente y skips (evita duplicados si poller corre múltiples veces).

Refs: SAN-B.MB-6.3 · cierre TODO-M19-G1 (scope phase_changed listener;
risk-severity trigger sigue abierto en TODO-M19-G1 sub-scope) ·
SAN-E v3.MB-5.0 (cleanup OFERTA_RETAINER dormant entry · ADR-020 v3).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lifecycle import ProjectLifecycleEvent
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService


logger = logging.getLogger(__name__)


# Mapping clave estructurada `phase_changed:to:<new_fase>` → config purpose.
# El listener compone la clave desde `event.metadata_jsonb["new_fase"]`.
#
# ADR-020 v3 (SAN-E v3.MB-4.bis3 IMPLEMENTED FULLY · MB-5.0 cleanup):
# `phase_changed:to:retainer_cierre` removido · OFERTA_RETAINER hard-revoked
# cliente-facing. Cuando trigger BD project_lifecycle_events se active
# (MB-6.1+), retainer offer cliente debe usar ClientNotification (M21)
# directamente, NO MagicLink.
MILESTONE_TO_MAGIC_LINK_MAPPING: dict[str, dict[str, Any]] = {
    "phase_changed:to:adecuacion": {
        "purpose": MagicLinkPurpose.APROBACION_PROPUESTA,
        "ttl_hours": 168,  # 7 días
    },
    "phase_changed:to:implantacion": {
        "purpose": MagicLinkPurpose.FIRMA_DOCUMENTO,
        "ttl_hours": 168,
    },
    "phase_changed:to:verificacion": {
        "purpose": MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
        "ttl_hours": 72,  # 3 días (acción sensible)
    },
    "phase_changed:to:conformidad": {
        "purpose": MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
        "ttl_hours": 168,
    },
}


async def process_phase_changed_event(
    db: AsyncSession,
    event: ProjectLifecycleEvent,
    *,
    recipient_email: str,
    base_url: str = "https://app.fulkro.es",
    sent_to_contact_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """Procesa un event lifecycle 'phase_changed' · genera magic-link mapeado.

    Returns:
        UUID del magic-link generado, o None si:
        - event.event_type != 'phase_changed'
        - new_fase no está en MILESTONE_TO_MAGIC_LINK_MAPPING
        - ya existe magic-link con scope.source_event_id == event.id (idempotencia)
        - event.project_id es None (event huérfano)
    """
    if event.event_type != "phase_changed":
        return None
    if event.project_id is None:
        logger.debug("M19 trigger skip · event %s sin project_id", event.id)
        return None

    metadata = event.metadata_jsonb or {}
    new_fase = metadata.get("new_fase")
    if not new_fase:
        return None

    key = f"phase_changed:to:{new_fase}"
    config = MILESTONE_TO_MAGIC_LINK_MAPPING.get(key)
    if config is None:
        logger.debug("M19 trigger skip · milestone %s sin mapping", key)
        return None

    # Idempotency · check si ya existe ML con scope.source_event_id == event.id
    existing = await db.execute(
        select(MagicLink.id).where(
            MagicLink.project_id == event.project_id,
            MagicLink.scope["source_event_id"].astext == str(event.id),
            MagicLink.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info(
            "M19 trigger idempotent skip · event %s ya procesado", event.id
        )
        return None

    # Generate magic-link
    svc = MagicLinkService(db)
    request = MagicLinkGenerateRequest(
        project_id=event.project_id,
        purpose=config["purpose"],
        recipient_email=recipient_email,
        sent_to_contact_id=sent_to_contact_id,
        scope={
            "source_event_id": str(event.id),
            "milestone": key,
            "auto_generated": True,
            "trigger_source": "m19_phase_changed",
        },
        ttl_hours=config.get("ttl_hours"),
    )
    response = await svc.generate_magic_link(request, base_url=base_url)
    logger.info(
        "M19 trigger · magic-link %s creado para event %s milestone=%s",
        response.magic_link_id, event.id, key,
    )
    return response.magic_link_id


async def process_recent_phase_changes(
    db: AsyncSession,
    *,
    recipient_email_resolver,
    base_url: str = "https://app.fulkro.es",
    limit: int = 100,
) -> dict[str, int]:
    """Poll batch · procesa events 'phase_changed' recientes idempotente.

    ``recipient_email_resolver(event)`` debe retornar tuple
    (email: str, contact_id: UUID | None) para el event dado.
    Si retorna None, el event se skipea.

    Returns dict con counters: ``processed`` (nuevos ML) ·
    ``skipped_unmapped`` · ``skipped_idempotent`` · ``skipped_no_recipient``.
    """
    res = await db.execute(
        select(ProjectLifecycleEvent).where(
            ProjectLifecycleEvent.event_type == "phase_changed",
        ).order_by(ProjectLifecycleEvent.event_date.desc()).limit(limit)
    )
    events = list(res.scalars().all())

    counters = {
        "processed": 0,
        "skipped_unmapped": 0,
        "skipped_idempotent": 0,
        "skipped_no_recipient": 0,
    }

    for event in events:
        metadata = event.metadata_jsonb or {}
        new_fase = metadata.get("new_fase")
        if not new_fase or f"phase_changed:to:{new_fase}" not in MILESTONE_TO_MAGIC_LINK_MAPPING:
            counters["skipped_unmapped"] += 1
            continue

        recipient = recipient_email_resolver(event)
        if recipient is None:
            counters["skipped_no_recipient"] += 1
            continue
        email, contact_id = recipient

        ml_id = await process_phase_changed_event(
            db, event,
            recipient_email=email,
            base_url=base_url,
            sent_to_contact_id=contact_id,
        )
        if ml_id is not None:
            counters["processed"] += 1
        else:
            counters["skipped_idempotent"] += 1

    return counters
