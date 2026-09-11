"""Builder de contexto para E-012 · Acta de Categorización + DdA (R03-wiring).

Canonicaliza la generación del acta E-012. Antes los endpoints m01 renderizaban
``acta_e012_provisional.docx`` (variante B · firmantes incorrectos: Presidente +
RSI en lugar de la DOBLE FIRMA COMPETENTE del art. 40.2 RD 311/2022: Responsable
de la Información + Responsable del Servicio aprueban; el Responsable de Seguridad
suscribe conformidad). Aquí se construye el contexto para la plantilla m06
canónica (``E012_...md``, ya corregida con la doble firma) desde el dominio m01.

Contrato (verificado leyendo la plantilla):
- ``cliente.{razon_social,poblacion}``
- ``proyecto.{categoria_ens,version_actual,fecha_aprobacion_inicial}``
- ``decision_categorizacion.{nivel_global,fecha_decision,dimensiones{C,I,D,A,T},
  metodologia}``
- ``responsables.{responsable_informacion,_servicio,_seguridad}.{nombre,cargo}``

Reusa los helpers DICAT + responsables de ``alcance_generator`` (OPS-026 DRY).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from .alcance_generator import _ROLE_KEYS, _iso, _max_categoria, _max_level
from backend.app.motors.m06_document_factory.errores import (
    CategoriaNoDeterminadaError,
)
from backend.app.motors.m01_categorization.aplicabilidad import NO_AFECTADA

# Lo que se imprime en el acta para una dimension sin adscribir (Anexo I p.3).
_ETIQUETA_NO_AFECTADA = "No afectada"

logger = logging.getLogger(__name__)

_DIM_COLS = ("valoracion_c", "valoracion_i", "valoracion_d", "valoracion_a", "valoracion_t")
_DIM_KEYS = ("confidencialidad", "integridad", "disponibilidad", "autenticidad", "trazabilidad")


class E012ContextError(Exception):
    """El sistema no existe o no está categorizado · no se puede emitir el acta."""


async def build_e012_context(
    db: AsyncSession,
    system_id: uuid.UUID,
) -> tuple[dict[str, Any], uuid.UUID]:
    """Construye el contexto m06 del acta E-012 + devuelve el ``project_id``.

    Lanza ``E012ContextError`` si el sistema no existe.
    """
    row = (await db.execute(sa_text(
        "SELECT s.nombre, s.project_id, p.client_id, "
        "  COALESCE(c.nombre, 'Cliente') AS razon_social, c.cif, c.domicilio_fiscal "
        "FROM systems s JOIN projects p ON p.id = s.project_id "
        "LEFT JOIN clients c ON c.id = p.client_id "
        "WHERE s.id = :sid AND s.deleted_at IS NULL"
    ), {"sid": str(system_id)})).first()
    if row is None:
        raise E012ContextError(f"System {system_id} no existe · no se puede emitir el acta E-012")
    project_id = row[1]
    client_id = row[2]
    razon_social = str(row[3])

    # ── categorización (nivel + fecha) ──
    cat = (await db.execute(sa_text(
        "SELECT categoria_resultante, fecha_acta, aprobado_por "
        "FROM categorizations WHERE system_id = :sid AND deleted_at IS NULL "
        "ORDER BY version DESC NULLS LAST, created_at DESC LIMIT 1"
    ), {"sid": str(system_id)})).first()
    nivel = (str(cat[0]).upper() if cat and cat[0] else None)
    fecha = (_iso(cat[1]) if cat else None) or ""

    # ── dimensiones DICAT reales (máximo sobre servicios + tipos de info) ──
    srows = (await db.execute(sa_text(
        f"SELECT {', '.join(_DIM_COLS)} FROM services "
        "WHERE system_id = :sid AND deleted_at IS NULL"
    ), {"sid": str(system_id)})).all()
    itrows = (await db.execute(sa_text(
        f"SELECT {', '.join(_DIM_COLS)} FROM information_types "
        "WHERE system_id = :sid AND deleted_at IS NULL"
    ), {"sid": str(system_id)})).all()
    # O2 · una dimension no afectada se NOMBRA, no se calla. Antes esto era
    # el maximo cayendo a cadena vacia, y esa cadena disparaba el `else 'MEDIO'` de
    # la plantilla: el acta salia firmada declarando MEDIO una dimension que
    # nadie habia valorado. El Anexo I punto 3 dice que una dimension no
    # afectada NO se adscribe a ningun nivel, asi que el acta dice eso.
    dims_crudas: dict[str, str] = {}
    for i, key in enumerate(_DIM_KEYS):
        vals = [r[i] for r in srows] + [r[i] for r in itrows]
        dims_crudas[key] = _max_level(vals) or NO_AFECTADA
    dimensiones: dict[str, str] = {
        k: (_ETIQUETA_NO_AFECTADA if v == NO_AFECTADA else v)
        for k, v in dims_crudas.items()
    }
    if not nivel:
        # O1 · sin categoria NO se rellena con "BASICA": el acta E-012 es
        # justo el documento que DECLARA la categoria; inventarla aqui es
        # declarar por debajo en un acta firmada.
        nivel = _max_categoria(dims_crudas)
        if not nivel:
            raise CategoriaNoDeterminadaError("el acta de categorizacion E-012")

    # ── responsables ENS (m30 client_contacts · role_category canónico) ──
    responsables: dict[str, dict[str, str]] = {}
    try:
        crows = (await db.execute(sa_text(
            "SELECT full_name, COALESCE(role_category,'') AS rc, "
            "  COALESCE(role_title,'') AS pos FROM client_contacts "
            "WHERE client_id = :cid AND is_active = true AND deleted_at IS NULL"
        ), {"cid": str(client_id)})).mappings().all()
        for c in crows:
            rc = (c["rc"] or "").lower()
            if rc in _ROLE_KEYS and rc not in responsables:
                responsables[rc] = {"nombre": c["full_name"] or "—", "cargo": c["pos"] or "—"}
    except Exception:
        logger.debug("E-012 responsables best-effort fallo", exc_info=True)

    ctx = {
        "cliente": {"razon_social": razon_social, "poblacion": None},
        "proyecto": {
            "categoria_ens": nivel,
            "version_actual": "1.0",
            "fecha_aprobacion_inicial": fecha,
        },
        "decision_categorizacion": {
            "nivel_global": nivel,
            "fecha_decision": fecha,
            "dimensiones": dimensiones,
            "metodologia": "RD 311/2022 Anexo I + CCN-STIC 803",
        },
        "responsables": responsables,
    }
    return ctx, project_id
