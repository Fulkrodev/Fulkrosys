"""Cached loader and query helpers for the onboarding templates catalog.

Pattern cloned from m07_evidence/catalog_loader.py.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .enums import Role, Sector
from .types import OnboardingTemplate

TEMPLATES_DIR = Path(__file__).parent / 'templates'


@lru_cache(maxsize=1)
def load_all_templates() -> tuple[OnboardingTemplate, ...]:
    """Load all template JSONs from disk. Validates with Pydantic. Cached."""
    if not TEMPLATES_DIR.exists():
        raise FileNotFoundError(f'Templates directory not found: {TEMPLATES_DIR}')

    templates = []
    for path in sorted(TEMPLATES_DIR.glob('*.json')):
        raw = json.loads(path.read_text(encoding='utf-8'))
        template = OnboardingTemplate.model_validate(raw)
        templates.append(template)

    ids = [t.id for t in templates]
    if len(ids) != len(set(ids)):
        raise ValueError(f'Duplicate template ids: {ids}')

    keys = [(t.sector, t.role, t.version) for t in templates]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate (sector, role, version) combination')

    return tuple(templates)


def reload_templates() -> tuple[OnboardingTemplate, ...]:
    load_all_templates.cache_clear()
    return load_all_templates()


def get_template_by_id(template_id: str) -> Optional[OnboardingTemplate]:
    for t in load_all_templates():
        if t.id == template_id:
            return t
    return None


def find_template_for(sector: Sector, role: Role) -> Optional[OnboardingTemplate]:
    """Return latest version template for (sector, role)."""
    candidates = [
        t for t in load_all_templates()
        if t.sector == sector and t.role == role
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda t: t.version)


def list_available_sectors() -> list[Sector]:
    return sorted({t.sector for t in load_all_templates()})


def list_available_roles_for_sector(sector: Sector) -> list[Role]:
    return sorted({t.role for t in load_all_templates() if t.sector == sector})
