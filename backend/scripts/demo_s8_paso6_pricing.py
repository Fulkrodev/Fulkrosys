"""V-CHECK Sesion 8 Paso 6 — Pricing final M13/M14/M15.

4 casos:
  CASO 1: DataForma Galicia SL (PYME privada sanidad) MEDIA -> 11.500 EUR + 5 hitos.
  CASO 2: Ayuntamiento Test (AAPP BASICA urgente) -> 5.070 EUR + LCSP 60d + 3 hitos.
  CASO 3: Bolsa flex 100h a cliente privado -> 6.375 EUR (-15%).
  CASO 4: Quick scan -> C-001 con descuento futuro aplicado.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.core.legal import is_aapp
from backend.app.core.pricing import PricingCalculator
from backend.app.database import set_tenant_context
from backend.app.models.commercial import Contract, Invoice, Proposal


RESULTS: list[tuple[str, bool, str]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       {detail}")
    RESULTS.append((label, ok, detail))


async def _exec_ok(conn, sql: str, **params):
    sp = await conn.begin_nested()
    try:
        await conn.execute(sa_text(sql), params)
        await sp.commit()
    except Exception:
        await sp.rollback()


async def _cleanup(engine, cif: str):
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT id FROM clients WHERE cif = :cif"
        ), {"cif": cif})
        row = r.first()
        if not row:
            return
        cid = str(row[0])
        # Delete invoices + lines
        await _exec_ok(conn,
            "DELETE FROM invoice_lines WHERE invoice_id IN "
            "(SELECT id FROM invoices WHERE client_id = :cid)",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM invoices WHERE client_id = :cid", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM contracts WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM proposals WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM leads WHERE empresa_cif = :cif", cif=cif)
        await _exec_ok(conn,
            "DELETE FROM projects WHERE client_id = :cid", cid=cid)
        await _exec_ok(conn,
            "DELETE FROM clients WHERE id = :cid", cid=cid)


async def _setup(engine, cif: str, nombre: str, sector: str):
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        lead_id = uuid.uuid4()
        await conn.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, sector, created_at) "
            "VALUES (:id, :nm, :cif, :s, now())"
        ), {"id": str(cid), "nm": nombre, "cif": cif, "s": sector})
        await conn.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
            "created_at) VALUES (:id, :cid, 'ENS Proyecto', 'MEDIA', now())"
        ), {"id": str(pid), "cid": str(cid)})
        await conn.execute(sa_text(
            "INSERT INTO leads (id, empresa_nombre, empresa_cif, sector, "
            "estado, created_at) "
            "VALUES (:id, :nm, :cif, :s, 'nuevo', now())"
        ), {"id": str(lead_id), "nm": nombre, "cif": cif, "s": sector})
        return cid, pid, lead_id


async def _run(engine, fn):
    async with engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            r = await fn(s)
            await trans.commit()
            return r
        finally:
            await s.close()


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n" + "=" * 70)
    print("V-CHECK SESION 8 PASO 6 — Pricing final M13/M14/M15")
    print("=" * 70)

    from backend.app.motors.m13_commercial.proposal_service import ProposalService
    from backend.app.motors.m14_contracts.contract_service import ContractService
    from backend.app.motors.m15_billing.billing_service import BillingService

    prop_svc = ProposalService()
    contract_svc = ContractService()
    billing_svc = BillingService()

    DATAFORMA_CIF = "B60000006"
    AYTO_CIF = "P60000006"
    BOLSA_CIF = "B60000007"
    QUICK_CIF = "B60000008"

    try:
        # ── CASO 1: DataForma Media sanidad ──────────────────────────
        for c in (DATAFORMA_CIF, AYTO_CIF, BOLSA_CIF, QUICK_CIF):
            await _cleanup(engine, c)

        cid1, pid1, lead1 = await _setup(
            engine, DATAFORMA_CIF, "DataForma Galicia SL (P6)", "sanidad",
        )
        cliente1 = {"cif": DATAFORMA_CIF, "razon_social": "DataForma Galicia SL", "sector": "sanidad"}

        async def _caso1(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            p = await prop_svc.generate_proposal_apendice_m(
                s, lead_id=lead1, categoria="MEDIA", cliente=cliente1,
                sector="sanidad", project_id=pid1,
            )
            c = await contract_svc.generate_contract_apendice_m(
                s, proposal_id=p.id, project_id=pid1, cliente=cliente1,
                cliente_firmante_nombre="RSEG DataForma",
                cliente_firmante_cargo="Responsable Seguridad",
            )
            inv = await billing_svc.generate_milestone_invoice_apendice_m(
                s, contract_id=c.id, milestone_code="hito_1_firma",
                cliente=cliente1,
            )
            return p, c, inv
        p1, c1, i1 = await _run(engine, _caso1)

        ok = (
            float(p1.importe_total) == 11500.0
            and len((p1.hitos_pago or {}).get("hitos", [])) == 5
            and float(i1.base_imponible) == 2990.0  # 26% × 11500
            and (i1.fecha_vencimiento - i1.fecha_emision).days == 30
        )
        report(
            "CASO 1 — DataForma Media sanidad → 11.500 EUR + 5 hitos + hito_1 2.990 EUR",
            ok,
            f"proposal_total={p1.importe_total}, hitos={len((p1.hitos_pago or {}).get('hitos', []))}, "
            f"hito_1_invoice={float(i1.base_imponible)}, plazo_pago={(i1.fecha_vencimiento - i1.fecha_emision).days}d",
        )

        # ── CASO 2: Ayuntamiento BASICA urgente ──────────────────────
        cid2, pid2, lead2 = await _setup(
            engine, AYTO_CIF, "Ayuntamiento Test (P6)", "administracion_publica",
        )
        cliente2 = {
            "cif": AYTO_CIF, "razon_social": "Ayuntamiento Test",
            "sector": "administracion_publica",
        }
        assert is_aapp(cliente2), "Ayuntamiento debe detectarse AAPP"

        async def _caso2(s):
            await set_tenant_context(s, client_id=cid2, project_id=pid2)
            p = await prop_svc.generate_proposal_apendice_m(
                s, lead_id=lead2, categoria="BASICA", cliente=cliente2,
                dias_hasta_plazo=28, project_id=pid2,
            )
            c = await contract_svc.generate_contract_apendice_m(
                s, proposal_id=p.id, project_id=pid2, cliente=cliente2,
                cliente_firmante_nombre="Alcalde Test",
                cliente_firmante_cargo="Alcalde",
            )
            inv = await billing_svc.generate_milestone_invoice_apendice_m(
                s, contract_id=c.id, milestone_code="hito_1_firma",
                cliente=cliente2,
            )
            return p, c, inv
        p2, c2, i2 = await _run(engine, _caso2)

        urgent = (p2.importe_desglose or {}).get("urgent", False)
        aapp_flag = (c2.parametros_xyzpr or {}).get("is_aapp", False)
        plazo = (i2.fecha_vencimiento - i2.fecha_emision).days
        ok2 = (
            float(p2.importe_total) == 5070.0
            and urgent
            and aapp_flag
            and plazo == 60
            and "LCSP" in (i2.concepto or "")
        )
        report(
            "CASO 2 — Ayto AAPP BASICA urgente → 5.070 EUR + LCSP + plazo 60d",
            ok2,
            f"total={p2.importe_total}, urgent={urgent}, aapp={aapp_flag}, "
            f"plazo_pago={plazo}d, concepto={i2.concepto}",
        )

        # ── CASO 3: Bolsa flex 100h ──────────────────────────────────
        cid3, pid3, _ = await _setup(
            engine, BOLSA_CIF, "Consultoria Test SL (bolsa)", "tecnologia",
        )

        async def _caso3(s):
            await set_tenant_context(s, client_id=cid3, project_id=pid3)
            return await billing_svc.generate_bolsa_flex_invoice(
                s, client_id=cid3, hours=100,
            )
        i3 = await _run(engine, _caso3)
        ok3 = (
            float(i3.base_imponible) == 6375.0
            and "15% descuento" in (i3.concepto or "")
        )
        report(
            "CASO 3 — Bolsa flex 100h → 6.375 EUR (-15%)",
            ok3,
            f"base={float(i3.base_imponible)}, total={float(i3.total)}, "
            f"concepto={i3.concepto}",
        )

        # ── CASO 4: Quick scan → C-001 con descuento ─────────────────
        cid4, pid4, lead4 = await _setup(
            engine, QUICK_CIF, "Consultoria Quick Test SL", "tecnologia",
        )

        async def _caso4_part1(s):
            await set_tenant_context(s, client_id=cid4, project_id=pid4)
            inv_qs = await billing_svc.generate_quick_scan_invoice(
                s, client_id=cid4, with_future_discount=True, project_id=pid4,
            )
            return inv_qs
        i4_qs = await _run(engine, _caso4_part1)

        # Cliente firma C-001 Basica 3900 — aplicar descuento manual
        # (logica integrada sera en Paso 7 Email workflows).
        from decimal import Decimal
        calc = PricingCalculator()
        basica = calc.calculate_implantacion("BASICA")
        descuento_qs = Decimal(str(i4_qs.base_imponible))  # 1500
        contrato_neto = float(basica.total - descuento_qs)  # 2400
        hitos_recalc = calc.get_milestones("BASICA", basica.total - descuento_qs)
        ok4 = (
            float(i4_qs.base_imponible) == 1500.0
            and "Descontable" in (i4_qs.concepto or "")
            and contrato_neto == 2400.0
            and sum(float(h.amount) for h in hitos_recalc.milestones) == 2400.0
        )
        report(
            "CASO 4 — Quick scan 1.500 EUR → C-001 Basica neto 2.400 EUR (-1.500 descuento)",
            ok4,
            f"quick_scan={float(i4_qs.base_imponible)}, contrato_neto={contrato_neto}, "
            f"hitos=[{float(hitos_recalc.milestones[0].amount):.0f}, "
            f"{float(hitos_recalc.milestones[1].amount):.0f}, "
            f"{float(hitos_recalc.milestones[2].amount):.0f}]",
        )

    finally:
        await engine.dispose()

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 70)
    print(f"RESUMEN: {passed}/{total} PASS")
    print("=" * 70)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
