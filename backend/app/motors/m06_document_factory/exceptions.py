"""Motor 6 -- Document Factory -- exception hierarchy.

Pattern: consistent with M4 Gap Analysis (8 exceptions) and M3 DdA Engine.
"""


class DocumentFactoryError(Exception):
    """Base exception for Motor 6 Document Factory errors."""


class TemplateNotFoundError(DocumentFactoryError):
    """Template not found by codigo or id."""


class TemplateInactiveError(DocumentFactoryError):
    """Template exists but is_active=False."""


class TemplateFileMissingError(DocumentFactoryError):
    """Template .docx file not found on disk."""


class DocumentNotFoundError(DocumentFactoryError):
    """Generated document not found by id."""


class RenderError(DocumentFactoryError):
    """Generic error during DOCX rendering."""


class MissingPlaceholderError(DocumentFactoryError):
    """Required placeholders missing from render context."""


class PDFConversionError(DocumentFactoryError):
    """LibreOffice PDF conversion failed or timed out."""


class SigningError(DocumentFactoryError):
    """Ed25519 key loading or signing failed."""


class CatalogLoadError(DocumentFactoryError):
    """template_catalog_v1.yaml not found or malformed."""
