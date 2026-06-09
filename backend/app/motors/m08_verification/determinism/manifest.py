"""Run manifest hash + golden runs (doc §11 · determinismo demostrable).

`run_manifest_hash = sha256(canonical_json({
    scope_snapshot, tool_versions, template_versions, config,
    model_version, target_snapshot_ref
}))`

Clave de reproducibilidad: ante el auditor, la MISMA entrada produce el
MISMO hash. Un *golden run* es un run de referencia versionado; re-ejecutar
y comparar el manifest_hash detecta drift no intencionado (en herramientas,
templates o el propio pipeline). Cualquier variación del manifest exige
explicación (doc §11).

Puro y determinista (canonical JSON · sort_keys · sin timestamps/randoms).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _canonical_json(obj: Any) -> str:
    """JSON canónico determinista: claves ordenadas, sin espacios variables."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


@dataclass
class RunManifest:
    """Manifest reproducible de un run de verificación (doc §11)."""
    scope_snapshot: dict[str, Any]
    tool_versions: dict[str, str] = field(default_factory=dict)
    template_versions: dict[str, str] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    model_version: str | None = None
    target_snapshot_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        # Solo los campos que definen el determinismo (excluye nada volátil).
        return {
            "scope_snapshot": self.scope_snapshot,
            "tool_versions": self.tool_versions,
            "template_versions": self.template_versions,
            "config": self.config,
            "model_version": self.model_version,
            "target_snapshot_ref": self.target_snapshot_ref,
        }

    def compute_hash(self) -> str:
        return hashlib.sha256(
            _canonical_json(self.to_dict()).encode("utf-8")
        ).hexdigest()


def compute_run_manifest_hash(manifest: dict[str, Any]) -> str:
    """SHA-256 del manifest canónico (acepta dict plano)."""
    keys = (
        "scope_snapshot", "tool_versions", "template_versions",
        "config", "model_version", "target_snapshot_ref",
    )
    canonical = {k: manifest.get(k) for k in keys}
    return hashlib.sha256(
        _canonical_json(canonical).encode("utf-8")
    ).hexdigest()


def build_run_manifest(
    *,
    scope: dict[str, Any],
    tool_versions: dict[str, str] | None = None,
    template_versions: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
    model_version: str | None = None,
    target_snapshot_ref: str | None = None,
) -> tuple[RunManifest, str]:
    """Construye el manifest + su hash. El scope se normaliza (excluye
    contadores derivados volátiles que no afectan al determinismo)."""
    scope_snapshot = {
        k: v for k, v in (scope or {}).items()
        if k not in ("totals",)  # 'totals' es derivado · no parte del input
    }
    m = RunManifest(
        scope_snapshot=scope_snapshot,
        tool_versions=tool_versions or {},
        template_versions=template_versions or {},
        config=config or {},
        model_version=model_version,
        target_snapshot_ref=target_snapshot_ref,
    )
    return m, m.compute_hash()


def compare_to_golden(
    current_hash: str,
    golden_hash: str | None,
    *,
    current_manifest: dict[str, Any] | None = None,
    golden_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compara el manifest actual contra el golden run.

    Devuelve {match, drift_fields}. Si match=False, drift_fields lista qué
    secciones del manifest cambiaron (para la explicación obligatoria §11).
    """
    if golden_hash is None:
        return {"match": None, "reason": "no_golden", "drift_fields": []}
    if current_hash == golden_hash:
        return {"match": True, "drift_fields": []}
    drift_fields: list[str] = []
    if current_manifest is not None and golden_manifest is not None:
        for key in (
            "scope_snapshot", "tool_versions", "template_versions",
            "config", "model_version", "target_snapshot_ref",
        ):
            if current_manifest.get(key) != golden_manifest.get(key):
                drift_fields.append(key)
    return {
        "match": False,
        "reason": "manifest_drift",
        "drift_fields": drift_fields,
    }
