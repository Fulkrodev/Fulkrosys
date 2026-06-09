"""Sub-lote 1.B.8.C · Compila los templates Web-Legal LW-001/002/003 a DOCX.

Patron heredado de build_whistleblowing_templates.py (multi-subdir-aware).

LW-* son plantillas adyacencia normativa NO-ENS (LSSI Ley 34/2002 + RGPD
para sitio web corporativo). Codigos LW-001/002/003 segregados del rango
E-1XX/E-2XX por clara separacion normativa (LECCION-OPS-032 + AMEND-016 v2).

Uso:
    PYTHONPATH=. python backend/scripts/build_web_legal_templates.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_BASE = ROOT / "backend" / "app" / "motors" / "m06_document_factory" / "templates"
DOCX_OUTPUT_DIR = ROOT / "var" / "templates_docx"

# (codigo_docx, subdir_relativo_a_templates, md_filename)
TEMPLATES = [
    ("LW-001", "policies", "LW001_politica_privacidad_web.md"),
    ("LW-002", "policies", "LW002_politica_cookies.md"),
    ("LW-003", "policies", "LW003_aviso_legal_lssi.md"),
]


JINJA_BLOCK = re.compile(r"```jinja\s*(.+?)```", re.DOTALL)


def extract_jinja_body(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    m = JINJA_BLOCK.search(text)
    if not m:
        return text
    return m.group(1).strip()


def build_one(code: str, subdir: str, md_filename: str) -> Path:
    md_path = TEMPLATES_BASE / subdir / md_filename
    if not md_path.exists():
        raise FileNotFoundError(f"Template MD no encontrado: {md_path}")
    body = extract_jinja_body(md_path)

    DOCX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_md = DOCX_OUTPUT_DIR / f"_tmp_{code}.md"
    tmp_md.write_text(body, encoding="utf-8")

    docx_out = DOCX_OUTPUT_DIR / f"{code}.docx"

    cmd = [
        "pandoc",
        str(tmp_md),
        "-o", str(docx_out),
        "--from", "gfm",
        "--to", "docx",
        "--wrap=preserve",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        tmp_md.unlink()
    except FileNotFoundError:
        pass
    if result.returncode != 0:
        raise RuntimeError(f"pandoc fallo para {code}: {result.stderr}")
    print(f"[ok] {code} -> {docx_out} ({docx_out.stat().st_size} bytes)")
    return docx_out


def main() -> int:
    for code, subdir, filename in TEMPLATES:
        build_one(code, subdir, filename)
    print(f"\n=== {len(TEMPLATES)} templates Web-Legal construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
