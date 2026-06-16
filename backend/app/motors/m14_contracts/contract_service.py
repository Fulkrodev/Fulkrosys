"""Contract lifecycle service (M14).

Estados: draft → firmado_marcos → sent → firmado_cliente → vigente → vencido/rescindido.

Plantillas:
- C-001 Contrato de servicios de consultoría ENS
- C-002 Adenda contractual proveedores (ENS/RGPD Art.28)
- C-003 Contrato de retainer post-certificación
- C-004 NDA mutuo
- C-005 Acuerdo de nivel de servicio (SLA)
"""
from __future__ import annotations

import hashlib
import io
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import (
    ClientCommitment,
    Contract,
    Proposal,
)
from backend.app.motors.m13_commercial.garantia import extract_garantia


CONTRACT_TEMPLATES: dict[str, dict[str, str]] = {
    "C-001": {
        "nombre": "Contrato de servicios de consultoría ENS",
        "tipo": "servicio",
    },
    "C-002": {
        "nombre": "Adenda contractual proveedores (ENS/RGPD Art.28)",
        "tipo": "adenda",
    },
    "C-003": {
        "nombre": "Contrato de retainer post-certificación",
        "tipo": "retainer",
    },
    "C-004": {
        "nombre": "NDA mutuo",
        "tipo": "nda",
    },
    "C-005": {
        "nombre": "Acuerdo de nivel de servicio (SLA)",
        "tipo": "sla",
    },
}

XYZPR_DEFAULTS: dict[str, Any] = {
    "x_horas_sponsor_mes": 2,
    "y_horas_ti_f1": 4,
    "y_horas_ti_f3": 8,
    "z_tope_paron_eur": 3000,
    "p_dias_pausa_max": 10,
    "r_dias_resolucion_max": 30,
}

VALID_ESTADOS = {
    "draft", "firmado_marcos", "sent", "firmado_cliente",
    "vigente", "vencido", "rescindido",
}


class ContractError(Exception):
    pass


