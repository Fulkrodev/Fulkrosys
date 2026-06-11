"""Compila E-040 (Informe Final / SoA) · .md → .docx reproducible (R02).

E-040 vive en ``templates/deliverables/`` y NO estaba en ningún
``build_*_templates.py`` (su .docx se había construido de forma no reproducible
y por eso quedó fuera del flujo de mantenimiento). Este script cierra ese hueco:

1. Extrae el cuerpo Jinja del .md (strip de la valla ```jinja — patrón idéntico
   a ``build_sgsi_core_templates.extract_jinja_body``; la valla es el delimitador
   REQUERIDO del build, NO se elimina del .md).
2. Compila con pandoc (``gfm-smart``: igual que el resto de plantillas SGSI pero
   DESACTIVANDO la sustitución tipográfica `smart`, que curvaba las comillas de
   los filtros Jinja como ``default('1.0')`` y rompía el render).
3. Aplica el post-proceso idempotente de ``fix_docx_templates`` (leak-fixes +
   header/footer + bloque de firma estructurado) SOLO a E-040.docx — no toca el
   resto de las 130 plantillas (evita un diff binario masivo).

Uso:  PYTHONPATH=. python backend/scripts/build_informe_final_template.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document

# Reuse infrastructure existente (OPS-026 DRY firmísimo).
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
MD = (
    ROOT / "backend" / "app" / "motors" / "m06_document_factory"
    / "templates" / "deliverables"
    / "E040_informe_final_de_adecuacion_al_ens.md"
)
DOCX_DIR = ROOT / "var" / "templates_docx"
CODE = "E-040"


def main() -> int:
    if not MD.exists():
        raise FileNotFoundError(MD)

    body = extract_jinja_body(MD)
    DOCX_DIR.mkdir(parents=True, exist_ok=True)
    tmp_md = DOCX_DIR / f"_tmp_{CODE}.md"
    tmp_md.write_text(body, encoding="utf-8")
    docx_out = DOCX_DIR / f"{CODE}.docx"

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
        raise RuntimeError(f"pandoc fallo para {CODE}: {result.stderr}")
    print(f"[pandoc] {CODE} -> {docx_out} ({docx_out.stat().st_size} bytes)")

    # Post-proceso idempotente SOLO a E-040.docx (mismo orden que fix_docx main()).
    doc = Document(str(docx_out))
    fname = f"{CODE}.docx"
    if fname in LEAK_FIXES:
        apply_leak_fixes(doc, LEAK_FIXES[fname])
    _purge_legacy_sentinels(doc)
    title = HEADER_TITLES.get(CODE, f"Documento {CODE}")
    build_header(doc, CODE, title)
    build_footer(doc, CODE)
    if fname in SIGBLOCK_TEMPLATES and not _doc_has_sigblock(doc):
        append_sigblock(doc)
    doc.save(str(docx_out))
    print(f"[fix] {CODE}.docx -> header+footer+sigblock aplicados ({docx_out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
