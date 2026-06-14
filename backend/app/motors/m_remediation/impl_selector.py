"""Selector de implantación · m_remediation (ADR-055).

Dado el INVENTARIO del cliente (proveedores cloud + hosts/SO) y un conjunto de
medidas ENS a cerrar, SELECCIONA de forma DETERMINISTA (R1 · sin LLM en la
decisión) qué plantillas verificadas aplican y construye un PLAN DRY-RUN para
previsualizar antes de ejecutar. NUNCA genera pasos: solo elige plantillas del
catálogo y las parametriza desde el inventario + defaults.

El LLM (opcional · `suggest_params`) solo PROPONE valores para parámetros de
texto libre que no estén en el inventario (p.ej. ruta del repo de backup); el
humano los aprueba en el dry-run. La plantilla ejecutada nunca la escribe el LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.motors.m_remediation.catalog import ACTION_CATALOG
from backend.app.motors.m_remediation.host_playbooks import HOST_PLAYBOOKS
from backend.app.motors.m_remediation.impl_coverage import (
    implementation_templates_for_measure,
)


@dataclass
class ClientInventory:
    """Inventario mínimo para seleccionar plantillas (lo rellena el diagnóstico
    /onboarding · NO el LLM). providers: aws·microsoft_365·azure·google_workspace.
    host_os_families: linux·windows."""
    providers: tuple[str, ...] = ()
    host_os_families: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanStep:
    action_type: str
    platform: str
    tier: str
    title: str
    ens_measures: list[str]
    params: dict[str, Any]
    missing_required_params: list[str]
    requires_approval: bool
    dry_run_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "platform": self.platform,
            "tier": self.tier,
            "title": self.title,
            "ens_measures": self.ens_measures,
            "params": self.params,
            "missing_required_params": self.missing_required_params,
            "requires_approval": self.requires_approval,
            "dry_run_summary": self.dry_run_summary,
        }


def _platform_matches_inventory(platform: str, inv: ClientInventory) -> bool:
    if platform.startswith("cloud:"):
        return platform.split(":", 1)[1] in inv.providers
    if platform == "host":
        # host genérico aplica si hay al menos un host; el filtrado fino por SO
        # se hace al construir params (os_families del playbook).
        return bool(inv.host_os_families)
    return False


def _host_os_ok(action_type: str, inv: ClientInventory) -> bool:
    pb = HOST_PLAYBOOKS.get(action_type)
    if pb is None:
        return True
    return any(os in pb.os_families for os in inv.host_os_families)


def _resolve_params(action_type: str, inv: ClientInventory) -> tuple[dict, list[str]]:
    """Rellena params desde inventory + defaults · lista los required que faltan."""
    pb = HOST_PLAYBOOKS.get(action_type)
    if pb is None:
        return dict(inv.params.get(action_type, {})), []
    out: dict[str, Any] = {}
    missing: list[str] = []
    overrides = inv.params.get(action_type, {})
    for name, schema in pb.params_schema.items():
        if name in overrides:
            out[name] = overrides[name]
        elif "default" in schema:
            out[name] = schema["default"]
        elif schema.get("required"):
            missing.append(name)
    return out, missing


def build_dry_run_plan(
    measures: list[str],
    inventory: ClientInventory,
) -> list[PlanStep]:
    """Plan DRY-RUN determinista: plantillas que aplican al inventario para cerrar
    las medidas dadas. Sin ejecutar. requires_approval=True siempre (decisión
    Marcos: nada se toca sin un clic humano)."""
    steps: list[PlanStep] = []
    seen: set[str] = set()
    for measure in measures:
        for tpl in implementation_templates_for_measure(measure):
            action_type = tpl["action_type"]
            if action_type in seen:
                continue
            platform = tpl["platform"]
            if not _platform_matches_inventory(platform, inventory):
                continue
            if platform == "host" and not _host_os_ok(action_type, inventory):
                continue
            spec = ACTION_CATALOG[action_type]
            params, missing = _resolve_params(action_type, inventory)
            pb = HOST_PLAYBOOKS.get(action_type)
            dry = pb.dry_run_summary if pb else (
                f"Aplica '{spec.title_es}' sobre {platform} (cloud writer · "
                "preflight→snapshot→apply→verify→rollback)."
            )
            seen.add(action_type)
            steps.append(PlanStep(
                action_type=action_type,
                platform=platform,
                tier=spec.tier.value,
                title=spec.title_es,
                ens_measures=list(spec.ens_measures),
                params=params,
                missing_required_params=missing,
                requires_approval=True,
                dry_run_summary=dry,
            ))
    return steps
