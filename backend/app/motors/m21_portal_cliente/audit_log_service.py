"""AuditLogService · hash chain SHA-256 acciones cliente
(ADR-038 SAN-D MB-14.1).

Chain integrity:
- ``chain_index 0``: ``prev_hash = None``, ``hash_0 = SHA256(canonical_json
  (action_data) + "" + "0")``
- ``chain_index n>0``: ``prev_hash = hash_n-1``, ``hash_n = SHA256(canonical
  _json(action_data) + hash_n-1 + str(n))``

Backward compat (DEC-MB14-1 Opción A): rows pre-MB-14 con
``chain_index NULL`` ignoradas en verificación. Solo opera sobre rows
con ``chain_index NOT NULL`` AND ``project_id == X``.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.client_portal import ClientUserAudit
from backend.app.models.core import Project


class AuditLogService:
    """Audit log granular cliente · hash chain SHA-256."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_action(
        self,
        project_id: UUID,
        client_user_id: UUID,
        action_type: str,
        action_data: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        client_id: Optional[UUID] = None,
    ) -> ClientUserAudit:
        """Registra acción cliente con hash chain.

        Action types canónicos (extendibles):
        - LOGIN · LOGOUT · LOGIN_FAILED
        - VIEW_DASHBOARD · VIEW_TASKS · VIEW_DOCUMENTS · VIEW_CHAT ·
          VIEW_EVIDENCIAS
        - TASK_VIEW · TASK_START · TASK_COMPLETE · TASK_BLOCK
        - EVIDENCE_UPLOAD · EVIDENCE_DELETE
        - DOCUMENT_DOWNLOAD · DOCUMENT_VIEW
        - CHAT_MESSAGE_SEND
        - PROFILE_UPDATE · PASSWORD_CHANGE
          (SAN-E v3.MB-1.1 · 2FA_ENABLE/2FA_DISABLE removed · TOTP off cliente)
        - DATA_EXPORT
        """
        # 0. Derive client_id from project si no provided · RLS coherence
        if client_id is None:
            project = await self.db.get(Project, project_id)
            if project:
                client_id = project.client_id

        # 1. Get last chain_index per project (NOT NULL only)
        last_index = (
            await self.db.execute(
                select(func.max(ClientUserAudit.chain_index))
                .where(ClientUserAudit.project_id == project_id)
                .where(ClientUserAudit.chain_index.is_not(None))
            )
        ).scalar()

        if last_index is None:
            prev_hash = None
            chain_index = 0
        else:
            chain_index = int(last_index) + 1
            prev = (
                await self.db.execute(
                    select(ClientUserAudit.current_hash)
                    .where(ClientUserAudit.project_id == project_id)
                    .where(ClientUserAudit.chain_index == last_index)
                    .limit(1)
                )
            ).scalar()
            prev_hash = prev

        # 2. Compute current hash
        canonical_data = json.dumps(action_data, sort_keys=True, default=str)
        prev_hash_str = prev_hash or ""
        hash_input = f"{canonical_data}|{prev_hash_str}|{chain_index}"
        current_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        # 3. Insert · usa metadata_jsonb existing (alias semántico de
        # action_data del briefing v2 · DEC-MB14-1 reuso).
        audit = ClientUserAudit(
            project_id=project_id,
            client_user_id=client_user_id,
            client_id=client_id,
            action=action_type,
            action_type=action_type,
            metadata_jsonb=action_data,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            prev_hash=prev_hash,
            current_hash=current_hash,
            chain_index=chain_index,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(audit)
        await self.db.flush()
        await self.db.refresh(audit)
        return audit

    async def verify_chain_integrity(
        self, project_id: UUID, max_records: int = 1000,
    ) -> tuple[bool, Optional[int]]:
        """Verifica integridad hash chain per proyecto (rows con
        ``chain_index NOT NULL`` solamente · backward compat MB-14.1).

        Returns:
            (is_valid, broken_at_index)
        """
        records = (
            await self.db.execute(
                select(ClientUserAudit)
                .where(ClientUserAudit.project_id == project_id)
                .where(ClientUserAudit.chain_index.is_not(None))
                .order_by(ClientUserAudit.chain_index)
                .limit(max_records)
            )
        ).scalars().all()
        records = list(records)

        prev_hash: str | None = None
        for record in records:
            canonical = json.dumps(
                record.metadata_jsonb or {}, sort_keys=True, default=str,
            )
            prev_hash_str = prev_hash or ""
            hash_input = f"{canonical}|{prev_hash_str}|{record.chain_index}"
            expected = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            if record.current_hash != expected:
                return (False, record.chain_index)
            if record.prev_hash != prev_hash:
                return (False, record.chain_index)

            prev_hash = record.current_hash

        return (True, None)

    async def list_actions(
        self,
        project_id: UUID,
        client_user_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[ClientUserAudit]:
        """Lista acciones filtradas (admin view)."""
        query = (
            select(ClientUserAudit)
            .where(ClientUserAudit.project_id == project_id)
            .order_by(ClientUserAudit.created_at.desc())
            .limit(limit)
        )
        if client_user_id:
            query = query.where(ClientUserAudit.client_user_id == client_user_id)
        if action_type:
            query = query.where(ClientUserAudit.action_type == action_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def export_chain(self, project_id: UUID) -> dict:
        """Export auditable JSON chain completo · útil auditor externo."""
        records = (
            await self.db.execute(
                select(ClientUserAudit)
                .where(ClientUserAudit.project_id == project_id)
                .where(ClientUserAudit.chain_index.is_not(None))
                .order_by(ClientUserAudit.chain_index)
            )
        ).scalars().all()

        is_valid, broken_at = await self.verify_chain_integrity(project_id)

        return {
            "project_id": str(project_id),
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_integrity": {
                "valid": is_valid,
                "broken_at_index": broken_at,
            },
            "records": [
                {
                    "chain_index": r.chain_index,
                    "action_type": r.action_type or r.action,
                    "action_data": r.metadata_jsonb,
                    "ip_address": str(r.ip_address) if r.ip_address else None,
                    "session_id": r.session_id,
                    "user_agent": r.user_agent,
                    "prev_hash": r.prev_hash,
                    "current_hash": r.current_hash,
                    "created_at": r.created_at.isoformat(),
                    "client_user_id": (
                        str(r.client_user_id) if r.client_user_id else None
                    ),
                }
                for r in records
            ],
        }
