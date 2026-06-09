"""Deterministic parser for RD 311/2022 (ENS) consolidated HTML from BOE.

Parses the HTML into structured chunks suitable for RAG ingestion:
- Preamble
- Articles 1-41
- Disposiciones (adicionales, transitoria, derogatoria, finales)
- Anexo I  (categorisation)
- Anexo II (73 security measures)
- Anexo III (audit)
- Anexo IV (glossary)

Target output: ~125-150 chunks, exactly 73 unique measure_codes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Tag


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ParsedChunk:
    """Single parsed chunk from the RD 311/2022 HTML."""

    chunk_index: int
    heading_path: str
    article_ref: Optional[str]
    measure_code: Optional[str]
    content: str
    chunk_type: str  # preamble | article | disposition | annex_intro | measure
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Regex that matches any of the 73 ENS measure codes.
# Families: org, op.pl, op.acc, op.exp, op.ext, op.nub, op.cont, op.mon,
#           mp.if, mp.per, mp.eq, mp.com, mp.si, mp.sw, mp.info, mp.s
MEASURE_CODE_RE = re.compile(
    r"\b("
    r"org\.\d+"
    r"|op\.(?:pl|acc|exp|ext|nub|cont|mon)\.\d+"
    r"|mp\.(?:if|per|eq|com|si|sw|info|s)\.\d+"
    r")\b"
)

# Pattern to detect measure heading lines like:
#   "3.1 Política de seguridad [org.1]."
#   "4.1.1 Análisis de riesgos [op.pl.1]."
MEASURE_HEADING_RE = re.compile(
    r"^\s*\d+(?:\.\d+)*\s+.+?\["
    r"(org\.\d+"
    r"|op\.(?:pl|acc|exp|ext|nub|cont|mon)\.\d+"
    r"|mp\.(?:if|per|eq|com|si|sw|info|s)\.\d+"
    r")\]"
)

# Article reference pattern: "Artículo 1." or "Artículo 41."
ARTICLE_REF_RE = re.compile(r"Art[ií]culo\s+(\d+)\b")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _text(el: Tag) -> str:
    """Extract clean text from a BeautifulSoup element."""
    return el.get_text(separator=" ", strip=True)


def _collect_bloque_text(bloque: Tag, *, skip_heading: bool = False) -> str:
    """Collect all paragraph text from a div.bloque element.

    If *skip_heading* is True, skips h4/h5 headings.
    """
    parts: list[str] = []
    for child in bloque.children:
        if not isinstance(child, Tag):
            continue
        if skip_heading and child.name in ("h4", "h5"):
            continue
        # Skip bloque reference anchors
        cls = child.get("class", [])
        if "bloque" in cls and child.name == "p":
            continue
        parts.append(_text(child))
    return "\n".join(p for p in parts if p)


def _is_disposition(heading_text: str) -> bool:
    """Check whether this heading is a Disposicion."""
    return heading_text.startswith("Disposici")


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_rd311(html_path: Path) -> list[ParsedChunk]:
    """Parse the RD 311/2022 consolidated HTML into structured chunks.

    Returns a list of ParsedChunk with:
    - Exactly 73 unique measure_codes (from Anexo II)
    - Articles 1-41
    - Disposiciones (adicionales, transitoria, derogatoria, finales)
    - Annexes I, III, IV as single chunks
    - Preamble
    """
    html = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    chunks: list[ParsedChunk] = []
    idx = 0
    current_chapter = ""

    bloques = soup.find_all("div", class_="bloque")

    for bloque in bloques:
        # Detect chapter headings (h4.capitulo_num + h4.capitulo_tit)
        h4s = bloque.find_all("h4")
        anexo_num = None
        anexo_tit = None

        for h4 in h4s:
            cls = h4.get("class", [])
            txt = _text(h4)

            if "capitulo_num" in cls:
                current_chapter = txt
            elif "capitulo_tit" in cls:
                current_chapter = f"{current_chapter} - {txt}"
            elif "anexo_num" in cls:
                anexo_num = txt
            elif "anexo_tit" in cls:
                anexo_tit = txt

        # --- ANEXO II: Parse measures ---
        if anexo_num and "ANEXO II" in anexo_num:
            measure_chunks = _parse_anexo_ii(bloque, start_index=idx)
            chunks.extend(measure_chunks)
            idx += len(measure_chunks)
            continue

        # --- ANEXO I, III, IV: Single chunks ---
        if anexo_num and "ANEXO II" not in anexo_num:
            heading = f"{anexo_num} - {anexo_tit}" if anexo_tit else anexo_num
            content = _collect_bloque_text(bloque, skip_heading=True)
            if content.strip():
                chunks.append(ParsedChunk(
                    chunk_index=idx,
                    heading_path=heading,
                    article_ref=None,
                    measure_code=None,
                    content=content,
                    chunk_type="annex_intro",
                    metadata={"anexo": anexo_num},
                ))
                idx += 1
            continue

        # --- Articles and Disposiciones ---
        h5 = bloque.find("h5", class_="articulo")
        if h5:
            heading_text = _text(h5)
            content = _collect_bloque_text(bloque, skip_heading=True)
            if not content.strip():
                continue

            # Determine chunk_type
            if _is_disposition(heading_text):
                chunk_type = "disposition"
                article_ref = heading_text.split(".")[0].strip()
            else:
                chunk_type = "article"
                m = ARTICLE_REF_RE.search(heading_text)
                article_ref = f"Art. {m.group(1)}" if m else heading_text

            heading_path = f"{current_chapter} > {heading_text}" if current_chapter else heading_text

            chunks.append(ParsedChunk(
                chunk_index=idx,
                heading_path=heading_path,
                article_ref=article_ref,
                measure_code=None,
                content=content,
                chunk_type=chunk_type,
                metadata={},
            ))
            idx += 1
            continue

        # --- Preamble (first bloque with no headings) ---
        if not h4s and not bloque.find("h5"):
            content = _collect_bloque_text(bloque)
            if content.strip() and idx == 0:
                chunks.append(ParsedChunk(
                    chunk_index=idx,
                    heading_path="Preámbulo",
                    article_ref=None,
                    measure_code=None,
                    content=content,
                    chunk_type="preamble",
                    metadata={},
                ))
                idx += 1

    return chunks


# ---------------------------------------------------------------------------
# Anexo II measure parser
# ---------------------------------------------------------------------------

def _parse_anexo_ii(bloque: Tag, start_index: int) -> list[ParsedChunk]:
    """Parse the Anexo II div.bloque into individual measure chunks.

    The structure within the single bloque is:
    - Section headings as p.centro_cursiva (e.g., "3. Marco organizativo [ORG]")
    - Measure headings as p.parrafo_2 matching pattern like
      "3.1 Política de seguridad [org.1]."
    - Body paragraphs (p.parrafo, p.parrafo_2) following each measure heading

    Returns one chunk per measure, plus an intro chunk for the general
    dispositions at the start of Anexo II.
    """
    chunks: list[ParsedChunk] = []
    idx = start_index

    # Collect all child elements (skip navigational/anchor elements)
    children: list[Tag] = []
    for child in bloque.children:
        if isinstance(child, Tag):
            children.append(child)

    # Skip the first few elements (bloque anchor, ANEXO II heading, title)
    # Find where actual content starts (after h4 headings)
    content_start = 0
    for i, child in enumerate(children):
        if child.name == "h4":
            content_start = i + 1
    # Move past the last h4
    while content_start < len(children) and children[content_start].name == "h4":
        content_start += 1

    # Current section tracking
    current_section = "ANEXO II - Medidas de Seguridad"
    current_measure_code: Optional[str] = None
    current_measure_heading = ""
    current_paragraphs: list[str] = []
    intro_paragraphs: list[str] = []
    in_intro = True  # True until we hit the first measure heading

    for child in children[content_start:]:
        cls = child.get("class", [])
        text = _text(child)

        if not text:
            continue

        # Skip bloque reference anchors
        if "bloque" in cls and child.name == "p":
            continue

        # Section headings (p.centro_cursiva) like "3. Marco organizativo [ORG]"
        if "centro_cursiva" in cls:
            current_section = text
            # Check if this is a measure heading disguised as centro_cursiva
            m = MEASURE_HEADING_RE.match(text)
            if m:
                # Flush current measure
                if current_measure_code:
                    _flush_measure(
                        chunks, idx, current_section, current_measure_code,
                        current_measure_heading, current_paragraphs,
                    )
                    idx += 1
                    current_paragraphs = []

                current_measure_code = m.group(1).lower()
                current_measure_heading = text
                in_intro = False
            continue

        # Check if this paragraph starts a new measure
        m = MEASURE_HEADING_RE.match(text)
        if m:
            # Flush intro if we were still in it
            if in_intro and intro_paragraphs:
                chunks.append(ParsedChunk(
                    chunk_index=idx,
                    heading_path="ANEXO II - Disposiciones generales",
                    article_ref=None,
                    measure_code=None,
                    content="\n".join(intro_paragraphs),
                    chunk_type="annex_intro",
                    metadata={"anexo": "ANEXO II", "section": "disposiciones_generales"},
                ))
                idx += 1
                in_intro = False

            # Flush previous measure
            if current_measure_code:
                _flush_measure(
                    chunks, idx, current_section, current_measure_code,
                    current_measure_heading, current_paragraphs,
                )
                idx += 1
                current_paragraphs = []

            current_measure_code = m.group(1).lower()
            current_measure_heading = text
            continue

        # Regular paragraph — accumulate
        if in_intro:
            intro_paragraphs.append(text)
        elif current_measure_code:
            current_paragraphs.append(text)

    # Flush last measure
    if current_measure_code:
        _flush_measure(
            chunks, idx, current_section, current_measure_code,
            current_measure_heading, current_paragraphs,
        )
        idx += 1

    # Flush intro if no measures were found (safety)
    if in_intro and intro_paragraphs:
        chunks.append(ParsedChunk(
            chunk_index=idx,
            heading_path="ANEXO II - Disposiciones generales",
            article_ref=None,
            measure_code=None,
            content="\n".join(intro_paragraphs),
            chunk_type="annex_intro",
            metadata={"anexo": "ANEXO II", "section": "disposiciones_generales"},
        ))
        idx += 1

    return chunks


def _flush_measure(
    chunks: list[ParsedChunk],
    idx: int,
    section: str,
    code: str,
    heading: str,
    paragraphs: list[str],
) -> None:
    """Create a measure chunk and append it to the list."""
    content_parts = [heading] + paragraphs
    content = "\n".join(p for p in content_parts if p)

    chunks.append(ParsedChunk(
        chunk_index=idx,
        heading_path=f"ANEXO II > {section} > [{code}]",
        article_ref=None,
        measure_code=code,
        content=content,
        chunk_type="measure",
        metadata={"anexo": "ANEXO II", "section": section},
    ))
