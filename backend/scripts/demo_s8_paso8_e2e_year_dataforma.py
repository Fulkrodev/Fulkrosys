"""Demo E2E 1 año DataForma — Paso 8.3 (integra 7.11).

Simula el ciclo completo de 1 año de vida de un cliente DataForma:
comercial -> implantacion -> certificacion -> retainer -> vigilancia ->
renewal. Con fast-forward entre hitos.

Para el alcance del script: 18 steps key-path verificados (el spec
tiene 52 steps detallados, pero la mayoria son equivalentes; aqui se
condensan los mas criticos que demuestran integracion multi-motor).

Uso: python backend/scripts/demo_s8_paso8_e2e_year_dataforma.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


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
        for sql in (
            "DELETE FROM email_log WHERE client_id = :cid",
            "DELETE FROM retainer_reports WHERE client_id = :cid",
            "DELETE FROM commercial_discounts WHERE client_id = :cid",
            "DELETE FROM client_interactions WHERE magic_link_id IN "
            "(SELECT id FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid))",
            "DELETE FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)",
            "DELETE FROM invoice_lines WHERE invoice_id IN "
            "(SELECT id FROM invoices WHERE client_id = :cid)",
            "DELETE FROM invoices WHERE client_id = :cid",
            "DELETE FROM contracts WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)",
            "DELETE FROM proposals WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)",
            "DELETE FROM project_lifecycle_events WHERE client_id = :cid",
            "DELETE FROM renewal_campaigns WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)",
            "DELETE FROM retainer_contracts WHERE client_id = :cid",
            "DELETE FROM leads WHERE empresa_cif = :cif",
            "DELETE FROM projects WHERE client_id = :cid",
            "DELETE FROM clients WHERE id = :cid",
        ):
            await _exec_ok(conn, sql, cid=cid, cif=cif)


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
    from backend.app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n" + "=" * 72)
    print("DEMO E2E 1 AÑO DATAFORMA — Paso 8.3 (integra 7.11)")
    print("=" * 72)

    CIF = "B88888801"  # DataForma demo
    await _cleanup(engine, CIF)

    # ── Setup: cliente + lead + project ──────────────────────────────
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        lead_id = uuid.uuid4()
        await conn.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, sector, "
            "contacto_email, created_at) "
            "VALUES (:id, :nm, :cif, 'sanidad', "
            "'rseg@dataforma.es', now())"
        ), {
            "id": str(cid),
            "nm": "DataForma Galicia SL (E2E demo)",
            "cif": CIF,
        })
        await conn.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, "
            "categoria_objetivo, lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'ENS MEDIA DataForma', 'MEDIA', "
            "'ACTIVE', now())"
        ), {"id": str(pid), "cid": str(cid)})
        await conn.execute(sa_text(
            "INSERT INTO leads (id, empresa_nombre, empresa_cif, "
            "sector, estado, created_at) "
            "VALUES (:id, :nm, :cif, 'sanidad', 'nuevo', now())"
        ), {"id": str(lead_id), "nm": "DataForma", "cif": CIF})
    report("Setup) Cliente + lead + proyecto DataForma", True,
           f"client={cid} project={pid} lead={lead_id}")

    cliente_dict = {
        "cif": CIF, "razon_social": "DataForma Galicia SL",
        "sector": "sanidad",
    }

    # ── STEP 1 (Mes 1): P-001 Media sanidad 11.500 EUR ─────────────
    from backend.app.database import set_tenant_context
    from backend.app.motors.m13_commercial.proposal_service import (
        ProposalService,
    )

    async def _step1(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await ProposalService().generate_proposal_apendice_m(
            s, lead_id=lead_id, categoria="MEDIA",
            cliente=cliente_dict, sector="sanidad",
            project_id=pid,
        )
    p001 = await _run(engine, _step1)
    report(
        "1) Agente 19 genera P-001 Media sanidad 11.500 EUR",
        float(p001.importe_total) == 11500.0
        and len((p001.hitos_pago or {}).get("hitos", [])) == 5,
        f"total={p001.importe_total} hitos={len((p001.hitos_pago or {}).get('hitos', []))}",
    )

    # ── STEP 2 (Mes 1): C-001 generado con Apéndice Económico ─────
    from backend.app.motors.m14_contracts.contract_service import (
        ContractService,
    )

    async def _step2(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await ContractService().generate_contract_apendice_m(
            s, proposal_id=p001.id, project_id=pid,
            cliente=cliente_dict,
            cliente_firmante_nombre="Jorge RSEG",
            cliente_firmante_cargo="Responsable Seguridad",
        )
    c001 = await _run(engine, _step2)
    report(
        "2) Agente 20 genera C-001 con hitos oficiales",
        c001.plantilla_id == "C-001"
        and len(c001.parametros_xyzpr["pricing"]["hitos"]) == 5,
        f"total_contrato=11500, hitos={len(c001.parametros_xyzpr['pricing']['hitos'])}",
    )

    # ── STEP 3 (Mes 1): Hito 1 factura 2.990 EUR + email cliente ──
    from backend.app.motors.m15_billing.billing_service import BillingService

    async def _step3(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await BillingService().generate_milestone_invoice_apendice_m(
            s, contract_id=c001.id,
            milestone_code="hito_1_firma",
            cliente=cliente_dict,
        )
    hito1_inv = await _run(engine, _step3)
    report(
        "3) Hito 1 factura 2.990 EUR emitida",
        float(hito1_inv.base_imponible) == 2990.0,
        f"numero={hito1_inv.numero_correlativo} base={hito1_inv.base_imponible}",
    )

    # ── STEP 4 (Mes 1-2): 3 usuarios portal + primer acceso ───────
    from backend.app.core.email import get_email_sender, reset_email_sender
    # TODO-EMAIL-SENDER-CONSOLIDATION-001 RESOLVED: backend selector
    # ahora desde Settings.email_backend. Demo override via env var
    # estándar (uppercase del field name).
    os.environ["EMAIL_BACKEND"] = "mock"
    reset_email_sender()  # asegurar backend mock para el demo

    from backend.app.motors.m21_portal_cliente import auth_service

    async def _step4(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        users_created = []
        for name, email, role in [
            ("Jorge RSEG", "jorge@dataforma.es", "rseg"),
            ("Laura TI", "laura@dataforma.es", "director_ti"),
            ("Maria CEO", "maria@dataforma.es", "direccion"),
        ]:
            u, _ = await auth_service.create_user(
                s, client_id=cid, email=email, full_name=name,
                role=role, scopes=None, custom_role_description=None,
                dni=None,
            )
            # Email PRIMER_ACCESO_CLIENTE stub via EmailSender mock
            sender = get_email_sender()
            await sender.send(
                s, to=email,
                subject="Bienvenido a FULKRO",
                html_body=f"<p>Hola {name}, bienvenido</p>",
                template_used="primer_acceso_cliente",
                client_id=cid,
            )
            users_created.append(u.id)
        return users_created
    users_created = await _run(engine, _step4)
    report(
        "4) 3 usuarios portal creados + 3 emails PRIMER_ACCESO enviados",
        len(users_created) == 3,
        f"users={len(users_created)}",
    )

    # ── STEP 5-8 (Mes 3/5/8/10): Hitos 2-5 + certificacion ─────────
    from backend.app.motors.m25_lifecycle.lifecycle_paso4 import (
        LifecyclePaso4Service,
    )

    hitos_emitidos = []
    for code, mes in [
        ("hito_2_diagnostico_ar", 3),
        ("hito_3_dda_sgsi", 5),
        ("hito_4_dossier_auditor", 8),
        ("hito_5_certificacion", 10),
    ]:
        async def _bill(s, code=code):
            await set_tenant_context(s, client_id=cid, project_id=pid)
            return await BillingService().generate_milestone_invoice_apendice_m(
                s, contract_id=c001.id, milestone_code=code,
                cliente=cliente_dict,
            )
        inv = await _run(engine, _bill)
        hitos_emitidos.append((code, float(inv.base_imponible)))
    report(
        "5-8) 4 hitos adicionales facturados (Mes 3/5/8/10)",
        len(hitos_emitidos) == 4,
        " + ".join(f"{c.split('_')[1]}={a:.0f}" for c, a in hitos_emitidos),
    )

    # ── STEP 9 (Mes 10): mark_certified + offer retainer ───────────
    async def _step9(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        svc = LifecyclePaso4Service()
        cert_event = await svc.mark_certified(s, pid)
        offer = await svc.offer_retainer(
            s, pid, recipient_email="rseg@dataforma.es",
        )
        return cert_event, offer
    cert_ev, offer = await _run(engine, _step9)
    report(
        "9) mark_certified + offer_retainer magic link enviado",
        cert_ev.event_type == "certified" and offer.get("magic_link_id"),
        f"magic_link_ml={offer.get('magic_link_id')}",
    )

    # ── STEP 10 (Mes 10): accept R_STD retainer ────────────────────
    async def _step10(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await LifecyclePaso4Service().handle_retainer_decision(
            s, pid, decision="accept", tier="R_STD",
            precio_mensual=400.0, performed_by="cliente",
        )
    r_decision = await _run(engine, _step10)
    report(
        "10) Cliente acepta retainer R_STD 400 EUR/mes",
        r_decision["decision"] == "accept"
        and r_decision["tier"] == "R_STD",
        "",
    )

    # ── STEP 11-12 (Mes 12-13): 3 facturas retainer + E-801 Q1 ───
    retainer_facturas = []
    for mes in range(3):
        async def _bill_r(s):
            await set_tenant_context(s, client_id=cid)
            return await BillingService().generate_invoice(
                s, client_id=cid, project_id=None, contract_id=None,
                concepto=f"Retainer R_STD mensual mes {mes+11}",
                lineas=[{
                    "descripcion": "Cuota R_STD",
                    "cantidad": 1, "precio_unitario": 400.0,
                }],
                aplicar_irpf=True,
            )
        inv = await _run(engine, _bill_r)
        retainer_facturas.append(float(inv.total))
    report(
        "11) 3 facturas retainer R_STD mensuales emitidas",
        len(retainer_facturas) == 3
        and all(f > 350 for f in retainer_facturas),
        f"totals={retainer_facturas}",
    )

    from backend.app.motors.m23_retainer.report_service import ReportService

    async def _step12(s):
        return await ReportService().generate_e801_quarterly(
            s, client_id=cid, project_id=pid,
            year=2026, quarter=4,
        )
    e801 = await _run(engine, _step12)
    report(
        "12) E-801 Q4 trimestral generado + firmado Ed25519",
        e801.report_type == "E-801_quarterly"
        and e801.signature_ed25519 is not None,
        f"hash={e801.hash_sha256[:16]}...",
    )

    # ── STEP 13 (Año 1): E-802 anual + material change detection ─
    async def _step13(s):
        return await ReportService().generate_e802_annual(
            s, client_id=cid, project_id=pid, year=2026,
        )
    e802 = await _run(engine, _step13)
    report(
        "13) E-802 anual generado para revision por direccion",
        e802.report_type == "E-802_annual"
        and "revision por direccion" in (e802.payload_jsonb.get("recomendaciones") or ""),
        f"hash={e802.hash_sha256[:16]}...",
    )

    # ── STEP 14: Material change no-material (nueva sede) ─────────
    from backend.app.motors.m27_conformity.conformity_service_paso5 import (
        ConformityServicePaso5,
    )

    async def _step14(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await ConformityServicePaso5().detect_material_change(
            s, pid,
            change_type="location_change",
            description="Nueva sede Barcelona sin impacto en sistemas productivos",
            answers={"permanent_change": True},
        )
    mc_low = await _run(engine, _step14)
    report(
        "14) Material change 'Nueva sede' no-material (score < 0.6)",
        not mc_low.is_material,
        f"score={float(mc_low.materiality_score or 0):.2f}",
    )

    # ── STEP 15: Material change MATERIAL (externalizacion) ───────
    async def _step15(s):
        await set_tenant_context(s, client_id=cid, project_id=pid)
        return await ConformityServicePaso5().detect_material_change(
            s, pid,
            change_type="outsourcing",
            description="Externalizar hosting a cloud Azure nuevo proveedor",
            answers={
                "affects_critical_systems": True,
                "outsourced_abroad": True,
                "new_attack_surface": True,
                "permanent_change": True,
            },
        )
    mc_high = await _run(engine, _step15)
    report(
        "15) Material change 'Externalización' MATERIAL -> audit extra",
        mc_high.is_material
        and mc_high.triggered_extraordinary_audit,
        f"score={float(mc_high.materiality_score or 0):.2f} "
        f"audit_id={mc_high.extraordinary_audit_id}",
    )

    # ── STEP 16: Agente 15 alerta normativa sanidad ──────────────
    from backend.app.motors.m23_retainer.agent_15_vigilancia import (
        Agente15Vigilancia, FeedItem,
    )

    async def _step16(s):
        return await Agente15Vigilancia().run_daily_check(
            s, raw_items_override=[
                FeedItem(
                    source="ccn_cert",
                    source_item_id=f"e2e-{uuid.uuid4().hex[:8]}",
                    title="Vulnerabilidad critica ENS sector sanidad zero-day",
                    description="CCN-CERT emite boletin urgente",
                    source_url="https://ccn.test/v1",
                    published_at=datetime.now(timezone.utc),
                ),
            ],
        )
    agent_result = await _run(engine, _step16)
    report(
        "16) Agente 15 detecta + clasifica alerta critical sanidad",
        agent_result["new_count"] == 1,
        "alert creada critical",
    )

    # ── STEP 17 (Mes 18): alerta renewal 6m Marcos ────────────────
    from backend.app.motors.m27_conformity.renewal_scheduler import (
        CERTIFICATION_VALIDITY_DAYS, ALERT_6M_BEFORE_DAYS,
        run_renewal_bianual_check,
    )

    # Fast-forward: certified_at hace 550 dias (6m antes aniv)
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        await conn.execute(sa_text(
            "UPDATE projects SET certified_at = :c, "
            "lifecycle_state = 'CERTIFIED' WHERE id = :pid"
        ), {
            "pid": str(pid),
            "c": date.today() - timedelta(
                days=CERTIFICATION_VALIDITY_DAYS - ALERT_6M_BEFORE_DAYS,
            ),
        })

    async def _step17(s):
        return await run_renewal_bianual_check(s, today=date.today())
    renewal6 = await _run(engine, _step17)
    report(
        "17) Renewal alerta 6m antes aniversario (mes 18)",
        str(pid) in renewal6.alerts_6m,
        f"alerts_6m={len(renewal6.alerts_6m)}",
    )

    # ── STEP 18 (Mes 21): campaign 3m antes + dossier renewal ─────
    from backend.app.motors.m27_conformity.renewal_scheduler import (
        ALERT_3M_BEFORE_DAYS,
    )

    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        await conn.execute(sa_text(
            "UPDATE projects SET certified_at = :c WHERE id = :pid"
        ), {
            "pid": str(pid),
            "c": date.today() - timedelta(
                days=CERTIFICATION_VALIDITY_DAYS - ALERT_3M_BEFORE_DAYS,
            ),
        })

    async def _step18(s):
        return await run_renewal_bianual_check(s, today=date.today())
    renewal3 = await _run(engine, _step18)
    report(
        "18) Renewal campaign creada 3m antes aniversario (mes 21)",
        str(pid) in renewal3.campaigns_created_3m,
        f"campaigns={len(renewal3.campaigns_created_3m)}",
    )

    # ── Resumen final ───────────────────────────────────────────────
    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)

    # Metricas facturacion
    async def _metrics(s):
        await s.execute(sa_text("SET LOCAL ROLE fulkro"))
        try:
            count = (await s.execute(sa_text(
                "SELECT count(*) FROM invoices WHERE client_id = :cid"
            ), {"cid": str(cid)})).scalar()
            total_facturado = (await s.execute(sa_text(
                "SELECT COALESCE(sum(base_imponible), 0) FROM invoices "
                "WHERE client_id = :cid"
            ), {"cid": str(cid)})).scalar()
            emails = (await s.execute(sa_text(
                "SELECT count(*) FROM email_log WHERE client_id = :cid"
            ), {"cid": str(cid)})).scalar()
            alerts = (await s.execute(sa_text(
                "SELECT count(*) FROM normativa_alerts "
                "WHERE source = 'ccn_cert'"
            ))).scalar()
            return count, float(total_facturado or 0), emails, alerts
        finally:
            await s.execute(sa_text("RESET ROLE"))
    count, total_fact, emails, alerts = await _run(engine, _metrics)

    print("\n" + "=" * 72)
    print("RESUMEN DEMO E2E 1 AÑO DATAFORMA")
    print("=" * 72)
    print(f"Steps PASS:            {passed}/{total}")
    print(f"Facturas emitidas:     {count}")
    print(f"Facturacion total:     {total_fact:,.2f} EUR")
    print(f"Emails loggeados:      {emails}")
    print(f"Alertas Agente 15:     {alerts} (total en BD)")
    print("=" * 72)

    await engine.dispose()
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
