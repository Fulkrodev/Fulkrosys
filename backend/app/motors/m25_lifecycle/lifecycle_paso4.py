r"""M25 Paso 4 — Lifecycle Paso 4 service (cierre honesto sin retainer).

Extiende ``LifecycleService`` con el flujo completo de cierre del
proyecto cuando el cliente NO contrata retainer:

    mark_certified -> offer_retainer ->
        |-- decision='accept'  -> M23 RetainerService.create_retainer
        |-- decision='decline' -> start_grace_period (240 dias)
        \-- decision='thinking' -> start_grace_period (240 dias)

    Dentro del grace period, hitos calendaricos:

        dia 150 -> warning_sent a Marcos (mes 5)
        dia 180 -> reconsideration_sent al cliente (mes 6)
        dia 210 -> backup_generated + magic link descarga (mes 7)
        dia 240 -> data_deleted (GDPR hard delete) (mes 8)

    Tras dia 240: cliente puede reactivar con backup_id DENTRO de los
    60 dias de disponibilidad del ZIP archivado; despues, imposible.

Todo el flujo registra eventos en ``project_lifecycle_events`` para
auditoria y cockpit de Marcos.
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client, Project
from backend.app.models.lifecycle import (
    ProjectArchivedBackup,
    ProjectLifecycleEvent,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService

from .backup_builder import (
    build_and_sign_backup_zip,
    delete_backup_from_cold_storage,
    upload_backup_to_cold_storage,
)

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════════════════════════════

GRACE_PERIOD_DAYS_DEFAULT = 240  # 8 meses
GRACE_WARNING_MARCOS_DAY = 150   # mes 5
GRACE_RECONSIDERATION_DAY = 180  # mes 6
GRACE_BACKUP_DAY = 210           # mes 7
GRACE_DELETE_DAY = 240           # mes 8

BACKUP_DOWNLOAD_TTL_DAYS = 60

VALID_DECISIONS = ("accept", "decline", "thinking")

VALID_RETAINER_TIERS = ("R_MICRO", "R_LITE", "R_STD", "R_PLUS", "R_CRITICAL")

# Sincronizado con check constraint en migration d2e6f4a9b812 +
# extension migration audit_marked_event_type_001 (Sesión 3B-2B.6 Cluster 1 Phase 2)
ALLOWED_EVENT_TYPES = frozenset({
    "certified",
    "retainer_offered",
    "retainer_accepted",
    "retainer_declined",
    "grace_period_started",
    "backup_generated",
    "backup_sent",
    "warning_sent",
    "reconsideration_sent",
    "deletion_scheduled",
    "data_deleted",
    "reactivated",
    "audit_marked",  # Sesión 3B-2B.6 Cluster 1 Phase 2 · mark_audit_passed event
})


class LifecyclePaso4Error(Exception):
    pass


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_project_strict(db: AsyncSession, project_id: uuid.UUID) -> Project:
    res = await db.execute(select(Project).where(Project.id == project_id))
    project = res.scalar_one_or_none()
    if project is None:
        raise LifecyclePaso4Error(f"Project {project_id} no encontrado")
    return project


async def _get_client_strict(db: AsyncSession, client_id: uuid.UUID) -> Client:
    res = await db.execute(select(Client).where(Client.id == client_id))
    client = res.scalar_one_or_none()
    if client is None:
        raise LifecyclePaso4Error(f"Client {client_id} no encontrado")
    return client


async def _log_event(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None,
    client_id: uuid.UUID | None,
    event_type: str,
    performed_by: str = "marcos",
    metadata: dict[str, Any] | None = None,
    event_date: datetime | None = None,
    grace_period_days: int | None = None,
    backup_zip_path: str | None = None,
    backup_signature_ed25519: str | None = None,
    backup_download_magic_link_id: uuid.UUID | None = None,
    notification_sent_to: Iterable[str] | None = None,
) -> ProjectLifecycleEvent:
    """Registra un evento del ciclo de vida Paso 4."""
    if event_type not in ALLOWED_EVENT_TYPES:
        raise LifecyclePaso4Error(
            f"event_type invalido: {event_type}. Validos: {sorted(ALLOWED_EVENT_TYPES)}"
        )
    now = _now()
    event = ProjectLifecycleEvent(
        project_id=project_id,
        client_id=client_id,
        event_type=event_type,
        event_date=event_date or now,
        performed_by=performed_by,
        metadata_jsonb=metadata or None,
        grace_period_days=grace_period_days,
        backup_zip_path=backup_zip_path,
        backup_signature_ed25519=backup_signature_ed25519,
        backup_download_magic_link_id=backup_download_magic_link_id,
        notification_sent_to=list(notification_sent_to) if notification_sent_to else None,
        created_at=now,
    )
    db.add(event)
    await db.flush()
    return event


# ══════════════════════════════════════════════════════════════════════
# Service
# ══════════════════════════════════════════════════════════════════════


class LifecyclePaso4Service:
    """Cierre honesto del proyecto sin retainer + grace period 8 meses."""

    # ── certificacion ────────────────────────────────────────────────

    async def mark_certified(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        certified_on: date | None = None,
        performed_by: str = "marcos",
        metadata: dict[str, Any] | None = None,
    ) -> ProjectLifecycleEvent:
        project = await _get_project_strict(db, project_id)
        if project.certified_at:
            raise LifecyclePaso4Error(
                f"Proyecto ya certificado el {project.certified_at}"
            )
        project.certified_at = certified_on or date.today()
        project.lifecycle_state = "CERTIFIED"
        await db.flush()
        return await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="certified", performed_by=performed_by,
            metadata={"certified_on": project.certified_at.isoformat(), **(metadata or {})},
        )

    # ── audit-passed admin action ────────────────────────────────────
    #
    # Sesión 3B-2B.6 Cluster 1 Phase 2 · Marcos marca auditoría pasada
    # post entrega ZIP firmado (Phase 1) y feedback auditor ENAC offline.
    # Records audit_result en projects (passed | observed | correction_required
    # | failed) + opcional cadenamiento mark_certified si result == "passed"
    # (chain entrega lifecycle CERTIFIED → trigger retainer offer Phase 3).

    async def mark_audit_passed(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        result: str,
        audit_report_ref: str | None = None,
        performed_by: str = "marcos",
        cascade_certify: bool = True,
        cascade_retainer_offer: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Marca resultado auditoría ENAC · opcional cascade lifecycle CERTIFIED + retainer offer.

        Args:
            result: 'passed' | 'observed' | 'correction_required' | 'failed'
            audit_report_ref: optional reference (e.g. 'E-702-AUD-001')
            performed_by: admin user (default Marcos)
            cascade_certify: si True AND result=='passed' AND NOT yet certified,
                llama mark_certified() chain → emits 'certified' event extra.
            cascade_retainer_offer: si True AND cascade_certify exitoso,
                llama offer_retainer() chain (Sesión 3B-2B.6 Cluster 1 Phase 3).
                Cliente recibe notification in-portal automática post-cert.
                Non-fatal: si falla (sin ClientUser · etc) NO bloquea cert.
            metadata: additional payload audit log

        Returns:
            dict con audit_result + audit_passed_at + certified_event_id (if cascade) +
            retainer_offer_notification_id (if cascade_retainer_offer)
        """
        valid = {"passed", "observed", "correction_required", "failed"}
        if result not in valid:
            raise LifecyclePaso4Error(
                f"result inválido '{result}' · debe ser uno de {sorted(valid)}"
            )

        project = await _get_project_strict(db, project_id)
        if project.audit_passed_at:
            raise LifecyclePaso4Error(
                f"Proyecto ya tiene audit result registrado el {project.audit_passed_at.isoformat()} · "
                f"resultado actual: {project.audit_result}"
            )

        now_dt = datetime.now(timezone.utc)
        project.audit_passed_at = now_dt
        project.audit_passed_by = performed_by
        project.audit_result = result
        project.audit_report_ref = audit_report_ref
        await db.flush()

        event_metadata = {
            "result": result,
            "audit_report_ref": audit_report_ref,
            "audit_passed_at": now_dt.isoformat(),
            **(metadata or {}),
        }
        audit_event = await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="audit_marked", performed_by=performed_by,
            metadata=event_metadata,
        )

        response: dict[str, Any] = {
            "event_id": str(audit_event.id),
            "event_type": audit_event.event_type,
            "result": result,
            "audit_passed_at": now_dt.isoformat(),
            "audit_report_ref": audit_report_ref,
            "lifecycle_state": project.lifecycle_state,
        }

        # Cascade: si passed AND NOT yet certified → chain mark_certified.
        # Esto materializa state transition CERTIFIED y deja path abierto
        # para retainer offer (Phase 3 workflow hook listens audit_marked +
        # result=passed event).
        certify_succeeded = False
        if cascade_certify and result == "passed" and project.certified_at is None:
            try:
                cert_event = await self.mark_certified(
                    db, project_id,
                    performed_by=performed_by,
                    metadata={"triggered_by": "audit_marked", "audit_event_id": str(audit_event.id)},
                )
                response["certified_event_id"] = str(cert_event.id)
                response["lifecycle_state"] = "CERTIFIED"
                certify_succeeded = True
            except LifecyclePaso4Error as exc:
                # Idempotency: already certified · NOT fatal (log only)
                response["certified_skipped_reason"] = str(exc)

        # Sesión 3B-2B.6 Cluster 1 Phase 3 · retainer trigger automation.
        # Si certified ahora (cascade succeeded OR already certified) AND audit
        # result=passed AND cascade_retainer_offer=True · auto-llama offer_retainer
        # con recipient_email derived desde último ClientUser. Non-fatal: failure
        # (NO ClientUser · email mal formed · etc) NO bloquea cert · logged sólo.
        if (
            cascade_retainer_offer
            and result == "passed"
            and (certify_succeeded or project.certified_at is not None)
        ):
            try:
                # Derive recipient_email desde latest ClientUser del project's cliente
                from sqlalchemy import select
                from backend.app.models.client_portal import ClientUser

                user_res = await db.execute(
                    select(ClientUser)
                    .where(ClientUser.client_id == project.client_id)
                    .order_by(ClientUser.created_at.desc())
                    .limit(1),
                )
                client_user = user_res.scalar_one_or_none()
                if client_user is None:
                    response["retainer_offer_skipped_reason"] = (
                        "No hay ClientUser registrado · no se puede enviar oferta"
                    )
                else:
                    offer_result = await self.offer_retainer(
                        db, project_id,
                        recipient_email=client_user.email,
                        performed_by=performed_by,
                    )
                    response["retainer_offer_notification_id"] = offer_result.get(
                        "notification_id"
                    )
                    response["retainer_offer_url"] = offer_result.get("url")
            except LifecyclePaso4Error as exc:
                # Non-fatal · cert ya logged · retainer skip
                response["retainer_offer_skipped_reason"] = str(exc)
            except Exception as exc:  # pragma: no cover · network/DB resilience
                # Defence-in-depth: cualquier error (ImportError · network · etc)
                # NO bloquea audit_marked + certified events ya commit-ready.
                response["retainer_offer_skipped_reason"] = (
                    f"Error inesperado en retainer trigger: {exc}"
                )

        # FIX(wiring): art.31 RD 311/2022 · al pasar la auditoría ENAC de un
        # proyecto MEDIA/ALTA programar la auditoría bienal (730 días).
        # schedule_biannual_audit existía pero NUNCA se invocaba → el aviso de
        # renovación bienal nunca se disparaba automáticamente. BÁSICA es
        # autodeclaración (sin auditoría externa) → excluida. Idempotente +
        # non-fatal (no bloquea cert).
        categoria = str(
            getattr(project, "categoria_objetivo", "") or ""
        ).upper()
        if result == "passed" and categoria in ("MEDIA", "ALTA"):
            try:
                from backend.app.motors.m27_conformity.audit_schedule_service import (  # noqa: E501
                    schedule_biannual_audit,
                )
                sched_id = await schedule_biannual_audit(
                    db, project_id, now_dt.date(),
                    metadata={
                        "triggered_by": "audit_marked",
                        "audit_event_id": str(audit_event.id),
                    },
                )
                response["biannual_audit_schedule_id"] = str(sched_id)
            except Exception as exc:  # pragma: no cover · non-fatal
                response["biannual_audit_skipped_reason"] = str(exc)

        return response

    # ── oferta retainer ──────────────────────────────────────────────

    async def offer_retainer(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        recipient_email: str,
        base_url: str = "https://portal.fulkro.es",
        performed_by: str = "marcos",
    ) -> dict[str, Any]:
        project = await _get_project_strict(db, project_id)
        if not project.certified_at:
            raise LifecyclePaso4Error(
                "Proyecto aun no certificado — no se puede ofertar retainer"
            )

        # Post-MB-4.bis3 (ADR-020 v3): emit ClientNotification in-portal
        # NO magic_link · cliente accede /client-portal/retainer
        from sqlalchemy import select
        from backend.app.models.client_portal import ClientUser
        from backend.app.motors.m21_portal_cliente import (
            notification_service,
        )

        notif = None
        user_res = await db.execute(
            select(ClientUser)
            .where(ClientUser.client_id == project.client_id)
            .order_by(ClientUser.created_at.desc())
            .limit(1),
        )
        client_user = user_res.scalar_one_or_none()
        if client_user is not None:
            notif = await notification_service.emit_client_notification(
                db,
                project_id=project.id,
                client_user_id=client_user.id,
                type="retainer_offer",
                title=f"Oferta retainer disponible · {project.nombre}",
                body=(
                    "Hemos preparado una propuesta de retainer "
                    "post-certificación. Revísala en tu portal."
                ),
                target_url="/client-portal/retainer",
                priority="normal",
                payload={
                    "recommended_tiers": list(VALID_RETAINER_TIERS),
                    "project_name": project.nombre,
                },
                emitted_by_motor="m25",
            )
        await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="retainer_offered", performed_by=performed_by,
            metadata={
                "notification_id": str(notif.id) if notif else None,
                "recipient_email": recipient_email,
                "magic_link_id": None,
            },
            notification_sent_to=[recipient_email],
        )
        return {
            "magic_link_id": None,
            "notification_id": str(notif.id) if notif else None,
            "url": "/client-portal/retainer",
            "expires_at": None,
        }

    async def handle_retainer_decision(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        decision: str,
        tier: str | None = None,
        performed_by: str = "cliente",
        precio_mensual: float = 0.0,
    ) -> dict[str, Any]:
        if decision not in VALID_DECISIONS:
            raise LifecyclePaso4Error(
                f"decision invalida: {decision}. Validas: {VALID_DECISIONS}"
            )
        project = await _get_project_strict(db, project_id)
        if not project.certified_at:
            raise LifecyclePaso4Error("Proyecto no certificado")

        if decision == "accept":
            if tier is None or tier not in VALID_RETAINER_TIERS:
                raise LifecyclePaso4Error(
                    f"Para decision=accept se requiere tier valido: {VALID_RETAINER_TIERS}"
                )
            # Invocar M23 create_retainer
            from backend.app.motors.m23_retainer.retainer_service import (
                RetainerService, RetainerError,
            )
            try:
                existing = await RetainerService().get_retainer_by_project(
                    db, project.id,
                )
                if existing is None:
                    await RetainerService().create_retainer(
                        db,
                        client_id=project.client_id,
                        project_id=project.id,
                        perfil=tier,
                        precio_mensual=precio_mensual,
                        inicio=date.today(),
                    )
            except RetainerError as exc:
                raise LifecyclePaso4Error(
                    f"M23 RetainerService fallo al crear retainer: {exc}"
                ) from exc
            project.lifecycle_state = "RETAINER"
            await db.flush()
            return {
                "decision": "accept",
                "tier": tier,
                "event": (await _log_event(
                    db, project_id=project.id, client_id=project.client_id,
                    event_type="retainer_accepted", performed_by=performed_by,
                    metadata={"tier": tier, "precio_mensual": precio_mensual},
                )).id,
            }

        # decline / thinking -> grace period
        await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="retainer_declined", performed_by=performed_by,
            metadata={"reason": decision},
        )
        event = await self.start_grace_period(
            db, project.id,
            performed_by=performed_by,
            decision=decision,
        )
        return {
            "decision": decision,
            "grace_period_event_id": str(event.id),
        }

    # ── grace period ─────────────────────────────────────────────────

    async def start_grace_period(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        days: int = GRACE_PERIOD_DAYS_DEFAULT,
        started_at: datetime | None = None,
        performed_by: str = "system",
        decision: str | None = None,
    ) -> ProjectLifecycleEvent:
        project = await _get_project_strict(db, project_id)
        started = started_at or _now()
        project.grace_period_started_at = started
        project.grace_period_ends_at = started + timedelta(days=days)
        project.lifecycle_state = "ENDED_CHURN"
        await db.flush()
        return await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="grace_period_started", performed_by=performed_by,
            grace_period_days=days,
            event_date=started,
            metadata={
                "decision": decision,
                "ends_at": project.grace_period_ends_at.isoformat(),
            },
        )

    async def get_lifecycle_status(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> dict[str, Any]:
        project = await _get_project_strict(db, project_id)
        now = _now()

        status: dict[str, Any] = {
            "project_id": str(project.id),
            "project_name": project.nombre,
            "lifecycle_state": project.lifecycle_state,
            "certified_at": project.certified_at.isoformat() if project.certified_at else None,
            "grace_period_started_at": (
                project.grace_period_started_at.isoformat()
                if project.grace_period_started_at else None
            ),
            "grace_period_ends_at": (
                project.grace_period_ends_at.isoformat()
                if project.grace_period_ends_at else None
            ),
            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
        }

        if project.grace_period_started_at:
            elapsed = (now - project.grace_period_started_at).total_seconds() / 86400
            status["grace_days_elapsed"] = int(elapsed)
            status["grace_days_remaining"] = max(
                0, int(
                    (project.grace_period_ends_at - now).total_seconds() / 86400
                ) if project.grace_period_ends_at else 0,
            )
        return status

    async def get_lifecycle_events(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[ProjectLifecycleEvent]:
        res = await db.execute(
            select(ProjectLifecycleEvent)
            .where(ProjectLifecycleEvent.project_id == project_id)
            .order_by(ProjectLifecycleEvent.event_date.asc().nulls_last())
        )
        return list(res.scalars().all())

    # ── backup generation + sending ──────────────────────────────────

    async def generate_project_backup_zip(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        recipient_email: str | None = None,
        base_url: str = "https://portal.fulkro.es",
        performed_by: str = "celery",
        send_magic_link: bool = True,
    ) -> ProjectArchivedBackup:
        project = await _get_project_strict(db, project_id)
        client = await _get_client_strict(db, project.client_id)

        result = await build_and_sign_backup_zip(db, project, client)
        zip_bytes = result["zip_bytes"]
        sha256 = result["sha256"]

        zip_path = upload_backup_to_cold_storage(project.id, zip_bytes, sha256)

        now = _now()
        expires_at = now + timedelta(days=BACKUP_DOWNLOAD_TTL_DAYS)

        # INSERT via SET LOCAL ROLE fulkro_app_bypassrls para salvar RLS
        # (el flujo puede correrse desde celery / Marcos admin sin tenant
        # context cliente establecido)
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            backup = ProjectArchivedBackup(
                project_id=project.id,
                client_id=client.id,
                zip_path=zip_path,
                zip_size_bytes=len(zip_bytes),
                sha256_hash=sha256,
                ed25519_signature=result["signature"],
                ed25519_public_key_pem=result["public_key_pem"],
                manifest_jsonb=result["manifest"],
                generated_at=now,
                expires_at=expires_at,
                download_count=0,
                created_at=now,
            )
            db.add(backup)
            await db.flush()
        finally:
            await db.execute(text("RESET ROLE"))

        magic_link_id: uuid.UUID | None = None
        if send_magic_link and recipient_email:
            ml = await MagicLinkService(db).generate_magic_link(
                MagicLinkGenerateRequest(
                    project_id=project.id,
                    purpose=MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO,
                    recipient_email=recipient_email,
                    scope={
                        "archived_backup_id": str(backup.id),
                        "zip_size_bytes": len(zip_bytes),
                        "sha256": sha256,
                    },
                ),
                base_url=base_url,
            )
            magic_link_id = ml.magic_link_id

        await _log_event(
            db, project_id=project.id, client_id=client.id,
            event_type="backup_generated", performed_by=performed_by,
            backup_zip_path=zip_path,
            backup_signature_ed25519=result["signature"],
            metadata={
                "sha256": sha256,
                "size_bytes": len(zip_bytes),
                "expires_at": expires_at.isoformat(),
                "archived_backup_id": str(backup.id),
            },
        )
        if magic_link_id and recipient_email:
            await _log_event(
                db, project_id=project.id, client_id=client.id,
                event_type="backup_sent", performed_by=performed_by,
                backup_zip_path=zip_path,
                backup_download_magic_link_id=magic_link_id,
                notification_sent_to=[recipient_email],
                metadata={
                    "archived_backup_id": str(backup.id),
                },
            )
        return backup

    # ── warnings (Marcos / cliente) ─────────────────────────────────

    async def send_warning_to_marcos(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        days_remaining: int,
        marcos_email: str = "marcosmata@fulkro.es",
    ) -> ProjectLifecycleEvent:
        project = await _get_project_strict(db, project_id)
        return await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="warning_sent", performed_by="celery",
            metadata={
                "days_remaining": days_remaining,
                "purpose": "contactar_cliente_ultima_oportunidad",
            },
            notification_sent_to=[marcos_email],
        )

    async def send_reconsideration_to_client(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        recipient_email: str,
        base_url: str = "https://portal.fulkro.es",
    ) -> dict[str, Any]:
        project = await _get_project_strict(db, project_id)

        # Post-MB-4.bis3 (ADR-020 v3): emit ClientNotification in-portal
        from sqlalchemy import select
        from backend.app.models.client_portal import ClientUser
        from backend.app.motors.m21_portal_cliente import (
            notification_service,
        )

        notif = None
        user_res = await db.execute(
            select(ClientUser)
            .where(ClientUser.client_id == project.client_id)
            .order_by(ClientUser.created_at.desc())
            .limit(1),
        )
        client_user = user_res.scalar_one_or_none()
        if client_user is not None:
            notif = await notification_service.emit_client_notification(
                db,
                project_id=project.id,
                client_user_id=client_user.id,
                type="retainer_reconsideration",
                title="Última oportunidad: oferta retainer",
                body=(
                    f"Reconsidera la oferta de retainer post-{project.nombre}. "
                    "Esta es la última ventana antes del cierre."
                ),
                target_url="/client-portal/retainer",
                priority="high",
                payload={"project_name": project.nombre},
                emitted_by_motor="m25",
            )
        await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="reconsideration_sent", performed_by="celery",
            metadata={
                "magic_link_id": None,
                "notification_id": str(notif.id) if notif else None,
                "days_into_grace": GRACE_RECONSIDERATION_DAY,
            },
            notification_sent_to=[recipient_email],
        )
        return {
            "magic_link_id": None,
            "notification_id": str(notif.id) if notif else None,
            "url": "/client-portal/retainer",
            "expires_at": None,
        }

    # ── deletion (GDPR) ──────────────────────────────────────────────

    async def delete_project_data(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        performed_by: str = "celery",
        force: bool = False,
        confirm_project_name: str | None = None,
    ) -> ProjectLifecycleEvent:
        """Ejecuta borrado honesto del proyecto tras grace period.

        - SOFT DELETE del proyecto (deleted_at + lifecycle_state=PURGED)
        - HARD DELETE de contenidos personales GDPR:
            documents.full_text_content, documents.storage_path
            evidence.hash_sha256 -> NULL (referencia al binario se
              elimina; los binarios en MinIO se limpian via M07 / WORM)
            findings: eliminan datos identificables
            client_users del cliente se desactivan (client_portal)
        - RETIENE: audit_log, project_archived_backups, lifecycle_events
          para obligaciones contractuales / evidencia regulatoria.

        Segundo gate destructivo (WAVE C1 · §4.1/339):
          ``force=True`` salta TODAS las validaciones del grace period, por
          lo que ya no basta con un único booleano. Para forzar es OBLIGATORIO
          pasar ``confirm_project_name`` con el nombre EXACTO del proyecto
          (patrón "escribe el nombre para confirmar"). Si no coincide se
          rechaza con ``LifecyclePaso4Error``. El path normal de producción
          (grace period vencido, ``force=False``) no necesita confirmación.
        """
        project = await _get_project_strict(db, project_id)
        if force:
            # Segundo gate: confirmación explícita del nombre del proyecto.
            expected = (project.nombre or "").strip()
            provided = (confirm_project_name or "").strip()
            if not provided or provided != expected:
                raise LifecyclePaso4Error(
                    "Borrado forzado requiere confirm_project_name con el "
                    "nombre EXACTO del proyecto (segundo gate destructivo)."
                )
        else:
            if project.deleted_at is not None:
                raise LifecyclePaso4Error("Proyecto ya borrado")
            if project.grace_period_ends_at is None:
                raise LifecyclePaso4Error(
                    "Proyecto sin grace_period_ends_at — no se puede borrar"
                )
            if _now() < project.grace_period_ends_at:
                raise LifecyclePaso4Error(
                    "Grace period aun no finalizado — usa force=True + "
                    "confirm_project_name si realmente quieres forzar"
                )

        now = _now()
        # SET LOCAL ROLE fulkro_app_bypassrls para poder wipe tablas con RLS project
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            # Hard delete personal content (GDPR)
            await db.execute(
                text(
                    "UPDATE documents SET full_text_content = NULL, "
                    "storage_path = NULL, content_hash = NULL "
                    "WHERE project_id = :pid"
                ),
                {"pid": str(project.id)},
            )
            await db.execute(
                text("DELETE FROM evidence WHERE project_id = :pid"),
                {"pid": str(project.id)},
            )
            await db.execute(
                text("DELETE FROM findings WHERE project_id = :pid"),
                {"pid": str(project.id)},
            )
            # Desactivar usuarios cliente portal
            await db.execute(
                text(
                    "UPDATE client_users SET deactivated_at = now() "
                    "WHERE client_id = :cid AND deactivated_at IS NULL"
                ),
                {"cid": str(project.client_id)},
            )
            # Soft delete project
            project.deleted_at = now
            project.lifecycle_state = "PURGED"
            await db.flush()
        finally:
            await db.execute(text("RESET ROLE"))

        return await _log_event(
            db, project_id=project.id, client_id=project.client_id,
            event_type="data_deleted", performed_by=performed_by,
            metadata={
                "deleted_at": now.isoformat(),
                "tables_affected": [
                    "projects (soft)",
                    "documents (content wipe)",
                    "evidence (hard)",
                    "findings (hard)",
                    "client_users (deactivate)",
                ],
                "retained": [
                    "audit_log",
                    "project_archived_backups",
                    "project_lifecycle_events",
                    "invoices",
                ],
                "forced": bool(force),
                "force_confirmed_name": bool(force and confirm_project_name),
            },
        )

    # ── reactivation ─────────────────────────────────────────────────

    async def reactivate_project(
        self,
        db: AsyncSession,
        *,
        archived_backup_id: uuid.UUID,
        performed_by: str = "cliente",
        new_project_name: str | None = None,
    ) -> dict[str, Any]:
        """Reactiva un proyecto cerrado desde el backup.

        Condiciones:
          - backup no ha expirado (expires_at > now)
          - backup no ha sido deleted
        Crea un nuevo Project con lifecycle_state='ACTIVE' heredando
        client_id + nombre base; el manifiesto queda vinculado via el
        evento ``reactivated``.
        """
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            res = await db.execute(
                select(ProjectArchivedBackup).where(
                    ProjectArchivedBackup.id == archived_backup_id,
                )
            )
            backup = res.scalar_one_or_none()
            if backup is None:
                raise LifecyclePaso4Error(
                    f"Archived backup {archived_backup_id} no encontrado"
                )
            now = _now()
            if backup.deleted_at is not None:
                raise LifecyclePaso4Error(
                    "Backup ya eliminado — reactivacion imposible"
                )
            if backup.expires_at and backup.expires_at < now:
                raise LifecyclePaso4Error(
                    f"Backup expiro el {backup.expires_at.isoformat()} — "
                    f"reactivacion imposible"
                )
            client_res = await db.execute(
                select(Client).where(Client.id == backup.client_id),
            )
            client = client_res.scalar_one_or_none()
            if client is None:
                raise LifecyclePaso4Error(
                    f"Client {backup.client_id} no existe — no se puede reactivar"
                )
            old_project_name = (
                backup.manifest_jsonb.get("project_name")
                if backup.manifest_jsonb else None
            )
            new_name = new_project_name or (
                f"{old_project_name} (reactivado)"
                if old_project_name else "Reactivado desde backup"
            )
            new_project = Project(
                client_id=client.id,
                nombre=new_name,
                estado="active",
                lifecycle_state="ACTIVE",
            )
            db.add(new_project)
            await db.flush()

            event = await _log_event(
                db, project_id=new_project.id, client_id=client.id,
                event_type="reactivated", performed_by=performed_by,
                metadata={
                    "source_archived_backup_id": str(backup.id),
                    "source_project_id": str(backup.project_id) if backup.project_id else None,
                    "source_manifest_sha256": (
                        backup.manifest_jsonb.get("signed_digest_sha256")
                        if backup.manifest_jsonb else None
                    ),
                },
            )
            return {
                "new_project_id": str(new_project.id),
                "event_id": str(event.id),
                "backup_id": str(backup.id),
            }
        finally:
            await db.execute(text("RESET ROLE"))


