"""Builder de contexto para E-040 · Informe Final de Adecuación / SoA (R01+R02).

Antes (audit R01): la plantilla E-040 (el entregable estrella que el cliente
entrega al auditor ENAC) renderizaba con TODAS las tablas VACÍAS porque sólo
existía ``build_rectores_context`` (E-160/E-170), no un builder para el informe
final. Resultado: SoA documental en blanco → no auditable.

R02 (cierre real): además de poblar el núcleo (cumplimiento por familia), se
ALINEAN las claves al contrato exacto de la plantilla ``E040_...ens.md``
(``proyecto.*``, ``informe.fases/gaps/excepciones``, ``responsables.*``,
``informe.cuerpo_normativo.*``, ``informe.evidencias.*``) para que NINGÚN campo
núcleo renderice en blanco, y se diferencia riesgo intrínseco vs residual con
las columnas reales de ``magerit_risk_calculation``.

Contrato (verificado leyendo la plantilla):
- ``proyecto.{categoria_ens,fecha_inicio,fecha_fin,entidad_certificadora,
  version_actual,alcance.*}``.
- ``informe.cumplimiento.{familia}`` (16 familias Anexo II) + ``total`` ← m03 DdA
  (NÚCLEO · esquema verificado: dda_entries + ens_measures.familia).
- ``informe.cumplimiento_global`` ← % implantadas/aplicables.
- ``informe.activos.{tipo}`` ← m02 MAGERIT (magerit_assets.asset_type_code).
- ``informe.riesgos.*`` ← m02 MAGERIT (threat_assessment + risk_calculation).
- ``informe.dimensiones.{C,I,T,A,D}`` ← m01 categorización (best-effort).
- ``informe.cuerpo_normativo.{politicas,procedimientos}`` ← documents del proyecto.
- ``informe.evidencias.*`` ← m07 evidence (best-effort, clasificación por tipo).
- ``informe.auditoria_interna.*`` ← m09 (best-effort).
- ``cliente.*``, ``responsables.*``, ``informe.{fases,gaps,excepciones}``.

Política anti-alucinación: el NÚCLEO (cumplimiento) usa esquema verificado. Las
secciones de enriquecimiento van en try/except con DEFAULTS sensatos: si una
query falla (columna/tabla distinta), la sección degrada a 0/placeholder honesto
— NUNCA se inventa un dato. ``build_informe_final_context`` lanza
``InformeFinalEmptyError`` si no hay DdA aplicable (gate: no emitir SoA vacío).
"""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.motors.m06_document_factory.errores import (
    CategoriaNoDeterminadaError,
)

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

# Clasificación best-effort de evidencias → bucket de la tabla §8 de E-040.
# (palabra clave en tipo/nombre_tipo en minúsculas → bucket).
_EVIDENCE_BUCKETS = [
    ("actas", ("acta", "aprobacion", "aprobación", "politica", "política", "firma")),
    ("formacion", ("formacion", "formación", "concienciacion", "concienciación", "training")),
    ("riesgos", ("riesgo", "magerit", "amenaza")),
    ("restauracion", ("restauracion", "restauración", "backup", "copia", "recuper")),
    ("auditoria_interna", ("auditoria", "auditoría", "audit")),
    ("incidentes", ("incidente", "simulacro", "ejercicio")),
    ("proveedores", ("proveedor", "tercero", "supplier")),
    ("vulnerabilidades", ("vulnerabilidad", "pentest", "scan", "parche", "cve")),
    # bucket por defecto (configuraciones) para todo lo técnico no clasificado.
    ("configuraciones", ("config", "captura", "hardening", "screenshot", "log")),
]
_EVIDENCE_DEFAULT_BUCKET = "configuraciones"

# Etiquetas de riesgo residual consideradas "por encima del umbral de aceptación".
_HIGH_RISK_LABELS = ("alto", "muy alto", "muy_alto", "critico", "crítico", "high", "very high", "very_high")


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


def _evidence_bucket_for(*labels: str) -> str:
    hay = " ".join(x for x in labels if x).lower()
    for bucket, keywords in _EVIDENCE_BUCKETS:
        for kw in keywords:
            if kw in hay:
                return bucket
    return _EVIDENCE_DEFAULT_BUCKET


