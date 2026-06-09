"""Sub-lote 1.B.2 - Compila los templates BCP E-401 a E-406 a DOCX.

Replica el patron de build_verification_templates.py: extrae el bloque
Jinja de cada MD (el bloque ```jinja ... ```) y convierte a DOCX via
pandoc. Despues fix_docx_templates.py anadira header/footer/sigblock
si se ejecuta.

Uso:
    PYTHONPATH=. python backend/scripts/build_bcp_templates.py
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
    ("E-401", "E401_estrategias_de_continuidad.md"),
    ("E-402", "E402_bcp_plan_continuidad_negocio.md"),
    ("E-403", "E403_drp_plan_recuperacion_desastres.md"),
    ("E-404", "E404_plan_comunicaciones_crisis.md"),
    ("E-405", "E405_plan_pruebas_continuidad.md"),
    ("E-406", "E406_informe_pruebas_continuidad.md"),
]


JINJA_BLOCK = re.compile(r"```jinja\s*(.+?)```", re.DOTALL)


def extract_jinja_body(md_path: Path) -> str:
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
    print(f"[ok] {code} -> {docx_out} ({docx_out.stat().st_size} bytes)")
    return docx_out


def main() -> int:
    for code, filename in TEMPLATES:
        build_one(code, filename)
    print(f"\n=== {len(TEMPLATES)} templates BCP construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
