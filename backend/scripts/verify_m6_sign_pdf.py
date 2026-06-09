"""Gap 2+3 verification: M6 Ed25519 sign + LibreOffice PDF conversion.

Renders E-100 for DataForma with ``sign=True, generate_pdf=True`` and
verifies:
1. ``rendered_hash`` is a 64-char hex SHA-256 of the DOCX bytes.
2. ``signature_ed25519`` is a valid hex Ed25519 signature over that hash.
3. A PDF file exists at ``pdf_path`` with a valid ``%PDF-`` header.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path

os.environ["FULKRO_SKIP_WORKFLOW_GATES"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.motors.m06_document_factory.service import DocumentFactoryService
from backend.app.motors.m06_document_factory.signing import verify_bytes


def _ctx_for(client_row, project_row):
    from datetime import date, timedelta
    today = date.today()
    kickoff = today - timedelta(weeks=2)
    return {
        "cliente": {
            "razon_social": client_row["nombre"], "nif": client_row["cif"],
            "cif": client_row["cif"], "sector": client_row["sector"],
            "empleados": client_row["numero_empleados"],
            "numero_empleados": client_row["numero_empleados"],
            "domicilio_social": "Rúa do Camiño, 12, 3ª planta · 15004 A Coruña",
            "representante_legal": "María Pérez Núñez",
            "contacto_email": client_row["contacto_email"],
            "organo_aprobador_politicas": "Comité de Dirección",
            "provincia": client_row["provincia"],
        },
        "responsables": {
            "responsable_seguridad": {
                "nombre": "Jorge Fernández Rodríguez",
                "cargo": "CISO", "email": "rseg@dataforma.es",
            },
            "comite_seguridad": {
                "presidente": "María Pérez Núñez",
                "secretario": "Jorge Fernández Rodríguez",
                "frecuencia_reuniones": "Trimestral",
                "miembros": [],
            },
            "delegado_proteccion_datos": {
                "nombre": "Raquel Cabrera Gómez",
                "cargo": "DPO externa",
            },
        },
        "proyecto": {
            "id": str(project_row["id"]), "nombre": project_row["nombre"],
            "codigo_documento_base": "POL", "version_actual": "1.0",
            "categoria": "MEDIA", "categoria_ens": "MEDIA",
            "fecha_inicio": kickoff.isoformat(),
            "fecha_aprobacion_inicial": today.isoformat(),
            "proxima_revision": (today + timedelta(days=365)).isoformat(),
            "alcance": {
                "descripcion": "Sistemas clínicos digitales",
                "servicios_incluidos": ["Historia clínica"],
                "exclusiones": [],
            },
        },
    }


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.connect() as conn:
        trans = await conn.begin()
        db = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            qc = await db.execute(sa_text(
                "SELECT id, nombre, cif, sector, provincia, numero_empleados, "
                "contacto_email FROM clients WHERE lead_source='seed' "
                "AND nombre LIKE 'DataForma%' LIMIT 1"
            ))
            client = qc.mappings().first()
            await set_tenant_context(db, client_id=client["id"])
            qp = await db.execute(sa_text(
                "SELECT id, nombre, categoria_objetivo FROM projects "
                "WHERE client_id=:cid AND categoria_objetivo='M' LIMIT 1"
            ), {"cid": str(client["id"])})
            proj = qp.mappings().first()
            await set_tenant_context(
                db, client_id=client["id"], project_id=proj["id"]
            )

            svc = DocumentFactoryService(db)
            result = await svc.generate_document(
                project_id=proj["id"],
                template_codigo="E-100",
                context=_ctx_for(dict(client), dict(proj)),
                generate_pdf=True,
                sign=True,
                generated_by="verify_gap_2_3",
                enforce_gates=False,
            )
        finally:
            await trans.rollback()
            await db.close()
    await engine.dispose()

    print("=" * 72)
    print("GAP 2 + 3 VERIFICATION — E-100 for DataForma with sign + PDF")
    print("=" * 72)
    docx_path = Path(result.get("docx_path") or "")
    pdf_path_raw = result.get("pdf_path")
    pdf_path = Path(pdf_path_raw) if pdf_path_raw else None
    rendered_hash = result.get("rendered_hash") or result.get("hash_sha256")
    signature_hex = result.get("signature_ed25519")

    # --- GAP 2: Ed25519 signing ---
    print(f"\nGAP 2 — Ed25519 firma técnica")
    print(f"  DOCX path:     {docx_path}")
    print(f"  DOCX size:     {docx_path.stat().st_size if docx_path.exists() else 'MISSING'}")
    docx_bytes = docx_path.read_bytes() if docx_path.exists() else b""
    computed = hashlib.sha256(docx_bytes).hexdigest() if docx_bytes else "(no bytes)"
    print(f"  hash stored:   {rendered_hash}")
    print(f"  hash recomp:   {computed}")
    print(f"  hash match:    {'OK ✅' if computed == rendered_hash else 'MISMATCH ❌'}")
    print(f"  signature hex: {signature_hex[:48] + '…' if signature_hex else 'MISSING'}")
    if signature_hex and docx_bytes:
        # sign_document() signs the raw DOCX bytes (not the hash string),
        # so verification must use the same raw bytes.
        try:
            ok = verify_bytes(docx_bytes, bytes.fromhex(signature_hex))
        except Exception as exc:
            ok = False
            print(f"  verify error:  {exc}")
        print(f"  signature OK:  {'OK ✅' if ok else 'INVALID ❌'}")

    # --- GAP 3: LibreOffice PDF conversion ---
    print(f"\nGAP 3 — Conversión DOCX → PDF vía LibreOffice headless")
    if pdf_path and pdf_path.exists():
        pdf_bytes = pdf_path.read_bytes()
        has_header = pdf_bytes[:5] == b"%PDF-"
        print(f"  PDF path:      {pdf_path}")
        print(f"  PDF size:      {pdf_path.stat().st_size} bytes")
        print(f"  PDF header:    {'OK ✅' if has_header else 'INVALID ❌'} "
              f"({pdf_bytes[:8]!r})")
    else:
        print(f"  PDF path:      MISSING")
        print(f"  status:        ❌ FAILED")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