class ContractService:
    """Servicio de ciclo de vida de contratos."""

    @staticmethod
    def list_templates() -> list[dict[str, str]]:
        return [
            {"plantilla_id": k, **v} for k, v in CONTRACT_TEMPLATES.items()
        ]

    async def generate_contract(
        self,
        db: AsyncSession,
        proposal_id: uuid.UUID,
        project_id: uuid.UUID,
        plantilla_id: str,
        cliente_firmante_nombre: str,
        cliente_firmante_cargo: str,
        parametros: dict[str, Any] | None = None,
        clausula_recursos: dict[str, Any] | None = None,
        vigencia_meses: int = 12,
        signatory_contact_ids: list[uuid.UUID] | None = None,
    ) -> Contract:
        if plantilla_id not in CONTRACT_TEMPLATES:
            raise ContractError(
                f"Plantilla desconocida: {plantilla_id}. "
                f"Válidas: {sorted(CONTRACT_TEMPLATES)}"
            )

        proposal = (await db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )).scalar_one_or_none()
        if not proposal:
            raise ContractError(f"Proposal {proposal_id} no encontrada")
        if proposal.estado != "won":
            raise ContractError(
                f"Solo se generan contratos desde propuestas won "
                f"(actual: {proposal.estado})"
            )

        tpl = CONTRACT_TEMPLATES[plantilla_id]
        xyzpr = {**XYZPR_DEFAULTS, **(parametros or {})}

        contract = Contract(
            lead_id=proposal.lead_id,
            proposal_id=proposal_id,
            project_id=project_id,
            tipo=tpl["tipo"],
            plantilla_id=plantilla_id,
            cliente_firmante_nombre=cliente_firmante_nombre,
            cliente_firmante_cargo=cliente_firmante_cargo,
            clausula_recursos=clausula_recursos or {},
            parametros_xyzpr=xyzpr,
            # #10 B1 · alcance comercial congelado (§1 del contrato).
            alcance_snapshot=self.derive_commercial_scope(proposal),
            vigente_desde=date.today(),
            vigente_hasta=date.today() + timedelta(days=30 * vigencia_meses),
            estado="draft",
        )
        db.add(contract)
        await db.flush()

        contract.hash_sha256 = self._compute_hash(contract)
        await db.flush()

        # Sub-fase 5.5.F integración M30 (plan v4.2 5.5.4.5):
        # auto-log contract_signature en timeline para signatarios.
        if signatory_contact_ids:
            from backend.app.motors.m30_client_contacts.service import (
                ClientContactService, ContactNotFoundError,
            )
            cs = ClientContactService(db)
            for contact_id in signatory_contact_ids:
                try:
                    await cs.log_interaction(
                        contact_id=contact_id,
                        interaction_type="contract_signature",
                        source_motor="m14",
                        source_id=contract.id,
                        summary=f"Signatory contrato {plantilla_id}",
                        details={
                            "plantilla_id": plantilla_id,
                            "tipo": tpl["tipo"],
                        },
                    )
                except ContactNotFoundError:
                    # Silent fail si contact_id inválido — no bloquea
                    # generación de contrato.
                    continue

        return contract

    # ══════════════════════════════════════════════════════════════════
    # Paso 6 — contrato Apendice M v2.2 con hitos oficiales + LCSP
    # ══════════════════════════════════════════════════════════════════

    async def generate_contract_apendice_m(
        self,
        db: AsyncSession,
        *,
        proposal_id: uuid.UUID,
        project_id: uuid.UUID,
        cliente: Any,
        cliente_firmante_nombre: str,
        cliente_firmante_cargo: str,
        vigencia_meses: int = 12,
        clausula_recursos: dict[str, Any] | None = None,
        narrative_mode: str = "deterministic",
    ) -> Contract:
        """Genera un C-001 apoyandose en ``Proposal.hitos_pago`` (Paso 6).

        Requiere una propuesta ya generada con
        ``ProposalService.generate_proposal_apendice_m``. Inyecta en
        ``parametros_xyzpr`` los datos necesarios para que el template
        C-001 renderice hitos oficiales + clausula LCSP AAPP + garantia
        por categoria.
        """
        proposal = (await db.execute(
            select(Proposal).where(Proposal.id == proposal_id)
        )).scalar_one_or_none()
        if proposal is None:
            raise ContractError(f"Proposal {proposal_id} no encontrada")

        from backend.app.core.legal import is_aapp as _is_aapp
        from backend.app.core.pricing import PricingCalculator

        aapp = _is_aapp(cliente)
        categoria = (proposal.categoria_objetivo or "").upper()
        if not categoria:
            raise ContractError(
                "Proposal sin categoria_objetivo — no se puede derivar plantilla"
            )

        # Recalcular hitos para asegurar suma exacta == contract_total
        calc = PricingCalculator()
        mp = calc.get_milestones(
            categoria,
            Decimal(str(proposal.importe_total or 0)),
        )
        hitos_payload = [
            {
                "code": h.code,
                "pct": float(h.pct * 100),
                "description": h.description,
                "amount": float(h.amount),
            }
            for h in mp.milestones
        ]

        importe_desglose = proposal.importe_desglose or {}
        parametros_xyzpr = {
            **XYZPR_DEFAULTS,
            "apendice_m_version": "v2.2",
            "pricing": {
                "categoria": categoria,
                "total": float(proposal.importe_total or 0),
                "base": importe_desglose.get("base"),
                "extras": importe_desglose.get("extras", []),
                "urgency_surcharge": importe_desglose.get("urgency_surcharge", 0),
                "urgent": importe_desglose.get("urgent", False),
                "garantia": extract_garantia(
                    importe_desglose, proposal.notas_marcos,
                ),
                "hitos": hitos_payload,
            },
            "is_aapp": aapp,
            "payment_days": 60 if aapp else 30,
        }

        contract = Contract(
            lead_id=proposal.lead_id,
            proposal_id=proposal_id,
            project_id=project_id,
            tipo="c001_implantacion_apendice_m",
            plantilla_id="C-001",
            cliente_firmante_nombre=cliente_firmante_nombre,
            cliente_firmante_cargo=cliente_firmante_cargo,
            clausula_recursos=clausula_recursos or {},
            parametros_xyzpr=parametros_xyzpr,
            # #10 B1 · alcance comercial congelado (§1 del contrato).
            alcance_snapshot=self.derive_commercial_scope(proposal),
            vigente_desde=date.today(),
            vigente_hasta=date.today() + timedelta(days=30 * vigencia_meses),
            estado="draft",
        )
        db.add(contract)
        await db.flush()

        if narrative_mode == "llm":
            try:
                llm_draft = await self._generate_clauses_via_agent_20(
                    db,
                    proposal_id=proposal_id,
                    cliente=cliente,
                    cliente_firmante_nombre=cliente_firmante_nombre,
                    cliente_firmante_cargo=cliente_firmante_cargo,
                )
                params = dict(contract.parametros_xyzpr or {})
                params["llm_clauses"] = llm_draft
                contract.parametros_xyzpr = params
                await db.flush()
            except Exception as exc:
                params = dict(contract.parametros_xyzpr or {})
                params["llm_clauses_error"] = str(exc)[:500]
                contract.parametros_xyzpr = params
                await db.flush()

        contract.hash_sha256 = self._compute_hash(contract)
        await db.flush()
        return contract

    async def _generate_clauses_via_agent_20(
        self,
        db: AsyncSession,
        *,
        proposal_id: uuid.UUID,
        cliente: Any,
        cliente_firmante_nombre: str,
        cliente_firmante_cargo: str,
    ) -> dict[str, Any]:
        """Invoca Agente 20 para producir clausulas narrativas Sonnet 4.6."""
        from backend.app.agents.agent_20_negociacion import (
            Agent20NegociadorContractual,
        )
        agent = Agent20NegociadorContractual()
        return await agent.generate_contract_clauses(
            db,
            proposal_id=proposal_id,
            cliente=cliente,
            cliente_firmante_nombre=cliente_firmante_nombre,
            cliente_firmante_cargo=cliente_firmante_cargo,
        )

    @staticmethod
    def _compute_hash(contract: Contract) -> str:
        """Hash SHA-256 del contenido esencial del contrato.

        Serialización determinista (sort_keys) — cualquier modificación de los
        campos esenciales cambia el hash; firmas/timestamps NO lo afectan.
        """
        xyzpr_json = json.dumps(contract.parametros_xyzpr or {}, sort_keys=True, default=str)
        clausula_json = json.dumps(contract.clausula_recursos or {}, sort_keys=True, default=str)
        payload = (
            f"{contract.id}|{contract.plantilla_id}|{contract.proposal_id}|"
            f"{contract.cliente_firmante_nombre}|{contract.cliente_firmante_cargo}|"
            f"{contract.vigente_desde}|{contract.vigente_hasta}|"
            f"{xyzpr_json}|{clausula_json}"
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def derive_commercial_scope(proposal: Proposal) -> dict[str, Any]:
        """#10 B1 · alcance COMERCIAL del contrato (categoría + dimensiones de la
        Proposal). Es el §1 del contrato · distinto del alcance ENS narrativo del
        E-155 (entregable post-firma · #10 B2). Se congela en
        ``Contract.alcance_snapshot`` al generar (trazabilidad legal/ENAC)."""
        alc = proposal.alcance or {}
        return {
            "categoria": (proposal.categoria_objetivo or "").upper() or None,
            "empleados": alc.get("empleados"),
            "sistemas": alc.get("sistemas"),
            "ubicaciones": alc.get("ubicaciones"),
            "sector_regulado": alc.get("sector_regulado"),
            "exclusiones": alc.get("exclusiones") or [],
            "importe_total": (
                float(proposal.importe_total)
                if proposal.importe_total is not None else None
            ),
        }

    async def get_contract(
        self, db: AsyncSession, contract_id: uuid.UUID
    ) -> Contract | None:
        res = await db.execute(select(Contract).where(Contract.id == contract_id))
        return res.scalar_one_or_none()

    async def list_contracts(
        self, db: AsyncSession, project_id: uuid.UUID | None = None
    ) -> list[Contract]:
        stmt = select(Contract)
        if project_id:
            stmt = stmt.where(Contract.project_id == project_id)
        stmt = stmt.order_by(Contract.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def set_scan_window(
        self,
        db: AsyncSession,
        contract_id: uuid.UUID,
        scan_window: dict | None,
    ) -> Contract:
        """Establece (o limpia con None) la ventana de escaneo del contrato.

        Consumed by M08 verification scope_deriver vía fetch_scan_window_for_project
        para wiring contractual de la ventana nocturna (TODO-M8-G3 · SAN-B.MB-3.bis.3).
        """
        c = await self.get_contract(db, contract_id)
        if not c:
            raise ContractError(f"Contract {contract_id} no encontrado")
        c.scan_window = scan_window
        await db.flush()
        return c

    async def sign_marcos(
        self, db: AsyncSession, contract_id: uuid.UUID
    ) -> Contract:
        c = await self.get_contract(db, contract_id)
        if not c:
            raise ContractError(f"Contract {contract_id} no encontrado")
        if c.estado != "draft":
            raise ContractError(
                f"Solo se firma Marcos sobre contratos draft (actual: {c.estado})"
            )
        c.firmado_marcos_at = datetime.now(timezone.utc)
        c.estado = "firmado_marcos"
        c.hash_sha256 = self._compute_hash(c)
        await db.flush()
        return c

    # §3.3: send_for_client_signature + register_client_signature ELIMINADOS
    # (código muerto · #43). El flujo autoritativo es el m13 ContractSigningFlow
    # (FIRMA_CONTRATO + canvas Ed25519); el endpoint send-client delega en m13 y
    # el callback register-client-signature ya se eliminó. La UI nunca los llamaba.

    async def retract_in_flight_contract(
        self,
        db: AsyncSession,
        contract_id: uuid.UUID,
        motivo: str = "recategorizacion",
    ) -> Contract:
        """#5 cabo N2.5 · retira/anula un contrato EN VUELO (enviado al cliente
        y/o firmado por Marcos, SIN firma del cliente) para que el cliente NO
        firme un contrato obsoleto.

        Inviolable: NUNCA toca un contrato con firma del cliente
        (``firmado_cliente_at``) — eso es N3 (vía formal · nuevo contrato/adenda).

        Barreras (defensa en profundidad):
          1. Revoca EFECTIVAMENTE el magic-link de firma → ``consume_magic_link``
             rechaza links revocados, así que ``confirm_signing`` falla (la única
             barrera real del flujo público #43, que NO mira ``estado``).
          2. Cierra el ``SigningIntent`` (status='expired') → cierra cualquier
             bypass vía ``/firmas-pendientes`` (sign rechaza intents no pending).
          3. ``estado`` → 'anulado_recategorizacion' + constancia en ``adendas``.
        """
        c = await self.get_contract(db, contract_id)
        if not c:
            raise ContractError(f"Contract {contract_id} no encontrado")
        if c.firmado_cliente_at is not None:
            raise ContractError(
                "El contrato está FIRMADO por el cliente · no se retira (la firma "
                "es inmutable · usa la vía formal: nuevo contrato/adenda)"
            )
        if c.estado not in ("firmado_marcos", "sent"):
            raise ContractError(
                f"El contrato no está en vuelo (estado actual: {c.estado})"
            )

        # 1) Revocar el magic-link (barrera efectiva del flujo público de firma).
        if c.firmado_cliente_link_id:
            from backend.app.motors.m12_magic_link.service import (
                MagicLinkService,
                MagicLinkNotFoundError,
            )
            try:
                await MagicLinkService(db).revoke_magic_link(
                    c.firmado_cliente_link_id,
                    reason=f"contrato_retirado:{motivo}",
                )
            except MagicLinkNotFoundError:
                pass  # ya inexistente · idempotente

        # 2) Cerrar el SigningIntent (cierra el bypass /firmas-pendientes).
        if c.signing_intent_id:
            from backend.app.motors.m05_signing.models import SigningIntent
            intent = await db.get(SigningIntent, c.signing_intent_id)
            if intent is not None and intent.status not in (
                "signed", "rejected", "expired",
            ):
                intent.status = "expired"

        # 3) Anular el contrato + dejar constancia (NO se borra · traza).
        now = datetime.now(timezone.utc)
        c.estado = "anulado_recategorizacion"
        adendas = c.adendas if isinstance(c.adendas, dict) else {}
        retracts = adendas.get("retracts")
        if not isinstance(retracts, list):
            retracts = []
        retracts.append({
            "tipo": "contrato_en_vuelo_retirado",
            "motivo": motivo,
            "at": now.isoformat(),
            "magic_link_revocado": (
                str(c.firmado_cliente_link_id)
                if c.firmado_cliente_link_id else None
            ),
        })
        adendas["retracts"] = retracts
        c.adendas = adendas
        await db.flush()
        return c

    async def add_commitment(
        self,
        db: AsyncSession,
        contract_id: uuid.UUID,
        tipo: str,
        descripcion: str | None = None,
        parametro: str | None = None,
        valor_esperado: str | None = None,
    ) -> ClientCommitment:
        c = await self.get_contract(db, contract_id)
        if not c:
            raise ContractError(f"Contract {contract_id} no encontrado")

        commitment = ClientCommitment(
            contract_id=contract_id,
            project_id=c.project_id,
            tipo=tipo,
            descripcion=descripcion,
            parametro=parametro,
            valor_esperado=valor_esperado,
            cumplido=None,
        )
        db.add(commitment)
        await db.flush()
        return commitment

    async def list_commitments(
        self, db: AsyncSession, contract_id: uuid.UUID
    ) -> list[ClientCommitment]:
        res = await db.execute(
            select(ClientCommitment).where(ClientCommitment.contract_id == contract_id)
        )
        return list(res.scalars().all())

    async def check_commitments(
        self, db: AsyncSession, contract_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        commitments = await self.list_commitments(db, contract_id)
        results = []
        now = datetime.now(timezone.utc)
        for com in commitments:
            if com.valor_actual is None or com.valor_esperado is None:
                cumplido = None
            else:
                cumplido = com.valor_actual == com.valor_esperado
            com.cumplido = cumplido
            com.ultima_verificacion_at = now
            results.append({
                "commitment_id": str(com.id),
                "tipo": com.tipo,
                "parametro": com.parametro,
                "valor_esperado": com.valor_esperado,
                "valor_actual": com.valor_actual,
                "cumplido": cumplido,
            })
        await db.flush()
        return results

    async def generate_docx(
        self, db: AsyncSession, contract_id: uuid.UUID
    ) -> bytes:
        from docx import Document

        c = await self.get_contract(db, contract_id)
        if not c:
            raise ContractError(f"Contract {contract_id} no encontrado")
        tpl = CONTRACT_TEMPLATES.get(c.plantilla_id, {"nombre": "Contrato"})

        doc = Document()
        doc.add_heading(tpl["nombre"], level=0)
        doc.add_paragraph(f"Plantilla: {c.plantilla_id}")
        doc.add_paragraph(f"Firmante cliente: {c.cliente_firmante_nombre}")
        doc.add_paragraph(f"Cargo: {c.cliente_firmante_cargo}")
        doc.add_paragraph(f"Vigencia: {c.vigente_desde} – {c.vigente_hasta}")

        doc.add_heading("Parámetros XYZPR", level=1)
        for k, v in (c.parametros_xyzpr or {}).items():
            doc.add_paragraph(f"• {k}: {v}")

        if c.clausula_recursos:
            doc.add_heading("Cláusula de recursos del cliente", level=1)
            for k, v in c.clausula_recursos.items():
                doc.add_paragraph(f"• {k}: {v}")

        doc.add_heading("Firmas", level=1)
        doc.add_paragraph(
            f"Marcos: {c.firmado_marcos_at or 'pendiente'}"
        )
        doc.add_paragraph(
            f"Cliente: {c.firmado_cliente_at or 'pendiente'}"
        )
        doc.add_paragraph(f"Hash SHA-256: {c.hash_sha256 or '-'}")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
