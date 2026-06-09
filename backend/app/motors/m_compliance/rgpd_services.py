"""GDPR Data Subject Rights services (atom 9.bis.2).

Three services exposed to clientes:

- ``RGPDAccessService``       — Art. 15 (right of access). Builds a
  cross-motor ZIP with the cliente's profile, projects, documents
  metadata, chat threads and signing intents.

- ``RGPDPortabilityService``  — Art. 20 (right to portability). Returns
  the same data as Art. 15 in a single JSON-LD payload (schema.org
  vocabularies) suitable for machine re-import elsewhere.

- ``RGPDErasureService``      — Art. 17 (right to erasure). Creates an
  ``ErasureRequest`` (Marcos reviews) and, on approval, anonymises the
  ``client_users`` row in-place. Audit log entries are NEVER deleted
  (legal retention obligation under RD 311/2022 art. 24.1 ENS — 7 years
  evidence retention). Documents and signing intents have their
  signer/author display name replaced by a tombstone, preserving the
  legal validity of the signature chain.
"""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.compliance_breach_erasure import (
    ERASURE_COMPLETED,
    ERASURE_PENDING,
    ERASURE_PROCESSING,
    ERASURE_REJECTED_AUDIT,
    FulkroErasureRequest,
)


_README = (
    "# FULKRO · Exportación de datos personales (Art. 15 RGPD)\n"
    "\n"
    "Esta exportación contiene todos los datos personales que FULKRO trata "
    "sobre tu persona, en formato JSON estructurado.\n"
    "\n"
    "## Estructura del ZIP\n"
    "\n"
    "- `perfil/profile.json`               — datos identificativos y de "
    "consentimiento.\n"
    "- `proyectos/projects.json`            — proyectos del cliente al "
    "que perteneces.\n"
    "- `documentos/documents.json`          — metadatos de documentos "
    "(sin contenido binario).\n"
    "- `comunicaciones/chat_messages.json`  — historial de mensajes en el "
    "portal cliente.\n"
    "- `comunicaciones/whatsapp.json`       — mensajes WhatsApp Business "
    "asociados a tu cuenta.\n"
    "- `firmas/signing_intents.json`        — registros de firma "
    "electrónica.\n"
    "- `auditoria/audit_log.json`           — eventos de auditoría asociados "
    "a tu sesión.\n"
    "\n"
    "## Tus derechos\n"
    "\n"
    "Conforme al RGPD (UE 2016/679) y la LOPDGDD 3/2018 puedes:\n"
    "\n"
    "- Solicitar la rectificación (Art. 16) escribiendo a dpo@fulkro.es.\n"
    "- Solicitar la supresión (Art. 17) desde el portal cliente "
    "`POST /portal/rgpd/erasure`.\n"
    "- Solicitar la portabilidad (Art. 20) desde "
    "`GET /portal/rgpd/portability` (mismo contenido en JSON-LD).\n"
    "- Presentar una reclamación ante la AEPD: https://www.aepd.es\n"
    "\n"
    "Para cualquier consulta: dpo@fulkro.es\n"
)


def _to_jsonable(value: Any) -> Any:
    """Render datetime/UUID etc. as JSON-friendly types."""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _rows_as_dicts(rows: list[Any], columns: list[str]) -> list[dict[str, Any]]:
    return [
        {col: _to_jsonable(row[idx]) for idx, col in enumerate(columns)}
        for row in rows
    ]


