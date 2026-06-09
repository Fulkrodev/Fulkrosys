"""Motor 6 -- Document Factory -- Pydantic schemas.

Pattern consistent with M4 and M19. Uses ConfigDict(from_attributes=True).
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ================================================================
# Template schemas
# ================================================================


class TemplateOut(BaseModel):
    """Full template response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    codigo: str
    nombre: str
    categoria: str
    familia_ens: str | None = None
    aplica_desde: str | None = None
    version_actual: str
    docx_path: str | None = None
    # M6-G2: normalizado a dict puro {name: {description, required}}.
    # El ``catalog_loader._normalize_placeholders`` toleraba listas legacy,
    # pero ya no existe ninguna en el catalogo productivo.
    placeholders_requeridos: dict[str, Any] | None = None
    is_active: bool
    content_hash: str | None = None
    fuente_md: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class TemplateListFilters(BaseModel):
    """Query filters for listing templates."""
    categoria: str | None = None
    familia_ens: str | None = None
    aplica_desde: str | None = None
    is_active: bool | None = None


# ================================================================
# Document schemas
# ================================================================


class DocumentOut(BaseModel):
    """Full generated document response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    tipo: str | None = None
    nombre: str
    version_actual: str | None = None
    estado: str | None = None
    template_codigo: str | None = None
    docx_path: str | None = None
    pdf_path: str | None = None
    rendered_hash: str | None = None
    signature_ed25519: str | None = None
    context_snapshot: dict[str, Any] | None = None
    generated_by: str | None = None
    generated_at: datetime | None = None
    aprobado_por: str | None = None
    fecha_aprobacion: Any | None = None
    created_at: datetime
    updated_at: datetime | None = None


class GenerateDocumentRequest(BaseModel):
    """Request to generate a document from a template."""
    template_codigo: str = Field(..., description="Template codigo to render")
    context: dict[str, Any] = Field(
        ..., description="Jinja2 context dict for placeholders"
    )
    generate_pdf: bool = Field(
        True, description="Also generate PDF via LibreOffice"
    )
    sign: bool = Field(
        True, description="Sign with Ed25519 after rendering"
    )
    generated_by: str | None = Field(
        None, max_length=255, description="User or system that triggered generation"
    )


class GenerateDocumentResponse(BaseModel):
    """Response after generating a document."""
    document_id: UUID
    template_codigo: str
    nombre: str
    docx_path: str
    pdf_path: str | None = None
    rendered_hash: str
    signature_ed25519: str | None = None
    estado: str
    generated_at: datetime
    pdf_warning: str | None = Field(
        None, description="Warning if PDF conversion failed (non-fatal)"
    )


class RenderPreviewRequest(BaseModel):
    """Request to preview a rendered document (ephemeral, not persisted)."""
    template_codigo: str
    context: dict[str, Any]


class RenderPreviewResponse(BaseModel):
    """Preview response with rendered placeholder summary."""
    template_codigo: str
    nombre: str
    placeholders_provided: list[str]
    placeholders_missing: list[str]
    preview_ok: bool
    message: str


# ================================================================
# Dashboard schemas
# ================================================================


class DocumentFactoryDashboard(BaseModel):
    """Dashboard overview for document factory."""
    project_id: UUID
    total_documents: int = 0
    by_estado: dict[str, int] = Field(default_factory=dict)
    by_template: dict[str, int] = Field(default_factory=dict)
    total_templates_catalog: int = 0
    total_templates_active: int = 0
    templates_with_docx: int = 0
    latest_generation: datetime | None = None
    generated_at: datetime
