"""#42 FASE C · genera el DOCX canónico REDACTADO del contrato comercial (C-001)
con datos realistas y vuelca su texto íntegro para revisión (checkpoint Marcos).

    python -m backend.scripts.preview_contract_c001
"""
from __future__ import annotations

import io
from pathlib import Path

from docx import Document

from backend.app.motors.m14_contracts.legal_templates import (
    LegalContext,
    generate_legal_docx,
)


def _build_sample_ctx() -> LegalContext:
    return LegalContext(
        project_id=__import__("uuid").uuid4(),
        # Cliente (#9 · autorrelleno desde Client)
        client_name="Guadaltel S.A.",
        client_cif="A41000000",
        client_domicilio="Av. de la Innovación 1, 41020 Sevilla",
        client_persona_contacto="Ana García López",
        client_representante="Ana García López",
        # Emisor (#44 · identidad fiscal única del consultor)
        fulkro_name="Marcos Mata García",
        fulkro_cif="77171140E",
        fulkro_domicilio="Paseo de la Dirección 46, 28039 Madrid",
        fulkro_representante="Marcos Mata García",
        rseg_name="Responsable de Seguridad designado",
        # Pricing + hitos (#42 · de Proposal/PricingCalculator)
        categoria="MEDIA",
        importe_total=11500.0,
        hitos=[
            {"code": "hito_1_firma", "pct": 30.0,
             "description": "Firma del contrato y kickoff", "amount": 3450.0},
            {"code": "hito_2_dda_politicas", "pct": 40.0,
             "description": "DdA + políticas + análisis de riesgos", "amount": 4600.0},
            {"code": "hito_5_certificacion", "pct": 30.0,
             "description": "Auditoría ENAC superada / conformidad", "amount": 3450.0},
        ],
        # Alcance comercial congelado (#10 B1 · alcance_snapshot)
        alcance={
            "categoria": "MEDIA", "sistemas": 5, "ubicaciones": 2,
            "empleados": 30,
            "exclusiones": ["Sistemas OT/industriales", "Apps de terceros no integradas"],
        },
        # Agent 20 · cláusulas específicas del caso (COMPLEMENTO)
        llm_clauses={
            "clauses_draft": (
                "Cláusula específica A: El Cliente facilitará acceso de solo "
                "lectura a su tenant Microsoft 365 para el discovery de evidencias.\n"
                "Cláusula específica B: Dado el carácter de proveedor de la AAPP, "
                "el Cliente comunicará a FULKRO cualquier requisito de "
                "categorización heredado del órgano de contratación."
            ),
        },
    )


def _dump_docx_text(data: bytes) -> str:
    doc = Document(io.BytesIO(data))
    lines: list[str] = []
    body = doc.element.body
    # Recorre el cuerpo en orden (párrafos + tablas).
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            p = Paragraph(child, doc)
            txt = p.text.strip()
            if txt:
                lines.append(txt)
        elif child.tag.endswith("}tbl"):
            tbl = Table(child, doc)
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells]
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def main() -> None:
    ctx = _build_sample_ctx()
    data = generate_legal_docx("contrato_prestacion_servicios", ctx).getvalue()
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "contract_c001_preview.docx"
    out_path.write_bytes(data)
    print(f"DOCX generado: {out_path} ({len(data)} bytes)\n")
    print("=" * 72)
    print(_dump_docx_text(data))
    print("=" * 72)


if __name__ == "__main__":
    main()
