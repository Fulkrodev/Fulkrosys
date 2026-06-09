"""#10 B2 · borrador automático del Documento de Alcance SGSI (E-155) post-SIGNED.

Al firmar el contrato (o provisionar por wizard) se intenta generar un BORRADOR
de E-155 derivado del contexto disponible (Client + categoría + System.frontera).
El borrador queda 'PENDIENTE REVISIÓN CONSULTOR' (frontmatter del template) ·
Marcos lo edita · la aprobación del cliente es #27 (fuera de la Ola 2).

BEST-EFFORT: si la generación falla (catálogo de templates sin seedear, gate de
workflow, fichero DOCX ausente, etc.) NO rompe la conversión — se omite y se
loguea. El alcance COMERCIAL del contrato (§1) es otra cosa y vive en
``Contract.alcance_snapshot`` (#10 B1).

NOTA DE VERIFICACIÓN (honestidad): la tabla ``templates`` está vacía en
``fulkro_test`` (y el seed de templates es una tarea de infra aparte), por lo que
el render real del E-155 NO se verifica end-to-end en test. Aquí se prueba el
contexto (forma) + la GARANTÍA de no-ruptura (la conversión sigue verde aunque el
borrador se omita). Cuando el catálogo esté seedeado, el borrador se generará.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def build_e155_draft_context(
    *,
    client_nombre: str | None,
    client_cif: str | None,
    client_domicilio: str | None,
    categoria: str | None,
    system_frontera: str | None,
    alcance_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Contexto BORRADOR para E-155 con los datos disponibles al firmar.

    Las claves de alcance van bajo ``alcance.*``, ALINEADAS con cómo el .md ya
    estructura el resto (``cliente.*`` / ``proyecto.*`` / ``responsables.*``).
    El ``alcance_snapshot`` comercial congelado del contrato (#10 B1) se VUELCA
    aquí: exclusiones REALES por nombre + nº de sistemas/ubicaciones. El detalle
    nominal (nombres de sistemas/sedes, responsables, dimensiones, firmas) lo
    completa Marcos en la revisión (el template tolera los huecos con
    fallbacks ``else '—'``)."""
    snap = alcance_snapshot or {}
    cat = categoria or snap.get("categoria")
    servicio_principal = (
        system_frontera
        or "Servicio prestado a la Administración Pública objeto de la "
        "adecuación ENS"
    )

    # alcance.* · misma estructura que las secciones 3 y 4 del .md.
    alcance: dict[str, Any] = {
        "servicios": [{"nombre": servicio_principal}],
        # Los activos esenciales se materializan tras el inventario MAGERIT.
        "activos_esenciales": [],
    }
    n_sistemas = snap.get("sistemas")
    if n_sistemas:
        alcance["sistemas"] = [{
            "nombre": (
                f"{n_sistemas} sistema(s) de información en el alcance "
                "(inventario nominal a detallar en la revisión del consultor)"
            )
        }]
    n_ubicaciones = snap.get("ubicaciones")
    if n_ubicaciones:
        alcance["sedes"] = [{
            "nombre": (
                f"{n_ubicaciones} ubicación(es)/sede(s) en el alcance "
                "(a confirmar en la revisión del consultor)"
            )
        }]
    # Las exclusiones SÍ vienen nombradas en el snapshot → se vuelcan reales.
    exclusiones = snap.get("exclusiones") or []
    alcance["exclusiones"] = [
        e if isinstance(e, dict) else {"elemento": str(e)} for e in exclusiones
    ]

    return {
        "cliente": {
            "razon_social": client_nombre or "Cliente",
            "nif": client_cif or "",
            "domicilio_social": client_domicilio or "",
        },
        "proyecto": {
            "categoria_ens": cat,
            "servicio_principal": servicio_principal,
            "version_actual": "1.0",
        },
        "categorizacion": {"nivel_global": cat},
        "dims": {},
        "responsables": {},
        "firmas": {},
        "consultor": {"footer_text": "Fulkro"},
        "alcance": alcance,
    }


async def generate_e155_draft_best_effort(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    generated_by: str = "system",
) -> bool:
    """Genera el borrador E-155 post-SIGNED. Devuelve True si se generó, False si
    se omitió. NUNCA propaga excepción al caller (best-effort vía SAVEPOINT)."""
    try:
        row = (await db.execute(text(
            "SELECT c.nombre, c.cif, c.domicilio_fiscal, p.categoria_objetivo "
            "FROM projects p JOIN clients c ON c.id = p.client_id "
            "WHERE p.id = :pid"
        ), {"pid": str(project_id)})).first()
        if row is None:
            return False
        frontera = (await db.execute(text(
            "SELECT frontera FROM systems WHERE project_id = :pid "
            "ORDER BY created_at ASC LIMIT 1"
        ), {"pid": str(project_id)})).scalar()
        # #10 B1 → B2 · vuelca el alcance comercial congelado del contrato
        # (sistemas/ubicaciones/exclusiones) en el borrador, en vez de fallbacks.
        snap = (await db.execute(text(
            "SELECT alcance_snapshot FROM contracts "
            "WHERE project_id = :pid AND alcance_snapshot IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ), {"pid": str(project_id)})).scalar()
        if isinstance(snap, str):
            import json
            snap = json.loads(snap)

        ctx = build_e155_draft_context(
            client_nombre=row[0], client_cif=row[1], client_domicilio=row[2],
            categoria=row[3], system_frontera=frontera,
            alcance_snapshot=snap,
        )

        from backend.app.motors.m06_document_factory.service import (
            DocumentFactoryService,
        )
        # SAVEPOINT: un fallo del render/persist NO aborta la transacción de la
        # conversión (que commitea después).
        async with db.begin_nested():
            await DocumentFactoryService(db).generate_document(
                project_id=project_id,
                template_codigo="E-155",
                context=ctx,
                generate_pdf=False,
                sign=False,          # borrador · no se sella aún
                enforce_gates=False,  # al firmar aún no hay DdA congelada
                generated_by=generated_by,
            )
        return True
    except Exception:
        logger.warning(
            "#10 B2 · borrador E-155 omitido (best-effort) · project %s",
            project_id, exc_info=True,
        )
        return False
