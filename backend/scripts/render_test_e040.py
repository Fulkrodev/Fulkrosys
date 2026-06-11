"""Render-test E-040 (R02 · cierre real) — NO es un test unitario.

Renderiza el E-040.docx recompilado con ``build_informe_final_context`` sobre un
proyecto REAL con DdA (proyecto demo) y vuelca el contexto + el DOCX a ``out/``.
Conéctate como superusuario ``fulkro`` (dev) para saltar RLS en el harness.

Uso:  .venv/bin/python backend/scripts/render_test_e040.py [project_id]
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import text as sa_text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.app.motors.m06_document_factory.informe_final_generator import (  # noqa: E402
    build_informe_final_context,
)
from backend.app.motors.m06_document_factory.rendering import render_docx  # noqa: E402

# DSN runtime dev (fulkro_app · NOBYPASSRLS) · se fija el contexto de tenant.
DSN = "postgresql+asyncpg://fulkro_app:fulkro_app_dev_password@localhost:5433/fulkro"
DEFAULT_PID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DOCX = ROOT / "var" / "templates_docx" / "E-040.docx"
OUT = ROOT / "out" / "e040_rendered_test.docx"


async def main() -> int:
    pos_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pid = uuid.UUID(pos_args[0]) if pos_args else DEFAULT_PID
    engine = create_async_engine(DSN, echo=False)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        # Bypass RLS en el harness vía el rol escape canónico (BYPASSRLS).
        await db.execute(sa_text("SET ROLE fulkro_app_bypassrls"))
        ctx = await build_informe_final_context(db, pid)
    await engine.dispose()

    out = OUT
    if "--synth" in sys.argv:
        # Inyecta datos sintéticos para EJERCITAR las ramas de lista/tabla que el
        # proyecto demo deja vacías (cuerpo_normativo, fases, sedes, riesgos,
        # evidencias, gaps, excepciones). Verifica el render con datos reales.
        inf = ctx["informe"]
        ctx["proyecto"]["fecha_inicio"] = "2026-01-15"
        ctx["proyecto"]["fecha_fin"] = "2026-04-30"
        ctx["proyecto"]["alcance"]["servicios"] = [
            "Portal de tramitación electrónica", "Sede electrónica",
        ]
        ctx["proyecto"]["alcance"]["sedes"] = [
            {"nombre": "Sede Central Madrid", "direccion": "C/ Gran Vía 1, 28013 Madrid", "tipo": "Sede física"},
            {"nombre": "Región AWS eu-west-1", "direccion": "Irlanda (UE)", "tipo": "Región cloud"},
        ]
        inf["fases"] = [
            {"nombre": "Categorización y alcance", "descripcion": "12 tareas del WBS", "duracion_real": 2.0, "estado": "Completada"},
            {"nombre": "Implantación de medidas", "descripcion": "40 tareas del WBS", "duracion_real": 8.0, "estado": "En curso"},
        ]
        inf["cuerpo_normativo"]["politicas"] = [
            {"codigo": "E-100", "nombre": "Política de Seguridad de la Información", "version": "1.0", "fecha": "2026-02-01"},
            {"codigo": "E-101", "nombre": "Política de Control de Accesos", "version": "1.0", "fecha": "2026-02-01"},
        ]
        inf["cuerpo_normativo"]["procedimientos"] = [
            {"codigo": "E-200", "nombre": "Procedimiento de Alta de Personal", "version": "1.0", "fecha": "2026-02-15"},
        ]
        inf["riesgos"].update({
            "intrinsecos": 120, "residuales": 120, "por_encima_umbral": 3, "aceptados": 3,
            "acciones_plan": 30, "mitigar": 24, "transferir": 2, "evitar": 1, "aceptar": 3,
            "porcentaje_completado": 80.0,
        })
        inf["evidencias"] = {
            "actas": 21, "formacion": 4, "riesgos": 2, "configuraciones": 30,
            "restauracion": 3, "auditoria_interna": 1, "incidentes": 2,
            "proveedores": 5, "vulnerabilidades": 4, "total": 72,
        }
        inf["gaps"] = [
            {"medida_ens": "op.mon.1", "descripcion": "Monitorización SIEM parcial", "riesgo": "Medio", "accion": "Desplegar correlación de logs", "plazo": "Q3 2026"},
        ]
        inf["excepciones"] = [
            {"norma": "mp.eq.3", "justificacion": "Equipo legacy sin reemplazo inmediato", "vigencia": "6 meses", "mitigacion": "Aislamiento de red"},
        ]
        ctx["responsables"]["responsable_seguridad"] = {"nombre": "Ana Pérez", "cargo": "CISO"}
        ctx["cliente"]["organo_aprobador_politicas"] = "Comité de Dirección"
        out = ROOT / "out" / "e040_rendered_synth.docx"

    inf = ctx["informe"]
    print("=== CONTEXTO build_informe_final_context ===")
    print("proyecto.categoria_ens :", ctx["proyecto"]["categoria_ens"])
    print("proyecto.fecha_inicio  :", ctx["proyecto"]["fecha_inicio"])
    print("proyecto.fecha_fin     :", ctx["proyecto"]["fecha_fin"])
    print("cliente.razon_social   :", ctx["cliente"]["razon_social"])
    print("organo_aprobador       :", ctx["cliente"]["organo_aprobador_politicas"])
    print("responsable_seguridad  :", ctx["responsables"]["responsable_seguridad"])
    print("cumplimiento_global    :", inf["cumplimiento_global"], "%")
    print("cumplimiento.total     :", inf["cumplimiento"]["total"])
    print("op_nub                 :", inf["cumplimiento"]["op_nub"])
    print("op_mon                 :", inf["cumplimiento"]["op_mon"])
    print("activos.total          :", inf["activos"]["total"])
    print("riesgos                :", inf["riesgos"])
    print("fases                  :", len(inf["fases"]))
    print("cuerpo_normativo pol/proc:",
          len(inf["cuerpo_normativo"]["politicas"]), "/",
          len(inf["cuerpo_normativo"]["procedimientos"]))
    print("evidencias.total       :", inf["evidencias"]["total"])

    out.parent.mkdir(parents=True, exist_ok=True)
    render_docx(template_path=DOCX, context=ctx, output_path=out)
    print(f"\n=== RENDER OK: {out} ({out.stat().st_size} bytes) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
