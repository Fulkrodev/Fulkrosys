"""Builder de contexto para E-155 · Documento de Alcance del SGSI (R05).

Antes (audit R05): la plantilla E-155 se auto-declaraba BORRADOR y el bloque
``alcance.*`` (servicios/sistemas/sedes/exclusiones) NO tenía builder → se
renderizaba con texto placeholder ("Por determinar en el inventario…", "Sede
principal"). NC_MAYOR · no emitible para ENAC.

R05: ``build_e155_alcance_context`` agrega el alcance ESTRUCTURADO desde el
dominio m01 (``systems`` + ``services`` [con ``tipo`` finalista/instrumental] +
``information_types``) y las tablas nuevas ``system_sites`` (sedes físicas /
regiones cloud) y ``scope_exclusions`` (exclusiones justificadas), con las
dimensiones DICAT reales (regla del máximo, Anexo I RD 311/2022) y los
responsables ENS (m30 ``client_contacts``). Gate ``E155ScopeEmptyError``: no se
emite un alcance vacío.

Contrato (verificado leyendo ``E155_documento_alcance_sgsi.md``):
- ``cliente.{razon_social,nif,domicilio_social,representante_legal,
  organo_aprobador_politicas}`` ← clients + client_contacts
- ``proyecto.{categoria_ens,servicio_principal,version_actual,nombre_sistema,
  fecha_aprobacion_inicial}``
- ``sistema.nombre`` ← systems
- ``responsables.{responsable_informacion,_servicio,_seguridad,_sistema}
  .{nombre,cargo}`` ← client_contacts (role_category canónico m30)
- ``alcance.servicios[].{nombre,tipo,descripcion}`` ← services
- ``alcance.sistemas[].{nombre}`` ← systems (+ frontera)
- ``alcance.sedes[].{nombre,tipo,direccion,pais}`` ← system_sites
- ``alcance.activos_esenciales[].{nombre,tipo}`` ← m02 MAGERIT (best-effort)
- ``alcance.exclusiones[].{elemento,justificacion}`` ← scope_exclusions (fallback
  ``contracts.alcance_snapshot``)
- ``categorizacion.dimensiones.{confidencialidad,integridad,disponibilidad,
  autenticidad,trazabilidad}`` (regla del máximo) + ``nivel_global``

Anti-alucinación: el núcleo (servicios/sedes/exclusiones/dimensiones) viene de
tablas verificadas; el enriquecimiento (activos MAGERIT, exclusiones del
snapshot comercial) va en try/except con defaults honestos. NUNCA inventa datos.
``firmas.*`` y ``consultor.*`` los rellena el render (``_default_firmas`` /
``_inject_brand``).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# role_category canónico (m30 roles_ens) → clave de plantilla responsables.*
_ROLE_KEYS = (
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
)

_LEVEL_RANK = {"BAJO": 1, "MEDIO": 2, "ALTO": 3}
# (clave plantilla, columna valoración DICAT)
_DIMS = (
    ("confidencialidad", "valoracion_c"),
    ("integridad", "valoracion_i"),
    ("disponibilidad", "valoracion_d"),
    ("autenticidad", "valoracion_a"),
    ("trazabilidad", "valoracion_t"),
)
_TIPO_SERVICIO_LABEL = {"finalista": "finalista", "instrumental": "instrumental"}


class E155ScopeEmptyError(Exception):
    """El proyecto no tiene sistema/alcance · no emitir un E-155 vacío."""


def _norm_level(value: Any) -> str:
    return (str(value).upper().strip() if value is not None else "")


def _max_level(values) -> str | None:
    """Devuelve el nivel DICAT máximo (BAJO<MEDIO<ALTO) de una lista, o None."""
    best = None
    best_rank = 0
    for v in values:
        r = _LEVEL_RANK.get(_norm_level(v), 0)
        if r > best_rank:
            best_rank = r
            best = _norm_level(v)
    return best


async def build_e155_alcance_context(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Aglutina el contexto ``alcance.*`` + identidad + dimensiones para E-155.

    Lanza ``E155ScopeEmptyError`` si el proyecto no tiene sistema con tipos de
    información ni servicios (alcance sin definir → no se emite).
    """
    # ── sistema primario + proyecto + cliente (esquema verificado) ──
    sysrow = (await db.execute(sa_text(
        "SELECT s.id, s.nombre, s.frontera, s.descripcion, "
        "  p.client_id, COALESCE(c.nombre, 'Cliente') AS razon_social, "
        "  c.cif, c.domicilio_fiscal, p.categoria_objetivo "
        "FROM systems s "
        "JOIN projects p ON p.id = s.project_id "
        "LEFT JOIN clients c ON c.id = p.client_id "
        "WHERE s.project_id = :pid AND s.deleted_at IS NULL "
        "ORDER BY s.created_at ASC LIMIT 1"
    ), {"pid": str(project_id)})).first()
    if sysrow is None:
        raise E155ScopeEmptyError(
            f"Project {project_id}: sin sistema definido · cree el sistema y su "
            "categorización (M01) antes de emitir el Documento de Alcance E-155."
        )
    system_id = sysrow[0]
    system_nombre = str(sysrow[1] or "Sistema de información del ámbito SGSI")
    frontera = sysrow[2]
    client_id = sysrow[4]
    razon_social = str(sysrow[5])
    cif = sysrow[6]
    domicilio = sysrow[7]
    categoria_objetivo = (str(sysrow[8]).upper() if sysrow[8] else None)

    # ── servicios (núcleo · con tipo finalista/instrumental) ──
    srows = (await db.execute(sa_text(
        "SELECT nombre, tipo, justificacion, "
        "  valoracion_c, valoracion_i, valoracion_d, valoracion_a, valoracion_t "
        "FROM services WHERE system_id = :sid AND deleted_at IS NULL "
        "ORDER BY created_at ASC"
    ), {"sid": str(system_id)})).mappings().all()

    # ── tipos de información (núcleo · para regla del máximo DICAT) ──
    itrows = (await db.execute(sa_text(
        "SELECT nombre, "
        "  valoracion_c, valoracion_i, valoracion_d, valoracion_a, valoracion_t "
        "FROM information_types WHERE system_id = :sid AND deleted_at IS NULL "
        "ORDER BY created_at ASC"
    ), {"sid": str(system_id)})).mappings().all()

    if not srows and not itrows:
        raise E155ScopeEmptyError(
            f"Project {project_id}: el sistema no tiene servicios ni tipos de "
            "información · cargue el alcance (M01) antes de emitir el E-155."
        )

    servicios = [
        {
            "nombre": r["nombre"],
            "tipo": _TIPO_SERVICIO_LABEL.get(
                (r["tipo"] or "").lower(), None
            ),
            "descripcion": r["justificacion"] or None,
        }
        for r in srows
    ]

    # ── dimensiones DICAT reales (máximo sobre servicios + tipos de info) ──
    dimensiones: dict[str, str] = {}
    for key, col in _DIMS:
        vals = [r[col] for r in srows] + [r[col] for r in itrows]
        dimensiones[key] = _max_level(vals) or ""

    # ── categoría global (acta de categorización · best-effort) ──
    categoria = categoria_objetivo or _max_categoria(dimensiones) or "BASICA"
    fecha_aprobacion = None
    try:
        cat = (await db.execute(sa_text(
            "SELECT c.categoria_resultante, c.fecha_acta, c.aprobado_por "
            "FROM categorizations c JOIN systems s ON s.id = c.system_id "
            "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
            "ORDER BY c.created_at DESC LIMIT 1"
        ), {"pid": str(project_id)})).first()
        if cat and cat[0]:
            categoria = str(cat[0]).upper()
            fecha_aprobacion = _iso(cat[1])
    except Exception:
        logger.debug("E-155 categoría best-effort fallo", exc_info=True)

    # ── sistemas/plataformas en alcance (todos los systems del proyecto) ──
    allsys = (await db.execute(sa_text(
        "SELECT nombre, frontera FROM systems "
        "WHERE project_id = :pid AND deleted_at IS NULL ORDER BY created_at ASC"
    ), {"pid": str(project_id)})).mappings().all()
    sistemas = [
        {"nombre": s["nombre"], "descripcion": s["frontera"] or None}
        for s in allsys
    ]

    # ── sedes / regiones cloud (tabla nueva system_sites) ──
    sederows = (await db.execute(sa_text(
        "SELECT ss.nombre, ss.tipo, ss.direccion, ss.pais, ss.descripcion "
        "FROM system_sites ss JOIN systems s ON s.id = ss.system_id "
        "WHERE s.project_id = :pid AND ss.deleted_at IS NULL "
        "ORDER BY ss.created_at ASC"
    ), {"pid": str(project_id)})).mappings().all()
    sedes = [
        {
            "nombre": r["nombre"],
            "tipo": r["tipo"] or None,
            "direccion": r["direccion"] or None,
            "pais": r["pais"] or None,
            "descripcion": r["descripcion"] or None,
        }
        for r in sederows
    ]

    # ── exclusiones (tabla nueva scope_exclusions · fallback snapshot) ──
    exrows = (await db.execute(sa_text(
        "SELECT se.elemento, se.justificacion "
        "FROM scope_exclusions se JOIN systems s ON s.id = se.system_id "
        "WHERE s.project_id = :pid AND se.deleted_at IS NULL "
        "ORDER BY se.created_at ASC"
    ), {"pid": str(project_id)})).mappings().all()
    exclusiones = [
        {"elemento": r["elemento"], "justificacion": r["justificacion"] or None}
        for r in exrows
    ]
    if not exclusiones:
        exclusiones = _exclusiones_from_snapshot(await _load_alcance_snapshot(db, project_id))

    # ── activos esenciales (m02 MAGERIT · best-effort · degrada a []) ──
    activos_esenciales: list[dict[str, Any]] = []
    try:
        arows = (await db.execute(sa_text(
            "SELECT a.nombre, a.asset_type_code "
            "FROM magerit_assets a JOIN magerit_analysis ma ON ma.id = a.analysis_id "
            "WHERE ma.project_id = :pid AND COALESCE(a.es_esencial, false) = true "
            "ORDER BY a.nombre"
        ), {"pid": str(project_id)})).mappings().all()
        activos_esenciales = [
            {"nombre": r["nombre"], "tipo": r["asset_type_code"] or "—"}
            for r in arows
        ]
    except Exception:
        logger.debug("E-155 activos esenciales best-effort fallo", exc_info=True)

    # ── responsables ENS (m30 client_contacts · role_category canónico) ──
    responsables: dict[str, dict[str, str]] = {}
    organo = "Órgano de gobierno superior"
    representante = ""
    try:
        crows = (await db.execute(sa_text(
            "SELECT full_name, COALESCE(role_category,'') AS rc, "
            "  COALESCE(role_title,'') AS pos "
            "FROM client_contacts "
            "WHERE client_id = :cid AND is_active = true AND deleted_at IS NULL"
        ), {"cid": str(client_id)})).mappings().all()
        for c in crows:
            rc = (c["rc"] or "").lower()
            name = c["full_name"] or "—"
            if rc in _ROLE_KEYS and rc not in responsables:
                responsables[rc] = {"nombre": name, "cargo": c["pos"] or "—"}
            blob = f"{rc} {c['pos']}".lower()
            if c["full_name"] and ("sponsor" in blob or "direcc" in blob
                                   or "gobierno" in blob or "comit" in blob):
                organo = str(c["full_name"])
                representante = representante or str(c["full_name"])
    except Exception:
        logger.debug("E-155 responsables best-effort fallo", exc_info=True)

    servicio_principal = (
        next((s["nombre"] for s in servicios
              if s.get("tipo") == "finalista"), None)
        or (servicios[0]["nombre"] if servicios else None)
        or (str(frontera) if frontera else None)
        or "Servicio prestado a la Administración Pública objeto de la adecuación ENS"
    )

    return {
        "cliente": {
            "razon_social": razon_social,
            "nif": cif or "",
            "domicilio_social": domicilio or "",
            "representante_legal": representante,
            "organo_aprobador_politicas": organo,
        },
        "proyecto": {
            "categoria_ens": categoria,
            "servicio_principal": servicio_principal,
            "version_actual": "1.0",
            "nombre_sistema": system_nombre,
            "fecha_aprobacion_inicial": fecha_aprobacion or "",
        },
        "sistema": {"nombre": system_nombre},
        "responsables": responsables,
        "categorizacion": {
            "dimensiones": dimensiones,
            "nivel_global": categoria,
        },
        "alcance": {
            "servicios": servicios,
            "sistemas": sistemas,
            "sedes": sedes,
            "activos_esenciales": activos_esenciales,
            "exclusiones": exclusiones,
        },
    }


