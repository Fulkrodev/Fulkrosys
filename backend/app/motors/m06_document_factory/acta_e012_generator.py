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

# Codigo de la plantilla del acta en el catalogo (tabla `templates`).
_CODIGO_ACTA = "E-012"

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
    # O2 · el NIF y el domicilio se leian de la base y se tiraban: el contexto
    # solo llevaba la razon social. El acta es el documento que APRUEBA la
    # categorizacion de una entidad concreta, y la plantilla declara
    # `cliente.nif` como obligatorio -- pero el render suelto del endpoint no
    # pasaba `required_vars`, asi que el acta salia sin identificar fiscalmente
    # a quien la firma y nadie se enteraba.
    nif = (str(row[4]).strip() if row[4] else "") or None
    domicilio = (str(row[5]).strip() if row[5] else "") or None

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
        "cliente": {
            "razon_social": razon_social,
            "nif": nif,
            "poblacion": domicilio,
        },
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


async def generar_o_recuperar_acta_e012(
    db: AsyncSession,
    system_id: uuid.UUID,
) -> tuple[Any, dict[str, Any]]:
    """Devuelve el acta E-012 REGISTRADA del sistema, generandola si falta.

    O2 · EL DEFECTO
        Los endpoints ``GET /systems/{id}/acta-e012.{pdf,docx}`` renderizaban el
        acta en un directorio temporal, la mandaban al navegador y borraban el
        directorio. No quedaba fichero, ni fila en ``documents``, ni hash, ni
        firma. Y el expediente que recibe el auditor del ENAC se arma leyendo
        EXACTAMENTE esa tabla (``m09_audit_prep/dossier_generator._collect_documents``),
        asi que el acta de categorizacion -- el documento fundacional del ciclo,
        el de la doble firma del art. 40.2 -- no viajaba en el expediente.

        Ademas cada descarga volvia a renderizar: dos descargas del "mismo" acta
        daban dos ficheros distintos y ninguno quedaba guardado, de modo que no
        habia forma de decir que bytes firmo el cliente.

    COMO SE ARREGLA SIN DUPLICAR
        No se anyade un segundo camino de registro: se usa el que ya existe.
        ``DocumentFactoryService.generate_document`` renderiza, calcula el hash,
        firma con Ed25519, convierte a PDF, graba la fila en ``documents`` y
        sube una copia durable a MinIO. E-012 ya estaba en el catalogo de
        plantillas. Lo unico que faltaba era llamarlo.

    IDEMPOTENCIA
        La clave es (proyecto, E-012, version de la categorizacion). Un acta
        registra UNA decision de categorizacion; mientras esa decision sea la
        misma, la descarga devuelve el mismo fichero ya grabado. Una
        categorizacion nueva (version distinta) genera su propia acta. No vale
        la huella del render: el DOCX lleva sellos de tiempo dentro del zip y
        dos renders del mismo contenido dan hashes distintos -- comprobado
        contra las dos filas E-808 del demo.
    """
    from pathlib import Path as _Path

    from sqlalchemy import select as _select

    from backend.app.models.documents import Document

    context, project_id = await build_e012_context(db, system_id)

    version = (await db.execute(sa_text(
        "SELECT version FROM categorizations WHERE system_id = :sid "
        "AND deleted_at IS NULL ORDER BY version DESC NULLS LAST, "
        "created_at DESC LIMIT 1"
    ), {"sid": str(system_id)})).scalar()
    # Se guarda DENTRO del contexto para que viaje al `context_snapshot` de la
    # fila y la busqueda de arriba tenga por donde agarrarse.
    context["version_categorizacion"] = str(version) if version is not None else "1"

    existente = (await db.execute(
        _select(Document).where(
            Document.project_id == project_id,
            Document.template_codigo == _CODIGO_ACTA,
            Document.deleted_at.is_(None),
            Document.context_snapshot["version_categorizacion"].astext
            == context["version_categorizacion"],
        ).order_by(Document.generated_at.desc().nulls_last()).limit(1)
    )).scalar_one_or_none()

    if existente is not None:
        rutas = {"pdf_path": existente.pdf_path, "docx_path": existente.docx_path}
        if any(r and _Path(r).exists() for r in rutas.values()):
            return existente, {
                "document_id": existente.id,
                "rendered_hash": existente.rendered_hash,
                "signature_ed25519": existente.signature_ed25519,
                "reutilizado": True,
                **rutas,
            }
        # La fila esta pero el binario no (contenedor recreado). Se regenera:
        # mejor un acta reproducible que un 503 sobre una ruta muerta.

    from backend.app.motors.m06_document_factory.service import (
        DocumentFactoryService,
    )

    resultado = await DocumentFactoryService(db).generate_document(
        project_id=project_id,
        template_codigo=_CODIGO_ACTA,
        context=context,
        generate_pdf=True,
        sign=True,
        generated_by="m01.categorizacion",
        # El acta es la fase 1 del ciclo; la puerta de la DdA congelada es la
        # fase 3. Exigirla aqui invertiria el orden del ciclo ENS: no se puede
        # declarar aplicabilidad antes de haber aprobado la categorizacion.
        enforce_gates=False,
    )
    resultado["reutilizado"] = False
    doc = await db.get(Document, resultado["document_id"])
    return doc, resultado
