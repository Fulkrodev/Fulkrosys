"""Registry adapter — formal submission to ENS registry / certification body."""
from __future__ import annotations

import hashlib
import json
import uuid


def export(project_id: uuid.UUID, params: dict) -> dict:
    """Descriptor de presentación al registro ENS (formulario + checklist).

    S10 fix: antes devolvía un ``artifact_path`` a un ``.zip`` que NINGÚN código
    generaba (referencia a un fichero inexistente que el admin "descargaba"). El
    paquete real de presentación es el DOSSIER FIRMADO de m09
    (POST /audit-prep/projects/{id}/dossier/generate-signed-zip), que el admin
    descarga y sube al registro. Este adapter produce solo el descriptor + el
    checklist; ``artifact_path`` es None (no se fabrica un ZIP fantasma) y
    ``artifact_source`` apunta al artefacto real.
    """
    payload = {
        "project_id": str(project_id),
        "registry_target": params.get("target", "REGISTRO_ENS"),
        "form_id": params.get("form_id", "F-001"),
        "annexes": params.get("annexes", []),
    }
    body = json.dumps(payload, sort_keys=True).encode()
    artifact_hash = hashlib.sha256(body).hexdigest()
    return {
        "tool": "Registro",
        "project_id": project_id,
        "artifact_path": None,
        "artifact_source": "m09_signed_dossier_zip",
        "artifact_hash": artifact_hash,
        "checklist": [
            "Generar/descargar el dossier firmado (m09 · dossier/generate-signed-zip)",
            "Acceder al registro electronico correspondiente",
            "Subir el dossier firmado con certificado digital",
            "Guardar el justificante de presentacion (CSV / PDF firmado)",
            "Adjuntar el justificante como proof",
        ],
    }
