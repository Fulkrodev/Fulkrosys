"""Sub-lote 1.B.8.D · Compila los templates LCSP L-XXX a DOCX.

Patron heredado de build_whistleblowing_templates.py / build_web_legal_templates.py
(multi-subdir-aware).

L-* son ENTREGABLES adyacencia normativa LCSP (Ley 9/2017 Contratos del
Sector Publico) que el cliente firma para presentar a AAPP en procedimientos
de licitacion. Familia 'deliverables/' (no policies/) por su naturaleza
declarativa firmada por cliente.

Codigos L-001 (Declaracion Responsable art 140) · L-003 (Compromiso
adscripcion medios art 76.2) · L-004 (Solvencia tecnica arts 89-91) ·
L-005 (Clausula confidencialidad art 133). L-002 (DEUC) se gestiona en
sub-lote 1.B.8.E separado.

Uso:
    PYTHONPATH=. python backend/scripts/build_lcsp_templates.py
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
    ("L-001", "deliverables", "L001_declaracion_responsable_art140_lcsp.md"),
    ("L-002", "deliverables", "L002_modelo_deuc_documento_europeo_unico_contratacion.md"),
    ("L-003", "deliverables", "L003_compromiso_adscripcion_medios_art762_lcsp.md"),
    ("L-004", "deliverables", "L004_acreditacion_solvencia_tecnica_lcsp.md"),
    ("L-005", "deliverables", "L005_clausula_confidencialidad_aapp_art133_lcsp.md"),
    ("L-006", "deliverables", "L006_compromiso_subrogacion_personal_art130_lcsp.md"),
    ("L-007", "deliverables", "L007_anexo_subrogacion_listado_personal_convenio.md"),
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
    print(f"\n=== {len(TEMPLATES)} templates LCSP construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