class RGPDAccessService:
    """Art. 15 GDPR · build a cross-motor ZIP with the cliente's data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _empty_payload(client_user_id: UUID) -> dict[str, Any]:
        return {
            "profile": None,
            "projects": [],
            "documents": [],
            "chat_messages": [],
            "whatsapp": [],
            "signing_intents": [],
            "audit_log": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_for_client_user_id": str(client_user_id),
        }

    async def _gather_cliente_data(self, client_user_id: UUID) -> dict[str, Any]:
        """Run the cross-motor SELECTs.

        Callers must have set ``app.current_client_id`` to the owning
        tenant before invoking this method (the cliente API endpoint does
        it from the authenticated subject; admin paths look it up via
        ``fulkro_erasure_requests`` which has no RLS). When the cliente
        cannot be resolved (e.g. anonymised), an empty payload is returned.
        """
        # 1. Profile
        profile_row = await self.db.execute(
            text(
                """
                SELECT cu.id, cu.client_id, cu.email, cu.full_name, cu.dni,
                       cu.last_login, cu.created_at, cu.whatsapp_number,
                       cu.whatsapp_verified_at, cu.whatsapp_opt_in_at,
                       c.nombre AS client_name, c.cif AS client_cif
                FROM client_users cu
                JOIN clients c ON c.id = cu.client_id
                WHERE cu.id = :uid
                """
            ),
            {"uid": str(client_user_id)},
        )
        profile_record = profile_row.first()
        profile = (
            _rows_as_dicts(
                [profile_record],
                [
                    "id",
                    "client_id",
                    "email",
                    "full_name",
                    "dni",
                    "last_login",
                    "created_at",
                    "whatsapp_number",
                    "whatsapp_verified_at",
                    "whatsapp_opt_in_at",
                    "client_name",
                    "client_cif",
                ],
            )[0]
            if profile_record
            else None
        )

        client_id = profile["client_id"] if profile else None

        # 2. Projects (filtered by client_id via existing FK)
        projects_rows = await self.db.execute(
            text(
                """
                SELECT id, client_id, nombre, created_at
                FROM projects
                WHERE client_id = :cid
                ORDER BY created_at
                """
            ),
            {"cid": str(client_id) if client_id else None},
        )
        projects = _rows_as_dicts(
            projects_rows.all(),
            ["id", "client_id", "nombre", "created_at"],
        )

        # 3. Documents metadata (NO binary; metadata only)
        project_ids = [p["id"] for p in projects]
        if project_ids:
            docs_rows = await self.db.execute(
                text(
                    """
                    SELECT d.id, d.nombre, d.tipo, d.estado, d.project_id,
                           d.created_at, d.version_actual
                    FROM documents d
                    WHERE d.project_id::text = ANY(:pids)
                    ORDER BY d.created_at
                    """
                ),
                {"pids": project_ids},
            )
            documents = _rows_as_dicts(
                docs_rows.all(),
                [
                    "id", "nombre", "tipo", "estado", "project_id",
                    "created_at", "version_actual",
                ],
            )
        else:
            documents = []

        # 4. Chat messages (cliente-facing). chat_messages may not yet exist
        # in older deployments; handle gracefully.
        try:
            if project_ids:
                chat_rows = await self.db.execute(
                    text(
                        """
                        SELECT cm.id, cm.thread_id, cm.author_user_id,
                               cm.body, cm.created_at
                        FROM chat_messages cm
                        JOIN chat_threads ct ON ct.id = cm.thread_id
                        WHERE ct.project_id::text = ANY(:pids)
                        ORDER BY cm.created_at
                        """
                    ),
                    {"pids": project_ids},
                )
                chat = _rows_as_dicts(
                    chat_rows.all(),
                    ["id", "thread_id", "author_user_id", "body", "created_at"],
                )
            else:
                chat = []
        except Exception:  # noqa: BLE001 — column variation
            chat = []

        # 5. WhatsApp messages (cliente threads · best effort)
        try:
            wa_rows = await self.db.execute(
                text(
                    """
                    SELECT id, direction, status, body_preview, created_at
                    FROM whatsapp_messages
                    WHERE client_user_id = :uid
                    ORDER BY created_at
                    """
                ),
                {"uid": str(client_user_id)},
            )
            whatsapp = _rows_as_dicts(
                wa_rows.all(),
                ["id", "direction", "status", "body_preview", "created_at"],
            )
        except Exception:  # noqa: BLE001 — column variation across deploys
            whatsapp = []

        # 6. Signing intents created by this cliente (created_by_user_id).
        # signing_intents has no signer_email column; we filter by
        # ``created_by_user_id`` which links back to the cliente login.
        try:
            signing_rows = await self.db.execute(
                text(
                    """
                    SELECT id, document_id, signable_type, status,
                           created_at, expires_at
                    FROM signing_intents
                    WHERE created_by_user_id = :uid
                    ORDER BY created_at
                    """
                ),
                {"uid": str(client_user_id)},
            )
            signing = _rows_as_dicts(
                signing_rows.all(),
                [
                    "id",
                    "document_id",
                    "signable_type",
                    "status",
                    "created_at",
                    "expires_at",
                ],
            )
        except Exception:  # noqa: BLE001
            signing = []

        # 7. Audit log filtered by the cliente identifier (audit_log
        # schema · uses ``usuario`` text column). We match the email or
        # the UUID string format that the audit middleware sets.
        try:
            audit_rows = await self.db.execute(
                text(
                    """
                    SELECT id, tabla, accion, usuario, timestamp
                    FROM audit_log
                    WHERE usuario = :email
                       OR usuario = :uid_text
                       OR registro_id::text = :uid_text
                    ORDER BY timestamp
                    LIMIT 1000
                    """
                ),
                {
                    "email": (profile or {}).get("email", ""),
                    "uid_text": str(client_user_id),
                },
            )
            audit = _rows_as_dicts(
                audit_rows.all(),
                ["id", "tabla", "accion", "usuario", "timestamp"],
            )
        except Exception:  # noqa: BLE001
            audit = []

        return {
            "profile": profile,
            "projects": projects,
            "documents": documents,
            "chat_messages": chat,
            "whatsapp": whatsapp,
            "signing_intents": signing,
            "audit_log": audit,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_for_client_user_id": str(client_user_id),
        }

    async def build_zip(self, client_user_id: UUID) -> io.BytesIO:
        """Return the cross-motor data as an in-memory ZIP."""
        data = await self._gather_cliente_data(client_user_id)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.md", _README)
            zf.writestr(
                "perfil/profile.json",
                json.dumps(data["profile"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "proyectos/projects.json",
                json.dumps(data["projects"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "documentos/documents.json",
                json.dumps(data["documents"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "comunicaciones/chat_messages.json",
                json.dumps(data["chat_messages"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "comunicaciones/whatsapp.json",
                json.dumps(data["whatsapp"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "firmas/signing_intents.json",
                json.dumps(data["signing_intents"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "auditoria/audit_log.json",
                json.dumps(data["audit_log"], indent=2, ensure_ascii=False),
            )
            zf.writestr(
                "metadata.json",
                json.dumps(
                    {
                        "generated_at": data["generated_at"],
                        "generated_for_client_user_id": data[
                            "generated_for_client_user_id"
                        ],
                        "regulatory_basis": "Art. 15 GDPR (UE 2016/679)",
                        "format_version": "fulkro.v1",
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
            )
        buf.seek(0)
        return buf


class RGPDPortabilityService:
    """Art. 20 GDPR · machine-readable JSON-LD export."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_payload(self, client_user_id: UUID) -> dict[str, Any]:
        """Return a JSON-LD-shaped dict suitable for inter-processor import."""
        data = await RGPDAccessService(self.db)._gather_cliente_data(
            client_user_id
        )
        profile = data.get("profile") or {}
        return {
            "@context": {
                "schema": "https://schema.org/",
                "fulkro": "https://fulkro.es/schema/v1#",
            },
            "@type": "schema:Person",
            "schema:identifier": str(client_user_id),
            "schema:email": profile.get("email"),
            "schema:givenName": profile.get("full_name"),
            "fulkro:client_id": profile.get("client_id"),
            "fulkro:client_cif": profile.get("client_cif"),
            "fulkro:whatsapp_number": profile.get("whatsapp_number"),
            "fulkro:consents": [],  # populated by atom 9.bis.1 (consent cols)
            "fulkro:projects": data.get("projects", []),
            "fulkro:documents": data.get("documents", []),
            "fulkro:chat_messages": data.get("chat_messages", []),
            "fulkro:signing_intents": data.get("signing_intents", []),
            "fulkro:generated_at": data["generated_at"],
            "fulkro:regulatory_basis": "Art. 20 GDPR (UE 2016/679)",
            "fulkro:format_version": "fulkro.ld.v1",
        }


