"""Billing service — facturación fiscal española (M15).

- Correlativo secuencial por (emisor_tenant, año): FULKRO-{año}-{NNNN}.
- IVA 21% default, IRPF 15% si cliente retiene.
- Verifactu hash chain: SHA-256(prev_hash|numero|fecha|base|total).
- Recordatorios automáticos de pago (15/30/45/60 días).
- Anulación vía factura rectificativa.

Nota RLS: el correlativo se calcula bajo el scope del cliente emisor.
Marcos es emisor único — cada cliente-tenant tiene su propia secuencia.

Integraciones (vía base de datos compartida, sin imports Python directos):
- M14 (Contracts): la tabla ``contracts`` proporciona ``contract_id``,
  importes y plan de pagos para emitir facturas asociadas a un contrato.
- M23 (Retainer): la tabla ``retainer_contracts`` define las cadencias
  recurrentes (mensual / trimestral) que dispara la generación periódica
  de facturas vía Celery beat.
Patrón SQL-first: cada motor mantiene su esquema y este servicio lee solo
los campos necesarios; no se acopla a las clases de dominio del otro motor.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.commercial import (
    Contract,
    Invoice,
    InvoiceLine,
    PaymentReminder,
)


IVA_DEFAULT = 21.0
IRPF_DEFAULT = 15.0
DIAS_VENCIMIENTO_DEFAULT = 30


class BillingError(Exception):
    pass


class BillingService:
    """Servicio de facturación fiscal."""

    async def generate_invoice(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
        project_id: uuid.UUID | None,
        contract_id: uuid.UUID | None,
        concepto: str,
        lineas: list[dict[str, Any]],
        tipo: str = "ordinaria",
        aplicar_irpf: bool = False,
        iva_percent: float = IVA_DEFAULT,
        irpf_percent: float = IRPF_DEFAULT,
        hito_asociado: str | None = None,
        dias_vencimiento: int = DIAS_VENCIMIENTO_DEFAULT,
        fecha_emision: date | None = None,
    ) -> Invoice:
        if not lineas:
            raise BillingError("Una factura requiere al menos una línea")
        if tipo not in ("ordinaria", "rectificativa", "proforma"):
            raise BillingError(f"Tipo inválido: {tipo}")

        fecha_emision = fecha_emision or date.today()

        # FIX P0-3 (integridad fiscal): serializa numeración correlativa + cadena
        # VeriFactu por (emisor único, año). Sin el lock, COUNT(*)+1 y la lectura
        # del hash previo corren en transacciones independientes (admin, beat
        # Celery m23, hito de contrato) → números fiscales DUPLICADOS y cadena
        # VeriFactu bifurcada bajo concurrencia. pg_advisory_xact_lock es
        # transaccional: se libera al commit/rollback, serializando toda la
        # emisión del año (Pattern #22). La red de seguridad en BD es el índice
        # único parcial sobre numero_correlativo (migración
        # invoice_correlative_unique_001): un duplicado residual falla ruidoso en
        # vez de corromper la secuencia fiscal en silencio.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:seq_key))"),
            {"seq_key": f"invoice_seq_{fecha_emision.year}"},
        )
        numero = await self._get_next_correlative(db, fecha_emision.year)

        base_imponible = Decimal("0")
        prepared_lines: list[dict[str, Any]] = []
        for idx, ln in enumerate(lineas):
            cantidad = Decimal(str(ln.get("cantidad", 1)))
            precio = Decimal(str(ln["precio_unitario"]))
            subtotal = (cantidad * precio).quantize(Decimal("0.01"))
            prepared_lines.append({
                "descripcion": ln["descripcion"],
                "cantidad": cantidad,
                "precio_unitario": precio,
                "subtotal": subtotal,
                "hito_asociado": ln.get("hito_asociado") or hito_asociado,
                "paron_asociado": ln.get("paron_asociado"),
                "orden": idx,
            })
            base_imponible += subtotal

        base_imponible = base_imponible.quantize(Decimal("0.01"))
        iva_importe = (base_imponible * Decimal(str(iva_percent)) / 100).quantize(Decimal("0.01"))
        if aplicar_irpf:
            irpf_val = Decimal(str(irpf_percent))
            irpf_importe = (base_imponible * irpf_val / 100).quantize(Decimal("0.01"))
        else:
            irpf_val = Decimal("0")
            irpf_importe = Decimal("0")
        total = (base_imponible + iva_importe - irpf_importe).quantize(Decimal("0.01"))

        verifactu_hash = await self._calculate_verifactu_hash(
            db, fecha_emision.year,
            numero=numero,
            fecha=fecha_emision,
            base=base_imponible,
            total=total,
        )

        invoice = Invoice(
            client_id=client_id,
            project_id=project_id,
            contract_id=contract_id,
            numero_correlativo=numero,
            tipo=tipo,
            concepto=concepto,
            # §4.4 audit-2026-06-15 · persistir Decimal directo (columnas
            # Numeric(12,2)) · el float() reintroducía imprecisión binaria en
            # importes fiscales/VeriFactu.
            base_imponible=base_imponible,
            iva_percent=Decimal(str(iva_percent)),
            iva_importe=iva_importe,
            irpf_percent=irpf_val,
            irpf_importe=irpf_importe,
            total=total,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_emision + timedelta(days=dias_vencimiento),
            estado_pago="pendiente",
            verifactu_hash=verifactu_hash,
        )
        db.add(invoice)
        await db.flush()

        for ln in prepared_lines:
            db.add(InvoiceLine(
                invoice_id=invoice.id,
                descripcion=ln["descripcion"],
                cantidad=ln["cantidad"],
                precio_unitario=ln["precio_unitario"],
                subtotal=ln["subtotal"],
                hito_asociado=ln["hito_asociado"],
                paron_asociado=ln["paron_asociado"],
                orden=ln["orden"],
            ))
        await db.flush()
        return invoice

    async def _get_next_correlative(self, db: AsyncSession, year: int) -> str:
        """Formato: FULKRO-{año}-{NNNN} · serie fiscal ÚNICA por emisor (global).

        El índice uq_invoices_numero_correlativo es GLOBAL (un solo emisor). El
        COUNT DEBE correr FUERA de RLS: bajo fulkro_app+tenant solo contaría las
        facturas del cliente actual → todos empezarían en 0001 → IntegrityError al
        2º cliente del año. bypassrls (transaction-scoped) cuenta toda la serie.
        """
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            count = (await db.execute(
                text(
                    "SELECT COUNT(*) FROM invoices "
                    "WHERE EXTRACT(YEAR FROM fecha_emision) = :y "
                    "AND tipo != 'anulada'"
                ),
                {"y": year},
            )).scalar() or 0
        finally:
            await db.execute(text("RESET ROLE"))
        return f"FULKRO-{year}-{count + 1:04d}"

    async def _calculate_verifactu_hash(
        self,
        db: AsyncSession,
        year: int,
        numero: str,
        fecha: date,
        base: Decimal,
        total: Decimal,
    ) -> str:
        """Hash encadenado Verifactu-style.

        Primera factura del año: prev_hash = "INICIO-{año}".
        Siguientes: prev_hash = verifactu_hash de la factura anterior del año.
        """
        # La cadena Verifactu es ÚNICA por emisor (global): leer la factura previa
        # FUERA de RLS, si no bajo fulkro_app+tenant cada cliente encadenaría su
        # propia sub-cadena (bifurcación de la cadena fiscal).
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            last = (await db.execute(
                text(
                    "SELECT verifactu_hash FROM invoices "
                    "WHERE EXTRACT(YEAR FROM fecha_emision) = :y "
                    "AND verifactu_hash IS NOT NULL "
                    "ORDER BY fecha_emision DESC, numero_correlativo DESC "
                    "LIMIT 1"
                ),
                {"y": year},
            )).scalar()
        finally:
            await db.execute(text("RESET ROLE"))
        prev_hash = last or f"INICIO-{year}"
        payload = f"{prev_hash}|{numero}|{fecha.isoformat()}|{base}|{total}"
        return hashlib.sha256(payload.encode()).hexdigest()

    async def get_invoice(
        self, db: AsyncSession, invoice_id: uuid.UUID
    ) -> Invoice | None:
        res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        return res.scalar_one_or_none()

    async def list_invoices(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None = None,
        estado: str | None = None,
    ) -> list[Invoice]:
        stmt = select(Invoice)
        if project_id:
            stmt = stmt.where(Invoice.project_id == project_id)
        if estado:
            stmt = stmt.where(Invoice.estado_pago == estado)
        stmt = stmt.order_by(Invoice.fecha_emision.desc(), Invoice.numero_correlativo.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def list_invoices_by_client(
        self,
        db: AsyncSession,
        client_id: uuid.UUID,
    ) -> list[tuple[Invoice, str | None]]:
        """Retorna (Invoice, project_name) por cliente — sub-fase 5.A FASE 5.

        Endpoint agregado ``GET /billing/clients/{id}/invoices`` para Tab
        Facturas en panel ``/admin/clients/{id}``. Decisión audit pre-FASE 5
        H4: evitar N+1 que tendría el frontend si listase projects e iterase
        invoices por cada uno.

        ``project_name`` es ``None`` cuando ``Invoice.project_id`` es NULL
        (factura asociada a cliente sin project — caso legítimo).
        """
        from sqlalchemy.orm import aliased

        from backend.app.models.core import Project

        proj = aliased(Project)
        stmt = (
            select(Invoice, proj.nombre)
            .where(Invoice.client_id == client_id)
            .outerjoin(proj, Invoice.project_id == proj.id)
            .order_by(Invoice.fecha_emision.desc().nulls_last())
        )
        res = await db.execute(stmt)
        return [(invoice, name) for invoice, name in res.all()]

    async def list_lines(
        self, db: AsyncSession, invoice_id: uuid.UUID
    ) -> list[InvoiceLine]:
        res = await db.execute(
            select(InvoiceLine)
            .where(InvoiceLine.invoice_id == invoice_id)
            .order_by(InvoiceLine.orden)
        )
        return list(res.scalars().all())

    async def mark_paid(self, db: AsyncSession, invoice_id: uuid.UUID) -> Invoice:
        inv = await self.get_invoice(db, invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} no encontrada")
        if inv.estado_pago not in ("pendiente", "vencida"):
            raise BillingError(
                f"Solo pendientes/vencidas pasan a pagada (actual: {inv.estado_pago})"
            )
        inv.estado_pago = "pagada"
        await db.flush()
        return inv

    async def mark_overdue(self, db: AsyncSession, invoice_id: uuid.UUID) -> Invoice:
        inv = await self.get_invoice(db, invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} no encontrada")
        if inv.estado_pago != "pendiente":
            return inv
        inv.estado_pago = "vencida"
        await db.flush()
        return inv

    async def cancel_invoice(
        self, db: AsyncSession, invoice_id: uuid.UUID
    ) -> tuple[Invoice, Invoice]:
        """Anula una factura emitiendo una rectificativa negativa.

        Retorna (invoice_original, invoice_rectificativa).
        """
        inv = await self.get_invoice(db, invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} no encontrada")
        if inv.estado_pago == "anulada":
            raise BillingError("Invoice ya anulada")

        lineas = await self.list_lines(db, invoice_id)
        rect_lines = [
            {
                "descripcion": f"RECTIFICATIVA de {inv.numero_correlativo}: {ln.descripcion}",
                "cantidad": float(ln.cantidad),
                "precio_unitario": -float(ln.precio_unitario),
            }
            for ln in lineas
        ]
        rectificativa = await self.generate_invoice(
            db,
            client_id=inv.client_id,
            project_id=inv.project_id,
            contract_id=inv.contract_id,
            concepto=f"Rectificativa de {inv.numero_correlativo}",
            lineas=rect_lines,
            tipo="rectificativa",
            aplicar_irpf=(inv.irpf_importe or 0) > 0,
            iva_percent=float(inv.iva_percent or IVA_DEFAULT),
            irpf_percent=float(inv.irpf_percent or 0),
        )
        inv.estado_pago = "anulada"
        await db.flush()
        return inv, rectificativa

    async def generate_from_milestone(
        self,
        db: AsyncSession,
        contract_id: uuid.UUID,
        hito: str,
    ) -> Invoice:
        """Genera factura automática al completar un hito del contrato.

        Lee hitos_pago de la proposal ganada + importe_total → calcula importe
        proporcional → crea invoice con concepto ligado al hito.
        """
        c = (await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )).scalar_one_or_none()
        if not c:
            raise BillingError(f"Contract {contract_id} no encontrado")
        if not c.proposal_id:
            raise BillingError("Contract sin proposal_id asociado")

        from backend.app.models.commercial import Proposal
        proposal = (await db.execute(
            select(Proposal).where(Proposal.id == c.proposal_id)
        )).scalar_one_or_none()
        if not proposal:
            raise BillingError("Proposal origen no encontrada")

        hitos_data = (proposal.hitos_pago or {}).get("hitos") or []

        # Schema bridge: legacy generate_proposal stores {nombre, importe};
        # Apéndice-M generate_proposal_apendice_m stores {code, description, amount}.
        # Match by any label key and read amount from either key.
        def _hito_label(h: dict) -> str:
            return h.get("nombre") or h.get("description") or h.get("code") or ""

        hito_data = next((h for h in hitos_data if _hito_label(h) == hito), None)
        if not hito_data:
            raise BillingError(
                f"Hito '{hito}' no existe en la propuesta "
                f"(disponibles: {[_hito_label(h) for h in hitos_data]})"
            )

        importe = float(hito_data.get("importe") or hito_data.get("amount") or 0)
        if importe <= 0:
            raise BillingError(f"Hito '{hito}' sin importe válido")

        # Client from project
        from backend.app.models.core import Project
        project = (await db.execute(
            select(Project).where(Project.id == c.project_id)
        )).scalar_one_or_none()
        if not project:
            raise BillingError("Project del contrato no existe")

        return await self.generate_invoice(
            db,
            client_id=project.client_id,
            project_id=c.project_id,
            contract_id=contract_id,
            concepto=f"Hito {hito} — contrato {c.plantilla_id}",
            lineas=[{
                "descripcion": f"Hito {hito}",
                "cantidad": 1,
                "precio_unitario": importe,
                "hito_asociado": hito,
            }],
            hito_asociado=hito,
        )

    async def generate_reminder(
        self, db: AsyncSession, invoice_id: uuid.UUID, dias_vencida: int
    ) -> PaymentReminder:
        inv = await self.get_invoice(db, invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} no encontrada")
        if dias_vencida not in (15, 30, 45, 60):
            raise BillingError(
                "dias_vencida debe ser 15, 30, 45 o 60"
            )

        template = {
            15: "recordatorio_amable",
            30: "recordatorio_firme",
            45: "aviso_pre_judicial",
            60: "notificacion_deuda",
        }[dias_vencida]
        contenido = (
            f"Factura {inv.numero_correlativo} — {dias_vencida} días vencida. "
            f"Importe pendiente: {float(inv.total):.2f} €."
        )
        reminder = PaymentReminder(
            invoice_id=invoice_id,
            dias_vencida=dias_vencida,
            template_usado=template,
            canal="email",
            contenido=contenido,
            enviado_at=datetime.now(timezone.utc),
        )
        db.add(reminder)
        await db.flush()
        return reminder

    async def get_billing_summary(
        self, db: AsyncSession, project_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        invoices = await self.list_invoices(db, project_id=project_id)
        totales = {"facturado": 0.0, "cobrado": 0.0, "pendiente": 0.0, "vencido": 0.0, "anulado": 0.0}
        for inv in invoices:
            t = float(inv.total or 0)
            totales["facturado"] += t if inv.estado_pago != "anulada" else 0
            if inv.estado_pago == "pagada":
                totales["cobrado"] += t
            elif inv.estado_pago == "pendiente":
                totales["pendiente"] += t
            elif inv.estado_pago == "vencida":
                totales["vencido"] += t
            elif inv.estado_pago == "anulada":
                totales["anulado"] += t

        return {
            "total_invoices": len(invoices),
            **{k: round(v, 2) for k, v in totales.items()},
        }

    def _build_verifactu_qr_payload(self, inv, nif: str = "") -> str:
        """Return the AEAT Verifactu-style URL encoded in the invoice QR.

        Matches the format mandated by RD 1007/2023 Disposición
        Transitoria Segunda: ``?nif=X&numserie=Y&fecha=Z&importe=W``.
        The ``prewww2.aeat.es`` base is the one published by AEAT for
        the verification endpoint. ``hash`` is appended so auditors can
        cross-check the chain from the invoice itself.

        ``nif`` es el NIF/CIF del emisor (fuente única vía
        ``core.fiscal_identity.get_fiscal_identity`` · punto #44).
        Degradación elegante: si está vacío, el QR sale sin NIF (NUNCA
        con el placeholder ``__CONSULTOR_NIF__``).
        """
        from urllib.parse import urlencode

        from backend.app.config import get_settings
        params = {
            "nif": nif,
            "numserie": inv.numero_correlativo,
            "fecha": inv.fecha_emision.strftime("%d-%m-%Y"),
            "importe": f"{float(inv.total):.2f}",
            "hash": (inv.verifactu_hash or "")[:16],
        }
        # #25 · base parametrizable (default pre-prod · override prod por ENV
        # VERIFACTU_QR_BASE_URL). Antes hardcodeada a prewww2 → QR inescaneable
        # en producción.
        return get_settings().verifactu_qr_base_url + urlencode(params)

    async def generate_invoice_pdf(
        self, db: AsyncSession, invoice_id: uuid.UUID,
        include_qr: bool = True,
    ) -> bytes:
        """Generate the invoice document with a Verifactu-compatible QR.

        The QR encodes the AEAT verification URL including
        ``numserie``, ``fecha``, ``importe`` and a 16-char prefix of the
        chained ``verifactu_hash``. The image is embedded in-line so
        the auditor can scan it from the printed or PDF-exported invoice.
        """
        from docx import Document
        from docx.shared import Cm

        inv = await self.get_invoice(db, invoice_id)
        if not inv:
            raise BillingError(f"Invoice {invoice_id} no encontrada")
        lineas = await self.list_lines(db, invoice_id)

        # Identidad fiscal del emisor (FUENTE ÚNICA · punto #44) + receptor.
        from backend.app.core.fiscal_identity import get_fiscal_identity
        from backend.app.models.core import Client
        fiscal = await get_fiscal_identity(db)
        cliente = await db.get(Client, inv.client_id)

        doc = Document()
        doc.add_heading(f"Factura {inv.numero_correlativo}", level=0)

        # Bloque emisor — degradación elegante: si no hay datos fiscales
        # configurados, nota clara (NUNCA el placeholder __CONSULTOR_NIF__).
        doc.add_heading("Emisor", level=1)
        if fiscal.has_identity:
            if fiscal.display_name:
                doc.add_paragraph(fiscal.display_name)
            if (fiscal.nombre_comercial and fiscal.nombre_fiscal
                    and fiscal.nombre_comercial != fiscal.nombre_fiscal):
                doc.add_paragraph(f"Titular: {fiscal.nombre_fiscal}")
            if fiscal.has_nif:
                doc.add_paragraph(f"NIF: {fiscal.nif}")
            if fiscal.domicilio_completo:
                doc.add_paragraph(f"Domicilio fiscal: {fiscal.domicilio_completo}")
        else:
            doc.add_paragraph(
                "[Datos fiscales del emisor pendientes de configurar "
                "en /admin/settings/fiscal]"
            )

        # Bloque receptor (cliente).
        if cliente is not None:
            doc.add_heading("Receptor", level=1)
            doc.add_paragraph(cliente.nombre)
            if cliente.cif:
                doc.add_paragraph(f"CIF: {cliente.cif}")
            if cliente.provincia:
                doc.add_paragraph(f"Provincia: {cliente.provincia}")

        doc.add_paragraph(f"Tipo: {inv.tipo}")
        doc.add_paragraph(f"Fecha emisión: {inv.fecha_emision}")
        doc.add_paragraph(f"Fecha vencimiento: {inv.fecha_vencimiento}")
        doc.add_paragraph(f"Concepto: {inv.concepto}")

        doc.add_heading("Líneas", level=1)
        for ln in lineas:
            doc.add_paragraph(
                f"{ln.descripcion} — {ln.cantidad} x {float(ln.precio_unitario):.2f} € = {float(ln.subtotal):.2f} €"
            )

        doc.add_heading("Totales", level=1)
        doc.add_paragraph(f"Base imponible: {float(inv.base_imponible):.2f} €")
        doc.add_paragraph(f"IVA {inv.iva_percent}%: {float(inv.iva_importe):.2f} €")
        if inv.irpf_importe and float(inv.irpf_importe) > 0:
            doc.add_paragraph(f"Retención IRPF {inv.irpf_percent}%: -{float(inv.irpf_importe):.2f} €")
        doc.add_paragraph(f"TOTAL: {float(inv.total):.2f} €")
        doc.add_paragraph(f"Verifactu hash (SHA-256): {inv.verifactu_hash}")

        # Forma de pago — transferencia (degradación elegante si no hay IBAN).
        if fiscal.has_iban:
            doc.add_heading("Forma de pago — Transferencia bancaria", level=1)
            doc.add_paragraph(f"IBAN: {fiscal.iban}")
            if fiscal.bank_holder:
                doc.add_paragraph(f"Titular: {fiscal.bank_holder}")
            if fiscal.bank_institution:
                doc.add_paragraph(f"Entidad: {fiscal.bank_institution}")
            if fiscal.bank_bic:
                doc.add_paragraph(f"BIC/SWIFT: {fiscal.bank_bic}")

        if include_qr:
            try:
                import qrcode
                qr_url = self._build_verifactu_qr_payload(inv, fiscal.nif)
                qr = qrcode.QRCode(
                    version=None, box_size=6, border=2,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                )
                qr.add_data(qr_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                qr_buf = io.BytesIO()
                img.save(qr_buf, format="PNG")
                qr_buf.seek(0)
                doc.add_heading("Verificación AEAT (Verifactu)", level=1)
                doc.add_paragraph(
                    "Escanee el código QR con su aplicación de verificación "
                    "fiscal. URL codificada:"
                )
                doc.add_paragraph(qr_url)
                doc.add_picture(qr_buf, width=Cm(4.5))
            except ImportError:
                doc.add_paragraph(
                    "[QR no disponible — instale 'qrcode' para habilitarlo]"
                )

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    # ══════════════════════════════════════════════════════════════════
    # Paso 6 — facturas oficiales Apendice M (milestone/bolsa/quick/audit)
    # ══════════════════════════════════════════════════════════════════

    async def generate_milestone_invoice_apendice_m(
        self,
        db: AsyncSession,
        *,
        contract_id: uuid.UUID,
        milestone_code: str,
        cliente: Any = None,
    ) -> Invoice:
        """Genera factura de hito leyendo hitos Apendice M v2.2 de la propuesta.

        Diferencias con ``generate_from_milestone`` legacy:
        - Usa ``code`` (no ``nombre``) para identificar el hito.
        - Aplica plazo pago 60d si cliente AAPP (LCSP art. 198.4).
        - Concepto enriquecido con categoria + porcentaje.
        """
        from backend.app.models.commercial import Proposal
        from backend.app.models.core import Project

        c = (await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )).scalar_one_or_none()
        if not c:
            raise BillingError(f"Contract {contract_id} no encontrado")
        if not c.proposal_id:
            raise BillingError("Contract sin proposal_id asociado")
        proposal = (await db.execute(
            select(Proposal).where(Proposal.id == c.proposal_id)
        )).scalar_one_or_none()
        if not proposal:
            raise BillingError("Proposal origen no encontrada")

        hitos_data = (proposal.hitos_pago or {}).get("hitos") or []
        hito = next(
            (h for h in hitos_data if h.get("code") == milestone_code), None,
        )
        if not hito:
            raise BillingError(
                f"Hito '{milestone_code}' no existe en propuesta "
                f"(disponibles: {[h.get('code') for h in hitos_data]})"
            )
        importe = float(hito.get("amount") or 0)
        if importe <= 0:
            raise BillingError(
                f"Hito {milestone_code!r} sin importe valido"
            )

        project = (await db.execute(
            select(Project).where(Project.id == c.project_id)
        )).scalar_one_or_none()
        if not project:
            raise BillingError("Project del contrato no existe")

        # Resolver cliente si no se paso
        if cliente is None:
            from backend.app.models.core import Client
            cliente = (await db.execute(
                select(Client).where(Client.id == project.client_id)
            )).scalar_one_or_none()

        from backend.app.core.legal import is_aapp as _is_aapp
        aapp = _is_aapp(cliente)
        dias_venc = 60 if aapp else 30

        categoria = (proposal.categoria_objetivo or "").upper()
        concepto = (
            f"{categoria} {hito.get('description', milestone_code)} "
            f"({hito.get('pct', 0):.0f}% hito {milestone_code})"
        )
        linea_desc = (
            f"Hito {milestone_code}: {hito.get('description', '')} "
            f"({hito.get('pct', 0):.0f}% de {float(proposal.importe_total or 0):.2f} EUR)"
        )
        if aapp:
            concepto += " — Pago LCSP art. 198.4"

        return await self.generate_invoice(
            db,
            client_id=project.client_id,
            project_id=c.project_id,
            contract_id=contract_id,
            concepto=concepto,
            lineas=[{
                "descripcion": linea_desc,
                "cantidad": 1,
                "precio_unitario": importe,
                "hito_asociado": milestone_code,
            }],
            hito_asociado=milestone_code,
            dias_vencimiento=dias_venc,
        )

    async def generate_bolsa_flex_invoice(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        hours: int,
        project_id: uuid.UUID | None = None,
        concepto_detalle: str | None = None,
    ) -> Invoice:
        """Factura bolsa flex con descuento por volumen (Paso 6)."""
        from backend.app.core.pricing import PricingCalculator
        bolsa = PricingCalculator().calculate_bolsa_flex(hours)

        lineas = [{
            "descripcion": (
                f"{hours}h × {float(bolsa.price_per_hour):.2f} EUR/h"
                + (
                    f" (incluye -{int(bolsa.discount_pct * 100)}% "
                    "descuento volumen)"
                    if bolsa.discount_pct > 0 else ""
                )
            ),
            "cantidad": hours,
            "precio_unitario": float(bolsa.price_per_hour),
        }]

        concepto = bolsa.description
        if concepto_detalle:
            concepto = f"{concepto} — {concepto_detalle}"

        # Resolver AAPP si conocido
        from backend.app.models.core import Client
        cliente = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        from backend.app.core.legal import is_aapp as _is_aapp
        aapp = _is_aapp(cliente) if cliente else False
        return await self.generate_invoice(
            db,
            client_id=client_id,
            project_id=project_id,
            contract_id=None,
            concepto=concepto,
            lineas=lineas,
            dias_vencimiento=60 if aapp else 30,
        )

    async def generate_quick_scan_invoice(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        with_future_discount: bool = False,
        project_id: uuid.UUID | None = None,
    ) -> Invoice:
        """Factura quick scan 1.500 EUR con nota descuento futuro C-001.

        Si ``with_future_discount=True``, auto-crea un ``CommercialDiscount``
        type=quick_scan_to_implantacion con expires_at=+30d via
        DiscountService (Paso 7 final 7.8).
        """
        from backend.app.core.pricing import PricingCalculator
        qs = PricingCalculator().calculate_quick_scan(
            discount_if_implantation=with_future_discount,
        )
        concepto = qs["description"]
        lineas = [{
            "descripcion": "Quick scan pre-auditoria ENS (1 semana)",
            "cantidad": 1,
            "precio_unitario": float(qs["price"]),
        }]
        from backend.app.models.core import Client
        cliente = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        from backend.app.core.legal import is_aapp as _is_aapp
        aapp = _is_aapp(cliente) if cliente else False
        invoice = await self.generate_invoice(
            db,
            client_id=client_id,
            project_id=project_id,
            contract_id=None,
            concepto=concepto,
            lineas=lineas,
            dias_vencimiento=60 if aapp else 30,
        )

        # Paso 7 final 7.8 — auto-create commercial discount
        if with_future_discount:
            from backend.app.motors.m13_commercial.discount_service import (
                DiscountService,
            )
            await DiscountService().create_quick_scan_discount(
                db,
                client_id=client_id,
                source_invoice_id=invoice.id,
            )
        return invoice

    async def generate_audit_interna_invoice(
        self,
        db: AsyncSession,
        *,
        client_id: uuid.UUID,
        categoria: str,
        project_id: uuid.UUID | None = None,
    ) -> Invoice:
        """Factura auditoria interna independiente (Basica 2.500 / Media 5.500)."""
        from backend.app.core.pricing import PricingCalculator
        audit = PricingCalculator().calculate_audit_interna(categoria)
        lineas = [{
            "descripcion": audit["description"],
            "cantidad": 1,
            "precio_unitario": float(audit["price"]),
        }]
        from backend.app.models.core import Client
        cliente = (await db.execute(
            select(Client).where(Client.id == client_id)
        )).scalar_one_or_none()
        from backend.app.core.legal import is_aapp as _is_aapp
        aapp = _is_aapp(cliente) if cliente else False
        return await self.generate_invoice(
            db,
            client_id=client_id,
            project_id=project_id,
            contract_id=None,
            concepto=f"Auditoria interna {audit['categoria']} — CCN-STIC 808",
            lineas=lineas,
            dias_vencimiento=60 if aapp else 30,
        )
