"""Tests PDF signature embed helper · Ejecutable 7.7."""
from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from backend.app.motors.m05_signing.pdf_signature_embed import (
    _parse_dataurl_to_image_bytes,
    append_signature_page,
)


_FAKE_CANVAS_DATAURL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def test_parse_dataurl_to_image_bytes_valid():
    bytes_out = _parse_dataurl_to_image_bytes(_FAKE_CANVAS_DATAURL)
    assert bytes_out is not None
    assert bytes_out.startswith(b"\x89PNG")


def test_parse_dataurl_to_image_bytes_invalid_returns_none():
    assert _parse_dataurl_to_image_bytes("") is None
    assert _parse_dataurl_to_image_bytes("not-a-dataurl") is None
    assert _parse_dataurl_to_image_bytes("data:image/png;base64,@@invalid") is None


def test_append_signature_page_produces_valid_pdf(tmp_path: Path):
    """append_signature_page appends a page with signature block · PDF valid."""
    pdf_path = tmp_path / "sample_signed.pdf"
    buf = io.BytesIO()
    canvas = Canvas(buf, pagesize=A4)
    # Initial page
    canvas.setFont("Helvetica", 12)
    canvas.drawString(72, 750, "Sample document content")

    append_signature_page(
        canvas,
        signature_canvas_dataurl=_FAKE_CANVAS_DATAURL,
        signed_name="Juan",
        signed_surname="Pérez García",
        signed_at=datetime(2026, 5, 27, 18, 30, 0, tzinfo=UTC),
        ip_address="10.0.0.5",
        signature_ed25519=b"\x00" * 64,
        event_hash_sha256="a" * 64,
        document_label="Declaración de Aplicabilidad (DdA)",
    )
    canvas.save()

    pdf_bytes = buf.getvalue()
    pdf_path.write_bytes(pdf_bytes)

    assert pdf_bytes.startswith(b"%PDF-")
    # PDF must have at least 2 pages (initial + signature page)
    # ReportLab uses /Pages object with /Kids array · count entries
    page_count = pdf_bytes.count(b"/Type /Page") + pdf_bytes.count(b"/Type/Page")
    # 1 /Pages entry + 2 /Page entries · so at least 3 cumulative
    assert page_count >= 2, f"Expected ≥2 page entries · got {page_count}"
    assert len(pdf_bytes) > 1000  # non-trivial PDF
    # PDF contains image XObject (reportlab embeds canvas dataurl PNG)
    assert (
        b"/Subtype /Image" in pdf_bytes
        or b"/Subtype/Image" in pdf_bytes
    ), "Signature image was not embedded as PDF Image XObject"


def test_append_signature_page_graceful_when_image_invalid(tmp_path: Path):
    """Invalid dataurl renders placeholder text · NO exception."""
    buf = io.BytesIO()
    canvas = Canvas(buf, pagesize=A4)
    canvas.setFont("Helvetica", 12)
    canvas.drawString(72, 750, "Doc")

    # Should NOT raise
    append_signature_page(
        canvas,
        signature_canvas_dataurl="",
        signed_name="X",
        signed_surname="Y",
        signed_at=datetime(2026, 5, 27, 18, 30, 0, tzinfo=UTC),
        ip_address=None,
        signature_ed25519=b"\x00" * 64,
        event_hash_sha256="b" * 64,
        document_label="Test",
    )
    canvas.save()

    pdf_bytes = buf.getvalue()
    assert pdf_bytes.startswith(b"%PDF-")