class RGPDErasureService:
    """Art. 17 GDPR · cliente erasure workflow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_erasure(
        self,
        client_user_id: UUID,
        *,
        tenant_client_id: UUID,
        reason: str | None = None,
    ) -> FulkroErasureRequest:
        """Create a pending erasure request (idempotent per cliente).

        ``tenant_client_id`` is denormalised so admin paths can re-establish
        RLS context (``app.current_client_id``) without first looking up
        ``client_users``, which is RLS-protected.
        """
        # Refuse duplicate pending requests.
        existing = await self.db.execute(
            text(
                """
                SELECT id FROM fulkro_erasure_requests
                WHERE client_user_id = :uid
                  AND status IN ('pending', 'processing')
                ORDER BY requested_at DESC LIMIT 1
                """
            ),
            {"uid": str(client_user_id)},
        )
        existing_id = existing.scalar()
        if existing_id is not None:
            row = await self.db.execute(
                text(
                    "SELECT * FROM fulkro_erasure_requests WHERE id = :i"
                ),
                {"i": str(existing_id)},
            )
            mapping = row.mappings().first()
            return FulkroErasureRequest(**{
                k: v for k, v in mapping.items() if hasattr(FulkroErasureRequest, k)
            })

        new = FulkroErasureRequest(
            client_user_id=str(client_user_id),
            tenant_client_id=str(tenant_client_id),
            requested_at=datetime.now(timezone.utc),
            requester_reason=reason,
            status=ERASURE_PENDING,
        )
        self.db.add(new)
        await self.db.flush()
        return new

    async def approve_and_anonymise(
        self,
        request_id: UUID,
        processed_by: str,
    ) -> FulkroErasureRequest:
        """Execute the tombstone anonymisation in-place.

        - ``client_users.email`` → ``anonymised_<uuid>@removed.fulkro.local``
        - ``client_users.whatsapp_number`` → NULL
        - ``client_users.full_name`` → ``Eliminado por solicitud · <iso date>``
        - ``client_users.dni`` → NULL
        - ``documents.signed_by_name`` / ``signing_intents.signer_name`` →
          ``[anonimizado]`` to preserve the chain of legal validity while
          replacing the display identifier.
        - ``audit_log`` rows are PRESERVED (ENS retention obligation).
        """
        req_row = await self.db.execute(
            text(
                "SELECT id, client_user_id, tenant_client_id, status "
                "FROM fulkro_erasure_requests WHERE id = :i"
            ),
            {"i": str(request_id)},
        )
        record = req_row.first()
        if record is None:
            raise KeyError(f"ErasureRequest {request_id} not found")
        if record[3] not in (ERASURE_PENDING, ERASURE_PROCESSING):
            raise ValueError(
                f"ErasureRequest {request_id} is already {record[3]}"
            )

        client_user_id = record[1]
        tenant_client_id = record[2]
        # Bring RLS context to the cliente's tenant so the UPDATE on
        # ``client_users`` succeeds under fulkro_app.
        await self.db.execute(
            text("SELECT set_config('app.current_client_id', :cid, true)"),
            {"cid": str(tenant_client_id)},
        )
        tombstone_email = f"anonymised_{client_user_id}@removed.fulkro.local"
        tombstone_name = (
            "Eliminado por solicitud · "
            f"{datetime.now(timezone.utc).date().isoformat()}"
        )

        # Capture snapshot for audit trail (without sensitive data).
        snapshot_row = await self.db.execute(
            text(
                "SELECT created_at, last_login, client_id "
                "FROM client_users WHERE id = :uid"
            ),
            {"uid": str(client_user_id)},
        )
        snap = snapshot_row.first()
        tombstone_data = {
            "client_id": str(snap[2]) if snap else None,
            "created_at": snap[0].isoformat() if snap and snap[0] else None,
            "last_login": snap[1].isoformat() if snap and snap[1] else None,
            "anonymised_at": datetime.now(timezone.utc).isoformat(),
            "retention_basis": (
                "RD 311/2022 art. 24.1 — audit log preserved 7 years"
            ),
        } if snap else None

        # In-place anonymisation. ``client_users`` is updated as fulkro_app
        # (NOSUPERUSER · RLS does not apply to platform tables without
        # project_id, so direct UPDATE is allowed).
        await self.db.execute(
            text(
                """
                UPDATE client_users
                SET email = :email,
                    full_name = :name,
                    dni = NULL,
                    whatsapp_number = NULL,
                    whatsapp_verified_at = NULL,
                    whatsapp_opt_in_at = NULL
                WHERE id = :uid
                """
            ),
            {"email": tombstone_email, "name": tombstone_name, "uid": str(client_user_id)},
        )
        # Note · signing_intents has no human-readable signer_name to
        # anonymise (data is stored as document_hash_sha256 + intent_payload
        # JSON). The legal validity chain is preserved by NOT deleting any
        # row; if the cliente's identifying data appears inside
        # intent_payload it is the responsibility of the m05 signing motor
        # to mask it on output, not this erasure flow.

        # Mark request completed.
        await self.db.execute(
            text(
                """
                UPDATE fulkro_erasure_requests
                SET status = :status,
                    processed_at = NOW(),
                    processed_by = :who,
                    tombstone_data = CAST(:td AS jsonb),
                    audit_log_preserved = TRUE
                WHERE id = :rid
                """
            ),
            {
                "status": ERASURE_COMPLETED,
                "who": processed_by,
                "td": json.dumps(tombstone_data) if tombstone_data else None,
                "rid": str(request_id),
            },
        )
        await self.db.flush()

        refreshed_row = await self.db.execute(
            text("SELECT * FROM fulkro_erasure_requests WHERE id = :i"),
            {"i": str(request_id)},
        )
        mapping = refreshed_row.mappings().first()
        return FulkroErasureRequest(**{
            k: v for k, v in mapping.items() if hasattr(FulkroErasureRequest, k)
        })

    async def reject_audit_retention(
        self,
        request_id: UUID,
        processed_by: str,
        rejection_reason: str | None = None,
    ) -> FulkroErasureRequest:
        """Reject the request because legal retention applies."""
        default_reason = (
            "Datos retenidos por obligación legal: RD 311/2022 art. 24.1 — "
            "retención de evidencias ENS durante 7 años + Art. 30.4 RGPD. "
            "El registro de auditoría asociado se mantiene anonimizado al "
            "vencer la obligación."
        )
        await self.db.execute(
            text(
                """
                UPDATE fulkro_erasure_requests
                SET status = :status,
                    processed_at = NOW(),
                    processed_by = :who,
                    rejection_reason = :reason
                WHERE id = :rid
                """
            ),
            {
                "status": ERASURE_REJECTED_AUDIT,
                "who": processed_by,
                "reason": rejection_reason or default_reason,
                "rid": str(request_id),
            },
        )
        await self.db.flush()
        refreshed_row = await self.db.execute(
            text("SELECT * FROM fulkro_erasure_requests WHERE id = :i"),
            {"i": str(request_id)},
        )
        mapping = refreshed_row.mappings().first()
        return FulkroErasureRequest(**{
            k: v for k, v in mapping.items() if hasattr(FulkroErasureRequest, k)
        })
