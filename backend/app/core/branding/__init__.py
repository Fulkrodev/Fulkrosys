"""Reusable cliente branding helpers · Sesión 3B-2B.4 Phase 4.

Cross-motor branding injection (PDF generators · email templates · future
report renderers). Wraps ClientBrandingService + MinIO logo materialization
en API portable cross M21/M22/M14/M27 motors.
"""
from backend.app.core.branding.pdf_context import (
    BrandingPdfContext,
    build_branding_pdf_context,
    materialize_client_logo,
)

__all__ = [
    "BrandingPdfContext",
    "build_branding_pdf_context",
    "materialize_client_logo",
]
