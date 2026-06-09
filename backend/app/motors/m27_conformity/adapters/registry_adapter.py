"""Registry adapter — formal submission to ENS registry / certification body."""
from __future__ import annotations

import hashlib
import json
import uuid


def export(project_id: uuid.UUID, params: dict) -> dict:
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
        "artifact_path": f"exports/registry/{project_id}/submission_{artifact_hash[:8]}.zip",
        "artifact_hash": artifact_hash,
        "checklist": [
            "Verificar que el ZIP contiene formularios y anexos requeridos",
            "Acceder al registro electronico correspondiente",
            "Subir el ZIP firmado con certificado digital",
            "Guardar el justificante de presentacion (CSV / PDF firmado)",
            "Adjuntar el justificante como proof",
        ],
    }
