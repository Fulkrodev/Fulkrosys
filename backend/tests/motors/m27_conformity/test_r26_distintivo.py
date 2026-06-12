"""R26 · Distintivo de Conformidad (CCN-STIC 809) persistido + adjunto + slot cert.

Verifica empíricamente (BD real · RLS enforced):
- attach_distintivo_on_registered transiciona CONFORMANT→REGISTERED, crea el
  Document E-049 (clasificacion 'conformidad'), lo enlaza a la ruta · idempotente.
- emisión antes de CONFORMANT → error.
- build_distintivo_context puebla client_domicilio desde clients.domicilio_fiscal.
- generate_declaration_docx es category-aware (BÁSICA autoevaluación · MEDIA/ALTA
  «no sustituye al certificado de la entidad acreditada»).
- attach_external_certificate: solo CERTIFICACIÓN (MEDIA/ALTA), exige PDF, enlaza
  external_cert_document_id · BÁSICA lo rechaza.
- read_distintivo_bytes nunca 503 (regenera si no hay MinIO).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.database import set_tenant_context
from backend.app.models.conformity_lifecycle import ConformityRouteRow
from backend.app.models.documents import Document
from backend.app.motors.m27_conformity.distintivo_generator import (
    DistintivoContext,
    build_distintivo_context,
    derive_cert_id,
    generate_declaration_docx,
)
from backend.app.motors.m27_conformity.distintivo_persistence import (
    DISTINTIVO_TEMPLATE_CODIGO,
    EXTERNAL_CERT_TEMPLATE_CODIGO,
    DistintivoIssueError,
    attach_distintivo_on_registered,
    attach_external_certificate,
    read_distintivo_bytes,
)
from backend.tests.conftest import _admin_setup, setup_test_project


async def _project_with_route(db, *, categoria: str, status: str, domicilio: str = ""):
    client_id, project_id = await setup_test_project(db)
    cid, pid = uuid.UUID(client_id), uuid.UUID(project_id)
    route_type = "declaracion_basica" if categoria == "BASICA" else "certificacion_enac"
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET categoria_objetivo = :c WHERE id = :p"
        ), {"c": categoria, "p": project_id})
        if domicilio:
            await db.execute(sa_text(
                "UPDATE clients SET domicilio_fiscal = :d WHERE id = :c"
            ), {"d": domicilio, "c": client_id})
    await set_tenant_context(db, client_id=cid, project_id=pid)
    route = ConformityRouteRow(
        project_id=pid, route_type=route_type, status=status,
    )
    db.add(route)
    await db.flush()
    return cid, pid, route


async def test_issue_transitions_and_attaches_idempotent(db):
    _, pid, route = await _project_with_route(db, categoria="MEDIA", status="CONFORMANT")

    res = await attach_distintivo_on_registered(db, pid)
    assert res["route_state"] == "REGISTERED"
    assert res["transitioned_to_registered"] is True
    doc_id = res["distintivo_document_id"]

    doc = await db.get(Document, uuid.UUID(doc_id))
    assert doc is not None
    assert doc.template_codigo == DISTINTIVO_TEMPLATE_CODIGO
    assert doc.clasificacion == "conformidad"
    assert "Distintivo de Conformidad" in doc.nombre
    assert route.distintivo_document_id == doc.id

    # Idempotente: 2ª llamada NO crea otro Document.
    res2 = await attach_distintivo_on_registered(db, pid)
    assert res2["distintivo_document_id"] == doc_id
    count = (await db.execute(
        select(Document).where(
            Document.project_id == pid,
            Document.template_codigo == DISTINTIVO_TEMPLATE_CODIGO,
            Document.deleted_at.is_(None),
        )
    )).scalars().all()
    assert len(count) == 1


async def test_issue_rejected_before_conformant(db):
    _, pid, _ = await _project_with_route(db, categoria="MEDIA", status="ROUTE_LOCKED")
    with pytest.raises(DistintivoIssueError):
        await attach_distintivo_on_registered(db, pid)


async def test_build_context_populates_domicilio(db):
    _, pid, _ = await _project_with_route(
        db, categoria="BASICA", status="CONFORMANT", domicilio="Calle Mayor 1, 28013 Madrid",
    )
    ctx = await build_distintivo_context(db, pid)
    assert ctx.client_domicilio == "Calle Mayor 1, 28013 Madrid"


def _ctx(cat: str) -> DistintivoContext:
    pid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    return DistintivoContext(
        project_id=pid, cert_id=derive_cert_id(pid), client_name="Acme S.L.",
        client_cif="B12345678", client_domicilio="Calle Mayor 1, Madrid",
        system_name="Sede electrónica", system_category=cat, today="2026-05-05",
        expiry_date="2028-05-05", public_badge_url="https://x/badge.svg",
        services_summary="x", information_summary="y", assets_essential_count=8,
        dda_total=73, dda_aplicables=68, dda_con_refuerzos=12, dda_no_aplica=5,
        conformes_count=66, no_conformes_count=14, pct_conformidad=82.5,
        rseg_name="Ana Ruiz", rseg_email="ana@acme.es",
        sponsor_name="Dir Acme", sponsor_email="dir@acme.es",
    )


def test_declaration_docx_category_aware_basica():
    import io
    import zipfile
    data = generate_declaration_docx(_ctx("BASICA")).getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    assert "autoevaluación CCN-STIC 809" in xml or "autoevaluación" in xml
    assert "Distintivo de Conformidad con el ENS" in xml


def test_declaration_docx_category_aware_media_disclaims_certificado():
    import io
    import zipfile
    data = generate_declaration_docx(_ctx("MEDIA")).getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    # Para MEDIA/ALTA el distintivo NO sustituye al certificado de la entidad acreditada.
    assert "entidad de certificación acreditada" in xml
    assert "sustituye" in xml


async def test_external_certificate_only_certification(db):
    _, pid_basica, _ = await _project_with_route(db, categoria="BASICA", status="CONFORMANT")
    with pytest.raises(DistintivoIssueError):
        await attach_external_certificate(
            db, pid_basica, filename="cert.pdf",
            content=b"%PDF-1.4 fake", content_type="application/pdf",
        )

    _, pid_media, route = await _project_with_route(db, categoria="MEDIA", status="REGISTERED")
    res = await attach_external_certificate(
        db, pid_media, filename="cert.pdf",
        content=b"%PDF-1.4 contenido certificado acreditado",
        content_type="application/pdf",
    )
    doc = await db.get(Document, uuid.UUID(res["external_cert_document_id"]))
    assert doc.template_codigo == EXTERNAL_CERT_TEMPLATE_CODIGO
    assert doc.clasificacion == "certificado"
    assert route.external_cert_document_id == doc.id


async def test_external_certificate_rejects_non_pdf(db):
    _, pid, _ = await _project_with_route(db, categoria="ALTA", status="REGISTERED")
    with pytest.raises(DistintivoIssueError):
        await attach_external_certificate(
            db, pid, filename="cert.txt", content=b"not a pdf",
            content_type="text/plain",
        )


async def test_read_distintivo_bytes_never_fails(db):
    _, pid, _ = await _project_with_route(db, categoria="MEDIA", status="CONFORMANT")
    await attach_distintivo_on_registered(db, pid)
    data, filename = await read_distintivo_bytes(db, pid)
    assert data[:2] == b"PK"  # DOCX (zip) magic
    assert filename.endswith(".docx")
    assert "Distintivo_Conformidad_ENS" in filename
