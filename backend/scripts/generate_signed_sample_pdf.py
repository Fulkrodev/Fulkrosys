"""Empirical sample · Ejecutable 7.7 · TIER 1 signed PDF generation.

Generates an example PDF (sample document) + appends signature page using
fake canvas dataurl + nombre + apellido + ed25519 mock + hash chain mock.

Usage:
  python -m backend.scripts.generate_signed_sample_pdf [output_path]

Default output: out/ejecutable_7_7_sample_signed.pdf

Verifies empirically:
- ReportLab platypus integration works
- append_signature_page reusable across PDF generators
- Embedded image renders correctly
- Verification badge displays signature hex + hash chain
"""
from __future__ import annotations

import io
import sys
from datetime import UTC, datetime
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from backend.app.motors.m05_signing.pdf_signature_embed import (
    append_signature_page,
)


_SAMPLE_CANVAS_DATAURL = (
    "data:image/png;base64,"
    # 64x32 minimal PNG (1 pixel tinted) · sample signature placeholder
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAAAgCAYAAACinX6EAAAAJUlEQVR4nO3OMQEAAAjDMOZf9Lyhh"
    "u0kRZqXcgM0PuiZmYWvLIYPCwUFnLfHaTAAAAAASUVORK5CYII="
)


def main(output_path: Path) -> None:
    buf = io.BytesIO()
    canvas = Canvas(buf, pagesize=A4)
    width, height = A4

    # Sample first page (placeholder document content)
    canvas.setFillColor(HexColor("#1e293b"))
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(2 * cm, height - 3 * cm, "Documento de Ejemplo · FULKRO")
    canvas.setFont("Helvetica", 12)
    canvas.drawString(
        2 * cm, height - 4 * cm,
        "Este es un documento de muestra para demostrar el embed de firma.",
    )
    canvas.drawString(
        2 * cm, height - 4.7 * cm,
        "La firma del cliente se añade en la última página por este motor.",
    )
    canvas.setFillColor(HexColor("#7c3aed"))
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(
        2 * cm, height - 6 * cm,
        "Ejecutable 7.7 · TIER 1 Canvas Signature",
    )

    # Append signature page
    append_signature_page(
        canvas,
        signature_canvas_dataurl=_SAMPLE_CANVAS_DATAURL,
        signed_name="María",
        signed_surname="García López",
        signed_at=datetime.now(UTC),
        ip_address="192.168.1.42",
        signature_ed25519=bytes.fromhex("a1b2c3d4e5f67890" * 8),  # 64 bytes
        event_hash_sha256=(
            "9b8a7c6d5e4f3210" "fedcba9876543210"
            "1234567890abcdef" "abcdef0987654321"
        ),
        document_label="Declaración de Aplicabilidad (DdA) ENS Anexo II",
    )

    canvas.save()
    pdf_bytes = buf.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    print(f"✓ Signed sample PDF generated: {output_path}")
    print(f"  Size: {len(pdf_bytes)} bytes")


if __name__ == "__main__":
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("out") / "ejecutable_7_7_sample_signed.pdf"
    )
    main(out)
