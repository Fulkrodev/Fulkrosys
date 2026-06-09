"""Motor 5 -- Obligations Instantiation -- data types.

Dataclasses used by the instantiation pipeline to carry context
and report outcomes without coupling to SQLAlchemy models.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClientContext:
    """Subset of client data needed for template personalisation."""

    razon_social: str
    cif: str | None = None
    sector: str | None = None
    organo_aprobador_politicas: str | None = None
    contacto_email: str | None = None


@dataclass
class ProjectContext:
    """Project-level data required for obligation instantiation."""

    project_id: uuid.UUID
    nombre_proyecto: str
    categoria_ens: str  # BASICA | MEDIA | ALTA
    cliente: ClientContext
    sistema_principal: str | None = None
    fecha_kickoff_iso: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class GapInput:
    """Represents a single gap that requires obligations."""

    gap_id: Optional[uuid.UUID]
    measure_code: str


@dataclass
class InstantiationOutcome:
    """Result of instantiating obligations for a single gap."""

    gap_id: Optional[uuid.UUID]
    measure_code: str
    obligations_created_ids: list[uuid.UUID] = field(default_factory=list)
    obligations_existing_ids: list[uuid.UUID] = field(default_factory=list)
    templates_skipped_no_match: list[str] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
