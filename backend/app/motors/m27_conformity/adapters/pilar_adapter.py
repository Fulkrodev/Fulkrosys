"""PILAR adapter — export AR en formato compatible PILAR (.mgr XML).

Genera un XML con la estructura de analisis de riesgos MAGERIT v3 que
PILAR puede importar. Marcos descarga y sube manualmente a PILAR.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_mgr_file(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Genera contenido XML formato PILAR (.mgr) desde M2 MAGERIT + M1.

    Returns dict con:
      tool, artifact_content (bytes XML), artifact_hash, checklist.
    """
    root = Element("PilarImport", {
        "version": "3.0",
        "generator": "FULKRO-M27",
        "project_id": str(project_id),
    })
    meta = SubElement(root, "Metadata")
    SubElement(meta, "GeneratedAt").text = (
        datetime.now(timezone.utc).isoformat()
    )

    # Proyecto + cliente
    await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
    try:
        proj_row = (await db.execute(sa_text(
            "SELECT p.id, p.nombre, p.categoria_objetivo, c.nombre AS cli "
            "FROM projects p JOIN clients c ON p.client_id = c.id "
            "WHERE p.id = :pid"
        ), {"pid": str(project_id)})).first()
        if proj_row:
            proj = SubElement(root, "Proyecto")
            SubElement(proj, "Nombre").text = proj_row.nombre or ""
            SubElement(proj, "Cliente").text = proj_row.cli or ""
            SubElement(proj, "Categoria").text = proj_row.categoria_objetivo or "BASICA"

        # Activos desde systems + service + information_types
        systems = (await db.execute(sa_text(
            "SELECT id::text, nombre, descripcion FROM systems "
            "WHERE project_id = :pid"
        ), {"pid": str(project_id)})).all()
        activos = SubElement(root, "Activos")
        for sys_row in systems:
            act = SubElement(activos, "Activo", {"id": sys_row.id})
            SubElement(act, "Nombre").text = sys_row.nombre or ""
            SubElement(act, "Descripcion").text = sys_row.descripcion or ""
            SubElement(act, "Tipo").text = "S"  # Servicio

            # Valoracion DICAT desde categorizations
            cat_row = (await db.execute(sa_text(
                "SELECT valoracion_d FROM information_types "
                "WHERE system_id = :sid LIMIT 1"
            ), {"sid": sys_row.id})).first()
            val = SubElement(act, "Valoracion")
            if cat_row:
                for dim, code in (("D", "d"), ("I", "i"), ("C", "c"),
                                  ("A", "a"), ("T", "t")):
                    v = getattr(cat_row, f"valoracion_{code}", None)
                    SubElement(val, dim).text = v or "BAJO"

        # Amenazas desde magerit_analyses si existen (savepoint para tolerar
        # tabla ausente o esquema diferente sin abortar la transaccion).
        amenazas = SubElement(root, "Amenazas")
        sp = await db.begin_nested()
        threats = []
        try:
            threats = (await db.execute(sa_text(
                "SELECT id::text, threat_code, descripcion FROM magerit_threats "
                "WHERE analysis_id IN (SELECT id FROM magerit_analyses "
                "WHERE project_id = :pid)"
            ), {"pid": str(project_id)})).all()
            await sp.commit()
        except Exception:  # pragma: no cover
            await sp.rollback()
            SubElement(amenazas, "Note").text = "MAGERIT aun no analizado"
        for th in threats:
            am = SubElement(amenazas, "Amenaza", {"codigo": th.threat_code or ""})
            SubElement(am, "Descripcion").text = th.descripcion or ""
    finally:
        await db.execute(sa_text("RESET ROLE"))

    xml_bytes = tostring(root, encoding="utf-8", xml_declaration=True)
    artifact_hash = hashlib.sha256(xml_bytes).hexdigest()
    return {
        "tool": "PILAR",
        "project_id": project_id,
        "artifact_path": (
            f"exports/pilar/{project_id}/ar_{artifact_hash[:8]}.mgr.xml"
        ),
        "artifact_content": xml_bytes,
        "artifact_hash": artifact_hash,
        "checklist": [
            "Abrir PILAR escritorio en version validada",
            "Menu Archivo -> Importar analisis...",
            "Seleccionar el fichero .mgr.xml descargado",
            "Verificar que los activos coinciden con el inventario M2",
            "Verificar valoraciones DICAT por activo",
            "Ajustar probabilidades y amenazas segun criterio profesional",
            "Adjuntar captura de la importacion exitosa como proof",
        ],
    }


def export(project_id: uuid.UUID, params: dict) -> dict:
    """Stub sincrono (para tests offline y compatibilidad con api.py v1).

    Para la generacion real usar ``generate_mgr_file(db, project_id)``.
    """
    import hashlib, json
    payload = {
        "project_id": str(project_id),
        "version": params.get("version", "v1"),
        "ar_summary": "MAGERIT v3 risk analysis export (sync stub)",
        "magerit_version": "3.0",
    }
    body = json.dumps(payload, sort_keys=True).encode()
    artifact_hash = hashlib.sha256(body).hexdigest()
    return {
        "tool": "PILAR",
        "project_id": project_id,
        "artifact_path": (
            f"exports/pilar/{project_id}/ar_{artifact_hash[:8]}.xml"
        ),
        "artifact_hash": artifact_hash,
        "checklist": [
            "Abrir PILAR escritorio en version validada",
            "Importar el fichero XML",
            "Verificar que los activos coinciden con el inventario M2",
            "Verificar que las amenazas seleccionadas son las esperadas",
            "Adjuntar captura de la importacion como proof",
        ],
    }
