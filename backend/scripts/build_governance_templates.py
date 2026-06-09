"""Sub-lote 1.B.9 · Compila los templates Gobierno SGSI + Ruta Basica + Retainer.

Patron heredado de build_lcsp_templates.py (multi-subdir-aware).

Sub-atom A · 1.B.9.A Gobierno SGSI + Actas Core:
  E-002 Acta nombramiento roles ENS (policies)
  E-003 Acta constitucion comite seguridad (policies)
  E-012 Acta aprobacion categorizacion + DA (deliverables)
  E-090 Informe diagnostico inicial GAP (deliverables)

Sub-atom B · 1.B.9.B Ruta Basica lifecycle:
  E-041 Declaracion conformidad ENS (deliverables)
  E-042 Comunicacion cambio material sistema (deliverables)
  E-043 Renovacion periodica conformidad (deliverables)

Sub-atom C · 1.B.9.C Retainer reporting (cuando architect entregue VERBATIM):
  E-614 Informe trimestral retainer (deliverables)
  E-615 Informe anual retainer (deliverables)

LECCION-OPS-030 caso 4 sostenida: loops `{% for %}` en linea APARTE (patron L-003/L-007).

Uso:
    PYTHONPATH=. python backend/scripts/build_governance_templates.py
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
    ("E-002", "policies", "E002_acta_nombramiento_roles_ens.md"),
    ("E-003", "policies", "E003_acta_constitucion_comite_seguridad.md"),
    ("E-012", "deliverables", "E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad.md"),
    ("E-090", "deliverables", "E090_informe_diagnostico_inicial.md"),
    # E-155 Documento de Alcance del SGSI · FASE 0 (CCN-STIC 805/809) · cierra el
    # hueco #10 B2 (faltaba el DOCX base · el .md existia pero nunca se compilo).
    ("E-155", "deliverables", "E155_documento_alcance_sgsi.md"),
    ("E-041", "deliverables", "E041_declaracion_conformidad_ens.md"),
    ("E-042", "deliverables", "E042_comunicacion_cambio_material_sistema.md"),
    ("E-043", "deliverables", "E043_renovacion_periodica_conformidad.md"),
    ("E-614", "deliverables", "E614_informe_trimestral_retainer.md"),
    ("E-615", "deliverables", "E615_informe_anual_retainer.md"),
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
    print(f"\n=== {len(TEMPLATES)} templates Gobierno construidos ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
