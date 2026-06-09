"""Motor 5 -- Obligations Library -- loader.

Loads the 30-template obligations library from JSON, validates with
Pydantic, and exposes query helpers used by the engine and API.

All functions are pure (no DB access). The library is cached in memory
after first load.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from backend.app.motors.m05_obligations.types import (
    ObligationTemplate,
    ObligationsLibrary,
)

LIBRARY_PATH = (
    Path(__file__).resolve().parent / "library" / "obligations_library.json"
)


class LibraryLoadError(Exception):
    """Raised when the library JSON cannot be loaded or validated."""


class TemplateNotFoundError(Exception):
    """Raised when a requested template ID does not exist."""


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""


# ── Core loader ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_library(path: Path | None = None) -> ObligationsLibrary:
    """Load and validate the obligations library from JSON.

    Results are cached after first call. Use reload_library() to clear.
    Raises LibraryLoadError on file/parse/validation failures.
    """
    target = path or LIBRARY_PATH
    if not target.exists():
        raise LibraryLoadError(f"Library file not found: {target}")

    try:
        with open(target, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise LibraryLoadError(f"Cannot parse library JSON: {exc}") from exc

    try:
        library = ObligationsLibrary.model_validate(raw)
    except Exception as exc:
        raise LibraryLoadError(f"Library validation failed: {exc}") from exc

    # Check for duplicate IDs
    seen_ids: set[str] = set()
    for tpl in library.templates:
        if tpl.id in seen_ids:
            raise LibraryLoadError(f"Duplicate template ID: {tpl.id}")
        seen_ids.add(tpl.id)

    return library


def reload_library() -> ObligationsLibrary:
    """Clear cache and reload the library from disk."""
    load_library.cache_clear()
    return load_library()


# ── Query helpers ───────────────────────────────────────────────────

def get_all_templates(library: ObligationsLibrary | None = None) -> list[ObligationTemplate]:
    """Return all templates from the library."""
    lib = library or load_library()
    return list(lib.templates)


def get_template_by_id(
    template_id: str,
    library: ObligationsLibrary | None = None,
) -> ObligationTemplate:
    """Return a single template by ID. Raises TemplateNotFoundError if missing."""
    lib = library or load_library()
    for tpl in lib.templates:
        if tpl.id == template_id:
            return tpl
    raise TemplateNotFoundError(f"Template not found: {template_id}")


def get_templates_for_measure(
    measure_code: str,
    category: str | None = None,
    library: ObligationsLibrary | None = None,
) -> list[ObligationTemplate]:
    """Return templates matching a measure code, optionally filtered by category."""
    lib = library or load_library()
    results = [t for t in lib.templates if t.measure_code == measure_code]
    if category:
        results = [t for t in results if t.categoria == category]
    return results


def get_templates_count_by_measure(
    library: ObligationsLibrary | None = None,
) -> dict[str, int]:
    """Return a dict mapping measure_code -> count of templates."""
    lib = library or load_library()
    counts: dict[str, int] = defaultdict(int)
    for tpl in lib.templates:
        counts[tpl.measure_code] += 1
    return dict(counts)


def resolve_dependencies(
    template_id: str,
    library: ObligationsLibrary | None = None,
) -> list[ObligationTemplate]:
    """Resolve full dependency chain for a template (topological order).

    Returns the list of prerequisite templates that must be completed
    before `template_id`, ordered from root dependencies first.
    Does NOT include the template itself.
    Raises CircularDependencyError if a cycle is detected.
    Raises TemplateNotFoundError if any template in the chain is missing.
    """
    lib = library or load_library()

    # Build lookup
    by_id: dict[str, ObligationTemplate] = {t.id: t for t in lib.templates}
    if template_id not in by_id:
        raise TemplateNotFoundError(f"Template not found: {template_id}")

    resolved: list[str] = []
    visiting: set[str] = set()

    def _visit(tid: str) -> None:
        if tid in resolved:
            return
        if tid in visiting:
            raise CircularDependencyError(
                f"Circular dependency detected involving: {tid}"
            )
        visiting.add(tid)
        tpl = by_id.get(tid)
        if tpl is None:
            raise TemplateNotFoundError(
                f"Dependency template not found: {tid}"
            )
        for dep_id in tpl.dependencias_template_ids:
            _visit(dep_id)
        visiting.discard(tid)
        resolved.append(tid)

    # Visit all dependencies of the target (but not the target itself)
    target = by_id[template_id]
    for dep_id in target.dependencias_template_ids:
        _visit(dep_id)

    return [by_id[tid] for tid in resolved]
