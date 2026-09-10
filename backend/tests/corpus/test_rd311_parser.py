"""Offline parser tests for RD 311/2022.

These tests do NOT require a database -- they only exercise the parser
against the downloaded HTML file.
"""

import os
import re
from pathlib import Path

import pytest

from backend.app.corpus.rd311_parser import parse_rd311

# Raíz del repo por traversal (mismo patrón que backend/app/startup_checks.py:22):
# backend/tests/corpus/test_rd311_parser.py → parents[3] == raíz del repo.
# Antes esto apuntaba a una ruta absoluta de una máquina concreta, así que fuera
# de esa máquina el fixture se saltaba SIEMPRE y el test era vacuo.
_REPO_ROOT = Path(__file__).resolve().parents[3]
# Mismo default y mismo override (FULKRO_CORPUS_DIR) que
# backend/app/corpus/rd311_ingest.py.
CORPUS_DIR = Path(os.environ.get("FULKRO_CORPUS_DIR") or (_REPO_ROOT / "var" / "corpus"))
HTML_PATH = CORPUS_DIR / "boe" / "RD_311_2022_consolidado.html"


@pytest.fixture(scope="module")
def chunks():
    if not HTML_PATH.exists():
        pytest.skip(
            f"RD 311/2022 HTML no descargado en {HTML_PATH} "
            "(descárgalo ahí o exporta FULKRO_CORPUS_DIR)"
        )
    return parse_rd311(HTML_PATH)


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------

def test_total_chunks_reasonable(chunks):
    """Total chunk count should be between 80 and 250."""
    assert 80 <= len(chunks) <= 250, f"Got {len(chunks)} chunks"


def test_has_73_measures(chunks):
    """Exactly 73 unique measure codes must be present."""
    measures = [c for c in chunks if c.chunk_type == "measure"]
    codes = {c.measure_code for c in measures}
    assert len(codes) == 73, f"Expected 73 measure codes, got {len(codes)}: {sorted(codes)}"


def test_has_articles(chunks):
    """At least 30 article chunks must be present (target: 41)."""
    articles = [c for c in chunks if c.chunk_type == "article"]
    assert len(articles) >= 30, f"Expected >= 30 articles, got {len(articles)}"


def test_has_41_articles(chunks):
    """Exactly 41 article chunks (Art. 1 through Art. 41)."""
    articles = [c for c in chunks if c.chunk_type == "article"]
    assert len(articles) == 41, f"Expected 41 articles, got {len(articles)}"


def test_has_8_dispositions(chunks):
    """Exactly 8 disposition chunks."""
    dispositions = [c for c in chunks if c.chunk_type == "disposition"]
    assert len(dispositions) == 8, f"Expected 8 dispositions, got {len(dispositions)}"


def test_has_preamble(chunks):
    """At least 1 preamble chunk."""
    preambles = [c for c in chunks if c.chunk_type == "preamble"]
    assert len(preambles) >= 1, f"Expected >= 1 preamble, got {len(preambles)}"


def test_has_annex_chunks(chunks):
    """At least 3 annex_intro chunks (Anexos I, III, IV + possibly II intro)."""
    annexes = [c for c in chunks if c.chunk_type == "annex_intro"]
    assert len(annexes) >= 3, f"Expected >= 3 annex_intro chunks, got {len(annexes)}"


# ---------------------------------------------------------------------------
# Measure code format
# ---------------------------------------------------------------------------

def test_measure_codes_format(chunks):
    """All measure_codes must match the expected regex pattern."""
    pattern = re.compile(r"^(org\.\d+|op\.\w+\.\d+|mp\.\w+\.\d+)$")
    for c in chunks:
        if c.measure_code:
            assert pattern.match(c.measure_code), f"Invalid code: {c.measure_code}"


# ---------------------------------------------------------------------------
# Content quality
# ---------------------------------------------------------------------------

def test_all_chunks_have_content(chunks):
    """Every chunk must have non-trivial content (> 10 chars)."""
    for c in chunks:
        assert c.content and len(c.content.strip()) > 10, (
            f"Chunk {c.chunk_index} ({c.chunk_type}) has insufficient content: "
            f"{repr(c.content[:50])}"
        )


def test_chunk_indices_are_sequential(chunks):
    """Chunk indices should be sequential starting from 0."""
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks))), "Chunk indices are not sequential"


# ---------------------------------------------------------------------------
# Specific measure presence
# ---------------------------------------------------------------------------

def test_org_measures_complete(chunks):
    """org.1 through org.4 must be present."""
    codes = {c.measure_code for c in chunks if c.measure_code}
    for i in range(1, 5):
        assert f"org.{i}" in codes, f"Missing org.{i}"


def test_op_pl_measures_complete(chunks):
    """op.pl.1 through op.pl.5 must be present."""
    codes = {c.measure_code for c in chunks if c.measure_code}
    for i in range(1, 6):
        assert f"op.pl.{i}" in codes, f"Missing op.pl.{i}"


def test_op_acc_measures_complete(chunks):
    """op.acc.1 through op.acc.6 must be present."""
    codes = {c.measure_code for c in chunks if c.measure_code}
    for i in range(1, 7):
        assert f"op.acc.{i}" in codes, f"Missing op.acc.{i}"


def test_mp_s_measures_complete(chunks):
    """mp.s.1 through mp.s.4 must be present."""
    codes = {c.measure_code for c in chunks if c.measure_code}
    for i in range(1, 5):
        assert f"mp.s.{i}" in codes, f"Missing mp.s.{i}"
