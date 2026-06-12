"""SIMULACIÓN HIPERREALISTA · Cliente ENS ALTA (ruta certificación ENAC + continuidad).

Recorre el ciclo ALTA, ejercitando el código real. Incluye lo propio de ALTA: las
73 medidas del Anexo II + refuerzos, y la CONTINUIDAD (op.cont.* · E-400 BIA /
E-401 Estrategias / E-403 DRP) con RTO/RPO reales. EXCEPTO pentest OSCP. Vuelca a
out/sim_alta/ + asegura invariantes.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text

from backend.tests.conftest import _admin_setup
from backend.tests.integration.test_sim_basica import _docx_text_from_path, _seed

_OUT = Path("/home/usuario/fulkro/out/sim_alta")


def _dump(name: str, text: str) -> None:
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / name).write_text(text, encoding="utf-8")


@pytest.mark.asyncio
async def test_sim_alta_full_lifecycle(db, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "1")
    report: list[str] = ["# SIMULACIÓN ALTA · Ayuntamiento de Villaverde del Río (ENAC + continuidad)\n"]

    def log(m: str) -> None:
        report.append(m)

    cid, pid, sid = await _seed(db, cat="ALTA")

    from backend.app.motors.m01_categorization.service import CategorizationService
    res = await CategorizationService(db).compute_for_system(sid)
    categoria = res.category if hasattr(res, "category") else res.categoria
    assert str(categoria).upper().endswith("ALTA"), categoria
    log(f"## 1-2. Alta + categorización → **{categoria}**\n")
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET fecha_kickoff=current_date - interval '120 days', "
            "fecha_objetivo_certificacion=current_date + interval '30 days' WHERE id=:p"),
            {"p": str(pid)})
        await db.execute(sa_text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, aprobado_por, "
            "fecha_acta, created_at) VALUES (gen_random_uuid(), :s, 'ALTA', "
            "'Comité de Seguridad', current_date, now())"), {"s": str(sid)})

    # DdA ALTA (73) + implantada
    from backend.app.motors.m03_dda.enums import CategoriaSistema
    from backend.app.motors.m03_dda.service import DdaService
    await DdaService(db).generate_dda(pid, CategoriaSistema("ALTA"),
                                      responsable="Beatriz Seguridad López", enforce_gates=False)
    apl = (await db.execute(sa_text(
        "SELECT count(*) FILTER (WHERE aplicabilidad <> 'no_aplica'), "
        "count(*) FILTER (WHERE aplicabilidad = 'aplica_con_refuerzos') "
        "FROM dda_entries WHERE project_id=:p AND deleted_at IS NULL"), {"p": str(pid)})).first()
    aplicables, refuerzos = int(apl[0]), int(apl[1])
    log(f"## 3. DdA ALTA · {aplicables} aplicables · {refuerzos} con refuerzos (+R).\n")
    assert aplicables >= 70, f"ALTA aplicables={aplicables}"
    assert refuerzos > 0, "ALTA debe tener medidas con refuerzos (+R)"
    await db.execute(sa_text(
        "UPDATE dda_entries SET estado_implementacion='implantada', "
        "aprobado_por='Beatriz Seguridad López', fecha_aprobacion=current_date "
        "WHERE project_id=:p AND aplicabilidad <> 'no_aplica'"), {"p": str(pid)})
    await db.flush()

    # E-040
    from backend.app.motors.m06_document_factory.informe_final_generator import (
        build_informe_final_context,
    )
    from backend.app.motors.m06_document_factory.service import DocumentFactoryService
    svc = DocumentFactoryService(db)
    await svc.load_template_metadata_from_catalog()
    e040_ctx = await build_informe_final_context(db, pid)
    e040 = await svc.generate_document(project_id=pid, template_codigo="E-040",
                                       context=e040_ctx, generate_pdf=False, sign=False,
                                       generated_by="sim")
    _dump("E-040_informe_final.txt", _docx_text_from_path(e040["docx_path"]))
    log(f"## 4. E-040 · cumplimiento global {e040_ctx['informe']['cumplimiento_global']}%\n")

    # 5. CONTINUIDAD ALTA (op.cont.*): BIA + Estrategias + DRP con RTO/RPO reales
    from backend.app.motors.m19_risk.bia_service import create_bia_entry
    await create_bia_entry(db, pid, "Tramitación electrónica de expedientes",
                           rto_hours=4, rpo_hours=1, daily_impact_eur=Decimal("40000"))
    await create_bia_entry(db, pid, "Registro de entrada/salida", rto_hours=24, rpo_hours=4)
    from backend.app.motors.m06_document_factory.continuity_generator import (
        build_bia_context, build_continuity_context, build_drp_context,
    )
    e400 = await svc.generate_document(project_id=pid, template_codigo="E-400",
                                       context=await build_bia_context(db, pid),
                                       generate_pdf=False, sign=False, generated_by="sim")
    e401 = await svc.generate_document(project_id=pid, template_codigo="E-401",
                                       context=await build_continuity_context(db, pid),
                                       generate_pdf=False, sign=False, generated_by="sim")
    e403 = await svc.generate_document(project_id=pid, template_codigo="E-403",
                                       context=await build_drp_context(db, pid),
                                       generate_pdf=False, sign=False, generated_by="sim")
    e400_text = _docx_text_from_path(e400["docx_path"])
    e401_text = _docx_text_from_path(e401["docx_path"])
    e403_text = _docx_text_from_path(e403["docx_path"])
    _dump("E-400_bia.txt", e400_text)
    _dump("E-401_estrategias.txt", e401_text)
    _dump("E-403_drp.txt", e403_text)
    log("## 5. Continuidad ALTA (op.cont.*)\n"
        f"E-400 BIA · proceso crítico + RTO 4 horas: {'Tramitación electrónica de expedientes' in e400_text and '4 horas' in e400_text}\n"
        f"E-401 Estrategias · estrategia por RTO: {'Redundancia activa' in e401_text}\n"
        f"E-403 DRP · sitio primario sede física: {'CPD' in e403_text or 'Casa Consistorial' in e403_text or 'Sede' in e403_text}\n")
    assert "Tramitación electrónica de expedientes" in e400_text
    assert "4 horas" in e400_text
    assert "{{" not in e400_text and "{{" not in e401_text and "{{" not in e403_text
    assert "Redundancia activa" in e401_text  # estrategia para RTO<=4

    # 6. Conformidad ALTA: distintivo 809 (acompaña, no sustituye al certificado ENAC)
    from backend.app.models.conformity_lifecycle import ConformityRouteRow
    db.add(ConformityRouteRow(project_id=pid, route_type="certificacion_enac", status="CONFORMANT"))
    await db.flush()
    from backend.app.motors.m27_conformity.distintivo_persistence import (
        attach_distintivo_on_registered, read_distintivo_bytes,
    )
    dist = await attach_distintivo_on_registered(db, pid, generated_by="sim")
    assert dist["route_state"] == "REGISTERED"
    import io
    from docx import Document as _Docx
    dist_bytes, _ = await read_distintivo_bytes(db, pid)
    dist_full = "\n".join(p.text for p in _Docx(io.BytesIO(dist_bytes)).paragraphs)
    _dump("E-049_distintivo.txt", dist_full)
    assert "no sustituye" in dist_full.lower()
    log("## 6. Conformidad ALTA · distintivo CCN-STIC 809 (no sustituye certificado ENAC)\n")

    _dump("REPORT.md", "\n".join(report))
