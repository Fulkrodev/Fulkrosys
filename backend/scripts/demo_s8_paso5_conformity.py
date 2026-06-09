"""V-CHECK Sesion 8 Paso 5 — Demo M27 Conformity Lifecycle sobre DataForma.

Flujo:
  a) initialize_conformity_route DataForma MEDIA + overlay hints Azure
  b) apply_pce_overlay cloud_azure_es (medidas extra al DdA)
  c) generate_role_topology DataForma (~6 personas pyme_media)
  d) material_change no-material (score < 0.6)
  e) material_change material (score >= 0.6 -> extraordinary_audit)
  f) Adapter PILAR -> .mgr XML desde M2
  g) Adapter INES -> snapshot anual XLSX
  h) CLARA ingester -> evidencias M7
  i) trigger_renewal_campaign (+21m)
  j) TEST-PCE-01 Cloud Azure overlay aplicado con medidas esperadas
  k) TEST-PCE-02 µCeENS ayuntamiento overlay en segundo cliente sintetico
"""
from __future__ import annotations

import asyncio
import io
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openpyxl import load_workbook
from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.models.conformity_lifecycle import (
    ConformityRouteRow,
    MaterialChangeRow,
    PceOverlayRow,
)
from backend.app.motors.m27_conformity.adapters.clara_ingester import (
    ingest_clara_output,
)
from backend.app.motors.m27_conformity.adapters.ines_adapter import (
    generate_ines_snapshot,
)
from backend.app.motors.m27_conformity.adapters.pilar_adapter import (
    generate_mgr_file,
)
from backend.app.motors.m27_conformity.conformity_service_paso5 import (
    ConformityServicePaso5,
)


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
        await _exec_ok(conn,
            "DELETE FROM client_interactions WHERE magic_link_id IN "
            "(SELECT id FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid))",
            cid=cid)
        await _exec_ok(conn,
            "DELETE FROM magic_links WHERE project_id IN "
            "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        for tbl in (
            "project_archived_backups", "project_lifecycle_events",
            "pce_overlays", "extraordinary_audits", "material_changes",
            "recategorizations", "role_exception_memos", "role_topologies",
            "renewal_campaigns", "basic_declarations",
            "conformity_submissions", "conformity_routes",
            "effort_estimates", "stakeholders_graph_snapshots",
        ):
            await _exec_ok(conn,
                f"DELETE FROM {tbl} WHERE project_id IN "
                "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        for tbl in (
            "findings", "evidence", "documents",
            "information_types", "services", "categorizations", "systems",
        ):
            await _exec_ok(conn,
                f"DELETE FROM {tbl} WHERE project_id IN "
                "(SELECT id FROM projects WHERE client_id = :cid) "
                if tbl != "information_types" and tbl != "services" and tbl != "categorizations"
                else f"DELETE FROM {tbl} WHERE system_id IN "
                "(SELECT id FROM systems WHERE project_id IN "
                "(SELECT id FROM projects WHERE client_id = :cid))",
                cid=cid)
        await _exec_ok(conn, "DELETE FROM systems WHERE project_id IN "
                       "(SELECT id FROM projects WHERE client_id = :cid)", cid=cid)
        await _exec_ok(conn, "DELETE FROM invoices WHERE client_id = :cid", cid=cid)
        await _exec_ok(conn, "DELETE FROM retainer_contracts WHERE client_id = :cid",
                       cid=cid)
        await _exec_ok(conn, "DELETE FROM exploratory_meetings WHERE client_id = :cid",
                       cid=cid)
        await _exec_ok(conn, "DELETE FROM projects WHERE client_id = :cid", cid=cid)
        await _exec_ok(conn, "DELETE FROM clients WHERE id = :cid", cid=cid)


