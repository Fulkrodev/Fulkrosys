"""N5 · las piezas del CCN dejan de inventarse datos y de dar por bueno un FAIL.

TRES DEFECTOS, TRES ARREGLOS

1. INES · la "inversion en seguridad" se calculaba SUMANDO LAS FACTURAS DEL
   CONSULTOR al cliente (`SELECT SUM(base_imponible) FROM invoices`). Eso son
   los honorarios de Fulkro, no lo que la organizacion invierte en seguridad:
   ni el personal, ni el hardware, ni las licencias, ni la formacion, ni los
   demas proveedores. El INES es el informe del art. 32 que la ORGANIZACION
   rinde; poner ahi la factura del consultor es inventar el dato, y ademas
   inventarlo al alza en favor de quien lo genera.

2. CLARA · el ingestor creaba evidencia `vigente = true` para TODOS los
   controles, incluidos los que vienen en FAIL. Calculaba `status_map` y no lo
   usaba. Un control que falla quedaba como evidencia valida de la medida ENS.

3. LUCIA · no hay integracion. Lo que hay es un reloj de plazos del art. 33
   (`notificado_lucia`, deadlines 24/72h), que es otra cosa. No se promete
   integracion en ningun texto.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import _admin_setup, setup_test_project


# ── 1 · INES ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ines_no_inventa_la_inversion_sumando_facturas_del_consultor(db):
    """Con facturas del consultor en la BD, la inversion NO sale de ahi."""
    from backend.app.motors.m27_conformity.ines_generator import collect_ines_data

    client_id, project_id = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO invoices (id, client_id, numero_correlativo, "
            " fecha_emision, base_imponible, total, estado_pago, created_at) "
            "VALUES (:id, :cid, 'F-N5-001', CURRENT_DATE, 9999.00, 12098.79, "
            "        'emitida', now())"
        ), {"id": str(uuid.uuid4()), "cid": client_id})
    await db.flush()

    from datetime import date
    report = await collect_ines_data(db, uuid.UUID(client_id), date.today().year)

    assert report.investment_eur is None, (
        "la inversion en seguridad no puede derivarse de las facturas del "
        f"consultor · salio {report.investment_eur}"
    )


@pytest.mark.asyncio
async def test_el_docx_de_ines_dice_que_el_dato_lo_aporta_la_organizacion(db):
    """Si no hay dato, el documento lo dice; no lo deja en blanco sin explicar."""
    from datetime import date

    from backend.app.motors.m27_conformity.ines_generator import (
        collect_ines_data,
        generate_ines_json,
    )

    client_id, _ = await setup_test_project(db)
    report = await collect_ines_data(db, uuid.UUID(client_id), date.today().year)
    payload = generate_ines_json(report)

    assert payload["investment_security_eur"] is None
    nota = (payload.get("investment_security_note") or "").lower()
    assert "organiza" in nota, f"falta la nota que explica el hueco: {nota!r}"


# ── 2 · CLARA ─────────────────────────────────────────────────────────
XML_CON_FALLO = b"""<?xml version="1.0" encoding="UTF-8"?>
<clara>
  <control id="CLARA-W-UAC-01" status="PASS" description="UAC habilitado"/>
  <control id="CLARA-L-PATCH-01" status="FAIL" description="Parches pendientes"/>
