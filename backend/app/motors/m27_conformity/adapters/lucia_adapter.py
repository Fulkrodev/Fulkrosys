"""LUCIA adapter — payload for incident notification to CCN-CERT (manual-assisted)."""
from __future__ import annotations

import hashlib
import json
import uuid


def export(project_id: uuid.UUID, params: dict) -> dict:
    payload = {
        "project_id": str(project_id),
        "incident_id": params.get("incident_id"),
        "severity": params.get("severity", "MEDIUM"),
        "timeline": params.get("timeline", []),
    }
    body = json.dumps(payload, sort_keys=True).encode()
    artifact_hash = hashlib.sha256(body).hexdigest()
    return {
        "tool": "LUCIA",
        "project_id": project_id,
        "artifact_path": f"exports/lucia/{project_id}/incident_{artifact_hash[:8]}.json",
        "artifact_hash": artifact_hash,
        "checklist": [
            "Abrir LUCIA y autenticar con certificado",
            "Crear incidente nuevo o continuar el existente",
            "Pegar/adjuntar la cronologia generada",
            "Confirmar clasificacion del incidente",
            "Adjuntar acuse de recibo de LUCIA como proof",
        ],
    }
