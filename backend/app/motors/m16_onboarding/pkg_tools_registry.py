"""Registry of PKG tools with Anthropic tool-use format metadata.

M11 Copiloto discovers tools via list_tools() and invokes via call_tool().
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from . import pkg_tools

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "pkg_project_summary",
        "description": "Resumen completo del Project Knowledge Graph: total nodos y aristas agrupados por tipo.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string", "description": "UUID del proyecto"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_project_summary,
    },
    {
        "name": "pkg_count_assets_by_type",
        "description": "Cuenta activos tecnicos agrupados por subtipo (endpoint, server, repository, cloud_provider).",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_count_assets_by_type,
    },
    {
        "name": "pkg_count_identities_by_type",
        "description": "Cuenta identidades digitales agrupadas por tipo (user, group, service_account).",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_count_identities_by_type,
    },
    {
        "name": "pkg_get_mfa_coverage",
        "description": "Porcentaje de usuarios con MFA habilitado. CRITICO para ENS op.acc.6 R2 (100% requerido).",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_get_mfa_coverage,
    },
    {
        "name": "pkg_list_systems",
        "description": "Sistemas de informacion del proyecto con categoria ENS y criticidad. Sin datos personales.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_list_systems,
    },
    {
        "name": "pkg_list_providers",
        "description": "Proveedores externos del proyecto. Relevante para op.ext.* del ENS.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_list_providers,
    },
    {
        "name": "pkg_get_stakeholder_roles",
        "description": "Roles ENS obligatorios asignados vs pendientes (sponsor, RSEG, RSI, RI, DPO). Sin nombres.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_get_stakeholder_roles,
    },
    {
        "name": "pkg_get_critical_dependencies",
        "description": "Cadenas de dependencia (depends_on) entre sistemas y activos.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_get_critical_dependencies,
    },
    {
        "name": "pkg_count_processes",
        "description": "Procesos de negocio inventariados del cliente.",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_count_processes,
    },
    {
        "name": "pkg_get_onboarding_completion",
        "description": "Estado de completitud de onboarding sessions (completadas, en progreso, pendientes).",
        "input_schema": {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
        "function": pkg_tools.pkg_get_onboarding_completion,
    },
]


def list_tools() -> list[dict]:
    """Return tools without the function (for serialization)."""
    return [{"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]} for t in TOOL_DEFINITIONS]


def get_tool(name: str) -> Optional[dict]:
    for t in TOOL_DEFINITIONS:
        if t["name"] == name:
            return t
    return None


async def call_tool(name: str, args: dict, session: AsyncSession) -> dict:
    """Invoke a tool by name. Returns serializable dict."""
    tool = get_tool(name)
    if tool is None:
        raise ValueError(f"Tool {name} no existe. Disponibles: {[t['name'] for t in TOOL_DEFINITIONS]}")
    if "project_id" in args:
        args["project_id"] = uuid.UUID(args["project_id"])
    return await tool["function"](session, **args)