# ══════════════════════════════════════════════════════════════════════
# Celery / scheduler helpers
# ══════════════════════════════════════════════════════════════════════


async def process_grace_period_checkpoints(
    db: AsyncSession,
    *,
    today: datetime | None = None,
    base_url: str = "https://portal.fulkro.es",
    marcos_email: str = "marcosmata@fulkro.es",
) -> dict[str, Any]:
    """Ejecuta los hitos del grace period para todos los proyectos.

    Se invoca desde el Celery task ``lifecycle_grace_period_check`` a
    diario. En cada proyecto en ``ENDED_CHURN`` con grace fields, mira
    dias transcurridos y dispara warning/reconsideration/backup/delete.

    ``today`` se inyecta para fast-forward en demo + tests.
    """
    today = today or _now()
    service = LifecyclePaso4Service()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(Project).where(
                Project.lifecycle_state == "ENDED_CHURN",
                Project.grace_period_started_at.is_not(None),
                Project.deleted_at.is_(None),
            )
        )
        projects = list(res.scalars().all())
    finally:
        await db.execute(text("RESET ROLE"))

    processed = {
        "warning_marcos_sent": [],
        "reconsideration_client_sent": [],
        "backup_generated": [],
        "data_deleted": [],
        "errors": [],
    }

    async def _has_event_for(project_id: uuid.UUID, event_type: str) -> bool:
        res = await db.execute(
            select(ProjectLifecycleEvent.id).where(
                ProjectLifecycleEvent.project_id == project_id,
                ProjectLifecycleEvent.event_type == event_type,
            ).limit(1)
        )
        return res.scalar_one_or_none() is not None

    # Snapshot del tenant context actual para restaurarlo al final
    prev_client = (await db.execute(
        text("SELECT current_setting('app.current_client_id', true)")
    )).scalar()
    prev_project = (await db.execute(
        text("SELECT current_setting('app.current_project_id', true)")
    )).scalar()

    from backend.app.database import set_tenant_context

    for project in projects:
        elapsed_days = int(
            (today - project.grace_period_started_at).total_seconds() / 86400
        )

        # Setamos tenant context para este proyecto (se restaura al final)
        await set_tenant_context(
            db, client_id=project.client_id, project_id=project.id,
        )

        recipient_email = None
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            client_res = await db.execute(
                select(Client).where(Client.id == project.client_id),
            )
            client = client_res.scalar_one_or_none()
            if client and client.contacto_email:
                recipient_email = client.contacto_email
        finally:
            await db.execute(text("RESET ROLE"))

        try:
            if elapsed_days >= GRACE_DELETE_DAY and not await _has_event_for(project.id,
                "data_deleted"
            ):
                await service.delete_project_data(
                    db, project.id, performed_by="celery",
                )
                processed["data_deleted"].append(str(project.id))
                continue  # nada mas que hacer tras borrado

            if elapsed_days >= GRACE_BACKUP_DAY and not await _has_event_for(project.id,
                "backup_generated"
            ):
                await service.generate_project_backup_zip(
                    db, project.id,
                    recipient_email=recipient_email,
                    base_url=base_url,
                    performed_by="celery",
                    send_magic_link=bool(recipient_email),
                )
                processed["backup_generated"].append(str(project.id))

            if elapsed_days >= GRACE_RECONSIDERATION_DAY and not await _has_event_for(project.id,
                "reconsideration_sent"
            ):
                if recipient_email:
                    await service.send_reconsideration_to_client(
                        db, project.id,
                        recipient_email=recipient_email,
                        base_url=base_url,
                    )
                    processed["reconsideration_client_sent"].append(str(project.id))

            if elapsed_days >= GRACE_WARNING_MARCOS_DAY and not await _has_event_for(project.id,
                "warning_sent"
            ):
                days_remaining = max(0, GRACE_DELETE_DAY - elapsed_days)
                await service.send_warning_to_marcos(
                    db, project.id,
                    days_remaining=days_remaining,
                    marcos_email=marcos_email,
                )
                processed["warning_marcos_sent"].append(str(project.id))
        except Exception as exc:  # pragma: no cover
            logger.exception("grace checkpoint fallo en %s", project.id)
            processed["errors"].append({
                "project_id": str(project.id),
                "error": str(exc),
            })

    # Restaurar tenant context previo
    await db.execute(
        text("SELECT set_config('app.current_client_id', :v, true)"),
        {"v": prev_client or ""},
    )
    await db.execute(
        text("SELECT set_config('app.current_project_id', :v, true)"),
        {"v": prev_project or ""},
    )

    return processed


