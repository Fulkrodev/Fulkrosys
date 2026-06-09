"""Tests · magic-bytes upload validation (auditoría 2026-06-07)."""
import pytest

from backend.app.core.upload_validation import (
    MagicByteMismatch,
    validate_magic_bytes,
)


def test_valid_pdf_passes():
    validate_magic_bytes(b"%PDF-1.7\n...", ".pdf")  # no raise


def test_pdf_extension_with_spoofed_content_rejected():
    with pytest.raises(MagicByteMismatch):
        validate_magic_bytes(b"MZ\x90\x00 fake exe", ".pdf")


def test_valid_png_passes():
    validate_magic_bytes(b"\x89PNG\r\n\x1a\n....", ".png")


def test_png_with_jpeg_content_rejected():
    with pytest.raises(MagicByteMismatch):
        validate_magic_bytes(b"\xff\xd8\xff\xe0 jpeg", ".png")


def test_docx_ooxml_zip_passes():
    validate_magic_bytes(b"PK\x03\x04 docx zip container", ".docx")


def test_doc_ole2_passes():
    validate_magic_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 ole2", ".doc")


def test_txt_no_signature_allows_any():
    validate_magic_bytes(b"cualquier texto plano", ".txt")
    validate_magic_bytes(b"a,b,c\n1,2,3", ".csv")


def test_unknown_extension_not_validated():
    # Extensión no catalogada → no valida (la whitelist la gobierna aparte).
    validate_magic_bytes(b"random bytes", ".xyz")


def test_case_insensitive_extension():
    validate_magic_bytes(b"%PDF-1.4", ".PDF")
    with pytest.raises(MagicByteMismatch):
        validate_magic_bytes(b"not a pdf", ".PDF")
