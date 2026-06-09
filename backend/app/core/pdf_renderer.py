"""PDF rendering service: docxtpl + LibreOffice headless conversion.

Reusable across all motors that need to generate formal documents (Motor 1
Acta E-012, Motor 6 Document Factory, Motor 9 Audit Prep, Motor 13 Commercial,
Motor 14 Contracts, Motor 25 Lifecycle Archival).

Pipeline:
    1. Jinja2 fills placeholders in a .docx template using docxtpl
    2. LibreOffice headless converts the .docx to .pdf
    3. Both files are returned (caller decides what to do with each)
"""
import asyncio
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from docxtpl import DocxTemplate

logger = logging.getLogger(__name__)


class PDFRenderError(Exception):
    """Raised when DOCX template rendering or PDF conversion fails."""


class PDFRenderer:
    """Render DOCX templates to filled DOCX + PDF.

    Use as async context manager. Cleanup is automatic.

    Usage:
        async with PDFRenderer() as renderer:
            docx_bytes, pdf_bytes = await renderer.render(template_path, context)
    """

    LIBREOFFICE_TIMEOUT_SECONDS = 30

    def __init__(self, libreoffice_bin: str = "libreoffice"):
        self.libreoffice_bin = libreoffice_bin
        self._workdir: Path | None = None

    async def __aenter__(self):
        self._workdir = Path(tempfile.mkdtemp(prefix="fulkro_pdfrender_"))
        return self

    async def __aexit__(self, *args):
        if self._workdir and self._workdir.exists():
            shutil.rmtree(self._workdir, ignore_errors=True)

    async def render(
        self,
        template_path: Path,
        context: dict[str, Any],
    ) -> tuple[bytes, bytes]:
        """Render DOCX template with context, convert to PDF.

        Returns (docx_bytes, pdf_bytes).
        Raises PDFRenderError if template not found or conversion fails.
        """
        if not template_path.exists():
            raise PDFRenderError(f"Template not found: {template_path}")

        filled_docx_path = self._workdir / f"{uuid.uuid4().hex}.docx"

        # Step 1: docxtpl fills placeholders
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(filled_docx_path))

        docx_bytes = filled_docx_path.read_bytes()

        # Step 2: LibreOffice headless conversion
        pdf_bytes = await self._convert_to_pdf(filled_docx_path)

        return docx_bytes, pdf_bytes

    async def render_docx_only(
        self,
        template_path: Path,
        context: dict[str, Any],
    ) -> bytes:
        """Render DOCX template without PDF conversion.

        Useful when LibreOffice is not available or PDF is not needed.
        """
        if not template_path.exists():
            raise PDFRenderError(f"Template not found: {template_path}")

        filled_docx_path = self._workdir / f"{uuid.uuid4().hex}.docx"
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        doc.save(str(filled_docx_path))
        return filled_docx_path.read_bytes()

    async def _convert_to_pdf(self, docx_path: Path) -> bytes:
        """Run libreoffice --headless --convert-to pdf with timeout."""
        pdf_path = docx_path.with_suffix(".pdf")

        proc = await asyncio.create_subprocess_exec(
            self.libreoffice_bin,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--nologo",
            "--convert-to", "pdf",
            "--outdir", str(self._workdir),
            str(docx_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.LIBREOFFICE_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise PDFRenderError(
                f"LibreOffice timeout after {self.LIBREOFFICE_TIMEOUT_SECONDS}s"
            )

        if proc.returncode != 0:
            raise PDFRenderError(
                f"LibreOffice failed (rc={proc.returncode}): "
                f"{stderr.decode(errors='replace')}"
            )

        if not pdf_path.exists():
            raise PDFRenderError(f"LibreOffice did not produce {pdf_path}")

        return pdf_path.read_bytes()
