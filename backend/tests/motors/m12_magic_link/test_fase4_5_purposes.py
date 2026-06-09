"""Tests integración FASE 4.5 sub-bloque B.1.

Cobertura:
- 12 tests parametrize generate→by-token→consume cycle por purpose nuevo
  (#24-#35 ADR-011)
- 12 tests parametrize email render con scope realistic
- 2 tests endpoint GET / list (filter + RBAC pattern unit)
- 2 tests cc_emails + custom_subject/body persistence

Total: 28 tests · suite m12 esperada 55 + 28 = 83 passed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from backend.app.auth.dependencies import require_owner
from backend.app.database import set_tenant_context
from backend.app.models.operations import MagicLink
from backend.app.motors.m12_magic_link.api import router as m12_router
from backend.app.motors.m12_magic_link.emails.renderer import (
    render_email_for_magic_link,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import (
    MagicLinkNotFoundError,
    MagicLinkService,
)
from backend.tests.conftest import setup_test_project


BASE = "/api/v1/magic-links"

# FASE 4.5 ADR-011 originalmente 12 purposes. Post-MB-4.bis2 (ADR-020):
# 11 deprecated_soft v3 (cliente in-portal · hard-rejected). Solo
# APROBACION_PROPUESTA mantiene razón (pre-cliente comercial sin cuenta
# portal). Tests parametrize full cycle cubren solo legitimate.
FASE_4_5_PURPOSES: list[MagicLinkPurpose] = [
    MagicLinkPurpose.APROBACION_PROPUESTA,
]
# Purposes deprecated v3 (skip parametrize · hard-rejected en MagicLinkService):
# INVITACION_REUNION, APROBACION_FACTURA, SOLICITUD_INFORMACION,
# VALIDACION_CAMBIO_ALCANCE, ACEPTACION_RIESGO_RESIDUAL,
# COMUNICACION_INCIDENTE_SEGURIDAD, CONSENTIMIENTO_TRATAMIENTO_DATOS,
# CONFIRMACION_CONFORMIDAD, DESCARGA_CERTIFICADO_CONFORMIDAD,
# VOTACION_COMITE_SEGURIDAD, ENCUESTA_SATISFACCION_NPS


# Realistic scope per purpose · variables Jinja sub-bloque A · NO Lorem.
_SCOPE_BY_PURPOSE: dict[MagicLinkPurpose, dict] = {
    MagicLinkPurpose.INVITACION_REUNION: {
        "reunion_titulo": "Comité Directivo Q2",
        "reunion_fecha": "2026-05-20",
    },
    MagicLinkPurpose.APROBACION_PROPUESTA: {"propuesta_codigo": "P-001-2026"},
    MagicLinkPurpose.APROBACION_FACTURA: {
        "factura_codigo": "F-2026-042",
        "factura_importe": "9.500,00 €",
    },
    MagicLinkPurpose.SOLICITUD_INFORMACION: {"asunto_corto": "inventario de activos"},
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE: {"cambio_codigo": "CCA-2026-003"},
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL: {"riesgo_codigo": "R-AR-017"},
    MagicLinkPurpose.COMUNICACION_INCIDENTE_SEGURIDAD: {
        "incidente_codigo": "INC-2026-009",
        "severidad": "ALTA",
    },
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS: {},
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD: {},
    MagicLinkPurpose.DESCARGA_CERTIFICADO_CONFORMIDAD: {},
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD: {
        "acta_codigo": "Acta-Comite-2026-04",
        "sesion_fecha": "2026-04-15",
    },
    MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS: {},
}


# ════════════════════════════════════════════════════════════════════
# 12 tests · generate → by-token → consume cycle (parametrize)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", FASE_4_5_PURPOSES, ids=lambda p: p.value)
async def test_purpose_generate_consume_full_cycle(purpose, async_client, db):
    """Cada purpose nuevo: generate → by-token public → consume cycle.

    Valida:
    1. POST /generate retorna 201 con token + (opcionalmente) OTP
    2. GET /by-token/{token} retorna PublicStatus subset estricto
    3. POST /consume con OTP (si requerido) retorna 200 + scope
    4. recipient_email_hint enmascarado correctamente
    """
    client_id, project_id = await setup_test_project(db)
    scope = _SCOPE_BY_PURPOSE[purpose]

    # 1. Generate
    gen = await async_client.post(
        f"{BASE}/generate",
        json={
            "project_id": project_id,
            "purpose": purpose.value,
            "recipient_email": "rseg@dataforma.es",
            "scope": scope,
        },
    )
    assert gen.status_code == 201, f"{purpose.value}: {gen.status_code} {gen.text}"
    gen_data = gen.json()
    assert gen_data["purpose"] == purpose.value
    token = gen_data["token"]

    # 2. By-token public status
    status_resp = await async_client.get(f"{BASE}/by-token/{token}")
    assert status_resp.status_code == 200, status_resp.text
    sd = status_resp.json()
    assert sd["tipo_operacion"] == purpose.value
    assert sd["scope"] == scope
    assert sd["revocado"] is False
    assert sd["usos"] == 0
    # Privacidad: hint enmascarado, NO email completo
    assert sd["recipient_email_hint"] == "rse***@dataforma.es"
    # Privacidad: campos sensibles NO presentes en response
    for forbidden in ("id", "project_id", "recipient_email", "cc_emails", "custom_subject"):
        assert forbidden not in sd, f"{purpose.value}: leaked {forbidden}"

    # 3. Consume
    consume_payload = {"token": token}
    if gen_data.get("otp"):
        consume_payload["otp"] = gen_data["otp"]
    consume = await async_client.post(f"{BASE}/consume", json=consume_payload)
    assert consume.status_code == 200, f"{purpose.value} consume: {consume.text}"
    cd = consume.json()
    assert cd["purpose"] == purpose.value


# ════════════════════════════════════════════════════════════════════
# 12 tests · email render con scope realistic (parametrize · no DB)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("purpose", FASE_4_5_PURPOSES, ids=lambda p: p.value)
def test_purpose_email_renders_realistic_scope(purpose):
    """Email render con scope realistic NO lanza, interpola variables y
    cumple memoria interna (sin refs Motor X / Agente X)."""
    cliente = {"razon_social": "DataForma Galicia SL", "cif": "B72634815"}
    proyecto = {"nombre": "Certificación ENS Media — 2026", "codigo_documento_base": "POL"}
    destinatario = {"nombre": "Jorge Fernández", "cargo": "RSEG", "email": "rseg@dataforma.es"}

    extra = dict(_SCOPE_BY_PURPOSE[purpose])
    # Variables existing del test invariante existing (cobertura común)
    extra.setdefault("documento", {"codigo": "E-100", "titulo": "Política"})
    extra.setdefault("medida", {"codigo": "op.acc.6"})

    subject, html, text = render_email_for_magic_link(
        purpose=purpose,
        link_url="https://fulkro.es/ml/consume?token=abc",
        expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        cliente=cliente,
        proyecto=proyecto,
        destinatario=destinatario,
        otp="123456",
        **extra,
    )

    assert subject, f"{purpose.value}: empty subject"
    assert "<!DOCTYPE html>" in html, f"{purpose.value}: not full HTML"
    assert "Marcos Mata García" in html
    assert "Marcos Mata García" in text
    # Sin refs internas (regla feedback memory)
    for forbidden in ("Motor 12", "Motor 30", "Agente ", "Document Factory", "Copiloto"):
        assert forbidden not in html, f"{purpose.value}: leaked {forbidden!r}"
    # Sin placeholders sin resolver del scope realistic
    for token_marker in extra:
        if isinstance(extra[token_marker], str):
            placeholder = "{" + token_marker + "}"
            assert placeholder not in html, (
                f"{purpose.value}: unresolved {placeholder} en html"
            )


# ════════════════════════════════════════════════════════════════════
# 2 tests · endpoint GET / list filter + RBAC pattern unit
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_admin_can_list_magic_links_filtered_by_purpose(async_client, db):
    """Admin (async_client stub Marcos) puede listar links filtrados."""
    client_id, project_id = await setup_test_project(db)

    # Post-MB-4.bis2: generate 2 links de purposes legitimate distintos
    # (APROBACION_PROPUESTA + FIRMA_DOCUMENTO · ambos pre/tercero · NO deprecated)
    for purpose in ("aprobacion_propuesta", "firma_documento"):
        await async_client.post(
            f"{BASE}/generate",
            json={
                "project_id": project_id,
                "purpose": purpose,
                "recipient_email": "test@example.com",
            },
        )

    # List filtered by purpose=aprobacion_propuesta → 1 row
    r = await async_client.get(
        f"{BASE}",
        params={"project_id": project_id, "purpose": "aprobacion_propuesta"},
    )
    assert r.status_code == 200, r.text
    items = r.json()
    assert len(items) == 1, f"expected 1, got {len(items)}: {items}"
    assert items[0]["tipo_operacion"] == "aprobacion_propuesta"
    assert items[0]["project_id"] == project_id
    assert items[0]["revocado"] is False
    # List item EXPONE recipient_email completo (admin · audit visibility)
    assert items[0]["recipient_email"] == "test@example.com"

    # List sin filtro → 2 rows del proyecto
    r2 = await async_client.get(f"{BASE}", params={"project_id": project_id})
    assert r2.status_code == 200
    assert len(r2.json()) == 2


def test_list_endpoint_has_require_owner_dependency():
    """Pattern repo: endpoint /magic-links list debe tener require_owner.

    Validación static · no necesita HTTP setup. Garantiza que cualquier
    cliente no-admin recibe 401/403 de la dep antes de llegar al handler.
    """
    list_route = next(
        (r for r in m12_router.routes if getattr(r, "path", None) == "/magic-links" and "GET" in r.methods),
        None,
    )
    assert list_route is not None, "GET /magic-links route no encontrada"
    # FastAPI Dependant: usar .call (la función) para compararla con require_owner
    dep_calls = [d.call for d in list_route.dependant.dependencies]
    assert require_owner in dep_calls, (
        f"GET /magic-links debe usar require_owner; deps: {dep_calls}"
    )


# ════════════════════════════════════════════════════════════════════
# 2 tests · cc_emails + custom_subject/body persistence
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_with_cc_emails_persists_array(async_client, db):
    """cc_emails se persiste como TEXT[] en BD (col migration f658961972a2)."""
    client_id, project_id = await setup_test_project(db)
    gen = await async_client.post(
        f"{BASE}/generate",
        json={
            "project_id": project_id,
            "purpose": "aprobacion_propuesta",
            "recipient_email": "main@example.com",
            "cc_emails": ["cc1@example.com", "cc2@example.com"],
        },
    )
    assert gen.status_code == 201, gen.text
    link_id = gen.json()["magic_link_id"]

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = (
        await db.execute(select(MagicLink).where(MagicLink.id == link_id))
    ).scalar_one()
    assert row.cc_emails == ["cc1@example.com", "cc2@example.com"]


@pytest.mark.asyncio
async def test_generate_with_custom_email_overrides(async_client, db):
    """custom_subject + custom_body_intro + ttl/max_uses overrides persistidos."""
    client_id, project_id = await setup_test_project(db)
    gen = await async_client.post(
        f"{BASE}/generate",
        json={
            "project_id": project_id,
            "purpose": "aprobacion_propuesta",
            "recipient_email": "test@example.com",
            "custom_subject": "Subject custom Marcos",
            "custom_body_intro": "Hola Jorge, antes del template oficial:",
            "ttl_hours": 240,
            "max_uses": 9,
        },
    )
    assert gen.status_code == 201, gen.text
    link_id = gen.json()["magic_link_id"]

    await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
    row = (
        await db.execute(select(MagicLink).where(MagicLink.id == link_id))
    ).scalar_one()
    assert row.custom_subject == "Subject custom Marcos"
    assert row.custom_body_intro == "Hola Jorge, antes del template oficial:"
    # Override TTL: aprox now+240h (default solicitud_informacion = 14*24=336h)
    delta_hours = (row.expira_at - datetime.now(timezone.utc)).total_seconds() / 3600
    assert 239 <= delta_hours <= 241, f"TTL override ignorado: {delta_hours}h"
    assert row.max_usos == 9


# ════════════════════════════════════════════════════════════════════
# Bonus · by-token 404 para token inexistente (regression guard)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_by_token_returns_404_for_unknown_token(async_client, db):
    r = await async_client.get(f"{BASE}/by-token/unknown_token_xxx")
    assert r.status_code == 404
