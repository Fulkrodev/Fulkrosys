"""ContractSigningFlow · magic-link OTP+geo firma contrato comercial.

SAN-D MB-19.4 · ADR-041.

Orquesta firma de contratos comerciales lead→cliente vía magic-link
purpose `FIRMA_CONTRATO` (TTL 72h · OTP True · geo True · max_uses 3).

Flow:

1. Marcos genera Contract DOCX (M14 contract_service existing).
2. Marcos invoca `send_for_signing(contract_id, recipient_email,
   recipient_name)`:
   - Genera magic-link `FIRMA_CONTRATO` con OTP+geo via MagicLinkService.
   - (Opcional) Envía email cliente con link + OTP per canal separado
     (NotificationOrchestrator integration · MB-19+ deferrable si no
     existe template).
   - Marca Contract.firmado_cliente_link_id = magic_link.id (FK existing).
3. Cliente abre URL magic-link · introduce OTP · confirma con geo capture.
4. Sistema invoca `confirm_signing(token, otp, ip, user_agent, geo)`:
   - Consume magic-link (MagicLinkService.consume_magic_link).
   - UPDATE Contract.firmado_cliente_at = NOW().
   - Trigger CommercialWorkflowService.handle_contract_signed para
     auto-conversion lead→Project+ClientUser+Milestones.

Refs:
- backend/app/motors/m12_magic_link/service.py:MagicLinkService
- backend/app/motors/m12_magic_link/purposes.py:FIRMA_CONTRATO
- backend/app/motors/m13_commercial/services/commercial_workflow_service.py
- backend/app/models/commercial.py:Contract
- ADR-041 (CRM workflow comercial m13 extension)
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import Contract, Lead, Proposal
from backend.app.models.core import Client, Project
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import (
    MagicLinkConsumeRequest,
    MagicLinkGenerateRequest,
)
from backend.app.motors.m12_magic_link.service import (
    MagicLinkService,
    MagicLinkOTPRequired,
    MagicLinkInvalidOTPError,
    MagicLinkExpiredError,
    MagicLinkRevokedError,
    MagicLinkExhaustedError,
    MagicLinkOTPBlockedError,
    MagicLinkNotFoundError,
)
from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
    CommercialWorkflowService,
)


logger = logging.getLogger(__name__)


class ContractSigningFlowError(Exception):
    """Error genérico ContractSigningFlow."""


class ContractNotFoundError(ContractSigningFlowError):
    """Contract no encontrado."""


class ContractSigningFlow:
    """Magic-link OTP+geo signing contract comercial · m13 extension MB-19.4.

    Servicios async stateless · usa AsyncSession existing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ────────────────────────────────────────────────────────────
    # SEND FOR SIGNING
    # ────────────────────────────────────────────────────────────

    async def send_for_signing(
        self,
        *,
        contract_id: uuid.UUID,
        recipient_email: str,
        recipient_name: str,
        created_by_user_id: uuid.UUID,
        base_url: str = "https://app.fulkro.es",
        custom_subject: str | None = None,
        custom_body_intro: str | None = None,
        ttl_hours: int | None = None,
    ) -> dict[str, Any]:
        """Genera magic-link FIRMA_CONTRATO + actualiza Contract con FK link.

        NO envía email automáticamente · responsabilidad del caller (admin
        UI o ContractService API endpoint puede invocar EmailSender luego).
        Esto reduce coupling SMTP/Postmark en handler crítico de firma.

        Args:
            contract_id: UUID Contract a firmar.
            recipient_email: email cliente firmante (cliente_firmante_*).
            recipient_name: nombre cliente firmante (audit log + email subject).
            base_url: dominio frontend (default app.fulkro.es).
            custom_subject: override subject email default.
            custom_body_intro: texto Marcos prepend al body template.
            ttl_hours: override TTL default 72h (rango admin · 24-168h).

        Returns:
            dict con:
              {
                "magic_link_id": str(UUID),
                "url": str (URL completa para cliente),
                "otp": str | None (6 dígitos · enviar canal separado),
                "expires_at": str ISO datetime,
                "action_label": str (humano "Firmar contrato..."),
              }

        Raises:
            ContractNotFoundError: contract_id no existe.
        """
        contract = await self.db.get(Contract, contract_id)
        if contract is None:
            raise ContractNotFoundError(
                f"Contract {contract_id} no encontrado"
            )

        # MagicLinkGenerateRequest requiere project_id FK válido a projects.
        # Pre-conversion · Contract puede no tener project_id aún · creamos
        # placeholder Project (lifecycle_state=DRAFT) que será populated
        # post-firma vía CommercialWorkflowService.handle_contract_signed
        # (Lead.convertido_a_proyecto_id apuntará a este Project).
        target_project_id = contract.project_id
        if target_project_id is None:
            target_project_id = await self._ensure_placeholder_project(
                contract,
            )

        # #43 · congelar documento_sha256 sobre los BYTES del DOCX canónico
        # (render UNA vez · FASE C) + crear el SigningIntent m05 que el cliente
        # firmará con canvas Ed25519. El intent referencia el contrato vía
        # signable_ref_id/type='contract' (puente reverso · gratis) y queda
        # enlazado en contract.signing_intent_id (M-OLA2-C · puente directo).
        # NO step-up OTP (no está en REQUIRES_STEP_UP_OTP · el OTP vive en la
        # puerta magic-link FIRMA_CONTRATO · decisión A/B).
        from backend.app.database import set_tenant_context
        from backend.app.motors.m05_signing.service import SigningService
        from backend.app.motors.m14_contracts.legal_templates import (
            render_canonical_contract_docx,
        )
        from backend.app.motors.m24_idms.idms_service import IDMSService

        docx_bytes = await render_canonical_contract_docx(self.db, contract)
        contract.documento_sha256 = hashlib.sha256(docx_bytes).hexdigest()

        # Archivar el DOCX canónico (cuyo hash se firma) en IDMS AHORA, con los
        # BYTES exactos que se firman → su content_hash == documento_sha256 →
        # documento firmado verificable e inmutable (lo que inspecciona ENAC).
        # Re-render en SIGN podría diferir (fecha de generación) → mismatch de
        # hash; por eso se persiste aquí. Contexto RLS del proyecto placeholder.
        _proj = await self.db.get(Project, target_project_id)
        if _proj is not None:
            await set_tenant_context(
                self.db, client_id=_proj.client_id, project_id=target_project_id,
            )
        archived = await IDMSService().intake_document(
            self.db,
            project_id=target_project_id,
            nombre=f"Contrato_{contract.plantilla_id or 'C'}_{contract.id}.docx",
            contenido=docx_bytes,
            tipo_mime="docx",  # documents.tipo es VARCHAR(50) · el MIME largo trunca
            subido_por="system:firma_contrato",
        )
        contract_document_id = archived["document"].id

        intent = await SigningService(self.db).create_intent(
            project_id=target_project_id,
            signable_type="contrato_comercial",
            document_hash_sha256=contract.documento_sha256,
            created_by_user_id=created_by_user_id,
            document_id=contract_document_id,
            signable_ref_id=contract.id,
            signable_ref_type="contract",
            intent_payload={
                "flow": "contract_signing",
                "plantilla_id": contract.plantilla_id,
                "recipient_name": recipient_name,
            },
        )
        contract.signing_intent_id = intent.id
        await self.db.flush()

        ml_service = MagicLinkService(self.db)
        ml_request = MagicLinkGenerateRequest(
            project_id=target_project_id,
            purpose=MagicLinkPurpose.FIRMA_CONTRATO,
            recipient_email=recipient_email,
            scope={
                "flow": "contract_signing",
                "contract_id": str(contract_id),
                "recipient_name": recipient_name,
                # #43 · email del firmante propagado al scope para que la
                # conversión #7 pueda crear el ClientUser persistente aunque el
                # Client aún no tenga contacto_email fijado (lead B2B sin email).
                "recipient_email": recipient_email,
            },
            custom_subject=custom_subject,
            custom_body_intro=custom_body_intro,
            ttl_hours=ttl_hours,
        )

        ml_response = await ml_service.generate_magic_link(
            ml_request, base_url=base_url,
        )

        # Update Contract con FK magic-link
        contract.firmado_cliente_link_id = ml_response.magic_link_id
        # #43 · estado "sent" tras enviar a firma (equivalencia UI · el botón
        # send-client marcaba "sent" en el flujo anterior · #7.2). confirm_signing
        # lo lleva a "vigente" al firmar el canvas.
        if contract.estado in ("draft", "firmado_marcos"):
            contract.estado = "sent"
        # Si Contract.cliente_firmante_nombre vacío · populated desde recipient
        if not contract.cliente_firmante_nombre:
            contract.cliente_firmante_nombre = recipient_name
        await self.db.flush()

        return {
            "magic_link_id": str(ml_response.magic_link_id),
            "url": ml_response.url,
            "otp": ml_response.otp,
            "expires_at": ml_response.expires_at.isoformat(),
            "action_label": ml_response.action_label,
            "token": ml_response.token,
            "signing_intent_id": str(intent.id),
            "documento_sha256": contract.documento_sha256,
        }

    # ────────────────────────────────────────────────────────────
    # PREVIEW (#34 · FRENTE B · leer el contrato ANTES de firmar)
    # ────────────────────────────────────────────────────────────

    async def get_contract_document_for_preview(
        self, token: str,
    ) -> dict[str, Any]:
        """#34 (FRENTE B) · devuelve el DOCX EXACTO que el cliente va a firmar,
        para que lo lea/descargue ANTES de firmar (hoy se firma a ciegas · el
        documento solo iba por email). WYSIWYS: los bytes devueltos tienen
        ``content_hash == contract.documento_sha256`` (lo que se firma es lo que
        se lee). READ-ONLY · NO consume usos del magic-link (usa
        ``get_status_by_token`` · pre-consume). El token FIRMA_CONTRATO es la
        credencial.
        """
        from backend.app.models.documents import Document
        from backend.app.motors.m05_signing.models import SigningIntent

        ml_service = MagicLinkService(self.db)
        try:
            status = await ml_service.get_status_by_token(token)
        except MagicLinkNotFoundError as exc:
            raise ContractNotFoundError("Enlace de firma no válido") from exc

        if status.get("tipo_operacion") != MagicLinkPurpose.FIRMA_CONTRATO.value:
            raise ContractSigningFlowError(
                "Enlace de firma no válido para un contrato"
            )
        if status.get("revocado"):
            raise ContractSigningFlowError("El enlace de firma fue revocado")
        expira = status.get("expira_at")
        if expira is not None:
            if expira.tzinfo is None:  # pragma: no cover — asyncpg tz-aware
                expira = expira.replace(tzinfo=timezone.utc)
            if expira < datetime.now(timezone.utc):
                raise ContractSigningFlowError("El enlace de firma ha caducado")

        contract_id_str = (status.get("scope") or {}).get("contract_id")
        if not contract_id_str:
            raise ContractSigningFlowError("Enlace sin contrato asociado")
        contract_id = uuid.UUID(contract_id_str)

        # Lookups read-only bajo fulkro (token-gated · mismo patrón que la fase
        # de lookup de confirm_signing · sin mutación).
        await self.db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        contract = await self.db.get(Contract, contract_id)
        if contract is None:
            raise ContractNotFoundError("Contrato no encontrado")
        if contract.estado == "anulado_recategorizacion":
            raise ContractSigningFlowError(
                "Este contrato fue anulado/recategorizado · solicita a Fulkro "
                "el contrato actualizado."
            )
        if contract.signing_intent_id is None:
            raise ContractSigningFlowError(
                "El contrato aún no está preparado para firma"
            )
        intent = await self.db.get(SigningIntent, contract.signing_intent_id)
        doc = (
            await self.db.get(Document, intent.document_id)
            if intent is not None and intent.document_id is not None
            else None
        )
        if doc is None or not doc.storage_path:
            raise ContractNotFoundError("Documento del contrato no disponible")

        storage_path = str(doc.storage_path)
        if not storage_path.startswith("minio://"):
            raise ContractSigningFlowError(
                "Documento del contrato no disponible en este entorno"
            )
        from backend.app.core.storage.minio_client import get_object

        rest = storage_path[len("minio://"):]
        bucket, _, key = rest.partition("/")
        binary = get_object(bucket, key)

        filename = doc.nombre or f"contrato_{contract_id}.docx"
        if not filename.lower().endswith(".docx"):
            filename = f"{filename}.docx"
        return {
            "binary": binary,
            "filename": filename,
            "media_type": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            "documento_sha256": contract.documento_sha256,
        }

    # ────────────────────────────────────────────────────────────
    # CONFIRM SIGNING
    # ────────────────────────────────────────────────────────────

    async def confirm_signing(
        self,
        *,
        token: str,
        otp: str,
        signature_canvas_dataurl: str,
        signed_name: str,
        signed_surname: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        geo_lat: float | None = None,
        geo_lon: float | None = None,
    ) -> dict[str, Any]:
        """Cliente confirma firma · consume magic-link + UPDATE Contract +
        trigger auto-conversion lead→cliente.

        Args:
            token: JWT magic-link recibido vía URL.
            otp: 6 dígitos OTP recibido canal separado (SMS/email separado).
            ip_address: IP cliente (audit · jurídico).
            user_agent: User-Agent navegador (audit).
            geo_lat: latitud geo capture (firma legal vinculante).
            geo_lon: longitud geo capture.

        Returns:
            dict con:
              {
                "status": "signed",
                "contract_id": str(UUID),
                "signed_at": str ISO,
                "magic_link_id": str(UUID),
                "conversion": dict (CommercialWorkflowService output),
              }

        Raises:
            ContractSigningFlowError: token inválido/expirado · OTP inválido
                · contract no encontrado · auto-conversion failed.
        """
        ml_service = MagicLinkService(self.db)

        # El lookup del magic-link bypasea la RLS de magic_links
        # (project_isolation), igual que el endpoint público de consume (m12):
        # SET LOCAL ROLE fulkro_app_bypassrls para el lookup por token_hash + las lecturas
        # de contract/intent (también project-RLS). La conversión + firma se
        # ejecutan luego bajo fulkro_app (RLS estricta · anti-falso-verde).
        await self.db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))

        consume_request = MagicLinkConsumeRequest(
            token=token,
            otp=otp,
            client_ip=ip_address,
            user_agent=user_agent,
        )
        try:
            ml_response = await ml_service.consume_magic_link(consume_request)
        except (
            MagicLinkOTPRequired,
            MagicLinkInvalidOTPError,
            MagicLinkExpiredError,
            MagicLinkRevokedError,
            MagicLinkExhaustedError,
            MagicLinkOTPBlockedError,
            MagicLinkNotFoundError,
        ) as exc:
            raise ContractSigningFlowError(
                f"Magic-link inválido/expirado/OTP fail: {exc}"
            ) from exc

        # Verificar purpose es FIRMA_CONTRATO
        if ml_response.purpose != MagicLinkPurpose.FIRMA_CONTRATO:
            raise ContractSigningFlowError(
                f"Purpose incorrecto: esperado FIRMA_CONTRATO · recibido "
                f"{ml_response.purpose.value}"
            )

        # Extraer contract_id del scope
        scope = ml_response.scope or {}
        contract_id_str = scope.get("contract_id")
        if not contract_id_str:
            raise ContractSigningFlowError(
                "Magic-link scope.contract_id missing · token corrupto"
            )

        try:
            contract_id = uuid.UUID(contract_id_str)
        except ValueError as exc:
            raise ContractSigningFlowError(
                f"Magic-link scope.contract_id no es UUID válido: {contract_id_str}"
            ) from exc

        contract = await self.db.get(Contract, contract_id)
        if contract is None:
            raise ContractNotFoundError(
                f"Contract {contract_id} (desde scope) no encontrado"
            )

        # #5 cabo · defensa en profundidad: si el contrato fue ANULADO/
        # recategorizado tras enviarlo (N2.5 retract), NO puede firmarse (además
        # el magic-link ya está revocado · esto da mensaje claro al cliente).
        if contract.estado == "anulado_recategorizacion":
            raise ContractSigningFlowError(
                "Este contrato fue anulado/recategorizado y ya no puede firmarse. "
                "Contacta con Fulkro para recibir el contrato actualizado."
            )

        # ───────────────────────────────────────────────────────────
        # #43 · firma canvas Ed25519 + conversión #7 + IDMS · TODO en UNA
        # transacción atómica (el caller commitea 1×). Si CUALQUIER eslabón
        # posterior falla, el rollback deshace TAMBIÉN la promoción del proyecto
        # y el ClientUser (no queda cliente "real" sin contrato firmado · refuerzo 1).
        # ───────────────────────────────────────────────────────────
        from backend.app.motors.m05_signing.models import SigningIntent
        from backend.app.motors.m05_signing.service import SigningService

        if contract.signing_intent_id is None:
            raise ContractSigningFlowError(
                f"Contract {contract_id} sin signing_intent · ejecuta "
                f"send_for_signing primero (#43)"
            )
        intent = await self.db.get(SigningIntent, contract.signing_intent_id)
        if intent is None:
            raise ContractSigningFlowError(
                f"SigningIntent {contract.signing_intent_id} no encontrado"
            )

        # IDEMPOTENCIA (refuerzo 2): segunda firma (doble clic / reintento) →
        # no-op. No crea 2ª firma, ni 2º ClientUser, ni promociona dos veces.
        if intent.status == "signed":
            return {
                "status": "already_signed",
                "contract_id": str(contract_id),
                "signing_intent_id": str(intent.id),
                "magic_link_id": str(ml_response.magic_link_id),
            }

        signed_at = datetime.now(timezone.utc)

        # Volvemos a fulkro_app (RLS ESTRICTA) para la conversión + firma + IDMS:
        # el consume necesitaba fulkro para el lookup, pero la conversión #7 y la
        # firma DEBEN correr con RLS enforced (anti-falso-verde · #7.6). El
        # contexto de tenant lo fija handle_contract_signed.
        await self.db.execute(sa_text("SET LOCAL ROLE fulkro_app"))

        # 1) Conversión #7 PRIMERO (promueve proyecto ligero + crea ClientUser).
        #    Idempotente + advisory lock provision_lead_* (anti doble-provisión
        #    wizard/firma). NO commitea · flush dentro de esta misma tx.
        workflow = CommercialWorkflowService(self.db)
        conversion_result = await workflow.handle_contract_signed(contract_id)
        client_id = conversion_result.get("client_id")
        if client_id is None:
            raise ContractSigningFlowError(
                "Conversión #7 no resolvió client_id · no se puede firmar"
            )

        # 2) Resolver/crear el ClientUser REAL del firmante (identidad
        #    persistente · el SigningEvent apunta a ella · decisión C).
        signer_user_id = await self._resolve_or_create_signer(
            client_id=uuid.UUID(client_id) if isinstance(client_id, str)
            else client_id,
            conversion_result=conversion_result,
            scope=scope,
        )

        # Defensa RLS (defecto detectado en sim MEDIO E2E): cuando el proyecto
        # del contrato YA estaba establecido, handle_contract_signed toma el path
        # set_tenant_context(client_id=…) SIN project_id → current_project_id()
        # queda sin fijar y la firma sobre signing_intents
        # (RLS: project_id = current_project_id()) matchea 0 filas → StaleDataError.
        # Re-fijamos explícitamente el contexto del intent antes de firmar.
        from backend.app.database import set_tenant_context as _set_tenant_ctx

        await _set_tenant_ctx(
            self.db,
            client_id=(
                uuid.UUID(client_id) if isinstance(client_id, str) else client_id
            ),
            project_id=intent.project_id,
        )

        # 3) Firma canvas Ed25519 + hash chain (m05 · sobre documento_sha256).
        event = await SigningService(self.db).sign_canvas(
            intent_id=intent.id,
            user_id=signer_user_id,
            signature_canvas_dataurl=signature_canvas_dataurl,
            signed_name=signed_name,
            signed_surname=signed_surname,
            ip_address=ip_address,
            user_agent=user_agent,
            signature_message_extras={
                "magic_link_id": str(ml_response.magic_link_id),
                "geo": (
                    {"lat": geo_lat, "lon": geo_lon}
                    if geo_lat is not None and geo_lon is not None
                    else None
                ),
            },
        )

        # 4) IDMS · certificado de firma PDF (canvas + Ed25519 badge · Pattern
        #    #24). El DOCX firmado (content_hash == documento_sha256) ya quedó
        #    archivado en send_for_signing + enlazado en intent.document_id.
        await self._archive_signature_certificate(
            contract=contract, event=event, project_id=intent.project_id,
        )

        # 5) Finalizar contrato (vigente).
        contract.firmado_cliente_at = signed_at
        contract.estado = "vigente"
        existing_adendas = contract.adendas or {}
        existing_adendas["signing_audit"] = {
            "signed_at": signed_at.isoformat(),
            "magic_link_id": str(ml_response.magic_link_id),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "geo": (
                {"lat": geo_lat, "lon": geo_lon}
                if geo_lat is not None and geo_lon is not None
                else None
            ),
            "signing_event_id": str(event.id),
            "event_hash_sha256": event.event_hash_sha256,
            "signer_user_id": str(signer_user_id),
        }
        contract.adendas = existing_adendas
        await self.db.flush()

        return {
            "status": "signed",
            "contract_id": str(contract_id),
            "signed_at": signed_at.isoformat(),
            "magic_link_id": str(ml_response.magic_link_id),
            "signing_intent_id": str(intent.id),
            "signing_event_id": str(event.id),
            "event_hash_sha256": event.event_hash_sha256,
            "signer_user_id": str(signer_user_id),
            "conversion": conversion_result,
            # Ola 3 #12 · datos para el SSE enriquecido al admin (post-commit
            # en el endpoint · "Fulanito firmó el contrato C-001").
            "plantilla_id": contract.plantilla_id,
            "project_id": str(intent.project_id),
        }

    # ────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ────────────────────────────────────────────────────────────

    async def _resolve_or_create_signer(
        self,
        *,
        client_id: uuid.UUID,
        conversion_result: dict[str, Any],
        scope: dict[str, Any],
    ) -> uuid.UUID:
        """#43 decisión C · devuelve la identidad REAL y persistente del
        firmante (ClientUser.id). Si la conversión #7 ya lo creó, lo usa; si no,
        lo resuelve por (client_id, email) o lo crea. NUNCA un id sintético: el
        SigningEvent debe apuntar al firmante real (defendible ante ENAC)."""
        from sqlalchemy import select as _select

        from backend.app.models.client_portal import ClientUser

        cu_id = conversion_result.get("client_user_id")
        if cu_id:
            return uuid.UUID(cu_id) if isinstance(cu_id, str) else cu_id

        client = await self.db.get(Client, client_id)
        email = (client.contacto_email or "").strip().lower() if client else ""
        if not email:
            # Fallback autoritativo: el email del firmante es aquel al que se
            # envió el contrato (magic-link FIRMA_CONTRATO · scope.recipient_email).
            # Cubre el lead/cliente B2B cuyo contacto_email aún no se ha fijado:
            # sin esto, un cliente sin contacto_email NO podría firmar (#43).
            email = (scope.get("recipient_email") or "").strip().lower()
        if not email:
            raise ContractSigningFlowError(
                "Firmante sin email · no se puede crear ClientUser persistente "
                "para la firma del contrato (#43)"
            )

        existing = await self.db.scalar(
            _select(ClientUser).where(
                ClientUser.client_id == client_id,
                ClientUser.email == email,
            )
        )
        if existing is not None:
            return existing.id

        from backend.app.motors.m21_portal_cliente.auth_service import (
            AuthError,
            create_user,
        )

        full_name = scope.get("recipient_name") or (
            client.nombre if client else email
        )
        try:
            user, _temp_pwd = await create_user(
                self.db, client_id=client_id, email=email, full_name=full_name,
            )
            return user.id
        except AuthError as exc:
            # Carrera: creado entre el check y el create → re-resolver.
            again = await self.db.scalar(
                _select(ClientUser).where(
                    ClientUser.client_id == client_id,
                    ClientUser.email == email,
                )
            )
            if again is not None:
                return again.id
            raise ContractSigningFlowError(
                f"No se pudo resolver/crear el ClientUser firmante: {exc}"
            ) from exc

    async def _archive_signature_certificate(
        self,
        *,
        contract: Contract,
        event: Any,
        project_id: uuid.UUID,
    ) -> None:
        """#43 decisión D · certificado de firma PDF (canvas + Ed25519 badge +
        hash chain · Pattern #24) archivado en IDMS. Complementa al DOCX firmado
        (content_hash == documento_sha256) ya archivado en send_for_signing."""
        import io

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen.canvas import Canvas

        from backend.app.motors.m05_signing.pdf_signature_embed import (
            append_signature_page,
        )
        from backend.app.motors.m24_idms.idms_service import IDMSService

        buf = io.BytesIO()
        c = Canvas(buf, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(2 * cm, 27 * cm, "Certificado de firma electrónica")
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, 26.3 * cm, f"Contrato comercial · {contract.id}")
        append_signature_page(
            c,
            signature_canvas_dataurl=event.signature_canvas_dataurl or "",
            signed_name=event.signed_name or "",
            signed_surname=event.signed_surname or "",
            signed_at=event.created_at,
            ip_address=event.ip_address,
            signature_ed25519=event.signature_ed25519 or b"",
            event_hash_sha256=event.event_hash_sha256,
            document_label=(
                f"Contrato comercial {contract.plantilla_id or ''} · {contract.id}"
            ),
        )
        c.save()
        await IDMSService().intake_document(
            self.db,
            project_id=project_id,
            nombre=f"Certificado_firma_{contract.id}.pdf",
            contenido=buf.getvalue(),
            tipo_mime="application/pdf",
            subido_por="system:firma_contrato",
        )

    async def _ensure_placeholder_project(
        self, contract: Contract,
    ) -> uuid.UUID:
        """Crea Project placeholder (lifecycle_state=DRAFT) para contract sin
        project_id · necesario porque MagicLinkGenerateRequest requiere
        project_id FK válido.

        Strategy:
        1. Si contract.lead_id IS NOT NULL · find/create Client desde Lead
           + create Project placeholder asociado.
        2. Si contract.lead_id IS NULL · raise (escenario no soportado ·
           contract debe tener al menos lead_id para firmar).

        Updates:
        - contract.project_id = nuevo Project.id

        Returns:
            UUID del Project placeholder creado.
        """
        if contract.lead_id is None:
            raise ContractSigningFlowError(
                f"Contract {contract.id} sin lead_id ni project_id · "
                f"no se puede generar magic-link FIRMA_CONTRATO"
            )

        lead = await self.db.get(Lead, contract.lead_id)
        if lead is None:
            raise ContractSigningFlowError(
                f"Contract.lead_id={contract.lead_id} no encontrado"
            )

        # Find/Create Client (mismo helper logic que CommercialWorkflowService
        # · placeholder pre-firma)
        client = await self._find_or_create_client_from_lead(lead)

        # Create Project placeholder
        from sqlalchemy import select as _select
        # Evitar duplicar si ya existe project asociado a este client +
        # lead (idempotente edge case)
        existing_projects = (await self.db.execute(
            _select(Project).where(
                Project.client_id == client.id,
            ).limit(50)
        )).scalars().all()
        for p in existing_projects:
            if p.nombre == f"ENS · {lead.empresa_nombre}":
                contract.project_id = p.id
                await self.db.flush()
                return p.id

        categoria = (
            lead.categoria_objetivo_ens
            or "BASICA"
        )
        # Sub-atom 1.C.D.A.0.3 v3.8 · pre-populate tamano_empleados desde
        # proposal.alcance.empleados si resolvable (helper en commercial_workflow_service).
        from backend.app.motors.m13_commercial.services.commercial_workflow_service import (
            _map_empleados_to_tamano,
        )
        project_kwargs: dict[str, object] = {
            "client_id": client.id,
            "nombre": f"ENS · {lead.empresa_nombre}",
            "categoria_objetivo": categoria,
            "estado": "draft",
            "lifecycle_state": "DRAFT",  # Pre-firma · ascenderá a SIGNED post-confirm
            "archetype": lead.archetype_ens,
        }
        if contract.proposal_id:
            proposal = await self.db.get(Proposal, contract.proposal_id)
            if proposal and isinstance(proposal.alcance, dict):
                tamano = _map_empleados_to_tamano(
                    proposal.alcance.get("empleados"),
                )
                if tamano:
                    project_kwargs["tamano_empleados"] = tamano
        project = Project(**project_kwargs)
        self.db.add(project)
        await self.db.flush()

        contract.project_id = project.id
        await self.db.flush()
        return project.id

    async def _find_or_create_client_from_lead(
        self, lead: Lead,
    ) -> Client:
        """Find/Create Client (placeholder pre-firma · mismo logic que
        CommercialWorkflowService._find_or_create_client)."""
        from sqlalchemy import select as _select

        if lead.empresa_cif:
            existing = await self.db.scalar(
                _select(Client).where(Client.cif == lead.empresa_cif)
            )
            if existing:
                return existing

        if lead.contacto_email:
            existing = await self.db.scalar(
                _select(Client).where(
                    Client.contacto_email == lead.contacto_email,
                )
            )
            if existing:
                return existing

        client = Client(
            nombre=lead.empresa_nombre,
            cif=lead.empresa_cif or f"X{uuid.uuid4().hex[:8].upper()}",
            sector=lead.sector,
            contacto_email=lead.contacto_email,
            contacto_telefono=lead.contacto_telefono,
            lead_source=lead.origen,
        )
        self.db.add(client)
        await self.db.flush()
        return client
