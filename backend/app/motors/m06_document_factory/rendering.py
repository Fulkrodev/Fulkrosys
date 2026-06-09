"""Motor 6 -- Document Factory -- DOCX rendering and PDF conversion.

Uses docxtpl for Jinja2-based DOCX rendering and LibreOffice headless
for DOCX-to-PDF conversion.
"""
import subprocess
from pathlib import Path

import jinja2
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage
from loguru import logger

from backend.app.motors.m06_document_factory.exceptions import (
    MissingPlaceholderError,
    RenderError,
    PDFConversionError,
    TemplateFileMissingError,
)
from backend.app.fulkro_identity import (
    FULKRO_AUTHOR_NAME,
    FULKRO_AUTHOR_ROLE,
    FULKRO_EMAIL,
    FULKRO_FOOTER_TEXT,
    FULKRO_PHONE,
    FULKRO_WEB,
)
from backend.app.motors.m06_document_factory.filters import register_es_filters

# Identidad consultora centralizada (Ejecutable 7.6 · single source of truth).
# F-14-01: m06 NO importaba fulkro_identity → footer/tel/web/autor NO llegaban a
# las plantillas. Fallback de marca = "Fulkro" (no "Marcos") cuando no hay logo.
CONSULTOR_LOGO_FALLBACK_TEXT = "Fulkro · Consultoría ENS"

LIBREOFFICE_TIMEOUT_SECONDS = 60


class _SilentUndefined(jinja2.Undefined):
    """Jinja2 Undefined that silently returns empty string for any operation.

    Prevents UndefinedError when templates have optional variables not
    present in the render context. Required vars are validated separately
    via the required_placeholders parameter.
    """

    def __str__(self):
        return ""

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False

    def __getattr__(self, name):
        return _SilentUndefined()

    def __getitem__(self, name):
        return _SilentUndefined()


def _find_missing_required(context: dict, required_vars: list[str]) -> list[str]:
    """Check each dot-notation path in required_vars against context.
    Returns list of paths that are missing, None, or empty string.
    """
    missing = []
    for path in required_vars:
        parts = path.split(".")
        current = context
        found = True
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                found = False
                break
            current = current[part]
        if not found:
            missing.append(path)
            continue
        if current is None or (isinstance(current, str) and not current.strip()):
            missing.append(path)
    return missing


def _inject_brand(
    tpl: DocxTemplate,
    context: dict,
    cliente_logo_path: Path | None,
    consultor_logo_path: Path | None,
) -> None:
    """Inject ``cliente.header_brand`` and ``consultor.header_brand`` into
    context for template header rendering.

    If a logo path exists, an ``InlineImage`` is set; otherwise a
    stylised text fallback is used (client razon_social in uppercase for
    the client side, ``CONSULTOR_LOGO_FALLBACK_TEXT`` for the consultor).
    """
    cliente = context.setdefault("cliente", {})
    consultor = context.setdefault("consultor", {})

    if cliente_logo_path and cliente_logo_path.exists():
        cliente["header_brand"] = InlineImage(tpl, str(cliente_logo_path), height=Mm(12))
    else:
        razon = (cliente.get("razon_social") or "").upper()
        cliente["header_brand"] = razon or "CLIENTE"

    if consultor_logo_path and consultor_logo_path.exists():
        consultor["header_brand"] = InlineImage(tpl, str(consultor_logo_path), height=Mm(12))
    else:
        consultor["header_brand"] = CONSULTOR_LOGO_FALLBACK_TEXT

    # F-14-01: identidad Fulkro centralizada disponible para header/footer de
    # las plantillas (single source of truth · Ejecutable 7.6). setdefault para
    # no pisar overrides explícitos del contexto.
    consultor.setdefault("nombre_comercial", "Fulkro")
    consultor.setdefault("footer_text", FULKRO_FOOTER_TEXT)
    consultor.setdefault("telefono", FULKRO_PHONE)
    consultor.setdefault("email", FULKRO_EMAIL)
    consultor.setdefault("web", FULKRO_WEB)


