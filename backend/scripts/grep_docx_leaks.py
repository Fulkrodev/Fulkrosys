"""Scan all M6 DOCX templates for forbidden internal refs.

Two pass:

1. **Visible text** (paragraphs, tables, headers, footers) via python-docx.
2. **Raw XML inside the .docx zip** (word/document.xml,
   word/header*.xml, word/footer*.xml, word/styles.xml) via stdlib zipfile.
   Necessary to detect sentinels like ``FULKRO_*`` that are technically
   visible in the XML even when rendered at 1pt (a curious user with
   ``unzip -p`` or "show formatting marks" sees them).

Commercial templates (``C-*``, ``P-*``) may legitimately carry the
brand in the client-facing body (contracts / proposals) per the
``no internal refs externally`` rule. They are audited separately.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from docx import Document

ROOT = Path("/home/usuario/fulkro/var/templates_docx")
PATTERNS = [
    (re.compile(r"\bFULKRO\b"), "FULKRO"),
    (re.compile(r"\bMotor\s+\d+\b"), "Motor N"),
    (re.compile(r"\bAgente\s+\d+\b"), "Agente N"),
    (re.compile(r"\bM\d+-G\d+\b"), "MX-GY"),
    (re.compile(r"\bDocument Factory\b", re.IGNORECASE), "Document Factory"),
    (re.compile(r"\bCopiloto\b", re.IGNORECASE), "Copiloto"),
    (re.compile(r"\bvia Motor\b", re.IGNORECASE), "via Motor"),
]

# Patrones para escanear el XML INTERNO del .docx. Aqui no usamos ``\b``
# porque los sentinels antiguos eran ``FULKRO_HEADER_V2`` y queremos
# detectar tanto la palabra suelta como los sentinels compuestos.
XML_PATTERNS = [
    (re.compile(r"FULKRO[_\w]*"), "FULKRO[_*]"),
    (re.compile(r"\bMotor\s+\d+\b"), "Motor N"),
    (re.compile(r"\bAgente\s+\d+\b"), "Agente N"),
    (re.compile(r"\bM\d+-G\d+\b"), "MX-GY"),
    (re.compile(r"\bDocument Factory\b", re.IGNORECASE), "Document Factory"),
    (re.compile(r"\bCopiloto\b", re.IGNORECASE), "Copiloto"),
]
XML_PARTS_TO_SCAN_PREFIXES = ("word/document.xml", "word/header", "word/footer", "word/styles.xml")


def iter_all_paragraphs(doc):
    for p in doc.paragraphs:
        yield ("body", p.text)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield ("table", p.text)
    for section in doc.sections:
        for p in section.header.paragraphs:
            yield ("header", p.text)
        for p in section.footer.paragraphs:
            yield ("footer", p.text)


def scan(path: Path) -> list[tuple[str, str, str]]:
    doc = Document(str(path))
    hits: list[tuple[str, str, str]] = []
    for loc, text in iter_all_paragraphs(doc):
        if not text:
            continue
        for pat, label in PATTERNS:
            if pat.search(text):
                hits.append((label, loc, text.strip()[:180]))
    return hits


def scan_xml(path: Path) -> list[tuple[str, str, str]]:
    """Scan raw XML inside the .docx for forbidden substrings.

    Returns [(label, xml_part, sample), ...]. Catches sentinels and any
    other internal ref hidden in metadata or zero-size runs.
    """
    hits: list[tuple[str, str, str]] = []
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            for name in names:
                if not name.startswith(XML_PARTS_TO_SCAN_PREFIXES):
                    continue
                try:
                    raw = z.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                for pat, label in XML_PATTERNS:
                    for m in pat.finditer(raw):
                        sample = m.group(0)
                        hits.append((label, name, sample))
    except zipfile.BadZipFile:
        hits.append(("<corrupt-zip>", "<docx>", str(path)))
    return hits


def main() -> int:
    files = sorted(ROOT.glob("*.docx"))
    non_commercial = [f for f in files if not f.stem.startswith(("C-", "P-"))]
    commercial = [f for f in files if f.stem.startswith(("C-", "P-"))]

    print(f"Scanning {len(non_commercial)} non-commercial + {len(commercial)} commercial templates")
    print("Pass 1: visible text  ·  Pass 2: raw XML inside .docx zip")

    # Pass 1 — visible text (non-commercial only; commercial may carry brand)
    total_visible_hits = 0
    files_with_visible_hits = 0
    for f in non_commercial:
        hits = scan(f)
        if hits:
            files_with_visible_hits += 1
            total_visible_hits += len(hits)
            print(f"\n[VISIBLE · NON-COMMERCIAL] {f.name}: {len(hits)} hit(s)")
            for label, loc, snippet in hits:
                print(f"  [{label:<18}][{loc:<6}] {snippet}")

    # Pass 2 — raw XML scan (catches sentinels and other hidden internal refs)
    total_xml_hits = 0
    files_with_xml_hits = 0
    for f in non_commercial:
        hits_xml = scan_xml(f)
        if hits_xml:
            files_with_xml_hits += 1
            total_xml_hits += len(hits_xml)
            print(f"\n[XML · NON-COMMERCIAL] {f.name}: {len(hits_xml)} hit(s)")
            # Group by label to keep output short
            seen = set()
            for label, part, sample in hits_xml:
                key = (label, part, sample)
                if key in seen:
                    continue
                seen.add(key)
                print(f"  [{label:<18}][{part:<25}] {sample}")

    # Commercial: brand OK, but other leaks (Motor N, Agente N) should fail.
    commercial_other_hits = 0
    for f in commercial:
        hits = scan(f) + scan_xml(f)
        other_hits = [h for h in hits if h[0] != "FULKRO" and h[0] != "FULKRO[_*]"]
        if other_hits:
            commercial_other_hits += len(other_hits)
            print(f"\n[COMMERCIAL · should not leak Motor/Agente] {f.name}")
            for label, loc, snippet in other_hits:
                print(f"  [{label}][{loc}] {snippet}")

    print("\n=== TOTALS ===")
    print(f"non-commercial scanned                  : {len(non_commercial)}")
    print(f"non-commercial files with visible leaks : {files_with_visible_hits}")
    print(f"non-commercial visible hits total       : {total_visible_hits}")
    print(f"non-commercial files with XML leaks     : {files_with_xml_hits}")
    print(f"non-commercial XML hits total           : {total_xml_hits}")
    print(f"commercial files                        : {len(commercial)}  (brand OK)")
    print(f"commercial OTHER (forbidden) leaks      : {commercial_other_hits}")

    fails = (
        files_with_visible_hits
        + files_with_xml_hits
        + commercial_other_hits
    )
    if fails == 0:
        print("\nRESULTADO: 0 leaks (visible + XML) ✅")
        return 0
    print(f"\nRESULTADO: {fails} leaks detectados ❌")
    return 1


if __name__ == "__main__":
    sys.exit(main())