def _max_categoria(dimensiones: dict[str, str]) -> str | None:
    """Deriva BASICA/MEDIA/ALTA del máximo de las dimensiones (fallback)."""
    rank = max((_LEVEL_RANK.get(v, 0) for v in dimensiones.values()), default=0)
    return {1: "BASICA", 2: "MEDIA", 3: "ALTA"}.get(rank)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return value.date().isoformat()
    except AttributeError:
        try:
            return value.isoformat()
        except AttributeError:
            return str(value)


async def _load_alcance_snapshot(db: AsyncSession, project_id: uuid.UUID) -> dict:
    try:
        snap = (await db.execute(sa_text(
            "SELECT alcance_snapshot FROM contracts "
            "WHERE project_id = :pid AND alcance_snapshot IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"pid": str(project_id)})).scalar()
        if isinstance(snap, str):
            snap = json.loads(snap)
        return snap or {}
    except Exception:
        logger.debug("E-155 alcance_snapshot best-effort fallo", exc_info=True)
        return {}


def _exclusiones_from_snapshot(snap: dict) -> list[dict[str, Any]]:
    out = []
    for e in (snap.get("exclusiones") or []):
        if isinstance(e, dict):
            out.append({
                "elemento": e.get("elemento") or e.get("nombre") or str(e),
                "justificacion": e.get("justificacion"),
            })
        else:
            out.append({"elemento": str(e), "justificacion": None})
    return out