def _default_firmas(context: dict) -> None:
    """Populate ``firmas.elaborado/revisado/aprobado`` defaults from the
    render context so the structured sig block reads sensibly even
    before Motor 12 stamps digital signatures."""
    resp = context.get("responsables") or {}
    cliente = context.get("cliente") or {}
    proyecto = context.get("proyecto") or {}
    today_iso = proyecto.get("fecha_aprobacion_inicial") or proyecto.get("fecha_fin") or ""
    firmas = context.setdefault("firmas", {})
    firmas.setdefault("elaborado", {
        # F-14-01: autor desde fulkro_identity (no hardcode "Marcos Mata García"
        # / "Consultor independiente en ENS").
        "nombre": FULKRO_AUTHOR_NAME,
        "cargo": FULKRO_AUTHOR_ROLE,
        "fecha": today_iso,
        "firma_marca": "Firma manuscrita en documento impreso",
    })
    rseg = (resp.get("responsable_seguridad") or {})
    firmas.setdefault("revisado", {
        "nombre": rseg.get("nombre", ""),
        "cargo": rseg.get("cargo", "Responsable de Seguridad de la Información"),
        "fecha": today_iso,
        "firma_marca": "Firma manuscrita en documento impreso",
    })
    firmas.setdefault("aprobado", {
        "nombre": cliente.get("representante_legal", ""),
        "cargo": cliente.get("organo_aprobador_politicas", "Órgano de gobierno superior"),
        "fecha": today_iso,
        "firma_marca": "Firma manuscrita en documento impreso",
    })


def render_docx(
    template_path: Path,
    context: dict,
    output_path: Path,
    required_vars: list[str] | None = None,
    cliente_logo_path: Path | None = None,
    consultor_logo_path: Path | None = None,
) -> Path:
    """Render a DOCX template with context.

    If ``required_vars`` is provided, validates each dot-notation path
    exists and is not None/empty in context BEFORE rendering.
    Uses ``_SilentUndefined`` for optional vars during Jinja2 render.

    When ``cliente_logo_path`` or ``consultor_logo_path`` are provided
    and exist, they are embedded as inline images in the header via
    docxtpl's ``InlineImage``. Missing logos fall back to stylised
    text. A default ``firmas`` block is also injected when absent, so
    the signature table at the end of deliverables templates renders
    cleanly before Motor 12 stamps digital signatures.
    """
    if not template_path.exists():
        raise TemplateFileMissingError(f"Template file not found: {template_path}")

    if required_vars:
        missing = _find_missing_required(context, required_vars)
        if missing:
            raise MissingPlaceholderError(
                f"Missing required placeholders: {', '.join(missing)}"
            )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tpl = DocxTemplate(str(template_path))
        # Build an isolated render context so InlineImage / field objects
        # never leak back to the caller (which persists ``context`` as
        # JSONB for audit/debugging and chokes on non-JSON types).
        import copy
        render_ctx = copy.deepcopy(context)
        _inject_brand(tpl, render_ctx, cliente_logo_path, consultor_logo_path)
        _default_firmas(render_ctx)
        # nosec B701 · render DOCX via docxtpl (no HTML) · el escaping XML lo
        # gestiona docxtpl · autoescape=True corromperia el documento Word.
        env = jinja2.Environment(undefined=_SilentUndefined)  # nosec B701
        register_es_filters(env)
        tpl.render(render_ctx, jinja_env=env)
        tpl.save(str(output_path))
        logger.info("Rendered DOCX: {}", output_path)
        return output_path
    except (MissingPlaceholderError, TemplateFileMissingError):  # pragma: no cover
        raise
    except Exception as exc:
        raise RenderError(f"Failed to render DOCX {template_path}: {exc}") from exc


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path | None:
    """Convert a DOCX to PDF using LibreOffice headless.

    Args:
        docx_path: Path to the .docx file.
        output_dir: Directory where the PDF will be written.

    Returns:
        Path to the generated PDF, or None if conversion is not available.

    Raises:
        PDFConversionError: LibreOffice failed or timed out.
    """
    if not docx_path.exists():
        raise PDFConversionError(f"DOCX not found: {docx_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(output_dir),
        str(docx_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=LIBREOFFICE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:  # pragma: no cover — LibreOffice installed in deployment
        raise PDFConversionError(
            "LibreOffice not found. Install with: apt install libreoffice-writer"
        )
    except subprocess.TimeoutExpired:  # pragma: no cover — 60s timeout unlikely in tests
        raise PDFConversionError(
            f"LibreOffice conversion timed out after {LIBREOFFICE_TIMEOUT_SECONDS}s"
        )

    if result.returncode != 0:  # pragma: no cover — valid DOCX always converts
        raise PDFConversionError(
            f"LibreOffice exited with code {result.returncode}: {result.stderr}"
        )

    # LibreOffice writes the PDF with the same stem as the DOCX
    expected_pdf = output_dir / f"{docx_path.stem}.pdf"
    if not expected_pdf.exists():  # pragma: no cover — LibreOffice always produces output
        raise PDFConversionError(
            f"LibreOffice ran but PDF not found at {expected_pdf}"
        )

    logger.info("Converted to PDF: {}", expected_pdf)
    return expected_pdf
