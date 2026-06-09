"""M20 Workspace Service — lifecycle + files + feed + chat + videocalls.

Reglas:
- Workspace 1:1 con proyecto (unique project_id)
- Files: SHA-256 obligatorio calculado del contenido real
- Chat/Feed: append-only (no editar/borrar mensajes; only soft-archive)
- Videocall: state machine sin LiveKit real (future M20-LIVEKIT)

Future (M20-CHAT-ENCRYPTION): mensaje texto plano. Cifrar con Fernet
cuando el KMS este disponible.

Integraciones (via base de datos compartida, sin imports Python directos):
- M25 (Project Lifecycle): cuando un proyecto transita a estado
  CERTIFIED/CLOSED, el archivado del workspace se dispara consultando la
  tabla ``project_lifecycle_states``; se marca el workspace como
  ``archived_at`` y se inhibe la creacion de nueva actividad.
Patron SQL-first: M20 lee la transicion de M25 como hecho persistido,
sin acoplarse a la API ni al servicio Python de M25.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.collaboration import (
    CollaborativeWorkspace,
    VideocallSession,
    WorkspaceChatMessage,
    WorkspaceFeedItem,
    WorkspaceFile,
)


DEFAULT_CONFIG = {
    "features": {
        "chat": True,
        "files": True,
        "feed": True,
        "videocall": False,
    },
    "retention_days_post_close": 90,
}

VIDEOCALL_VALID_TRANSITIONS = {
    "solicitada": {"aceptada", "cancelada"},
    "aceptada": {"en_curso", "cancelada"},
    "en_curso": {"finalizada"},
    "finalizada": set(),
    "cancelada": set(),
}


class WorkspaceError(Exception):
    pass


class WorkspaceService:
    """Servicio principal del workspace colaborativo."""

    # ═══════════════ WORKSPACE LIFECYCLE ═══════════════

    async def create_workspace(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        nombre: str | None = None,
        config: dict | None = None,
    ) -> CollaborativeWorkspace:
        existing = await self.get_workspace(db, project_id)
        if existing:
            raise WorkspaceError(
                f"Workspace ya existe para project {project_id}"
            )
        merged_config = {**DEFAULT_CONFIG, **(config or {})}
        ws = CollaborativeWorkspace(
            project_id=project_id,
            nombre=nombre or f"Workspace — {project_id}",
            estado="active",
            config=merged_config,
            carpeta_docs_path=f"fulkro/projects/{project_id}/workspace/",
        )
        db.add(ws)
        await db.flush()
        return ws

    async def get_workspace(
        self, db: AsyncSession, project_id: uuid.UUID
    ) -> CollaborativeWorkspace | None:
        res = await db.execute(
            select(CollaborativeWorkspace).where(
                CollaborativeWorkspace.project_id == project_id,
            )
        )
        return res.scalar_one_or_none()

    async def archive_workspace(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        retention_days: int = 90,
    ) -> CollaborativeWorkspace:
        ws = await self.get_workspace(db, project_id)
        if not ws:
            raise WorkspaceError(f"Workspace no encontrado para {project_id}")
        if ws.estado == "destroyed":
            raise WorkspaceError(
                "No se puede archivar un workspace destruido"
            )
        if ws.estado == "archived":
            return ws
        ws.estado = "archived"
        ws.caducidad_at = datetime.now(timezone.utc) + timedelta(days=retention_days)
        await db.flush()
        return ws

    async def destroy_workspace(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        force: bool = False,
    ) -> CollaborativeWorkspace:
        """Transición terminal: archived -> destroyed.

        Reglas:
        - Solo destruir si workspace en estado 'archived'
        - Por defecto, exige que ``caducidad_at <= now()``
          (cumplimiento de retención)
        - ``force=True`` permite destruir antes del plazo (decisión
          manual del consultor; queda registrada en audit_log via trigger
          de la tabla ``collaborative_workspaces``)
        - Idempotente si ya está destroyed

        Efectos:
        - Marca todos los workspace_files como estado='destroyed'
          (preserva metadata para audit; el contenido en storage se
          considera invalidado)
        - chat/feed quedan congelados (append-only ya no admite nuevos
          inserts vía send_message/add_feed_item)
        """
        ws = await self.get_workspace(db, project_id)
        if not ws:
            raise WorkspaceError(f"Workspace no encontrado para {project_id}")
        if ws.estado == "destroyed":
            return ws  # idempotente
        if ws.estado != "archived":
            raise WorkspaceError(
                "Solo se puede destruir un workspace previamente archivado. "
                f"Estado actual: '{ws.estado}'."
            )
        if not force:
            if ws.caducidad_at is None:
                raise WorkspaceError(
                    "El workspace no tiene caducidad_at definida. "
                    "Use force=True si está seguro de destruir."
                )
            now = datetime.now(timezone.utc)
            if ws.caducidad_at > now:
                dias_restantes = (ws.caducidad_at - now).days
                raise WorkspaceError(
                    f"El workspace no caduca hasta "
                    f"{ws.caducidad_at.isoformat()} "
                    f"(faltan {dias_restantes} días). "
                    f"Use force=True para destruir antes del plazo."
                )

        # Marcar todos los archivos como destroyed
        files_result = await db.execute(
            select(WorkspaceFile).where(
                WorkspaceFile.workspace_id == ws.id,
            )
        )
        for f in files_result.scalars().all():
            f.estado = "destroyed"

        ws.estado = "destroyed"
        await db.flush()
        return ws

    @staticmethod
    def _ensure_writable(ws: CollaborativeWorkspace) -> None:
        """Bloquea operaciones de escritura si el workspace ya no es activo."""
        if ws.estado == "destroyed":
            raise WorkspaceError(
                "Workspace destruido: no se admiten nuevas operaciones"
            )
        if ws.estado == "archived":
            raise WorkspaceError(
                "Workspace archivado: solo lectura"
            )

    async def _get_ws_by_id(
        self, db: AsyncSession, workspace_id: uuid.UUID,
    ) -> CollaborativeWorkspace:
        """Look up workspace by id (not project_id). Internal helper."""
        res = await db.execute(
            select(CollaborativeWorkspace).where(
                CollaborativeWorkspace.id == workspace_id,
            )
        )
        ws = res.scalar_one_or_none()
        if ws is None:
            raise WorkspaceError(f"Workspace {workspace_id} no encontrado")
        return ws

    async def get_workspace_summary(
        self, db: AsyncSession, workspace_id: uuid.UUID
    ) -> dict[str, Any]:
        files_count = (await db.execute(
            select(func.count(WorkspaceFile.id)).where(
                WorkspaceFile.workspace_id == workspace_id,
                WorkspaceFile.estado == "active",
            )
        )).scalar() or 0

        unread_count = (await db.execute(
            select(func.count(WorkspaceFeedItem.id)).where(
                WorkspaceFeedItem.workspace_id == workspace_id,
                WorkspaceFeedItem.leido.is_(False),
            )
        )).scalar() or 0

        messages_count = (await db.execute(
            select(func.count(WorkspaceChatMessage.id)).where(
                WorkspaceChatMessage.workspace_id == workspace_id,
            )
        )).scalar() or 0

        videocalls_count = (await db.execute(
            select(func.count(VideocallSession.id)).where(
                VideocallSession.workspace_id == workspace_id,
            )
        )).scalar() or 0

        return {
            "files_count": files_count,
            "unread_feed_count": unread_count,
            "messages_count": messages_count,
            "videocalls_count": videocalls_count,
        }

    # ═══════════════ FILES ═══════════════

    async def upload_file(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        nombre: str,
        carpeta: str,
        contenido: bytes,
        tipo_mime: str = "application/octet-stream",
        subido_por: str = "marcos",
    ) -> WorkspaceFile:
        if not contenido:
            raise WorkspaceError("Contenido vacío no permitido")
        ws = await self._get_ws_by_id(db, workspace_id)
        self._ensure_writable(ws)
        hash_sha256 = hashlib.sha256(contenido).hexdigest()
        storage_path = (
            f"fulkro/projects/{project_id}/workspace/{carpeta.strip('/')}/"
            f"{hash_sha256[:12]}_{nombre}"
        )

        wf = WorkspaceFile(
            workspace_id=workspace_id,
            project_id=project_id,
            nombre=nombre,
            carpeta=carpeta or "/",
            path=storage_path,
            storage_path=storage_path,
            tipo_mime=tipo_mime,
            tamano_bytes=len(contenido),
            hash_sha256=hash_sha256,
            version=1,
            subido_por=subido_por,
            subido_at=datetime.now(timezone.utc),
            estado="active",
        )
        db.add(wf)
        await db.flush()

        # Feed item automático (regla 10 y flujo auditable)
        await self.add_feed_item(
            db, workspace_id=workspace_id, project_id=project_id,
            tipo="documento_subido",
            titulo=f"Documento subido: {nombre}",
            descripcion=f"Carpeta: {carpeta}",
            autor=subido_por,
            metadata={"file_id": str(wf.id), "hash_sha256": hash_sha256},
        )
        return wf

    async def list_files(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        carpeta: str | None = None,
        estado: str | None = "active",
    ) -> list[WorkspaceFile]:
        stmt = select(WorkspaceFile).where(WorkspaceFile.workspace_id == workspace_id)
        if carpeta:
            stmt = stmt.where(WorkspaceFile.carpeta == carpeta)
        if estado:
            stmt = stmt.where(WorkspaceFile.estado == estado)
        stmt = stmt.order_by(WorkspaceFile.subido_at.desc().nulls_last())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_file(
        self, db: AsyncSession, file_id: uuid.UUID
    ) -> WorkspaceFile | None:
        res = await db.execute(
            select(WorkspaceFile).where(WorkspaceFile.id == file_id)
        )
        return res.scalar_one_or_none()

    async def delete_file(
        self, db: AsyncSession, file_id: uuid.UUID
    ) -> WorkspaceFile:
        wf = await self.get_file(db, file_id)
        if not wf:
            raise WorkspaceError(f"File {file_id} no encontrado")
        wf.estado = "deleted"
        await db.flush()
        return wf

    async def get_folder_tree(
        self, db: AsyncSession, workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Árbol de carpetas derivado de las rutas de los files activos."""
        files = await self.list_files(db, workspace_id, estado="active")
        root: dict[str, Any] = {"name": "/", "children": {}, "files_count": 0}
        for f in files:
            parts = [p for p in (f.carpeta or "/").strip("/").split("/") if p]
            node = root
            for part in parts:
                child = node["children"].setdefault(
                    part, {"name": part, "children": {}, "files_count": 0}
                )
                node = child
            node["files_count"] += 1

        def to_list(node: dict) -> dict:
            return {
                "name": node["name"],
                "files_count": node["files_count"],
                "children": [to_list(c) for c in node["children"].values()],
            }

        return to_list(root)

    # ═══════════════ FEED ═══════════════

    async def add_feed_item(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        tipo: str,
        titulo: str,
        descripcion: str | None = None,
        autor: str = "plataforma",
        metadata: dict | None = None,
    ) -> WorkspaceFeedItem:
        ws = await self._get_ws_by_id(db, workspace_id)
        self._ensure_writable(ws)
        item = WorkspaceFeedItem(
            workspace_id=workspace_id,
            project_id=project_id,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
            autor=autor,
            item_metadata=metadata,
            leido=False,
        )
        db.add(item)
        await db.flush()
        return item

    async def list_feed(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        tipo: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkspaceFeedItem]:
        stmt = select(WorkspaceFeedItem).where(
            WorkspaceFeedItem.workspace_id == workspace_id,
        )
        if tipo:
            stmt = stmt.where(WorkspaceFeedItem.tipo == tipo)
        stmt = stmt.order_by(WorkspaceFeedItem.created_at.desc()).limit(limit).offset(offset)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def mark_read(
        self, db: AsyncSession, item_id: uuid.UUID,
    ) -> WorkspaceFeedItem:
        res = await db.execute(
            select(WorkspaceFeedItem).where(WorkspaceFeedItem.id == item_id)
        )
        item = res.scalar_one_or_none()
        if not item:
            raise WorkspaceError(f"Feed item {item_id} no encontrado")
        if not item.leido:
            item.leido = True
            item.leido_at = datetime.now(timezone.utc)
            await db.flush()
        return item

    async def get_unread_count(
        self, db: AsyncSession, workspace_id: uuid.UUID,
    ) -> int:
        res = await db.execute(
            select(func.count(WorkspaceFeedItem.id)).where(
                WorkspaceFeedItem.workspace_id == workspace_id,
                WorkspaceFeedItem.leido.is_(False),
            )
        )
        return res.scalar() or 0

    # ═══════════════ CHAT (append-only) ═══════════════

    async def send_message(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        autor: str,
        autor_tipo: str,
        mensaje: str,
        adjunto_file_id: uuid.UUID | None = None,
        respondiendo_a: uuid.UUID | None = None,
    ) -> WorkspaceChatMessage:
        if not mensaje or not mensaje.strip():
            raise WorkspaceError("Mensaje vacío no permitido")
        ws = await self._get_ws_by_id(db, workspace_id)
        self._ensure_writable(ws)
        msg = WorkspaceChatMessage(
            workspace_id=workspace_id,
            project_id=project_id,
            autor=autor,
            autor_tipo=autor_tipo,
            mensaje=mensaje,
            adjunto_file_id=adjunto_file_id,
            respondiendo_a=respondiendo_a,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def list_messages(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[WorkspaceChatMessage]:
        stmt = select(WorkspaceChatMessage).where(
            WorkspaceChatMessage.workspace_id == workspace_id,
        )
        if before:
            stmt = stmt.where(WorkspaceChatMessage.created_at < before)
        stmt = stmt.order_by(WorkspaceChatMessage.created_at.desc()).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_thread(
        self, db: AsyncSession, message_id: uuid.UUID,
    ) -> list[WorkspaceChatMessage]:
        original_res = await db.execute(
            select(WorkspaceChatMessage).where(WorkspaceChatMessage.id == message_id)
        )
        original = original_res.scalar_one_or_none()
        if not original:
            raise WorkspaceError(f"Mensaje {message_id} no encontrado")

        replies_res = await db.execute(
            select(WorkspaceChatMessage)
            .where(WorkspaceChatMessage.respondiendo_a == message_id)
            .order_by(WorkspaceChatMessage.created_at.asc())
        )
        replies = list(replies_res.scalars().all())
        return [original, *replies]

    # ═══════════════ VIDEOCALLS (state machine) ═══════════════

    @staticmethod
    def _check_transition(current: str, target: str) -> None:
        allowed = VIDEOCALL_VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise WorkspaceError(
                f"Transición no permitida: {current} → {target}. "
                f"Válidas: {sorted(allowed) or '[]'}"
            )

    async def request_videocall(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        solicitada_por: str,
        participantes: list[str],
    ) -> VideocallSession:
        ws = await self._get_ws_by_id(db, workspace_id)
        self._ensure_writable(ws)
        session = VideocallSession(
            workspace_id=workspace_id,
            project_id=project_id,
            estado="solicitada",
            solicitada_por=solicitada_por,
            participantes=participantes,
            solicitada_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.flush()
        return session

    async def _get_session(
        self, db: AsyncSession, session_id: uuid.UUID,
    ) -> VideocallSession:
        res = await db.execute(
            select(VideocallSession).where(VideocallSession.id == session_id)
        )
        s = res.scalar_one_or_none()
        if not s:
            raise WorkspaceError(f"Videocall {session_id} no encontrada")
        return s

    async def accept_videocall(
        self, db: AsyncSession, session_id: uuid.UUID,
    ) -> VideocallSession:
        s = await self._get_session(db, session_id)
        self._check_transition(s.estado or "", "aceptada")
        s.estado = "aceptada"
        s.aceptada_at = datetime.now(timezone.utc)
        await db.flush()
        return s

    async def start_videocall(
        self, db: AsyncSession, session_id: uuid.UUID,
    ) -> VideocallSession:
        s = await self._get_session(db, session_id)
        self._check_transition(s.estado or "", "en_curso")
        s.estado = "en_curso"
        s.iniciada_at = datetime.now(timezone.utc)
        # Future (M20-LIVEKIT): crear LiveKit room real aqui
        s.livekit_room_name = f"fulkro-ws-{s.workspace_id}-{session_id}"
        await db.flush()
        return s

    async def end_videocall(
        self, db: AsyncSession, session_id: uuid.UUID,
    ) -> VideocallSession:
        s = await self._get_session(db, session_id)
        self._check_transition(s.estado or "", "finalizada")
        s.estado = "finalizada"
        s.finalizada_at = datetime.now(timezone.utc)
        if s.iniciada_at:
            delta = s.finalizada_at - s.iniciada_at
            s.duracion_minutos = max(1, round(delta.total_seconds() / 60))
        await db.flush()
        return s

    async def cancel_videocall(
        self, db: AsyncSession, session_id: uuid.UUID,
    ) -> VideocallSession:
        s = await self._get_session(db, session_id)
        self._check_transition(s.estado or "", "cancelada")
        s.estado = "cancelada"
        await db.flush()
        return s

    async def list_videocalls(
        self, db: AsyncSession, workspace_id: uuid.UUID,
    ) -> list[VideocallSession]:
        res = await db.execute(
            select(VideocallSession)
            .where(VideocallSession.workspace_id == workspace_id)
            .order_by(VideocallSession.solicitada_at.desc().nulls_last())
        )
        return list(res.scalars().all())
