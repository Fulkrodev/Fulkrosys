"""Tests for CCN watermark cleaning in corpus ingester."""
import sys
from pathlib import Path

# Add scripts to path so we can import corpus_ingest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from corpus_ingest import clean_ccn_watermarks


def test_clean_removes_sin_clasificar():
    """Removes 'SIN CLASIFICAR' and 'Centro Criptologico Nacional SIN CLASIFICAR'."""
    raw = "Centro Criptológico Nacional   SIN CLASIFICAR\n\nEste es contenido útil.\n\nSIN CLASIFICAR"
    cleaned = clean_ccn_watermarks(raw)
    assert "SIN CLASIFICAR" not in cleaned
    assert "Centro Criptológico Nacional" not in cleaned
    assert "contenido útil" in cleaned


def test_clean_removes_escriba_aqui():
    """Removes '[Escriba aqui]' placeholder."""
    raw = "Título del documento\n\n[Escriba aquí]\n\nContenido real"
    cleaned = clean_ccn_watermarks(raw)
    assert "[Escriba aquí]" not in cleaned
    assert "Título del documento" in cleaned
    assert "Contenido real" in cleaned


def test_clean_preserves_legitimate_text():
    """Legitimate ENS text is not modified."""
    raw = "El Esquema Nacional de Seguridad clasifica los sistemas en 3 niveles."
    cleaned = clean_ccn_watermarks(raw)
    assert cleaned == raw


def test_clean_does_not_touch_ocr_artifacts():
    """OCR artifacts (spaced letters) are left untouched — separate problem."""
    raw = "Ce 1 n . t 1 r 0 o  C r i p t o g r a f i c o"
    cleaned = clean_ccn_watermarks(raw)
    assert "Ce 1 n . t 1 r 0 o" in cleaned