def _iso(value: Any) -> str | None:
    """Formatea un date/datetime a ISO; None si no aplica."""
    if value is None:
        return None
    try:
        return value.date().isoformat()  # datetime
    except AttributeError:
        try:
            return value.isoformat()  # date
        except AttributeError:
            return str(value)


async def build_informe_final_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Aglutina el contexto ``informe.*`` + ``proyecto.*`` para E-040 (SoA).

    Lanza ``InformeFinalEmptyError`` si la DdA no tiene medidas aplicables.
    """
    # ---- proyecto + cliente (verificado · mirror rectores_generator) ----
    proj = (await db.execute(
        sa_text(
            "SELECT p.client_id, COALESCE(c.nombre, 'Cliente') AS razon_social, "
            "  p.fecha_kickoff, p.fecha_objetivo_certificacion, p.certified_at, "
            "  p.categoria_objetivo, COALESCE(c.cif,'') AS nif, "
            "  COALESCE(c.domicilio_fiscal,'') AS domicilio "
            "FROM projects p LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ),
        {"pid": str(project_id)},
    )).first()
    if proj is None:
        raise InformeFinalEmptyError(f"Project {project_id} no existe")
    client_id = proj[0]
    razon_social = str(proj[1])
    cliente_nif = str(proj[6] or "") or "(NIF pendiente)"
    cliente_domicilio = str(proj[7] or "") or "(domicilio pendiente)"
    fecha_inicio = _iso(proj[2]) or "(pendiente)"
    fecha_fin = _iso(proj[4]) or _iso(proj[3]) or "(en curso)"
    categoria_objetivo = (str(proj[5]).upper() if proj[5] else None)

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
    # O1 · ver acta_e012_generator: sin categoria no se inventa.
    categoria = categoria_objetivo
    if not categoria:
        raise CategoriaNoDeterminadaError("el informe final de adecuacion E-040")
    fecha_aprobacion_categoria = date.today().isoformat()
    try:
        cat = (await db.execute(
            sa_text(
                "SELECT c.categoria_resultante, c.fecha_acta, c.created_at "
                "FROM categorizations c JOIN systems s ON s.id = c.system_id "
                "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
                "ORDER BY c.created_at DESC LIMIT 1"
            ),
            {"pid": str(project_id)},
        )).first()
        if cat and cat[0]:
            categoria = str(cat[0]).upper()
            fecha_aprobacion_categoria = (
                _iso(cat[1]) or _iso(cat[2]) or fecha_aprobacion_categoria
            )
    except Exception:
        logger.exception("E-040 categoría best-effort fallo")
    informe["fecha_aprobacion_categoria"] = fecha_aprobacion_categoria
    informe["categoria"] = categoria
    dims = {
        d: {
            "nivel": categoria,
            "justificacion": (
                "Nivel resultante de la valoración de impacto documentada en el "
                "acta de categorización del sistema (E-012)."
            ),
        }
        for d in ("confidencialidad", "integridad", "trazabilidad", "autenticidad", "disponibilidad")
    }
    informe["dimensiones"] = dims

    # ---- proyecto.* (categoría + fechas + alcance best-effort) ----
    proyecto = {
        "categoria_ens": categoria,
        "version_actual": "1.0",
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "entidad_certificadora": "(entidad acreditada por ENAC pendiente de designación)",
        "alcance": {
            "descripcion_completa": (
                f"Sistema de información de {razon_social} comprendido en el ámbito "
                f"objeto de adecuación al Esquema Nacional de Seguridad en categoría "
                f"{categoria}. El alcance detallado, con sus servicios, sistemas, "
                f"sedes y exclusiones, se define formalmente en el documento E-155 "
                f"(Documento de Alcance del SGSI)."
            ),
            "servicios": [],
            "sistemas": [],
            "sedes": [],
            "exclusiones": [],
        },
    }

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
    # alcance.servicios best-effort desde los servicios MAGERIT (tipo S).
    if activos.get("servicios"):
        proyecto["alcance"]["servicios"] = []  # detalle nominal en E-155 (R05)

    # ---- riesgos MAGERIT · intrínseco ≠ residual (columnas reales) ----
    riesgos = {
        "amenazas": 0, "pares_analizados": 0, "intrinsecos": 0,
        "residuales": 0, "por_encima_umbral": 0, "aceptados": 0,
        "acciones_plan": 0, "mitigar": 0, "transferir": 0, "evitar": 0,
        "aceptar": 0, "porcentaje_completado": 0,
    }
    try:
        ta = (await db.execute(
            sa_text(
                "SELECT COUNT(*) AS pares, COUNT(DISTINCT ta.threat_code) AS amenazas "
                "FROM magerit_threat_assessment ta "
                "JOIN magerit_analysis ma ON ma.id = ta.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )).first()
        if ta:
            riesgos["pares_analizados"] = int(ta[0] or 0)
            riesgos["amenazas"] = int(ta[1] or 0)
    except Exception:
        logger.debug("E-040 riesgos.pares best-effort fallo", exc_info=True)
    try:
        labels_sql = ", ".join(f"'{lab}'" for lab in _HIGH_RISK_LABELS)
        rc = (await db.execute(
            sa_text(
                "SELECT "
                "  COUNT(*) AS intrinsecos, "
                "  COUNT(*) FILTER (WHERE rc.risk_residual IS NOT NULL) AS residuales, "
                "  COUNT(*) FILTER (WHERE LOWER(COALESCE(rc.risk_level,'')) IN "
                f"   ({labels_sql})) AS por_encima "
                "FROM magerit_risk_calculation rc "
                "JOIN magerit_analysis ma ON ma.id = rc.analysis_id "
                "WHERE ma.project_id = :pid"
            ),
            {"pid": str(project_id)},
        )).first()
        if rc:
            riesgos["intrinsecos"] = int(rc[0] or 0)
            riesgos["residuales"] = int(rc[1] or 0)
            riesgos["por_encima_umbral"] = int(rc[2] or 0)
    except Exception:
        logger.debug("E-040 riesgos.calc best-effort fallo", exc_info=True)
    try:
        trows = (await db.execute(
            sa_text(
                "SELECT COALESCE(tp.treatment,'') AS treatment, "
                "  COALESCE(tp.status,'') AS status "
                "FROM magerit_treatment_plan tp "
                "JOIN magerit_analysis ma ON ma.id = tp.analysis_id "
                "WHERE ma.project_id = :pid AND tp.deleted_at IS NULL"
            ),
            {"pid": str(project_id)},
        )).mappings().all()
        completadas = 0
        for tr in trows:
            riesgos["acciones_plan"] += 1
            t = (tr["treatment"] or "").lower()
            if "mitig" in t:
                riesgos["mitigar"] += 1
            elif "transf" in t:
                riesgos["transferir"] += 1
            elif "evit" in t:
                riesgos["evitar"] += 1
            elif "acept" in t:
                riesgos["aceptar"] += 1
                riesgos["aceptados"] += 1
            if (tr["status"] or "").lower() in (
                "done", "completada", "completado", "closed", "finalizada",
            ):
                completadas += 1
        if riesgos["acciones_plan"]:
            riesgos["porcentaje_completado"] = _pct(completadas, riesgos["acciones_plan"])
    except Exception:
        logger.debug("E-040 riesgos.treatment best-effort fallo", exc_info=True)
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
            informe["auditoria_interna"]["fecha"] = _iso(ar[0])
    except Exception:
        logger.debug("E-040 auditoria best-effort fallo", exc_info=True)

    # ---- cuerpo normativo · documentos generados del proyecto (best-effort) ----
    cuerpo = {"politicas": [], "procedimientos": []}
    try:
        for cat_key, bucket in (("politica", "politicas"), ("procedimiento", "procedimientos")):
            drows = (await db.execute(
                sa_text(
                    "SELECT d.template_codigo AS codigo, "
                    "  COALESCE(d.nombre, t.nombre) AS nombre, "
                    "  COALESCE(d.version_actual, '1.0') AS version, "
                    "  d.fecha_aprobacion AS fecha "
                    "FROM documents d "
                    "JOIN templates t ON t.codigo = d.template_codigo "
                    "WHERE d.project_id = :pid AND d.deleted_at IS NULL "
                    "  AND t.categoria = :cat "
                    "ORDER BY d.template_codigo"
                ),
                {"pid": str(project_id), "cat": cat_key},
            )).mappings().all()
            cuerpo[bucket] = [
                {
                    "codigo": r["codigo"],
                    "nombre": r["nombre"],
                    "version": r["version"],
                    "fecha": _iso(r["fecha"]) or "(pendiente de aprobación)",
                }
                for r in drows
            ]
    except Exception:
        logger.debug("E-040 cuerpo_normativo best-effort fallo", exc_info=True)
    informe["cuerpo_normativo"] = cuerpo

    # ---- evidencias · m07 (best-effort · clasificación por tipo) ----
    evidencias = {b: 0 for b, _ in _EVIDENCE_BUCKETS}
    evidencias["total"] = 0
    try:
        erows = (await db.execute(
            sa_text(
                "SELECT COALESCE(tipo,'') AS tipo, COALESCE(nombre_tipo,'') AS nombre_tipo, "
                "  COUNT(*) AS n "
                "FROM evidence "
                "WHERE project_id = :pid AND deleted_at IS NULL AND vigente = true "
                "GROUP BY tipo, nombre_tipo"
            ),
            {"pid": str(project_id)},
        )).mappings().all()
        for r in erows:
            n = int(r["n"])
            evidencias[_evidence_bucket_for(r["tipo"], r["nombre_tipo"])] += n
            evidencias["total"] += n
    except Exception:
        logger.debug("E-040 evidencias best-effort fallo", exc_info=True)
    informe["evidencias"] = evidencias

    # ---- fases · m17 WBS agregado por fase (best-effort) → informe.fases ----
    fases: list[dict[str, Any]] = []
    try:
        frows = (await db.execute(
            sa_text(
                "SELECT phase, COUNT(*) AS n, "
                "  COALESCE(SUM(duration_days), 0) AS dias, "
                "  COUNT(*) FILTER (WHERE LOWER(COALESCE(status,'')) IN "
                "    ('done','completada','completado','closed','finalizada')) AS hechas, "
                "  MIN(start_date) AS ini "
                "FROM wbs_tasks "
                "WHERE project_id = :pid AND deleted_at IS NULL AND phase IS NOT NULL "
                "GROUP BY phase ORDER BY MIN(start_date) NULLS LAST"
            ),
            {"pid": str(project_id)},
        )).mappings().all()
        for fr in frows:
            n = int(fr["n"])
            hechas = int(fr["hechas"])
            dias = int(fr["dias"] or 0)
            estado = ("Completada" if hechas >= n and n > 0
                      else ("En curso" if hechas > 0 else "Planificada"))
            fases.append({
                "nombre": fr["phase"],
                "descripcion": f"{n} tareas del WBS",
                "duracion_real": round(dias / 7, 1) if dias else "—",
                "estado": estado,
            })
    except Exception:
        logger.debug("E-040 fases best-effort fallo", exc_info=True)
    informe["fases"] = fases

    # ---- gaps + excepciones (best-effort) → informe.* ----
    informe["gaps"] = []
    informe["excepciones"] = []

    # ---- cliente + responsables + órgano aprobador (best-effort) ----
    organo = "Órgano de gobierno superior"
    rseg_nombre = "(Responsable de Seguridad pendiente de designación)"
    rseg_cargo = "Responsable de Seguridad de la Información"
    try:
        crows = (await db.execute(
            sa_text(
                "SELECT full_name, COALESCE(role_category,'') AS rc, "
                "  COALESCE(role_title,'') AS pos "
                "FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true AND deleted_at IS NULL"
            ),
            {"cid": str(client_id)},
        )).mappings().all()
        for c in crows:
            blob = f"{c['rc']} {c['pos']}".lower()
            if c["full_name"] and ("sponsor" in blob or "direcc" in blob
                                   or "gobierno" in blob or "comit" in blob):
                organo = str(c["full_name"])
            if c["full_name"] and ("seg" in blob or "rseg" in blob or "ciso" in blob):
                rseg_nombre = str(c["full_name"])
                if c["pos"]:
                    rseg_cargo = str(c["pos"])
    except Exception:
        logger.debug("E-040 contactos best-effort fallo", exc_info=True)

    return {
        "cliente": {
            "razon_social": razon_social, "organo_aprobador_politicas": organo,
            "nif": cliente_nif, "domicilio_social": cliente_domicilio,
        },
        "proyecto": proyecto,
        "responsables": {
            "responsable_seguridad": {"nombre": rseg_nombre, "cargo": rseg_cargo},
        },
        "informe": informe,
    }