async def _create_project(engine, cif: str, name: str, categoria: str):
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        cid = uuid.uuid4()
        pid = uuid.uuid4()
        sid = uuid.uuid4()
        await conn.execute(sa_text(
            "INSERT INTO clients (id, nombre, cif, sector, "
            "numero_empleados, created_at) "
            "VALUES (:id, :nm, :cif, 'Tecnologia', 6, now())"
        ), {"id": str(cid), "nm": name, "cif": cif})
        await conn.execute(sa_text(
            "INSERT INTO projects (id, client_id, nombre, categoria_objetivo, "
            "lifecycle_state, created_at) "
            "VALUES (:id, :cid, 'ENS proyecto', :cat, 'ACTIVE', now())"
        ), {"id": str(pid), "cid": str(cid), "cat": categoria})
        await conn.execute(sa_text(
            "INSERT INTO systems (id, project_id, nombre, created_at) "
            "VALUES (:sid, :pid, 'ERP Principal', now())"
        ), {"sid": str(sid), "pid": str(pid)})
        await conn.execute(sa_text(
            "INSERT INTO information_types (id, system_id, nombre, "
            "valoracion_d, valoracion_i, valoracion_c, valoracion_a, "
            "valoracion_t, created_at) "
            "VALUES (gen_random_uuid(), :sid, 'Datos clientes', "
            "'MEDIO', 'MEDIO', 'MEDIO', 'MEDIO', 'BAJO', now())"
        ), {"sid": str(sid)})
        return cid, pid


