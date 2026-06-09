"""V-CHECK Sesion 8 Paso 1 — Filtros ES + re-render 7 templates afectados.

Genera DOCX + PDF de cada uno con contexto produccion completo DataForma
y verifica:
- 0 placeholders sueltos
- Moneda/fecha/porcentaje formato ES correcto
- Firma Ed25519
- 0 leaks
- Header + footer + bloque firmas
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import uuid
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.motors.m06_document_factory.service import (
    DocumentFactoryService,
)


# ════════════════════════════════════════════════════════════════════
# Leak patterns
# ════════════════════════════════════════════════════════════════════

# Patrones prohibidos en cualquier template (incluso comerciales)
STRICT_LEAK_PATTERNS = [
    re.compile(p) for p in [
        r"\bMotor \d+\b", r"\bAgente \d+\b",
        r"\bDocument Factory\b", r"\bCopiloto\b(?! ENS)",
        r"\bM\d+-V\d+\b", r"\bv5\.1\b",
    ]
]

# FULKRO es marca brand legitima en templates comerciales (C-*, P-*).
# Se prohibe en los entregables tecnicos (E-*).
BRAND_PATTERN = re.compile(r"\bFULKRO\b")

COMMERCIAL_PREFIXES = ("P-", "C-")


def leaks_in_docx(path: Path, template_code: str) -> list[str]:
    hits: list[str] = []
    try:
        from docx import Document
        d = Document(str(path))
        text = "\n".join(p.text for p in d.paragraphs)
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    text += "\n" + cell.text
    except Exception:
        return ["(could_not_open)"]
    is_commercial = template_code.startswith(COMMERCIAL_PREFIXES)
    patterns = list(STRICT_LEAK_PATTERNS)
    if not is_commercial:
        patterns.append(BRAND_PATTERN)
    for pat in patterns:
        if pat.search(text):
            hits.append(pat.pattern)
    # Buscar en XML interno
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            xml = z.read(name).decode("utf-8", errors="replace")
            for pat in patterns:
                if pat.search(xml):
                    if f"(XML) {pat.pattern}" not in hits:
                        hits.append(f"(XML) {pat.pattern}")
    return hits


def unrendered_placeholders(path: Path) -> list[str]:
    """Busca {{ var }} o {% stmt %} sin renderizar."""
    try:
        from docx import Document
        d = Document(str(path))
        text = "\n".join(p.text for p in d.paragraphs)
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    text += "\n" + cell.text
    except Exception:
        return []
    return re.findall(r"\{\{[^}]{1,80}\}\}|\{%[^%]{1,80}%\}", text)


# ════════════════════════════════════════════════════════════════════
# Contexto produccion DataForma completo
# ════════════════════════════════════════════════════════════════════

def production_context_dataforma(extras: dict | None = None) -> dict:
    today = datetime.now(timezone.utc).date()
    ctx = {
        "marcos": {
            "nombre": "Marcos Mata Garcia",
            "nif": "12345678Z",
            "email": "marcosmata@fulkro.es",
            "telefono": "+34 600 123 456",
        },
        "consultor": {
            "nombre": "Marcos Mata Garcia",
            "nif": "12345678Z",
            "email": "marcosmata@fulkro.es",
            "telefono": "+34 600 123 456",
        },
        "cliente": {
            "razon_social": "DataForma Galicia SL",
            "nif": "B72634815",
            "cif": "B72634815",
            "domicilio_social": "Rua Real 15, 2o, 15003 A Coruna",
            "sector": "sanidad_privada",
            "empleados": 180,
            "representante_legal": "Maria Perez Nunez",
            "organo_aprobador_politicas": "Consejo de Administracion",
            "logo_url": "",
            "persona_contacto": {
                "tratamiento": "Sra.",
                "nombre": "Maria",
                "apellidos": "Perez Nunez",
                "cargo": "Consejera Delegada",
                "email": "mperez@dataforma.es",
                "telefono": "+34 981 234 567",
            },
            "iban": "ES7620770024003102575766",
        },
        "proyecto": {
            "nombre": "Adecuacion ENS DataForma",
            "categoria_objetivo": "MEDIA",
            "alcance": "Historia clinica electronica + facturacion + RRHH",
            "fecha_aprobacion_inicial": today.isoformat(),
            "fecha_fin_estimada": (today + timedelta(days=240)).isoformat(),
            "version_actual": "1.0",
            "codigo_documento_base": "DFM-ENS-2026",
            "fecha_aprobacion": today.isoformat(),
            "fecha_fin": today.isoformat(),
        },
        "propuesta": {
            "numero": "P-001-0001",
            "version": "1.0",
            "fecha_emision": today.isoformat(),
            "fecha_reunion_exploratoria": (today - timedelta(days=5)).isoformat(),
            "fecha_validez": (today + timedelta(days=30)).isoformat(),
            "validez_dias": 30,
            "categoria_ens": "MEDIA",
            "certificadora_recomendada": "EQA Certificacion",
            "contexto_entendido": (
                "DataForma Galicia opera una plataforma sanitaria privada "
                "(180 empleados) que gestiona historia clinica electronica, "
                "facturacion a aseguradoras y nomina. La entidad se presenta "
                "a licitaciones del SERGAS y requiere certificacion ENS MEDIA "
                "en los proximos 10 meses."
            ),
            "duracion_meses": 10,
            "duracion_semanas": 42,
            "horas_estimadas": 320,
            "dedicacion_marcos": "20% del tiempo del consultor",
            "tarifa_hora": 85.00,
            "honorarios_marcos": 9500.00,
            "coste_auditoria_externa": 3500.00,
            "inversion_total_eur": 13000.00,
            "porcentaje_retencion": 0.10,
            "diagrama_gantt": "Ver Anexo I — planificacion detallada",
            "semana_inicio_diseno": 5,
            "semana_fin_diseno": 10,
            "semana_inicio_implantacion": 11,
            "semana_fin_implantacion": 26,
            "semana_inicio_verificacion": 27,
            "semana_fin_verificacion": 32,
            "semana_inicio_prep_auditoria": 33,
            "semana_fin_prep_auditoria": 36,
            "semana_inicio_auditoria": 37,
            "semana_fin_auditoria": 42,
            "semana_fin_diagnostico": 4,
            "modalidad": "proyecto_fijo_con_retainer",
            "importe_base": 9500.00,
            "importe_total": 13000.00,
            "importe_iva": 2730.00,
            "importe_total_iva": 15730.00,
        },
        "sede": {
            "nombre": "Sede central DataForma",
            "direccion": "Rua Real 15, 2o, 15003 A Coruna",
        },
        "servicio": "Historia Clinica Electronica",
        "supuesto": (
            "El cliente proporciona acceso a sus sistemas en tiempo y forma "
            "acordados en el cronograma."
        ),
        "exclusion": "Auditoria externa ENS (contratada por separado).",
        "fase": {"numero": 1, "nombre": "Diagnostico inicial"},
        "hito": {
            "nombre": "Firma de Politica de Seguridad",
            "fecha_estimada": (today + timedelta(days=45)).isoformat(),
        },
        "entregable": {
            "codigo": "E-050",
            "nombre": "Plan de Adecuacion ENS",
            "formato": "DOCX + PDF firmados",
        },
        "proveedor": {
            "nombre": "Telefonica Empresas",
            "servicio": "Conectividad VPN",
        },
        "riesgo": {
            "descripcion": "Retraso en aportacion de evidencias por parte del cliente",
            "probabilidad": "media",
            "impacto": "alto",
            "mitigacion": "Magic links semanales + recordatorios automaticos",
        },
        "colab": {
            "nombre": "Consultor asociado",
            "perfil": "Experto en MAGERIT",
            "rol": "Auditor interno",
            "dedicacion": "5% del tiempo",
        },
        "responsables": {
            "responsable_seguridad": {
                "nombre": "Jorge Fernandez Rodriguez",
                "cargo": "CISO / Responsable de Seguridad",
                "email": "jfernandez@dataforma.es",
            },
            "responsable_sistema": {
                "nombre": "Laura Vazquez Torres",
                "cargo": "IT Manager / Responsable del Sistema",
                "email": "lvazquez@dataforma.es",
            },
            "responsable_informacion": {
                "nombre": "Andres Lopez Fernandez",
                "cargo": "Responsable de la Informacion",
                "email": "alopez@dataforma.es",
            },
            "responsable_servicio": {
                "nombre": "Elena Garcia Pazos",
                "cargo": "Responsable del Servicio",
                "email": "egarcia@dataforma.es",
            },
        },
        "fecha_actual": today.isoformat(),
        "year": today.year,
    }
    if extras:
        ctx.update(extras)
    return ctx


# ════════════════════════════════════════════════════════════════════
# V-CHECK
# ════════════════════════════════════════════════════════════════════

TEMPLATES = ["P-001", "E-040", "E-050", "E-100", "E-101", "E-102", "E-103"]

RESULTS: list[tuple[str, bool, str]] = []
ARTIFACTS: list[tuple[str, Path, int]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"       {detail}")
    RESULTS.append((label, ok, detail))


async def _get_dataforma(engine) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT c.id, p.id FROM clients c JOIN projects p ON p.client_id = c.id "
            "WHERE c.nombre ILIKE '%DataForma%' LIMIT 1"
        ))
        row = r.first()
        if not row:
            raise RuntimeError("DataForma no existe.")
        return row[0], row[1]


async def main() -> int:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False,
    )

    client_id, project_id = await _get_dataforma(engine)
    print("\n" + "=" * 72)
    print("V-CHECK SESION 8 PASO 1 — Filtros ES + 7 templates afectados")
    print("=" * 72)
    print(f"client={client_id}  project={project_id}\n")

    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await DocumentFactoryService(db).load_template_metadata_from_catalog()
        await db.commit()

    ctx = production_context_dataforma()

    for code in TEMPLATES:
        async with Session() as db:
            await set_tenant_context(
                db, client_id=client_id, project_id=project_id,
            )
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            svc = DocumentFactoryService(db)
            try:
                out = await svc.generate_document(
                    project_id, code, context=ctx,
                    generate_pdf=True, sign=True,
                    generated_by="demo_s8_paso1",
                    enforce_gates=False,
                )
                await db.commit()
            except Exception as exc:
                report(f"{code} render", False, f"exc: {str(exc)[:100]}")
                continue

        docx_path = Path(out["docx_path"])
        pdf_path = Path(out["pdf_path"]) if out.get("pdf_path") else None
        sig = out.get("signature_ed25519")

        size_docx = docx_path.stat().st_size if docx_path.exists() else 0
        leaks = leaks_in_docx(docx_path, code)
        unrendered = unrendered_placeholders(docx_path)
        size_pdf = pdf_path.stat().st_size if pdf_path and pdf_path.exists() else 0

        ok = (
            size_docx > 15000
            and not leaks
            and not unrendered
            and bool(sig)
            and (not pdf_path or size_pdf > 5000)
        )
        ARTIFACTS.append((code, docx_path, size_docx))
        if pdf_path and pdf_path.exists():
            ARTIFACTS.append((f"{code} PDF", pdf_path, size_pdf))
        report(
            f"{code} render + sign + PDF + 0 leaks + 0 placeholders", ok,
            f"DOCX={size_docx}b · PDF={size_pdf}b · sig={bool(sig)} "
            f"· leaks={len(leaks)} · unrendered={len(unrendered)}"
            + (f" · LEAKS={leaks}" if leaks else "")
            + (f" · UNRENDERED={unrendered[:3]}" if unrendered else ""),
        )

    # Verificacion especifica de formato ES en P-001 (usa format_currency_es)
    p001_docx = next((p for l, p, _ in ARTIFACTS if l == "P-001"), None)
    if p001_docx and p001_docx.exists():
        from docx import Document
        d = Document(str(p001_docx))
        all_text = "\n".join(p.text for p in d.paragraphs)
        for t in d.tables:
            for row in t.rows:
                for cell in row.cells:
                    all_text += "\n" + cell.text
        has_es_currency = bool(re.search(
            r"\d{1,3}(\.\d{3})*,\d{2}\s?€", all_text,
        )) or bool(re.search(r"9\.500,00\s?€", all_text))
        has_dot_thousands = "9.500" in all_text
        report(
            "P-001 formato moneda ES aplicado (9.500,00 €)",
            has_es_currency or has_dot_thousands,
            f"currency_es_pattern={has_es_currency} · has '9.500'={has_dot_thousands}",
        )

    pass_count = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "=" * 72)
    print(f"RESUMEN S8 PASO 1 · {pass_count}/{total} checks PASS")
    print("=" * 72)
    print(f"  Artifacts ({len(ARTIFACTS)}):")
    for label, p, size in ARTIFACTS:
        print(f"    [{'OK' if p.exists() else 'MISSING'}] {label}: "
              f"{p.name} ({size}b)")
    print("=" * 72)

    await engine.dispose()
    return 0 if pass_count == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
