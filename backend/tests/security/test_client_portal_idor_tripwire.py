"""IDOR-class tripwire (static) · client-portal resource-id handlers.

Client-portal requests run under ``fulkro_app_bypassrls`` (RLS OFF), so a
handler that reaches a resource by a **non-project** id must verify ownership
with the no-oracle guard ``ensure_owned_via_project`` (404, never 403). Calling
the legacy per-motor ``_ensure_project_belongs_to_client`` *after* resolving
``project_id`` from a fetched resource is the "frágil" pattern the audit flagged
(403 leaks existence → resource-id enumeration oracle).

This test fails the build if that pattern is (re)introduced anywhere in the
client portal, so the IDOR class stays closed and cannot regress silently.

See backend/app/motors/m21_portal_cliente/ownership.py.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_MOTORS = Path(__file__).resolve().parents[2] / "app" / "motors"
_CLIENT_AUTH_MARKER = "get_current_client_user"
_FRAGILE_GUARD = "_ensure_project_belongs_to_client"
_NO_ORACLE_GUARD = "ensure_owned_via_project"
_PARAM_RE = re.compile(r"\{(\w+)\}")

_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

# Portal modules whose resource-id handlers were migrated to the no-oracle
# guard (positive regression lock).
_FIXED_PORTALS = (
    "m02_magerit/portal_api.py",
    "m03_dda/portal_api.py",
    "m06_document_factory/portal_api.py",
    "m19_risk/incident_portal_api.py",
    "m05_signing/api.py",
    "m23_retainer/retainer_checkin_portal_api.py",
    "m27_conformity/portal_api_dpc.py",
    "m_meetings/actas_portal_api.py",
)


def _client_portal_modules() -> list[Path]:
    out: list[Path] = []
    for p in _MOTORS.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if _CLIENT_AUTH_MARKER in text:
            out.append(p)
    return out


def _route_path(decorator: ast.expr) -> str | None:
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if not isinstance(func, ast.Attribute) or func.attr not in _HTTP_METHODS:
        return None
    if not decorator.args:
        return None
    first = decorator.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _resource_id_params(path: str) -> list[str]:
    """Path params that name a resource id (NOT project_id, NOT magic tokens)."""
    return [
        p for p in _PARAM_RE.findall(path)
        if p.endswith("_id") and p != "project_id"
    ]


def _iter_route_handlers(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for dec in node.decorator_list:
                path = _route_path(dec)
                if path is not None:
                    yield node, path
                    break


def test_no_client_portal_resource_handler_uses_fragile_guard():
    """No resource-id client handler may call the 403 fragile guard."""
    violations: list[str] = []
    for module in _client_portal_modules():
        src = module.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node, path in _iter_route_handlers(tree):
            if not _resource_id_params(path):
                continue
            body_src = ast.get_source_segment(src, node) or ""
            if f"{_FRAGILE_GUARD}(" in body_src:
                rel = module.relative_to(_MOTORS.parent.parent)
                violations.append(
                    f"{rel}::{node.name} (path={path!r}) llama al guard frágil "
                    f"'{_FRAGILE_GUARD}' sobre un id de recurso → oráculo 403. "
                    f"Sustitúyelo por {_NO_ORACLE_GUARD} (404)."
                )
    assert not violations, (
        "Patrón IDOR frágil (fetch-then-403) en el portal cliente:\n  - "
        + "\n  - ".join(violations)
    )


@pytest.mark.parametrize("rel", _FIXED_PORTALS)
def test_fixed_portals_use_no_oracle_guard(rel: str):
    """The migrated portals must keep importing/using the no-oracle guard."""
    src = (_MOTORS / rel).read_text(encoding="utf-8")
    assert _NO_ORACLE_GUARD in src, (
        f"{rel} debe usar {_NO_ORACLE_GUARD} (guard IDOR no-oráculo)."
    )
