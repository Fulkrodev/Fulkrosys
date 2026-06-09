"""CommercialWorkflowService · auto-conversion lead→cliente post-firma.

SAN-D MB-19.2 · ADR-041.

Orquestación automática cuando Contract.firmado_cliente_at registered:

1. Lead.estado_contacto → 'ganado' · Lead.fecha_conversion = NOW().
2. Find/Create Client M14 (por contacto_email · empresa_cif del Lead).
3. Create Project asociado al Client (categoria_objetivo desde Lead).
4. Lead.convertido_a_proyecto_id = Project.id.
5. (Optional) MilestoneFactory.create_milestones_for_contract si Contract
   tiene proposal_id con categoria + importe_total resolvable.
6. (Optional) Create ClientUser invite vía auth_service.create_user
   (skip silente si no hay email · Marcos completa manual luego).

Idempotente: si Lead.convertido_a_proyecto_id ya populated, retorna el
Project existing sin duplicar (handler re-trigger seguro post-error).

Refs:
- backend/app/motors/m13_commercial/services/lead_service.py
- backend/app/motors/m21_portal_cliente/auth_service.py:create_user
- backend/app/billing/milestone_factory.py:MilestoneFactory
- backend/app/models/commercial.py:Lead/Contract
- ADR-041 (CRM workflow comercial m13 extension).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.cif_norm import normalize_cif
from backend.app.database import set_tenant_context
from backend.app.models.commercial import Contract, Lead, Proposal
from backend.app.models.core import Client, Project
from backend.app.motors.m13_commercial.services.lead_service import (
    LeadService,
)


logger = logging.getLogger(__name__)


# Mapeo categoria_objetivo_ens (Lead) → categoria_objetivo (Project + Proposal).
# Project.categoria_objetivo es VARCHAR(10) · valores típicos 'BASICA' · 'MEDIA'
# · 'ALTA' (ya alineados con Lead.categoria_objetivo_ens VARCHAR(20)).

DEFAULT_CATEGORIA_FALLBACK = "BASICA"


def _map_empleados_to_tamano(empleados: object | None) -> str | None:
    """Sub-atom 1.C.D.A.0.3 v3.8 · maps proposal.alcance.empleados int/str to
    tamano_empleados enum (Anexo L v3.8).

    Returns None si NO mappable · caller usa server_default 'pequeno'.
    """
    if empleados is None:
        return None
    try:
        n = int(empleados)
    except (TypeError, ValueError):
        return None
    if n < 10:
        return "micro"
    if n < 50:
        return "pequeno"
    if n < 200:
        return "mediano"
    if n < 500:
        return "grande"
    return "enterprise"


class CommercialWorkflowError(Exception):
    """Error genérico CommercialWorkflowService."""


class ContractNotFoundError(CommercialWorkflowError):
    """Contract UUID no encontrado en BD."""


class CommercialWorkflowService:
    """Auto-conversion lead→cliente cuando contract firmado.

    Flow handler invocado desde ContractSigningFlow.confirm_signing
    (MB-19.4) cuando magic-link FIRMA_CONTRATO consumido + Contract
    marcado firmado.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ────────────────────────────────────────────────────────────
    # PUBLIC API
    # ────────────────────────────────────────────────────────────

    async def handle_contract_signed(
        self, contract_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Orquesta auto-conversion lead→cliente post-firma contrato.

        Workflow:
        1. Carga Contract + Lead.
        2. Lead.estado_contacto → ganado.
        3. Find/Create Client.
        4. Create Project asociado.
        5. Lead.convertido_a_proyecto_id = Project.id.
        6. MilestoneFactory si proposal_id + categoria + importe.
        7. (Opcional) ClientUser invite si email contacto.

        Args:
            contract_id: UUID Contract con firmado_cliente_at registered.

        Returns:
            dict con status + ids creados:
              {
                "status": "converted" | "skipped",
                "lead_id": str | None,
                "client_id": str | None,
                "project_id": str | None,
                "client_user_id": str | None,
                "milestones_created": int,
                "reason": str (si skipped),
              }

        Raises:
            ContractNotFoundError: contract_id no existe.
        """
        contract = await self.db.get(Contract, contract_id)
        if contract is None:
            raise ContractNotFoundError(
                f"Contract {contract_id} no encontrado"
            )

        result: dict[str, Any] = {
            "status": "skipped",
            "lead_id": None,
            "client_id": None,
            "project_id": None,
            "client_user_id": None,
            "milestones_created": 0,
            "reason": "",
        }

        if contract.lead_id is None:
            result["reason"] = "contract sin lead_id (convencional)"
            return result

        lead = await self.db.get(Lead, contract.lead_id)
        if lead is None:
            result["reason"] = f"lead {contract.lead_id} no encontrado"
            return result

        result["lead_id"] = str(lead.id)

        from backend.app.motors.m13_commercial.services.project_provisioning_service import (
            resolve_lead_client_id,
        )

        # Pattern #22 (#7.6) · serializa esta conversión por firma con la del
        # wizard (provision_project · mismo lead) → evita doble provisión cuando
        # un alta manual coincide con la auto-conversión por firma.
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('provision_lead_' || :lid))"),
            {"lid": str(lead.id)},
        )

        # ───────────────────────────────────────────────────────
        # Idempotencia REFINADA #7.4 (RLS-correcta #7.6): el proyecto existente
        # se lee bajo el contexto de SU dueño AUTORITATIVO (resuelto por señales
        # del lead · clients sin RLS), NO por un client re-resuelto que podría
        # diferir si el CIF/email del lead cambió tras la conversión (si difiriera,
        # la RLS de projects ocultaría el proyecto → falsa no-idempotencia →
        # duplicado). Proyecto REAL → idempotente; LIGERO → se PROMUEVE abajo.
        # ───────────────────────────────────────────────────────
        existing_project: Project | None = None
        if lead.convertido_a_proyecto_id is not None:
            owner_client_id = await resolve_lead_client_id(self.db, lead)
            if owner_client_id is not None:
                await set_tenant_context(self.db, client_id=owner_client_id)
                existing_project = await self.db.get(
                    Project, lead.convertido_a_proyecto_id,
                )
                is_lightweight = (
                    existing_project is not None
                    and existing_project.lifecycle_state == "DRAFT"
                    and existing_project.fase == "pre_venta"
                )
                if existing_project is not None and not is_lightweight:
                    result["status"] = "already_converted"
                    result["project_id"] = str(existing_project.id)
                    result["client_id"] = str(existing_project.client_id)
                    return result

        # ───────────────────────────────────────────────────────
        # 1. Lead → ganado (validamos transición · puede que estado_contacto
        #    actual sea propuesta_enviada · transición válida).
        # ───────────────────────────────────────────────────────
        lead_service = LeadService(self.db)
        try:
            lead = await lead_service.transition_estado_contacto(
                lead_id=lead.id,
                target_estado="ganado",
                notes=f"Contract {contract.id} firmado_cliente_at",
                metadata={
                    "event": "auto_conversion",
                    "contract_id": str(contract.id),
                },
            )
        except Exception as exc:
            # Log pero no abortar · puede ser estado terminal o legacy
            logger.warning(
                "transition lead→ganado falló · %s · continuando conversion",
                exc,
            )
            # Force estado_contacto = ganado (DEC explicit · firma es ground
            # truth · audit trail con metadata documenta forced transition)
            lead.estado_contacto = "ganado"
            lead.fecha_conversion = datetime.now(timezone.utc)
            await self.db.flush()

        # ───────────────────────────────────────────────────────
        # 2-3. Client + Proyecto (RLS-autosuficiente #7.6): en PROMOTE el client
        #      AUTORITATIVO es el dueño del proyecto ligero; en CREATE se
        #      resuelve/crea desde el lead. Contexto fijado ANTES de tocar projects
        #      (con RLS) · confirm_signing corre como fulkro_app sin contexto.
        # ───────────────────────────────────────────────────────
        if existing_project is not None:
            client = await self.db.get(Client, existing_project.client_id)
            # Contexto de proyecto ANTES de promover: el cambio de fase dispara
            # el trigger que inserta en project_lifecycle_events (RLS por proyecto).
            await set_tenant_context(
                self.db, client_id=client.id, project_id=existing_project.id,
            )
            project = await self._promote_lightweight_project(
                existing_project, lead, contract,
            )
        else:
            client = await self._find_or_create_client(lead)
            await set_tenant_context(self.db, client_id=client.id)
            project = await self._create_project_for_lead(client, lead, contract)
        result["client_id"] = str(client.id)
        result["project_id"] = str(project.id)
        # Contexto de proyecto para el resto (milestones · invite · audit_log R6).
        await set_tenant_context(self.db, client_id=client.id, project_id=project.id)

        # ───────────────────────────────────────────────────────
        # 4. Lead.convertido_a_proyecto_id = Project.id (rama B lo fija · rama A
        #    ya apunta al mismo proyecto ligero promovido)
        # ───────────────────────────────────────────────────────
        lead.convertido_a_proyecto_id = project.id
        await self.db.flush()

        # ───────────────────────────────────────────────────────
        # 5. Update contract con project_id
        # ───────────────────────────────────────────────────────
        if contract.project_id is None:
            contract.project_id = project.id
            await self.db.flush()

        # ───────────────────────────────────────────────────────
        # 6. MilestoneFactory · resolvable si proposal categoria+importe
        # ───────────────────────────────────────────────────────
        milestones_created = await self._create_milestones_if_resolvable(
            contract=contract, project=project, lead=lead,
        )
        result["milestones_created"] = milestones_created

        # ───────────────────────────────────────────────────────
        # 7. ClientUser invite (best-effort)
        # ───────────────────────────────────────────────────────
        client_user_id = await self._invite_client_user_best_effort(
            client=client, lead=lead,
        )
        if client_user_id:
            result["client_user_id"] = str(client_user_id)

        # audit_log R6 conversión (#7.6 · best-effort REAL vía SAVEPOINT · un
        # fallo del INSERT NO aborta la transacción de la firma).
        try:
            from backend.app.motors.m13_commercial.services.project_provisioning_service import (
                emit_conversion_audit_log,
            )
            async with self.db.begin_nested():
                await emit_conversion_audit_log(
                    self.db, project_id=project.id, client_id=client.id,
                    lead_id=lead.id, source="firma",
                )
        except Exception:
            logger.exception("audit_log conversión (firma) emit failed")

        # #10 B2 · borrador E-155 post-SIGNED (best-effort · NO bloquea la firma).
        from backend.app.motors.m13_commercial.services.fase0_bootstrap import (
            generate_e155_draft_best_effort,
        )
        await generate_e155_draft_best_effort(self.db, project_id=project.id)

        result["status"] = "converted"
        result["reason"] = "auto_conversion completed"
        return result

    # ────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ────────────────────────────────────────────────────────────

    async def _find_or_create_client(self, lead: Lead) -> Client:
        """Busca Client existing por (cif | email) o crea uno nuevo desde Lead.

        Prioriza CIF (identificador legal único) · fallback email.
        """
        # Match por CIF NORMALIZADO (#7 dedup robusto) · fallback al CIF crudo
        # para filas legacy sin cif_norm poblado.
        lead_cif_norm = normalize_cif(lead.empresa_cif)
        if lead_cif_norm:
            existing = await self.db.scalar(
                select(Client).where(
                    or_(
                        Client.cif_norm == lead_cif_norm,
                        Client.cif == lead.empresa_cif,
                    )
                )
            )
            if existing:
                logger.info(
                    "_find_or_create_client · match CIF(norm) %s · client %s",
                    lead_cif_norm, existing.id,
                )
                return existing

        # Match por email (lead_source/contacto_email pattern)
        if lead.contacto_email:
            existing = await self.db.scalar(
                select(Client).where(
                    Client.contacto_email == lead.contacto_email,
                )
            )
            if existing:
                logger.info(
                    "_find_or_create_client · match email %s · client %s",
                    lead.contacto_email, existing.id,
                )
                return existing

        # No existe · crear nuevo
        client = Client(
            nombre=lead.empresa_nombre,
            cif=lead.empresa_cif or self._generate_placeholder_cif(),
            sector=lead.sector,
            contacto_email=lead.contacto_email,
            contacto_telefono=lead.contacto_telefono,
            lead_source=lead.origen,
        )
        self.db.add(client)
        await self.db.flush()
        logger.info(
            "_find_or_create_client · created new client %s desde lead %s",
            client.id, lead.id,
        )
        return client

    async def _resolve_signing_fields(
        self, lead: Lead, contract: Contract,
    ) -> tuple[str, str | None]:
        """#7.4 · Resuelve (categoria_objetivo, tamano_empleados) en la firma.

        categoria: prefer Lead.categoria_objetivo_ens · fallback
        proposal.categoria_objetivo · default BASICA. tamano: desde
        proposal.alcance.empleados si resolvable. Carga proposal UNA vez (DRY ·
        compartido por crear rama B y promover rama A · OPS-026).
        """
        proposal = None
        if contract.proposal_id:
            proposal = await self.db.get(Proposal, contract.proposal_id)

        categoria = lead.categoria_objetivo_ens
        if not categoria and proposal and proposal.categoria_objetivo:
            categoria = proposal.categoria_objetivo
        if not categoria:
            categoria = DEFAULT_CATEGORIA_FALLBACK

        tamano = None
        if proposal is not None and isinstance(proposal.alcance, dict):
            tamano = _map_empleados_to_tamano(proposal.alcance.get("empleados"))
        return categoria, tamano

    async def _create_project_for_lead(
        self,
        client: Client,
        lead: Lead,
        contract: Contract,
    ) -> Project:
        """Crea Project asociado al Client desde Lead+Contract (rama B firma)."""
        categoria, tamano = await self._resolve_signing_fields(lead, contract)

        # Sub-atom 1.C.D.A.0.3 v3.8 · pre-populate dims comerciales desde
        # proposal.alcance. Resto dims con server_default · admin page refina.
        project_kwargs: dict[str, object] = {
            "client_id": client.id,
            "nombre": f"ENS · {lead.empresa_nombre}",
            "categoria_objetivo": categoria,
            "estado": "draft",
            "lifecycle_state": "SIGNED",  # Contract firmado · estado proyecto SIGNED
            "archetype": lead.archetype_ens,
            "papel_aapp": lead.papel_aapp,  # #7.4 arrastra Lead→Project
            "fecha_kickoff": None,  # Marcos define luego post-conversion
        }
        if tamano:
            project_kwargs["tamano_empleados"] = tamano
        project = Project(**project_kwargs)
        self.db.add(project)
        await self.db.flush()
        return project

    async def _promote_lightweight_project(
        self,
        project: Project,
        lead: Lead,
        contract: Contract,
    ) -> Project:
        """#7.4 rama A · Promueve el proyecto LIGERO (DRAFT/pre_venta) a SIGNED en
        la firma. NO crea otro proyecto · reusa el MISMO (convertido_a_proyecto_id
        estable) · deja de ser ligero (fase pre_venta → onboarding). Arrastra
        papel_aapp del lead (criterio de categorización).
        """
        categoria, tamano = await self._resolve_signing_fields(lead, contract)
        # #5 (Sub-bloque E) · si el proyecto ligero ya tiene suelo AAPP (Marcos
        # lo fijó pre-firma), preservar el piso: la categoría por firma nunca
        # baja del suelo heredado (Variante 2 · solo eleva).
        from backend.app.motors.m01_categorization.service import elevate_to_floor
        project.categoria_objetivo = elevate_to_floor(
            categoria, project.categoria_heredada_aapp
        )
        project.lifecycle_state = "SIGNED"
        project.fase = "onboarding"  # sale del estado ligero (pre_venta)
        project.estado = "draft"
        if lead.archetype_ens:
            project.archetype = lead.archetype_ens
        project.papel_aapp = lead.papel_aapp  # #7.4 arrastra Lead→Project
        if tamano:
            project.tamano_empleados = tamano
        await self.db.flush()
        return project

    async def create_lightweight_project_for_lead(self, lead: Lead) -> Project:
        """#7.3 · Crea (o reusa) el PROYECTO LIGERO de un lead para que pueda
        responder el cuestionario ANTES de la firma.

        ``lifecycle_state='DRAFT' + fase='pre_venta'`` = marca de proyecto ligero
        (los conteos de clientes activos lo EXCLUYEN · guard de coherencia #7.3).
        Idempotente: si el lead ya tiene proyecto (ligero o promovido) lo reusa.
        El MISMO proyecto se promociona a SIGNED en la firma (#7.4) · NO se crea
        otro. Arrastra ``papel_aapp`` del lead (criterio de categorización).
        """
        if lead.convertido_a_proyecto_id is not None:
            existing = await self.db.get(Project, lead.convertido_a_proyecto_id)
            if existing is not None:
                return existing

        client = await self._find_or_create_client(lead)
        # RLS: contexto de cliente antes de insertar el proyecto (mirror wizard).
        await set_tenant_context(self.db, client_id=client.id)
        project = Project(
            client_id=client.id,
            nombre=f"ENS · {lead.empresa_nombre}",
            categoria_objetivo=lead.categoria_objetivo_ens or DEFAULT_CATEGORIA_FALLBACK,
            archetype=lead.archetype_ens,
            papel_aapp=lead.papel_aapp,
            lifecycle_state="DRAFT",
            fase="pre_venta",
            estado="draft",
        )
        self.db.add(project)
        await self.db.flush()
        lead.convertido_a_proyecto_id = project.id
        await self.db.flush()
        return project

    async def _create_milestones_if_resolvable(
        self,
        *,
        contract: Contract,
        project: Project,
        lead: Lead,
    ) -> int:
        """Best-effort MilestoneFactory si proposal resolvable categoria+importe.

        Returns count milestones created · 0 si no resolvable.
        """
        if contract.proposal_id is None:
            logger.info(
                "_create_milestones · skip · contract %s sin proposal_id",
                contract.id,
            )
            return 0

        proposal = await self.db.get(Proposal, contract.proposal_id)
        if not proposal:
            return 0

        importe_total = proposal.importe_total
        categoria = (
            proposal.categoria_objetivo
            or lead.categoria_objetivo_ens
            or project.categoria_objetivo
        )

        if not importe_total or not categoria:
            logger.info(
                "_create_milestones · skip · proposal %s sin importe/categoria",
                proposal.id,
            )
            return 0

        try:
            from backend.app.billing.milestone_factory import MilestoneFactory
            factory = MilestoneFactory(self.db)
            created = await factory.create_milestones_for_contract(
                contract_id=contract.id,
                project_id=project.id,
                categoria=categoria,
                contract_total=Decimal(str(importe_total)),
                # Ejecutable 8 OLA 0 (#11 · #28): alimentar start_date para que
                # MilestoneFactory pueble scheduled_date (cronograma de pagos con
                # fechas reales = evidencia contractual MEDIA/ALTA). Antes quedaba
                # NULL en producción (solo los tests pasaban start_date).
                start_date=(
                    contract.firmado_cliente_at.date()
                    if contract.firmado_cliente_at else None
                ),
            )
            return len(created)
        except Exception as exc:
            logger.warning(
                "MilestoneFactory.create_milestones_for_contract failed · %s",
                exc,
            )
            return 0

    async def _invite_client_user_best_effort(
        self,
        *,
        client: Client,
        lead: Lead,
    ) -> uuid.UUID | None:
        """Crea ClientUser invite single-user-RW (ADR-013 v3) · best-effort.

        Skip silente si:
        - lead.contacto_email IS NULL
        - ya existe ClientUser con mismo email para este client
        - auth_service falla (log warning)

        Returns:
            UUID ClientUser creado · None si skipped/error.
        """
        if not lead.contacto_email:
            logger.info(
                "_invite_client_user · skip · lead %s sin contacto_email",
                lead.id,
            )
            return None

        try:
            from backend.app.motors.m21_portal_cliente.auth_service import (
                create_user, AuthError,
            )
            full_name = (
                lead.notas[:100] if lead.notas else lead.empresa_nombre
            )
            try:
                user, _temp_pwd = await create_user(
                    self.db,
                    client_id=client.id,
                    email=lead.contacto_email,
                    full_name=full_name,
                )
                # Magic-link PRIMER_ACCESO_CLIENTE generation queda a cargo
                # de admin via cockpit_resend_invite (m21 endpoint existing)
                # cuando Marcos quiera enviar el email real · evita coupling
                # NotificationOrchestrator + SMTP en handler crítico.
                return user.id
            except AuthError as exc:
                logger.info(
                    "_invite_client_user · skip · %s",
                    exc,
                )
                return None
        except Exception as exc:
            logger.warning(
                "_invite_client_user · error inesperado · %s",
                exc,
            )
            return None

    @staticmethod
    def _generate_placeholder_cif() -> str:
        """Genera CIF placeholder válido formato (1 letra + 8 dígitos).

        Marcos completa CIF real luego post-onboarding cuando cliente
        formaliza datos fiscales · spec v2.1 permite cif placeholder
        durante early-stage conversion.
        """
        return f"X{uuid.uuid4().hex[:8].upper()}"
