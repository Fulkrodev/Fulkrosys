"""Regresión (sim BÁSICA/MEDIA/ALTA 2026-06-13): TODOS los entregables que el
ciclo necesita deben estar en el catálogo (template_catalog_v1.yaml) Y tener su
DOCX construido — si no, /documents/generate da 404 'Template not found' y el
entregable se queda 'pillado' (p.ej. E-808 bloqueaba el cierre BÁSICA · 17 huecos).

Invariantes:
1. Todo código en REQUIRED_DELIVERABLES[BASICA|MEDIA|ALTA] está en el catálogo YAML.
2. Todo código E-* del registry m06 (deliverables/policies/procedures) está en el catálogo.
3. Todo entregable del catálogo (categoría entregable/politica/procedimiento) tiene
   su DOCX construido en var/templates_docx/{codigo}.docx.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from backend.app.motors.m06_document_factory.template_registry import TEMPLATE_REGISTRY
from backend.app.motors.m09_audit_prep.checklist_service import REQUIRED_DELIVERABLES

_ROOT = Path(__file__).resolve().parents[4]
_CATALOG = _ROOT / "docs" / "catalogs" / "template_catalog_v1.yaml"
_DOCX_DIR = _ROOT / "var" / "templates_docx"


def _catalog_codes() -> set[str]:
    data = yaml.safe_load(_CATALOG.read_text(encoding="utf-8"))
    return {t["codigo"] for t in data["templates"]}


def test_all_required_deliverables_in_catalog():
    cat = _catalog_codes()
    missing: dict[str, list[str]] = {}
    for categoria in ("BASICA", "MEDIA", "ALTA"):
        gaps = [c for c in REQUIRED_DELIVERABLES[categoria] if c not in cat]
        if gaps:
            missing[categoria] = gaps
    assert not missing, f"Entregables REQUERIDOS sin entrada en el catálogo: {missing}"


def test_all_registry_deliverable_codes_in_catalog():
    """Todo E-* del registry (deliverables/policies/procedures) debe estar en el
    catálogo (evita la deriva registry↔catálogo que dejó E-808 'pillado')."""
    cat = _catalog_codes()
    gaps = [
        code for code, meta in TEMPLATE_REGISTRY.items()
        if str(code).startswith("E-")
        and meta.get("type") in ("deliverables", "policies", "procedures")
        and code not in cat
    ]
    assert not gaps, f"Códigos del registry m06 ausentes del catálogo: {sorted(gaps)}"


def test_catalog_entregables_have_docx_built():
    """Todo entregable/política/procedimiento del catálogo tiene su DOCX construido
    (si falta, sync-catalog deja docx_path vacío → 404 'DOCX file not found')."""
    data = yaml.safe_load(_CATALOG.read_text(encoding="utf-8"))
    missing = [
        t["codigo"] for t in data["templates"]
        if t.get("categoria") in ("entregable", "politica", "procedimiento")
        and not (_DOCX_DIR / f"{t['codigo']}.docx").exists()
    ]
    assert not missing, f"Entregables del catálogo sin DOCX en var/templates_docx/: {sorted(missing)}"


def test_audit_questions_documento_esperado_valid():
    """Regresión (bug-hunt 2026-06-14): cada documento_esperado del simulador M10
    debe ser None o un código de plantilla REAL del catálogo. Antes varias medidas
    apuntaban a plantillas de medida ajena (op.exp.2→E-210, op.cont.1→E-500, etc.)
    → el simulador daba falsos conformes/NC y guiaba mal al cliente."""
    from backend.app.motors.m10_audit_sim.audit_questions import AUDIT_QUESTIONS
    cat = _catalog_codes()
    bad = {
        code: q.get("documento_esperado")
        for code, q in AUDIT_QUESTIONS.items()
        if q.get("documento_esperado") and q["documento_esperado"] not in cat
    }
    assert not bad, f"documento_esperado apunta a plantillas inexistentes en el catálogo: {bad}"