async def _run(engine, fn):
    async with engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            result = await fn(s)
            await trans.commit()
            return result
        finally:
            await s.close()


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)

    print("\n" + "=" * 70)
    print("V-CHECK SESION 8 PASO 5 — M27 Conformity Lifecycle")
    print("=" * 70)

    DATAFORMA_CIF = "B99999999"
    AYTO_CIF = "P99999999"

    try:
        await _cleanup(engine, DATAFORMA_CIF)
        await _cleanup(engine, AYTO_CIF)

        # ── Cliente 1: DataForma (MEDIA, cloud azure) ─────────────────
        cid1, pid1 = await _create_project(
            engine, DATAFORMA_CIF, "DataForma Test (M27)", "MEDIA",
        )
        report("setup) DataForma cliente + proyecto MEDIA creados", True,
               f"client={cid1} project={pid1}")

        svc = ConformityServicePaso5()

        # a) initialize route
        async def _init_route(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            r = await svc.initialize_conformity_route(
                s, pid1, detected_overlay_hints=["Azure AD", "Microsoft 365"],
            )
            return r
        route = await _run(engine, _init_route)
        ok = (
            route.route_type == "certificacion_enac"
            and "cloud_azure_es" in (route.metadata_jsonb or {}).get(
                "suggested_overlays", [])
        )
        report("a) initialize_conformity_route MEDIA + overlay hints",
               ok, f"route_type={route.route_type}")

        # b) apply overlay cloud_azure_es
        async def _apply_ov(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await svc.apply_pce_overlay(
                s, pid1, overlay_type="cloud_azure_es",
            )
        ov = await _run(engine, _apply_ov)
        n_measures = (ov.extra_measures_jsonb or {}).get("count", 0)
        report(
            "b) apply_pce_overlay cloud_azure_es",
            n_measures > 0, f"extra_measures_count={n_measures}",
        )

        # c) role_topology
        async def _role(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await svc.generate_role_topology(
                s, pid1, total_persons=6,
                roles_assigned={
                    "rseg": "Marcos (externo)",
                    "responsable_sistema": "Alice",
                    "responsable_informacion": "Bob",
                },
                sector="Tecnologia",
                approved_by="marcos",
            )
        topo = await _run(engine, _role)
        report(
            "c) role_topology DataForma 6 personas",
            topo.pattern == "pyme_basica" and topo.exceptions_count == 0,
            f"pattern={topo.pattern} exceptions={topo.exceptions_count}",
        )

        # d) material_change no-material
        async def _mc_low(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await svc.detect_material_change(
                s, pid1, change_type="location_change",
                description="Nueva sede Barcelona sin impacto en sistemas",
                answers={"permanent_change": True},
            )
        mc_low = await _run(engine, _mc_low)
        report(
            "d) material_change no-material (score < 0.6)",
            not mc_low.is_material,
            f"score={float(mc_low.materiality_score or 0)} material={mc_low.is_material}",
        )

        # e) material_change material
        async def _mc_high(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await svc.detect_material_change(
                s, pid1, change_type="outsourcing",
                description="Externalizar hosting a nuevo proveedor cloud externo",
                answers={
                    "affects_critical_systems": True,
                    "outsourced_abroad": True,
                    "new_attack_surface": True,
                    "permanent_change": True,
                },
            )
        mc_high = await _run(engine, _mc_high)
        report(
            "e) material_change material -> extraordinary_audit",
            mc_high.is_material and mc_high.triggered_extraordinary_audit,
            f"score={float(mc_high.materiality_score or 0)} "
            f"audit_id={mc_high.extraordinary_audit_id}",
        )

        # f) PILAR adapter
        async def _pilar(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await generate_mgr_file(s, pid1)
        pilar = await _run(engine, _pilar)
        ok_pilar = (
            pilar["artifact_content"].startswith(b"<?xml")
            and b"PilarImport" in pilar["artifact_content"]
            and len(pilar["artifact_hash"]) == 64
        )
        report(
            "f) Adapter PILAR -> .mgr XML generado",
            ok_pilar,
            f"bytes={len(pilar['artifact_content'])} "
            f"hash={pilar['artifact_hash'][:16]}...",
        )

        # g) INES adapter
        async def _ines(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await generate_ines_snapshot(s, pid1, year=2026)
        ines = await _run(engine, _ines)
        wb = load_workbook(io.BytesIO(ines["artifact_content"]))
        ok_ines = len(wb.sheetnames) == 5
        report(
            "g) Adapter INES -> XLSX snapshot anual 2026",
            ok_ines,
            f"sheets={wb.sheetnames} bytes={len(ines['artifact_content'])}",
        )

        # h) CLARA ingester
        clara_xml = b"""<?xml version="1.0"?>
        <ClaraReport>
          <check id="CLARA-W-FW-01" status="FAIL">Windows FW disabled</check>
          <check id="CLARA-L-SSH-01" status="PASS">SSH hardening OK</check>
          <check id="CLARA-L-AUDIT-01" status="PASS">auditd configured</check>
        </ClaraReport>"""

        async def _clara(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await ingest_clara_output(s, pid1, content=clara_xml)
        clara_result = await _run(engine, _clara)
        ok_clara = (
            clara_result["parsed_count"] == 3
            and clara_result["evidences_created_count"] >= 3
        )
        report(
            "h) CLARA ingester -> evidencias M7 creadas",
            ok_clara,
            f"parsed={clara_result['parsed_count']} "
            f"evidences={clara_result['evidences_created_count']} "
            f"measures={len(clara_result['ens_measures_touched'])}",
        )

        # i) renewal campaign
        async def _renewal(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            return await svc.trigger_renewal_campaign(
                s, pid1, auto_triggered=True,
            )
        camp = await _run(engine, _renewal)
        report(
            "i) trigger_renewal_campaign bianual (+21m)",
            camp.auto_triggered and camp.scheduled_for > datetime.now(timezone.utc),
            f"type={camp.campaign_type} scheduled={camp.scheduled_for}",
        )

        # j) TEST-PCE-01 summary
        async def _pce01(s):
            await set_tenant_context(s, client_id=cid1, project_id=pid1)
            res = await s.execute(
                select(PceOverlayRow).where(
                    PceOverlayRow.project_id == pid1,
                    PceOverlayRow.overlay_type == "cloud_azure_es",
                )
            )
            return res.scalar_one_or_none()
        pce01 = await _run(engine, _pce01)
        pce01_measures = (pce01.extra_measures_jsonb or {}).get("measures", [])
        ok_pce01 = any("pce-az" in (m.get("code") or "") for m in pce01_measures)
        report(
            "j) TEST-PCE-01 Cloud Azure overlay aplicado",
            ok_pce01 and len(pce01_measures) >= 8,
            f"overlay={pce01.overlay_type} measures={len(pce01_measures)}",
        )

        # OBSOLETO post sub-lote 1.B.8.A (AMEND-016 v2): demo Cliente 2
        # Ayuntamiento BASICA con overlay uceens_ayuntamiento eliminado.
        # Scope-out target empresa privada licitando AAPP (LECCION-OPS-032).
        # CLIENTE 2 (uceens) demo bloque removido junto con catalog YAMLs +
        # CHECK constraint enum reduction (migration m27_uceens_dropout_1b8a_001).

    finally:
        await engine.dispose()

    total = len(RESULTS)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = total - passed
    print("\n" + "=" * 70)
    print(f"RESUMEN: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 70)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
