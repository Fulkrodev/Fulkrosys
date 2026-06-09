"""M8 v5.1 Checkpoint 3 - Compila los templates E-702/E-703/E-704 a DOCX.

Extrae el cuerpo Jinja de cada MD (el bloque ```jinja ... ```) y convierte
a DOCX via pandoc. Despues ``fix_docx_templates.py`` anadira el header,
footer y signature block (ya hay codigo para eso — solo hace falta
extender HEADER_TITLES + SIGBLOCK_TEMPLATES si se quiere firma anclada).

Uso:
    PYTHONPATH=. python backend/scripts/build_verification_templates.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "backend" / "app" / "motors" / "m06_document_factory" / "templates" / "deliverables"
DOCX_OUTPUT_DIR = ROOT / "var" / "templates_docx"

TEMPLATES = [
    ("E-702", "E702_informe_verificacion_tecnica.md"),
    ("E-703", "E703_resumen_ejecutivo_verificacion.md"),
    ("E-704", "E704_informe_red_team.md"),
]


JINJA_BLOCK = re.compile(r"```jinja\s*(.+?)```", re.DOTALL)


def extract_jinja_body(md_path: Path) -> str:
    """Extrae el bloque `jinja ... ` del MD. Si no hay, devuelve el MD entero."""
    text = md_path.read_text(encoding="utf-8")
    m = JINJA_BLOCK.search(text)
    if not m:
        return text
    return m.group(1).strip()


def build_one(code: str, md_filename: str) -> Path:
    md_path = TEMPLATES_DIR / md_filename
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
    print(f"[ok] {code} -> {docx_out}")
    return docx_out


def main() -> int:
    for code, filename in TEMPLATES:
        build_one(code, filename)
    print(f"\n=== {len(TEMPLATES)} templates verificacion construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
