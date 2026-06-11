"""Recompila plantillas .docx concretas de forma reproducible y SEGURA (remediación ENS).

Generaliza build_informe_final_template.py: dado uno o varios E-codes, localiza su
.md fuente bajo templates/**, extrae el cuerpo Jinja (strip valla ```jinja), compila
con pandoc **gfm-smart** (DESACTIVA la sustitución tipográfica `smart`, que curva las
comillas de los literales Jinja como `'1.0'`/`default('1.0')` y rompe el render) y
aplica el post-proceso idempotente de fix_docx_templates (leak-fixes + header/footer +
bloque de firma) SOLO a esos .docx (no toca el resto · evita diff binario masivo).

Por qué no usar los build_*_templates.py existentes: usan `--from gfm` (smart ON) y
recompilan lotes enteros. Este script es quirúrgico y smart-safe.

Uso:  PYTHONPATH=. python backend/scripts/rebuild_docx_templates.py E-002 E-012 ...
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sgsi_core_templates import extract_jinja_body  # noqa: E402
from fix_docx_templates import (  # noqa: E402
    HEADER_TITLES,
    LEAK_FIXES,
    SIGBLOCK_TEMPLATES,
    _doc_has_sigblock,
    _purge_legacy_sentinels,
    append_sigblock,
    apply_leak_fixes,
    build_footer,
    build_header,
)

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_BASE = ROOT / "backend" / "app" / "motors" / "m06_document_factory" / "templates"
DOCX_DIR = ROOT / "var" / "templates_docx"


def _md_for(code: str) -> Path:
    """Localiza el .md fuente de un E-code (por prefijo de fichero ENNN_*.md)."""
    compact = code.replace("-", "")
    matches = sorted(TEMPLATES_BASE.glob(f"**/{compact}_*.md"))
    if not matches:
        raise FileNotFoundError(f"No .md fuente para {code} (patrón {compact}_*.md)")
    if len(matches) > 1:
        raise RuntimeError(f"Múltiples .md para {code}: {[m.name for m in matches]}")
    return matches[0]


def rebuild(code: str) -> Path:
    md = _md_for(code)
    body = extract_jinja_body(md)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    tmp_md = DOCX_DIR / f"_tmp_{code}.md"
    tmp_md.write_text(body, encoding="utf-8")
    docx_out = DOCX_DIR / f"{code}.docx"
    cmd = [
        "pandoc", str(tmp_md), "-o", str(docx_out),
        "--from", "gfm-smart", "--to", "docx", "--wrap=preserve",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        tmp_md.unlink()
    except FileNotFoundError:
        pass
    if result.returncode != 0:
        raise RuntimeError(f"pandoc fallo para {code}: {result.stderr}")

    doc = Document(str(docx_out))
    fname = f"{code}.docx"
    if fname in LEAK_FIXES:
        apply_leak_fixes(doc, LEAK_FIXES[fname])
    _purge_legacy_sentinels(doc)
    is_commercial = code.startswith(("C-", "P-"))
    if not is_commercial:
        build_header(doc, code, HEADER_TITLES.get(code, f"Documento {code}"))
        build_footer(doc, code)
    if fname in SIGBLOCK_TEMPLATES and not _doc_has_sigblock(doc):
        append_sigblock(doc)
    doc.save(str(docx_out))
    print(f"[ok] {code} -> {docx_out} ({docx_out.stat().st_size} bytes · src {md.name})")
    return docx_out


def main(argv: list[str]) -> int:
    if not argv:
        print("Uso: rebuild_docx_templates.py E-002 E-012 ...", file=sys.stderr)
        return 2
    for code in argv:
        rebuild(code)
    print(f"=== {len(argv)} plantillas recompiladas (gfm-smart) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
