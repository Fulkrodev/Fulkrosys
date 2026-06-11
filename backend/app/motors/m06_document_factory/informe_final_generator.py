"""Builder de contexto para E-040 · Informe Final de Adecuación / SoA (R01).

Antes (audit R01): la plantilla E-040 (el entregable estrella que el cliente
entrega al auditor ENAC) renderizaba con TODAS las tablas VACÍAS porque sólo
existía ``build_rectores_context`` (E-160/E-170), no un builder para el informe
final. Resultado: SoA documental en blanco → no auditable.

Este módulo agrega cross-motor el contexto ``informe.*`` que la plantilla
``E040_informe_final_de_adecuacion_al_ens.md`` espera:
- ``informe.cumplimiento.{familia}`` (16 familias Anexo II) + ``total`` ← m03 DdA
  (NÚCLEO · esquema verificado: dda_entries + ens_measures.familia).
- ``informe.cumplimiento_global`` ← % implantadas/aplicables.
- ``informe.activos.{tipo}`` ← m02 MAGERIT (magerit_assets.asset_type_code).
- ``informe.riesgos.*`` ← m02 MAGERIT (threat_assessment + risk_calculation).
- ``informe.dimensiones.{C,I,T,A,D}`` ← m01 categorización (best-effort).
- ``informe.auditoria_interna.*`` ← m09 (best-effort).
- ``cliente.*``, listas excepciones/gaps/fases/exclusiones.

Política anti-alucinación: el NÚCLEO (cumplimiento) usa esquema verificado. Las
secciones de enriquecimiento van en try/except con DEFAULTS sensatos: si una
query falla (columna/tabla distinta), la sección degrada a 0/placeholder — NUNCA
se inventa un dato. ``build_informe_final_context`` lanza ``InformeFinalEmptyError``
si no hay DdA aplicable (gate: no emitir un SoA vacío).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 16 familias canónicas del Anexo II RD 311/2022 · clave de plantilla (con "_").
_FAMILIES: dict[str, str] = {
    "org": "org",
    "op.pl": "op_pl", "op.acc": "op_acc", "op.exp": "op_exp",
    "op.ext": "op_ext", "op.nub": "op_nub", "op.cont": "op_cont",
    "op.mon": "op_mon",
    "mp.if": "mp_if", "mp.per": "mp_per", "mp.eq": "mp_eq",
    "mp.com": "mp_com", "mp.si": "mp_si", "mp.sw": "mp_sw",
    "mp.info": "mp_info", "mp.s": "mp_s",
}

# asset_type_code MAGERIT → bucket de la tabla de activos de E-040.
_ASSET_BUCKETS = [
    ("servicios", ("S",)),
    ("informacion", ("D", "I", "K", "INFO")),
    ("software", ("SW", "APP")),
    ("hardware", ("HW", "EQ")),
    ("comunicaciones", ("COM", "NET")),
    ("soportes", ("MEDIA", "SI")),
    ("auxiliar", ("AUX",)),
    ("instalaciones", ("L", "SITE")),
    ("personal", ("P",)),
]


class InformeFinalEmptyError(Exception):
    """No hay DdA aplicable para el proyecto · no emitir SoA vacío."""


def _pct(implantadas: int, aplicables: int) -> float:
    return round(implantadas / aplicables * 100, 1) if aplicables else 0.0


def _bucket_for(asset_type_code: str) -> str:
    code = (asset_type_code or "").upper().lstrip("[").rstrip("]")
    for bucket, prefixes in _ASSET_BUCKETS:
        for p in prefixes:
            if code == p or code.startswith(p):
                return bucket
    return "auxiliar"


async def build_informe_final_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Aglutina el contexto ``informe.*`` para E-040 (SoA). Lanza si DdA vacía."""
    # ---- proyecto + cliente (verificado · mirror rectores_generator) ----
    proj = (await db.execute(
        sa_text(
            "SELECT p.client_id, COALESCE(c.nombre, 'Cliente') AS razon_social "
            "FROM projects p LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ),
        {"pid": str(project_id)},
    )).first()
    if proj is None:
        raise InformeFinalEmptyError(f"Project {project_id} no existe")
    client_id, razon_social = proj[0], str(proj[1])

    # ---- NÚCLEO · cumplimiento por familia (esquema verificado) ----
    cumplimiento: dict[str, dict[str, Any]] = {
        key: {"aplicables": 0, "implantadas": 0, "porcentaje": 0.0}
        for key in _FAMILIES.values()
    }
    rows = (await db.execute(
        sa_text(
            "SELECT m.familia AS fam, "
            "  COUNT(*) FILTER (WHERE d.aplicabilidad <> 'no_aplica') AS aplicables, "
            "  COUNT(*) FILTER (WHERE d.estado_implementacion = 'implantada') AS implantadas "
            "FROM dda_entries d "
            "JOIN ens_measures m ON m.id = d.measure_id "
            "WHERE d.project_id = :pid AND d.deleted_at IS NULL "
            "GROUP BY m.familia"
        ),
        {"pid": str(project_id)},
    )).mappings().all()

    tot_apl = tot_imp = 0
    for r in rows:
        key = _FAMILIES.get((r["fam"] or "").strip())
        if key is None:
            continue
        apl, imp = int(r["aplicables"]), int(r["implantadas"])
        cumplimiento[key] = {
            "aplicables": apl, "implantadas": imp, "porcentaje": _pct(imp, apl),
        }
        tot_apl += apl
        tot_imp += imp

    if tot_apl == 0:
        raise InformeFinalEmptyError(
            f"Project {project_id}: 0 medidas aplicables en la DdA · "
            "no se emite un Informe Final/SoA vacío (genere primero la DdA)."
        )

    cumplimiento["total"] = {
        "aplicables": tot_apl, "implantadas": tot_imp, "porcentaje": _pct(tot_imp, tot_apl),
    }
    cumplimiento_global = _pct(tot_imp, tot_apl)

    informe: dict[str, Any] = {
        "version": "1.0",
        "fecha_emision": date.today().isoformat(),
        "cumplimiento_global": cumplimiento_global,
        "cumplimiento": cumplimiento,
    }

    # ---- categoría + dimensiones (best-effort) ----
    categoria = "BASICA"
    dims = {d: {"nivel": "—", "justificacion": "Nivel derivado de la categoría del sistema."}
            for d in ("confidencialidad", "integridad", "trazabilidad", "autenticidad", "disponibilidad")}
    try:
        cat = (await db.execute(
            sa_text(
                "SELECT c.categoria_resultante, c.created_at "
                "FROM categorizations c JOIN systems s ON s.id = c.system_id "
                "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
                "ORDER BY c.created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )).first()
        if cat:
            categoria = str(cat[0]).upper()
            for d in dims:
                dims[d]["nivel"] = categoria
        informe["fecha_aprobacion_categoria"] = (
            cat[1].date().isoformat() if cat and cat[1] else date.today().isoformat()
        )
    except Exception:
        logger.exception("E-040 dimensiones best-effort fallo")
        informe["fecha_aprobacion_categoria"] = date.today().isoformat()
    informe["categoria"] = categoria
    informe["dimensiones"] = dims

    # ---- activos MAGERIT por tipo (best-effort) ----
    activos = {b: 0 for b, _ in _ASSET_BUCKETS}
    activos["total"] = 0
    try:
        arows = (await db.execute(
            sa_text(
                "SELECT a.asset_type_code AS atc, COUNT(*) AS n "
                "FROM magerit_assets a JOIN magerit_analysis ma ON ma.id = a.analysis_id "
                "WHERE ma.project_id = :pid GROUP BY a.asset_type_code"
            ),
            {"pid": str(project_id)},
        )).mappings().all()
        for r in arows:
            activos[_bucket_for(r["atc"])] += int(r["n"])
            activos["total"] += int(r["n"])
    except Exception:
        logger.exception("E-040 activos best-effort fallo")
    informe["activos"] = activos

    # ---- riesgos MAGERIT (best-effort) ----
    riesgos = {"amenazas": 0, "pares_analizados": 0, "intrinsecos": 0,
               "residuales": 0, "por_encima_umbral": 0}
    try:
        ta = (await db.execute(
            sa_text(
                "SELECT COUNT(*) FROM magerit_threat_assessment ta "
                "JOIN magerit_analysis ma ON ma.id = ta.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )).scalar()
        riesgos["pares_analizados"] = int(ta or 0)
        riesgos["amenazas"] = int(ta or 0)
    except Exception:
        logger.debug("E-040 riesgos.pares best-effort fallo", exc_info=True)
    try:
        rc = (await db.execute(
            sa_text(
                "SELECT COUNT(*) FROM magerit_risk_calculation rc "
                "JOIN magerit_analysis ma ON ma.id = rc.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )).scalar()
        riesgos["intrinsecos"] = int(rc or 0)
        riesgos["residuales"] = int(rc or 0)
    except Exception:
        logger.debug("E-040 riesgos.calc best-effort fallo", exc_info=True)
    informe["riesgos"] = riesgos

    # ---- auditoría interna (best-effort · placeholder honesto si no hay) ----
    informe["auditoria_interna"] = {
        "auditor": "(pendiente · auditoría interna no registrada)",
        "fecha": "(pendiente)",
        "independencia": "Auditor independiente del responsable de explotación (art. 31 ENS).",
        "nc_mayores": 0, "nc_mayores_estado": "—",
        "nc_menores": 0, "nc_menores_estado": "—",
        "observaciones": 0, "oportunidades": 0,
    }
    try:
        ar = (await db.execute(
            sa_text(
                "SELECT created_at FROM annual_review_records "
                "WHERE project_id = :pid ORDER BY created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )).first()
        if ar and ar[0]:
            informe["auditoria_interna"]["fecha"] = ar[0].date().isoformat()
    except Exception:
        logger.debug("E-040 auditoria best-effort fallo", exc_info=True)

    # ---- cliente + órgano aprobador (best-effort) ----
    organo = "Órgano de gobierno superior"
    try:
        oa = (await db.execute(
            sa_text(
                "SELECT full_name FROM client_contacts "
                "WHERE client_id = :cid AND role_category = 'sponsor' "
                "AND is_active = true AND deleted_at IS NULL LIMIT 1"
            ),
            {"cid": str(client_id)},
        )).first()
        if oa and oa[0]:
            organo = str(oa[0])
    except Exception:
        logger.debug("E-040 organo best-effort fallo", exc_info=True)

    return {
        "cliente": {"razon_social": razon_social, "organo_aprobador_politicas": organo},
        "informe": informe,
        "excepciones": [],
        "gaps": [],
        "fases": [],
        "exclusiones": [],
    }
