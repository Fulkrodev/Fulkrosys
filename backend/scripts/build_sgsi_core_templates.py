"""Sub-atom 1.D.F.tris.B-bis · Compila los templates SGSI core ruta normal.

Patron heredado de build_governance_templates.py existing (pandoc gfm → docx).
NO duplicacion · reuse infrastructure 100%.

Plantillas SGSI core (ruta normal · vs ruta basica Cluster A):
  E-150 Plan de Adecuacion al ENS (policies)
  E-160 Manual del SGSI (policies)
  E-170 Plan Director de Seguridad trianual (policies)
  E-180 Declaracion Conformidad SGSI · autoevaluacion BASICA CCN-STIC 809 (policies)

Source: FULKRO architect curated · sub-atom 1.D.F.tris.B-bis.
NO reference doc externo F1/F2 cubre estos IDs (audit-first 2026-05-21 confirmed).

R30 sostener: contenido REAL primer principios · NO placeholders · admin asume
cero ENS · variables Jinja2 explicitas para fill-in real con dataset proyecto.

LECCION-OPS-030 caso 4 sostenida: loops `{% for %}` en linea APARTE (patron L-003/L-007).

Uso:
    PYTHONPATH=. python backend/scripts/build_sgsi_core_templates.py
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
    ("E-150", "policies", "E150_plan_adecuacion.md"),
    ("E-160", "policies", "E160_manual_sgsi.md"),
    ("E-170", "policies", "E170_plan_director.md"),
    ("E-180", "policies", "E180_declaracion_conformidad.md"),
]


JINJA_BLOCK = re.compile(r"```jinja\s*(.+?)```", re.DOTALL)
_JINJA_OPEN = re.compile(r"^```jinja\s*$", re.MULTILINE)


def extract_jinja_body(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    n_blocks = len(_JINJA_OPEN.findall(text))
    if n_blocks > 1:
        # R13 · GUARDA: un .md con >1 valla ```jinja perdia en SILENCIO todo
        # menos el primer bloque al compilar a .docx (search() devuelve solo el
        # 1.o). Fallar ruidosamente en vez de descartar contenido: el 2.o
        # documento debe separarse a su propia plantilla o fusionarse en el 1.o.
        raise RuntimeError(
            f"{md_path.name}: {n_blocks} bloques ```jinja. Separa el 2.o documento "
            f"a su propia plantilla o fusionalo en el 1.o (remediacion R13)."
        )
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
    print(f"\n=== {len(TEMPLATES)} templates SGSI core construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
