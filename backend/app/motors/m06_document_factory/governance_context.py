"""R14 · context builder de gobernanza org.2 (roles art.11 + comité + DPO).

Deriva server-side, desde m30 ``client_contacts`` + el proyecto/cliente, el
contexto de gobernanza que consumen los documentos org.2 (E-002 acta de
nombramiento de roles, E-003 acta de constitución del comité, y el anexo de
roles de E-100 · ver remediación R13). Nunca deja un rol vacío: cae a
``"(pendiente designación)"`` para que el documento sea siempre renderizable y
el auditor vea explícitamente qué falta nombrar.

Diseño: **best-effort, NUNCA lanza**. Se inyecta en el camino caliente de
``DocumentFactoryService.generate_document`` como contexto BASE (el contexto
explícito del caller siempre tiene prioridad vía deep-merge), de forma aditiva
igual que el branding. Si algo falla, devuelve la estructura con fallbacks.

Claves que aporta:
- ``responsables.{responsable_informacion, responsable_servicio,
  responsable_seguridad, responsable_sistema, administrador_seguridad}`` ·
  ``{nombre, cargo}`` (RD 311/2022 art. 11).
- ``comite_seguridad`` · ``{presidente, secretario, miembros[], frecuencia}``.
- ``dpo`` · ``{nombre, cargo}`` (RGPD art. 37-39 · puede no aplicar).
- ``cliente.numero_empleados`` (lo usa el anexo de roles de E-100).
- ``proyecto.proxima_revision`` = fecha de aprobación + 12 meses (revisión
  anual obligatoria · CCN-STIC 808/809).
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

PENDIENTE = "(pendiente designación)"

# RD 311/2022 art. 11 · los 5 roles que documentan E-002 / E-100 (anexo roles).
_ROLES_ART11 = (
    "responsable_informacion",
    "responsable_servicio",
    "responsable_seguridad",
    "responsable_sistema",
    "administrador_seguridad",
)

_ROLE_CARGO = {
    "responsable_informacion": "Responsable de la Información",
    "responsable_servicio": "Responsable del Servicio",
    "responsable_seguridad": "Responsable de la Seguridad",
    "responsable_sistema": "Responsable del Sistema",
    "administrador_seguridad": "Administrador de la Seguridad del Sistema",
}

# role_category (m30) → rol canónico art. 11. Acepta el nombre largo canónico y
# los alias cortos más habituales del catálogo de 14 categorías de m30.
_RC_ALIASES = {
    "rinfo": "responsable_informacion",
    "responsable_info": "responsable_informacion",
    "rserv": "responsable_servicio",
    "rseg": "responsable_seguridad",
    "rsis": "responsable_sistema",
    "admin_seguridad": "administrador_seguridad",
    "administrador_seguridad_sistema": "administrador_seguridad",
}

_DPO_RC = {"dpo", "delegado_proteccion_datos", "delegado", "dpd"}
_SPONSOR_RC = {"sponsor", "direccion", "dirección", "gobierno", "ceo", "patrocinador"}


def _iso(d) -> str | None:
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.date().isoformat() if isinstance(d, datetime) else d.isoformat()
    return str(d)


def _plus_12m(d) -> str | None:
    """Fecha + 12 meses (revisión anual). Maneja 29-feb cayendo a 28."""
    if d is None:
        return None
    base = d.date() if isinstance(d, datetime) else d
    if not isinstance(base, date):
        return None
    try:
        return base.replace(year=base.year + 1).isoformat()
    except ValueError:  # 29-feb -> 28-feb del año siguiente
        return base.replace(year=base.year + 1, day=28).isoformat()


def _empty_governance() -> dict:
    responsables = {
        role: {"nombre": PENDIENTE, "cargo": _ROLE_CARGO[role]}
        for role in _ROLES_ART11
    }
    return {
        "responsables": responsables,
        "comite_seguridad": {
            "presidente": PENDIENTE,
            "secretario": PENDIENTE,
            "miembros": [],
            "frecuencia": "semestral",
        },
        "dpo": {"nombre": PENDIENTE, "cargo": "Delegado de Protección de Datos"},
    }


async def build_governance_context(
    db: AsyncSession, project_id: UUID, *, fecha_aprobacion=None
) -> dict:
    """Construye el contexto de gobernanza org.2. NUNCA lanza."""
    gov = _empty_governance()
    cliente: dict = {}
    proyecto: dict = {}
    try:
        prow = (await db.execute(sa_text(
            "SELECT p.client_id, COALESCE(c.numero_empleados, NULL) AS n_emp "
            "FROM projects p LEFT JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ), {"pid": str(project_id)})).first()
        client_id = prow[0] if prow else None
        if prow and prow[1] is not None:
            cliente["numero_empleados"] = int(prow[1])
    except Exception:
        logger.debug("R14 governance: project/client best-effort fallo", exc_info=True)
        client_id = None

    # responsables + comité + DPO desde m30 client_contacts
    if client_id is not None:
        try:
            crows = (await db.execute(sa_text(
                "SELECT full_name, COALESCE(role_category,'') AS rc, "
                "  COALESCE(role_title,'') AS pos "
                "FROM client_contacts "
                "WHERE client_id = :cid AND is_active = true AND deleted_at IS NULL "
                "ORDER BY created_at ASC"
            ), {"cid": str(client_id)})).mappings().all()
            miembros: list[str] = []
            for c in crows:
                rc = (c["rc"] or "").strip().lower()
                name = (c["full_name"] or "").strip()
                if not name:
                    continue
                role = rc if rc in _ROLES_ART11 else _RC_ALIASES.get(rc)
                if role and gov["responsables"][role]["nombre"] == PENDIENTE:
                    gov["responsables"][role] = {
                        "nombre": name, "cargo": c["pos"] or _ROLE_CARGO[role],
                    }
                if rc in _DPO_RC and gov["dpo"]["nombre"] == PENDIENTE:
                    gov["dpo"] = {"nombre": name, "cargo": c["pos"] or "Delegado de Protección de Datos"}
                if rc in _SPONSOR_RC and gov["comite_seguridad"]["presidente"] == PENDIENTE:
                    gov["comite_seguridad"]["presidente"] = name
                if name not in miembros:
                    miembros.append(name)
            gov["comite_seguridad"]["miembros"] = miembros
            rseg = gov["responsables"]["responsable_seguridad"]["nombre"]
            if rseg != PENDIENTE:
                gov["comite_seguridad"]["secretario"] = rseg
        except Exception:
            logger.debug("R14 governance: client_contacts best-effort fallo", exc_info=True)

    # proxima_revision = fecha_aprobacion + 12m (best-effort)
    fa = fecha_aprobacion
    if fa is None:
        try:
            cat = (await db.execute(sa_text(
                "SELECT c.fecha_acta FROM categorizations c "
                "JOIN systems s ON s.id = c.system_id "
                "WHERE s.project_id = :pid AND c.deleted_at IS NULL "
                "ORDER BY c.created_at DESC LIMIT 1"
            ), {"pid": str(project_id)})).first()
            if cat and cat[0]:
                fa = cat[0]
        except Exception:
            logger.debug("R14 governance: fecha_acta best-effort fallo", exc_info=True)
    fa = fa or date.today()
    prox = _plus_12m(fa)
    if prox:
        proyecto["proxima_revision"] = prox
        proyecto.setdefault("fecha_aprobacion_inicial", _iso(fa))

    out: dict = dict(gov)
    if cliente:
        out["cliente"] = cliente
    if proyecto:
        out["proyecto"] = proyecto
    return out


def merge_governance_base(base: dict, caller: dict) -> dict:
    """Deep-merge de 1 nivel: ``base`` (gobernanza) rellena huecos; ``caller``
    (contexto explícito) SIEMPRE gana por clave. Para los dicts de nivel
    superior (cliente/proyecto/responsables/comite_seguridad) se fusionan sus
    sub-claves en vez de reemplazar el dict entero (evita perder
    numero_empleados/proxima_revision cuando el caller ya trae cliente/proyecto).
    """
    merged = dict(base)
    for k, v in caller.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            sub = dict(merged[k])
            sub.update(v)  # caller sub-claves ganan
            merged[k] = sub
        else:
            merged[k] = v
    return merged
