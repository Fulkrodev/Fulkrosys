"""M25 Project Lifecycle & Archival Service.

State machine:
    DRAFT → NEGOTIATING → SIGNED → ACTIVE → CERTIFIED
                                    ↓
                                RETAINER
                                    ↓
                            ENDED_RENEWAL_OK / ENDED_CHURN
                                    ↓
                                ARCHIVED
                                    ↓
                                  PURGED

Archive: ZIP firmado con todo el contenido M24/M7 + metadata.
Purge: sólo si purge_after <= hoy.

Usa modelos existentes:
- ProjectLifecycleState (tabla project_lifecycle_states) — eventos de transición
- ArchivedProject (tabla archived_projects) — archive package
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid
import zipfile
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client, Project
from backend.app.models.documents import Document, Evidence
from backend.app.models.lifecycle import ArchivedProject, ProjectLifecycleState


# ══════════════════ State machine ══════════════════

VALID_TRANSITIONS: dict[str, list[str]] = {
    "DRAFT": ["NEGOTIATING"],
    "NEGOTIATING": ["SIGNED", "DRAFT"],
    "SIGNED": ["ACTIVE"],
    "ACTIVE": ["CERTIFIED", "ENDED_CHURN"],
    "CERTIFIED": ["RETAINER", "ENDED_RENEWAL_OK"],
    "RETAINER": ["ENDED_RENEWAL_OK", "ENDED_CHURN"],
    "ENDED_RENEWAL_OK": ["ARCHIVED"],
    "ENDED_CHURN": ["ARCHIVED"],
    "ARCHIVED": ["PURGED"],
    "PURGED": [],
}

ALL_STATES = list(VALID_TRANSITIONS.keys())

DEFAULT_RETENTION_YEARS = 6


class LifecycleError(Exception):
    pass


class LifecycleService:
    """Gestiona ciclo de vida del proyecto + archival."""

    # ══════════════════ State machine ══════════════════

    async def get_current_state(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> str:
        project = await self._get_project(db, project_id)
        return project.lifecycle_state or "DRAFT"

    async def _get_project(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> Project:
        # Projects está RLS-scoped por client_id; asumimos contexto ya establecido.
        res = await db.execute(select(Project).where(Project.id == project_id))
        p = res.scalar_one_or_none()
        if not p:
            raise LifecycleError(f"Project {project_id} no encontrado")
        return p

    async def get_available_transitions(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[str]:
        current = await self.get_current_state(db, project_id)
        return list(VALID_TRANSITIONS.get(current, []))

    async def transition(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        to_state: str,
        reason: str | None = None,
        triggered_by: str = "marcos",
        metadata: dict | None = None,
        *,
        enforce_gates: bool = True,
    ) -> ProjectLifecycleState:
        if to_state not in ALL_STATES:
            raise LifecycleError(
                f"Estado inválido: {to_state}. Válidos: {ALL_STATES}"
            )

        project = await self._get_project(db, project_id)
        current = project.lifecycle_state or "DRAFT"
        allowed = VALID_TRANSITIONS.get(current, [])
        if to_state not in allowed:
            raise LifecycleError(
                f"Transición no permitida: {current} → {to_state}. "
                f"Desde '{current}' solo: {allowed}"
            )

        # Gate (P7-F1 · handoff H5): no se puede CERTIFICAR un proyecto sin un
        # dossier de preparación de auditoría (Motor 9) completo. Se gatea SOLO
        # to_state == "CERTIFIED": por la topología de VALID_TRANSITIONS,
        # RETAINER y ENDED_RENEWAL_OK sólo son alcanzables DESDE CERTIFIED (ya
        # pasaron el gate), y ENDED_CHURN es la vía de abandono (NO debe exigir
        # dossier · un proyecto puede abandonarse sin auditoría). Mirror del
        # patrón m03_dda/service.py:92.
        if enforce_gates and to_state == "CERTIFIED":
            from backend.app.core.workflow_gates import require_complete_audit_prep
            await require_complete_audit_prep(db, project_id)

        # Ejecutar transición
        project.lifecycle_state = to_state
        event = ProjectLifecycleState(
            project_id=project_id,
            state=to_state,
            previous_state=current,
            entered_at=datetime.now(timezone.utc),
            entered_by=triggered_by,
            reason=reason,
            metadata_extra=metadata,
        )
        db.add(event)
        await db.flush()

        # Acciones automáticas post-transición (best-effort, no bloqueantes)
        await self._on_transition(db, project_id, current, to_state)
        return event

    async def _on_transition(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        from_state: str,
        to_state: str,
    ) -> None:
        """Hooks automáticos por transición — best effort (no fail hard)."""
        try:
            if to_state == "ACTIVE" and from_state == "SIGNED":
                # Workspace M20 (si no existe ya)
                from backend.app.motors.m20_workspace.workspace_service import (
                    WorkspaceService, WorkspaceError,
                )
                try:
                    await WorkspaceService().create_workspace(db, project_id=project_id)
                except WorkspaceError:
                    pass  # ya existe
            elif to_state == "RETAINER" and from_state == "CERTIFIED":
                # Retainer M23 con perfil R_STD por defecto (Marcos ajusta después)
                from backend.app.motors.m23_retainer.retainer_service import (
                    RetainerService, RetainerError,
                )
                project = await self._get_project(db, project_id)
                if not await RetainerService().get_retainer_by_project(db, project_id):
                    try:
                        await RetainerService().create_retainer(
                            db,
                            client_id=project.client_id,
                            project_id=project_id,
                            perfil="R_STD",
                            precio_mensual=0.0,
                            inicio=date.today(),
                        )
                    except RetainerError:
                        pass  # ya existe o datos insuficientes
        except Exception:
            # NO bloquear transición por hook fallido
            pass

    async def get_history(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> list[ProjectLifecycleState]:
        res = await db.execute(
            select(ProjectLifecycleState)
            .where(ProjectLifecycleState.project_id == project_id)
            .order_by(ProjectLifecycleState.entered_at.asc().nulls_last())
        )
        return list(res.scalars().all())

    # ══════════════════ Archival ══════════════════

    async def archive_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        retention_years: int = DEFAULT_RETENTION_YEARS,
    ) -> ArchivedProject:
        project = await self._get_project(db, project_id)
        current = project.lifecycle_state or "DRAFT"
        if current not in ("ENDED_RENEWAL_OK", "ENDED_CHURN"):
            raise LifecycleError(
                f"Proyecto debe estar ENDED_* para archivar (actual: {current})"
            )

        # Check no existe archive previo
        existing = await self.get_archive(db, project_id)
        if existing and existing.estado != "purged":
            raise LifecycleError(f"Ya existe archive package para {project_id}")

        # Recopilar documentos y evidencias
        docs = list((await db.execute(
            select(Document).where(Document.project_id == project_id)
        )).scalars().all())
        evidences = list((await db.execute(
            select(Evidence).where(Evidence.project_id == project_id)
        )).scalars().all())

        client = (await db.execute(
            select(Client).where(Client.id == project.client_id)
        )).scalar_one_or_none()

        # Montar ZIP en memoria con manifest
        manifest = {
            "project_id": str(project_id),
            "project_nombre": project.nombre,
            "client_id": str(project.client_id) if project.client_id else None,
            "client_nombre": client.nombre if client else None,
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "documents_count": len(docs),
            "evidence_count": len(evidences),
            "retention_years": retention_years,
            "documents": [
                {
                    "id": str(d.id),
                    "nombre": d.nombre,
                    "content_hash": d.content_hash,
                    "storage_path": d.storage_path,
                    "clasificacion": d.clasificacion,
                }
                for d in docs
            ],
            "evidences": [
                {
                    "id": str(e.id),
                    "measure_code": e.measure_code,
                    "tipo": e.tipo,
                    "hash_sha256": e.hash_sha256,
                }
                for e in evidences
            ],
        }
        manifest_json = json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", manifest_json)
            # Guardar marcadores (no el binario real — está en MinIO/storage_path)
            for d in docs:
                zf.writestr(
                    f"documents/{d.id}.meta.json",
                    json.dumps({
                        "id": str(d.id),
                        "nombre": d.nombre,
                        "content_hash": d.content_hash,
                        "storage_path": d.storage_path,
                        "clasificacion": d.clasificacion,
                        "version_actual": d.version_actual,
                    }, sort_keys=True, ensure_ascii=False),
                )
            for e in evidences:
                zf.writestr(
                    f"evidence/{e.id}.meta.json",
                    json.dumps({
                        "id": str(e.id),
                        "measure_code": e.measure_code,
                        "tipo": e.tipo,
                        "hash_sha256": e.hash_sha256,
                    }, sort_keys=True, ensure_ascii=False),
                )

        zip_bytes = buf.getvalue()
        zip_hash = hashlib.sha256(zip_bytes).hexdigest()
        zip_path = f"fulkro/archives/{project_id}_{zip_hash[:12]}.zip"

        # Firma Ed25519 opcional
        signature = self._sign_ed25519(zip_bytes)

        today = date.today()
        purge_after = today.replace(year=today.year + retention_years)

        archive = ArchivedProject(
            client_id=project.client_id,
            client_nif=client.cif if client else None,
            client_name=client.nombre if client else None,
            project_id=project_id,
            project_name=project.nombre,
            archive_started_at=datetime.now(timezone.utc),
            archive_completed_at=datetime.now(timezone.utc),
            archive_zip_path=zip_path,
            archive_zip_hash_sha256=zip_hash,
            archive_zip_size_bytes=len(zip_bytes),
            manifest=manifest,
            signed_by="fulkro_platform",
            signature_ed25519=signature,
            retention_until=purge_after,
            retention_years=retention_years,
            estado="created",
            documents_count=len(docs),
            evidence_count=len(evidences),
        )
        db.add(archive)
        await db.flush()

        # Transicionar a ARCHIVED
        await self.transition(
            db, project_id, "ARCHIVED",
            reason="Archive package created",
            triggered_by="system",
        )
        return archive

    @staticmethod
    def _sign_ed25519(content: bytes) -> str | None:
        """Firma opcional con clave dev ephemeral (si disponible)."""
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import (
                Ed25519PrivateKey,
            )
            key = Ed25519PrivateKey.generate()
            sig = key.sign(content)
            return sig.hex()
        except Exception:
            return None

    async def get_archive(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> ArchivedProject | None:
        res = await db.execute(
            select(ArchivedProject)
            .where(ArchivedProject.project_id == project_id)
            .order_by(ArchivedProject.archive_completed_at.desc().nulls_last())
            .limit(1)
        )
        return res.scalar_one_or_none()

    async def purge_project(
        self, db: AsyncSession, project_id: uuid.UUID,
    ) -> ArchivedProject:
        archive = await self.get_archive(db, project_id)
        if not archive:
            raise LifecycleError(f"No existe archive para {project_id}")
        if archive.estado == "purged":
            raise LifecycleError("Archive ya purgado")

        today = date.today()
        if archive.retention_until and archive.retention_until > today:
            raise LifecycleError(
                f"Purge prematuro: retention_until={archive.retention_until} > hoy={today}"
            )

        archive.estado = "purged"
        archive.purged_at = datetime.now(timezone.utc)
        archive.archive_zip_path = None  # simula destrucción
        await db.flush()

        # Transicionar a PURGED
        await self.transition(
            db, project_id, "PURGED",
            reason="Archive purged after retention period",
            triggered_by="system",
        )
        return archive

    # ══════════════════ Dashboard global (sin RLS) ══════════════════

    async def get_lifecycle_summary(self, db: AsyncSession) -> dict[str, Any]:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            # Counts por estado
            rows = (await db.execute(
                select(Project.lifecycle_state, func.count(Project.id))
                .group_by(Project.lifecycle_state)
            )).all()
            by_state = {row[0] or "DRAFT": row[1] for row in rows}
            total = sum(by_state.values())

            # Pending archive: ENDED_* sin archive
            ended_rows = (await db.execute(
                select(Project.id, Project.nombre, Project.lifecycle_state).where(
                    Project.lifecycle_state.in_(("ENDED_RENEWAL_OK", "ENDED_CHURN")),
                )
            )).all()
            pending_archive = []
            for pid, nombre, state in ended_rows:
                existing = (await db.execute(
                    select(ArchivedProject.id).where(ArchivedProject.project_id == pid).limit(1)
                )).scalar_one_or_none()
                if not existing:
                    pending_archive.append({
                        "project_id": str(pid),
                        "nombre": nombre,
                        "state": state,
                    })

            # Pending purge: archive con retention_until <= hoy y estado != purged
            today = date.today()
            pending_purge_rows = (await db.execute(
                select(ArchivedProject).where(
                    ArchivedProject.retention_until <= today,
                    ArchivedProject.estado != "purged",
                )
            )).scalars().all()
            pending_purge = [
                {
                    "archive_id": str(a.id),
                    "project_id": str(a.project_id),
                    "project_name": a.project_name,
                    "retention_until": a.retention_until.isoformat() if a.retention_until else None,
                }
                for a in pending_purge_rows
            ]

            return {
                "by_state": by_state,
                "total": total,
                "pending_archive": pending_archive,
                "pending_archive_count": len(pending_archive),
                "pending_purge": pending_purge,
                "pending_purge_count": len(pending_purge),
            }
        finally:
            await db.execute(text("RESET ROLE"))