async def process_backup_expirations(
    db: AsyncSession,
    *,
    today: datetime | None = None,
) -> dict[str, Any]:
    """Borra backups ZIP cuyo ``expires_at`` <= today (hard delete MinIO)."""
    today = today or _now()
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(ProjectArchivedBackup).where(
                ProjectArchivedBackup.expires_at <= today,
                ProjectArchivedBackup.deleted_at.is_(None),
            )
        )
        expired = list(res.scalars().all())
        deleted: list[str] = []
        failed: list[str] = []
        for backup in expired:
            ok = delete_backup_from_cold_storage(backup.zip_path)
            backup.deleted_at = today
            await db.flush()
            if ok:
                deleted.append(str(backup.id))
            else:
                failed.append(str(backup.id))
        return {
            "deleted_count": len(deleted),
            "deleted_ids": deleted,
            "failed_ids": failed,
        }
    finally:
        await db.execute(text("RESET ROLE"))


# ══════════════════════════════════════════════════════════════════════
# Admin helpers
# ══════════════════════════════════════════════════════════════════════


async def list_archived_backups_for_client(
    db: AsyncSession, client_id: uuid.UUID,
) -> list[ProjectArchivedBackup]:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(ProjectArchivedBackup).where(
                ProjectArchivedBackup.client_id == client_id,
            ).order_by(ProjectArchivedBackup.generated_at.desc().nulls_last())
        )
        return list(res.scalars().all())
    finally:
        await db.execute(text("RESET ROLE"))


async def get_archived_backup(
    db: AsyncSession, archived_backup_id: uuid.UUID,
) -> ProjectArchivedBackup | None:
    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        res = await db.execute(
            select(ProjectArchivedBackup).where(
                ProjectArchivedBackup.id == archived_backup_id,
            )
        )
        return res.scalar_one_or_none()
    finally:
        await db.execute(text("RESET ROLE"))