</clara>
"""
# CLARA-L-PATCH-01 mapea a op.exp.3; CLARA-W-UAC-01 a op.acc.5.


@pytest.mark.asyncio
async def test_clara_no_crea_evidencia_vigente_para_un_control_en_FAIL(db):
    from backend.app.motors.m27_conformity.adapters.clara_ingester import (
        ingest_clara_output,
    )

    _, project_id = await setup_test_project(db)
    await ingest_clara_output(db, uuid.UUID(project_id), content=XML_CON_FALLO,
                              report_filename="clara.xml")

    filas = (await db.execute(text(
        "SELECT measure_code, vigente FROM evidence "
        "WHERE project_id = :p AND tipo = 'CLARA' AND deleted_at IS NULL"
    ), {"p": project_id})).all()
    vigentes_de_medidas_fallidas = [
        m for m, vig in filas if m == "op.exp.3" and vig
    ]
    assert not vigentes_de_medidas_fallidas, (
        "un control CLARA en FAIL no puede quedar como evidencia vigente de la "
        f"medida: {vigentes_de_medidas_fallidas}"
    )


@pytest.mark.asyncio
async def test_clara_genera_hallazgo_para_el_control_en_FAIL(db):
    from backend.app.motors.m27_conformity.adapters.clara_ingester import (
        ingest_clara_output,
    )

    _, project_id = await setup_test_project(db)
    res = await ingest_clara_output(
        db, uuid.UUID(project_id), content=XML_CON_FALLO,
        report_filename="clara.xml",
    )

    assert res.get("findings_created_count", 0) >= 1, (
        f"un FAIL tiene que generar hallazgo · salida: {res}"
    )
    filas = (await db.execute(text(
        "SELECT medida_afectada, fuente, severidad FROM findings "
        "WHERE project_id = :p AND deleted_at IS NULL"
    ), {"p": project_id})).all()
    assert filas, "no se creo ningun hallazgo"
    assert any(f[1] == "CLARA" for f in filas)


@pytest.mark.asyncio
async def test_clara_si_crea_evidencia_vigente_para_el_control_en_PASS(db):
    """El arreglo no puede tirar por la borda los controles que SI cumplen."""
    from backend.app.motors.m27_conformity.adapters.clara_ingester import (
        ingest_clara_output,
    )

    _, project_id = await setup_test_project(db)
    await ingest_clara_output(db, uuid.UUID(project_id), content=XML_CON_FALLO,
                              report_filename="clara.xml")

    filas = (await db.execute(text(
        "SELECT measure_code FROM evidence "
        "WHERE project_id = :p AND tipo = 'CLARA' AND vigente IS TRUE "
        "  AND deleted_at IS NULL"
    ), {"p": project_id})).all()
    assert filas, "los controles en PASS siguen generando evidencia vigente"


# ── 3 · LUCIA y PILAR ─────────────────────────────────────────────────
def test_no_se_promete_integracion_con_LUCIA_ni_con_PILAR():
    """Ni una promesa de integracion en el codigo ni en la documentacion viva."""
    import re
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[3]
    promesa = re.compile(
        r"(integraci[oó]n\s+(con\s+)?(LUCIA|PILAR)"
        r"|(LUCIA|PILAR)\s+integrad[oa]"
        r"|export(a|ar|acion|ación)?\s+(a\s+)?PILAR)",
        re.IGNORECASE,
    )
    culpables = []
    for carpeta in ("backend/app", "backend/scripts", "frontend/components",
                    "frontend/lib", "docs/catalogs"):
        base = raiz / carpeta
        if not base.exists():
            continue
        for f in list(base.rglob("*.py")) + list(base.rglob("*.ts")) \
                + list(base.rglob("*.tsx")) + list(base.rglob("*.yaml")):
            if "node_modules" in str(f):
                continue
            for n, linea in enumerate(f.read_text("utf-8", errors="ignore").splitlines(), 1):
                if promesa.search(linea):
                    culpables.append(f"{f.relative_to(raiz)}:{n}: {linea.strip()[:100]}")
    assert not culpables, (
        "se promete una integracion que no existe:\n" + "\n".join(culpables)
    )


def test_el_mapa_de_clara_solo_apunta_a_medidas_que_existen():
    """N5 · `mp.info.9` estaba en el mapa y NO existe (mp.info llega a .6).

    Era otro fosil de CCN-STIC 804 v2017 (RD 3/2010), hermano de los seis que
    quito N2 y que no estaba en aquella lista. Se descubrio leyendo el mapa,
    no por el grep de N2, asi que este test cierra la puerta por codigo.
    """
    import json
    from pathlib import Path

    from backend.app.motors.m27_conformity.adapters.clara_ingester import (
        CLARA_TO_ENS_MAP,
    )

    fixture = Path(__file__).resolve().parents[2] / "fixtures/anexo2_boe_verificado.json"
    boe = {m["codigo"] for m in json.loads(fixture.read_text("utf-8"))["medidas"]}
    invent = sorted({m for ms in CLARA_TO_ENS_MAP.values() for m in ms} - boe)
    assert not invent, f"el mapa CLARA apunta a medidas que no existen: {invent}"
