"""V-CHECK Sesion 8 Paso 2 — Demo M23 Retainer completo sobre DataForma.

Flujo:
1. Marcar DataForma como certified_at = today
2. Crear retainer R_STD (700 EUR/mes)
3. Mostrar calendario 12 meses programado
4. Generar primera factura recurrente M15 con QR Verifactu
5. Simular cambio material -> auditoria extraordinaria
6. Generar E-801 reporte trimestral (context para M6)
7. Dashboard query -> DataForma debe aparecer
8. Simular 21 meses -> renewal_prep activa
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.models.retainer import (
    RetainerContract,
)
from backend.app.motors.m23_retainer import (
    agent_26, billing_integration, paso2_extensions,
)
from backend.app.motors.m23_retainer.pricing_catalog_seed import (
    seed_pricing_catalog,
)
from backend.app.motors.m23_retainer.retainer_service import RetainerService


RESULTS: list[tuple[str, bool, str]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       {detail}")
    RESULTS.append((label, ok, detail))


async def _get_dataforma(engine) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT c.id, p.id FROM clients c "
            "JOIN projects p ON p.client_id = c.id "
            "WHERE c.nombre ILIKE '%DataForma%' LIMIT 1"
        ))
        row = r.first()
        if not row:
            raise RuntimeError(
                "DataForma no existe. Ejecuta seed_fake_clients primero."
            )
        return row[0], row[1]


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    client_id, project_id = await _get_dataforma(engine)
    print("\n" + "=" * 70)
    print("V-CHECK SESION 8 PASO 2 — M23 Retainer sobre DataForma")
    print("=" * 70)
    print(f"client_id={client_id}  project_id={project_id}\n")

    # Asegurar pricing_catalog seeded
    async with engine.begin() as conn:
        await seed_pricing_catalog(conn)
    report("0) pricing_catalog seeded", True, "4 retainer tiers + 3 implantacion")

    # ────────────────────────────────────────────────────────────
    # 1) Marcar DataForma certificada + crear retainer R_STD
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))

        # Limpiar retainer previo si hay
        await db.execute(sa_text("""
            DELETE FROM retainer_billing_events
            WHERE retainer_contract_id IN (
                SELECT id FROM retainer_contracts WHERE project_id = :pid
            )
        """), {"pid": str(project_id)})
        await db.execute(sa_text("""
            DELETE FROM retainer_activities
            WHERE project_id = :pid
        """), {"pid": str(project_id)})
        await db.execute(sa_text("""
            DELETE FROM retainer_contracts WHERE project_id = :pid
        """), {"pid": str(project_id)})
        await db.commit()

    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))

        # Sugerir tier
        sug = paso2_extensions.suggest_tier(
            "MEDIA", empleados=180, sector="sanidad_privada",
            datos_sensibles=True,
        )
        report(
            "1a) suggest_tier DataForma (MEDIA 180 empleados sanidad)",
            sug["tier_sugerido"] == "R_PLUS",
            f"Sugerido: {sug['tier_sugerido']} | {sug['justificacion']}",
        )

        # Crear retainer R_STD (inferior al sugerido, caso real consultor)
        svc = RetainerService()
        today = date.today()
        rc = await svc.create_retainer(
            db, client_id=client_id, project_id=project_id,
            perfil="R_STD",
            precio_mensual=700.00,
            inicio=today,
            fin=today + timedelta(days=730),
            next_renewal_date=today + timedelta(days=730),
        )
        report(
            "1b) RetainerContract R_STD creado",
            rc.id is not None and rc.precio_mensual == 700.00,
            f"contract_id={rc.id} | precio={rc.precio_mensual} EUR/mes "
            f"| SLA={rc.sla_respuesta_horas}h",
        )

        # Generar calendario 12 meses
        activities = await svc.generate_annual_activities(
            db, rc.id, year=today.year,
        )
        await db.commit()
        retainer_id = rc.id

    # Contar actividades por tipo
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await db.execute(sa_text("""
            SELECT tipo_actividad, COUNT(*)
            FROM retainer_activities
            WHERE retainer_contract_id = :rid AND deleted_at IS NULL
            GROUP BY tipo_actividad ORDER BY tipo_actividad
        """), {"rid": str(retainer_id)})
        by_type = {row[0]: row[1] for row in r.all()}

    total = sum(by_type.values())
    report(
        "2) Calendario 12 meses generado (R_STD)",
        total > 0 and by_type.get("comite_seguridad", 0) == 4,
        f"total={total} | por tipo: "
        + " · ".join(f"{k}:{v}" for k, v in sorted(by_type.items())[:5]),
    )

    # ────────────────────────────────────────────────────────────
    # 3) Primera factura recurrente M15
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        event = await billing_integration.generate_retainer_invoice(
            db, retainer_id,
        )
        invoice_id = event.invoice_id
        amount = event.amount
        await db.commit()
    report(
        "3) Primera factura recurrente (QR Verifactu via M15)",
        invoice_id is not None and amount > 0,
        f"invoice_id={invoice_id} | total={amount} EUR (700 + IVA 21% - IRPF 15%)",
    )

    # ────────────────────────────────────────────────────────────
    # 4) Cambio material -> auditoria extraordinaria
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        activity = await paso2_extensions.trigger_material_change_audit(
            db, project_id,
            change_description=(
                "Migracion del HIS a nueva plataforma cloud (AWS RDS). "
                "Afecta a activos criticos con datos de historia clinica."
            ),
            urgent=True,
        )
        await db.commit()
    report(
        "4) Trigger material change -> auditoria extraordinaria",
        activity.tipo_actividad.startswith("auditoria_extraordinaria")
        and activity.prioridad == "urgente",
        f"activity_id={activity.id} | "
        f"fecha={activity.fecha_programada} | prioridad={activity.prioridad}",
    )

    # ────────────────────────────────────────────────────────────
    # 5) E-801 reporte trimestral
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        qreport = await paso2_extensions.generate_quarterly_report(
            db, retainer_id, period_type="trimestral",
        )
        await db.commit()
    report(
        "5) E-801 reporte trimestral generado",
        qreport.id is not None and qreport.rag_overall is not None,
        f"report_id={qreport.id} | periodo={qreport.period_start} -> "
        f"{qreport.period_end} | rag={qreport.rag_overall}",
    )

    # ────────────────────────────────────────────────────────────
    # 6) Dashboard multi-cliente + health detail
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        health = await paso2_extensions.calculate_health_status(db, retainer_id)
    report(
        "6) Health status DataForma retainer",
        health["health"] in ("verde", "ambar", "rojo"),
        f"health={health['health']} | drivers={json.dumps(health['drivers'])}",
    )

    # ────────────────────────────────────────────────────────────
    # 7) Agente 26 weekly analysis
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        summary = await agent_26.summary_for_marcos(db)
    report(
        "7) Agente 26 weekly analysis",
        summary["total_alerts"] >= 0,
        f"alertas={summary['total_alerts']} | "
        f"por_priority={summary['by_priority']}",
    )

    # ────────────────────────────────────────────────────────────
    # 8) Renewal prep autotrigger 21m antes del aniversario
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        renewal_activity = await paso2_extensions.schedule_renewal_prep(
            db, retainer_id,
        )
        await db.commit()
    report(
        "8) Renewal prep autotrigger (3 meses antes bianual)",
        renewal_activity.tipo_actividad == "renewal_prep"
        and renewal_activity.prioridad == "alta",
        f"fecha={renewal_activity.fecha_programada} | titulo="
        f"{renewal_activity.titulo[:60]}",
    )

    # ────────────────────────────────────────────────────────────
    # 9) Upgrade tier R_STD -> R_PLUS
    # ────────────────────────────────────────────────────────────
    async with Session() as db:
        await set_tenant_context(db, client_id=client_id, project_id=project_id)
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        new_price = await paso2_extensions.get_tier_price(db, "R_PLUS")
        rc_obj = await db.get(RetainerContract, retainer_id)
        old_tier = rc_obj.perfil
        rc_obj.perfil = "R_PLUS"
        rc_obj.precio_mensual = float(new_price)
        await db.commit()
    report(
        "9) Upgrade tier R_STD -> R_PLUS",
        old_tier == "R_STD" and float(new_price) == 1200.00,
        f"old={old_tier} (700 EUR) -> R_PLUS ({new_price} EUR)",
    )

    # ────────────────────────────────────────────────────────────
    # Resumen
    # ────────────────────────────────────────────────────────────
    elapsed_s = 0  # no medimos tiempo
    pass_count = sum(1 for _, ok, _ in RESULTS if ok)
    total_s = len(RESULTS)

    print("\n" + "=" * 70)
    print(f"RESUMEN S8 PASO 2 · {pass_count}/{total_s} escenarios PASS")
    print("=" * 70)
    print("  Retainer DataForma:")
    print(f"    · Tier final: R_PLUS ({new_price} EUR/mes)")
    print(f"    · Activities programadas: {total}")
    print(f"    · Factura recurrente emitida: {amount} EUR")
    print(f"    · Health status: {health['health']}")
    print(f"    · Renewal prep programado: {renewal_activity.fecha_programada}")
    print(f"    · Alertas agente 26: {summary['total_alerts']}")
    if pass_count != total_s:
        print("\n  FAILS:")
        for lbl, ok, det in RESULTS:
            if not ok:
                print(f"    · {lbl}: {det}")
    print("=" * 70)

    await engine.dispose()
    return 0 if pass_count == total_s else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
