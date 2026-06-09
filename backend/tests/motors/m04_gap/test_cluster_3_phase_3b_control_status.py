"""CLUSTER 3 Phase 3B · compute_control_status false-green prevention tests.

Sesión 3B-2B.8 CLUSTER 3 Phase 3B · pure functional control status compute
deterministic R1 · canonical guard anti-false-green.

Ola 4 #20 (2026-06-04): el filtro por medida pasó a Evidence-based (semáforo
POR MEDIDA). La lógica Document anti-falso-verde de abajo SIGUE siendo válida y
valiosa, pero se invoca ahora por `control_id` (camino Document/agregado), no
por `measure_code` (que ahora es Evidence-based · ver TestMeasureEvidenceStatus).

Coverage:
- compute_control_status returns 'no_aplica' cuando NO documents existen
- compute_control_status returns 'verde' cuando TODOS pre-reqs cumplen
- compute_control_status returns 'amarillo' cuando documento NOT approved
- compute_control_status returns 'amarillo' cuando client_review_status != revisada_ok
- compute_control_status returns 'amarillo' cuando signing_intent NOT linked
  (para documents que requieren firma niveles 1-2)
- compute_control_status returns 'rojo' cuando documento expired
- missing_reasons explicit + R29 friendly translation
- requirements_met booleans per pre-req
- Regression: anti-false-green guard cuando severity-only would say verde

Pattern 19 cumulative formalized: anti-false-green guard pattern.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.motors.m04_gap.control_status_service import (
    ControlStatusResult,
    compute_control_status,
    translate_missing_reasons_cliente_friendly,
)
from backend.tests.conftest import _admin_setup, setup_test_project


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════


async def _create_document(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    tipo: str = "politica",
    estado: str | None = "approved",
    approved_at: datetime | None = None,
    client_review_status: str | None = None,
    client_signing_intent_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> uuid.UUID:
    """Create test Document row con flags configurables."""
    doc_id = uuid.uuid4()

    async with _admin_setup(db):
        params = {
            "id": str(doc_id),
            "pid": str(project_id),
            "tipo": tipo,
            "nombre": f"Test doc {doc_id.hex[:8]}",
            "estado": estado,
            "approved_at": approved_at,
            "review_status": client_review_status,
            "signing_intent": (
                str(client_signing_intent_id)
                if client_signing_intent_id else None
            ),
            "expires_at": expires_at,
        }
        await db.execute(text(
            "INSERT INTO documents "
            "(id, project_id, tipo, nombre, estado, approved_at, "
            "client_review_status, client_signing_intent_id, expires_at, "
            "created_at) "
            "VALUES (:id, :pid, :tipo, :nombre, :estado, :approved_at, "
            ":review_status, :signing_intent, :expires_at, now())"
        ), params)
    return doc_id


# ════════════════════════════════════════════════════════════════════
# Phase 3B · semaforo='no_aplica' cuando NO documents
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_no_documents_returns_no_aplica(db: AsyncSession) -> None:
    """compute_control_status returns 'no_aplica' cuando NO documents existen."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "no_aplica"
    assert result.documents_count == 0
    assert result.requirements_met["documents_exist"] is False
    assert any("Falta documentación" in r for r in result.missing_reasons)


# ════════════════════════════════════════════════════════════════════
# Phase 3B · semaforo='verde' cuando ALL pre-reqs cumplen
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_all_prereqs_met_returns_verde(db: AsyncSession) -> None:
    """compute_control_status returns 'verde' cuando documento approved +
    cliente reviewed + signed + NOT expired."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    signing_intent_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="politica",
        estado="approved",
        approved_at=now - timedelta(days=10),
        client_review_status="revisada_ok",
        client_signing_intent_id=signing_intent_id,
        expires_at=now + timedelta(days=365),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "verde"
    assert result.documents_count == 1
    assert result.documents_approved_count == 1
    assert result.cliente_reviewed_count == 1
    assert result.documents_signed_count == 1
    assert result.expired_count == 0
    assert all(result.requirements_met.values())
    assert result.missing_reasons == []


# ════════════════════════════════════════════════════════════════════
# Phase 3B · false-green prevention scenarios (anti-false-green guard)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_doc_not_approved_blocks_verde(db: AsyncSession) -> None:
    """Documento existe pero NOT approved → semaforo='amarillo' (anti-false-green)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="politica",
        estado="review",  # NOT approved
        approved_at=None,
        client_review_status="revisada_ok",
        client_signing_intent_id=uuid.uuid4(),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "amarillo"
    assert result.requirements_met["all_approved"] is False
    assert any("pendiente" in r and "aprobación" in r for r in result.missing_reasons)


@pytest.mark.asyncio
async def test_cliente_no_reviewed_blocks_verde(db: AsyncSession) -> None:
    """Documento approved pero cliente NO revisado → 'amarillo' (anti-false-green)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    now = datetime.now(timezone.utc)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="politica",  # require client review
        estado="approved",
        approved_at=now - timedelta(days=5),
        client_review_status="pendiente_revision",  # NOT revisada_ok
        client_signing_intent_id=uuid.uuid4(),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "amarillo"
    assert result.requirements_met["all_cliente_reviewed"] is False
    assert any("revisión" in r.lower() for r in result.missing_reasons)


@pytest.mark.asyncio
async def test_no_signing_intent_blocks_verde(db: AsyncSession) -> None:
    """Politica approved + reviewed pero NOT firmada (signing_intent NULL)
    → 'amarillo' (anti-false-green · falta firma cliente)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    now = datetime.now(timezone.utc)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="politica",
        estado="approved",
        approved_at=now - timedelta(days=5),
        client_review_status="revisada_ok",
        client_signing_intent_id=None,  # NOT signed
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "amarillo"
    assert result.requirements_met["all_signed"] is False
    assert any("firma" in r.lower() for r in result.missing_reasons)


@pytest.mark.asyncio
async def test_expired_document_returns_rojo(db: AsyncSession) -> None:
    """Documento caducado (expires_at past) → semaforo='rojo' (CRITICO)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    now = datetime.now(timezone.utc)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="politica",
        estado="approved",
        approved_at=now - timedelta(days=400),
        client_review_status="revisada_ok",
        client_signing_intent_id=uuid.uuid4(),
        expires_at=now - timedelta(days=1),  # EXPIRED 1 day ago
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    assert result.semaforo == "rojo"
    assert result.expired_count == 1
    assert result.requirements_met["no_expired"] is False
    assert any("caducado" in r.lower() for r in result.missing_reasons)


# ════════════════════════════════════════════════════════════════════
# Phase 3B · niveles 3-4 NO require cliente review
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_procedure_doc_no_client_review_required(db: AsyncSession) -> None:
    """Procedure (nivel 3) approved → 'verde' aun sin client_review_status
    (niveles 3-4 NO requieren cliente review · NULL accepted)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    now = datetime.now(timezone.utc)

    await _create_document(
        db,
        project_id=project_uuid,
        tipo="procedimiento",  # nivel 3 · NO require cliente review
        estado="approved",
        approved_at=now - timedelta(days=5),
        client_review_status=None,  # NOT required for nivel 3
        client_signing_intent_id=None,
        expires_at=now + timedelta(days=365),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, control_id=uuid.uuid4(),
    )

    # niveles 3-4: NO require cliente review NI firma
    assert result.semaforo == "verde"
    assert result.requirements_met["all_cliente_reviewed"] is True
    assert result.requirements_met["all_signed"] is True


# ════════════════════════════════════════════════════════════════════
# Phase 3B · API contract + UX translation
# ════════════════════════════════════════════════════════════════════


def test_translate_cliente_friendly_passthrough_mvp():
    """translate_missing_reasons_cliente_friendly MVP pass-through (default friendly)."""
    reasons = [
        "Falta documentación aplicable a esta medida.",
        "Hay 1 documento(s) pendiente(s) de tu firma.",
    ]
    translated = translate_missing_reasons_cliente_friendly(reasons)
    assert translated == reasons  # MVP pass-through


def test_control_status_result_to_dict():
    """ControlStatusResult.to_dict serializa todos campos."""
    result = ControlStatusResult(
        control_id=None,
        measure_code="op.acc.6",
        semaforo="verde",
        documents_count=1,
        documents_approved_count=1,
        documents_signed_count=1,
        cliente_reviewed_count=1,
        expired_count=0,
        missing_reasons=[],
        requirements_met={
            "documents_exist": True,
            "all_approved": True,
            "all_cliente_reviewed": True,
            "all_signed": True,
            "no_expired": True,
        },
    )
    d = result.to_dict()
    assert d["semaforo"] == "verde"
    assert d["measure_code"] == "op.acc.6"
    assert d["documents_count"] == 1
    assert d["requirements_met"]["all_approved"] is True


@pytest.mark.asyncio
async def test_compute_requires_control_id_or_measure_code(db: AsyncSession) -> None:
    """compute_control_status raises si NO control_id ni measure_code provided."""
    _, project_id_str = await setup_test_project(db)
    with pytest.raises(ValueError, match="control_id OR measure_code required"):
        await compute_control_status(
            db, project_id=uuid.UUID(project_id_str),
        )


# ════════════════════════════════════════════════════════════════════
# Ola 4 #20 · semáforo POR MEDIDA basado en Evidence (el FIX del stub)
# ════════════════════════════════════════════════════════════════════


async def _create_evidence(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    measure_code: str,
    vigente: bool = True,
    scan_status: str = "clean",
    fecha_caducidad: date | None = None,
) -> uuid.UUID:
    """Create test Evidence row con measure_code + flags configurables."""
    ev_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO evidence "
            "(id, project_id, measure_code, vigente, scan_status, "
            "fecha_caducidad, created_at) "
            "VALUES (:id, :pid, :mc, :vig, :scan, :cad, now())"
        ), {
            "id": str(ev_id),
            "pid": str(project_id),
            "mc": measure_code,
            "vig": vigente,
            "scan": scan_status,
            "cad": fecha_caducidad,
        })
    return ev_id


@pytest.mark.asyncio
async def test_measure_evidence_verde(db: AsyncSession) -> None:
    """Evidencia vigente + clean + no caducada → semáforo de la medida = verde."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.acc.6",
        vigente=True, scan_status="clean",
        fecha_caducidad=date.today() + timedelta(days=365),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    assert result.semaforo == "verde"
    assert result.documents_count == 1  # nº evidencias de la medida
    assert all(result.requirements_met.values())
    assert result.missing_reasons == []


@pytest.mark.asyncio
async def test_measure_evidence_caducada_rojo(db: AsyncSession) -> None:
    """Evidencia caducada → rojo (CRÍTICO · anti-falso-verde)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.acc.6",
        vigente=True, scan_status="clean",
        fecha_caducidad=date.today() - timedelta(days=1),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    assert result.semaforo == "rojo"
    assert result.expired_count == 1
    assert result.requirements_met["none_caducada"] is False
    assert any("caducada" in r.lower() for r in result.missing_reasons)


@pytest.mark.asyncio
async def test_measure_isolation_A_verde_B_rojo(db: AsyncSession) -> None:
    """EL FIX: el semáforo filtra POR MEDIDA, NO agrega el proyecto entero.

    Medida A (evidencia en regla) = verde · Medida B (evidencia caducada) = rojo,
    en el MISMO proyecto. Antes (stub) ambas devolvían el mismo agregado."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.acc.6",
        vigente=True, scan_status="clean",
        fecha_caducidad=date.today() + timedelta(days=365),
    )
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.exp.8",
        vigente=True, scan_status="clean",
        fecha_caducidad=date.today() - timedelta(days=1),  # caducada
    )

    res_a = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    res_b = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.exp.8",
    )
    assert res_a.semaforo == "verde", "medida A: evidencia en regla"
    assert res_b.semaforo == "rojo", "medida B: evidencia caducada"
    # Prueba el aislamiento: cada medida ve SOLO su evidencia (1 cada una).
    assert res_a.documents_count == 1
    assert res_b.documents_count == 1


@pytest.mark.asyncio
async def test_measure_no_evidence_amarillo(db: AsyncSession) -> None:
    """Medida aplicable SIN evidencia → amarillo (falta), NO no_aplica.

    La aplicabilidad la decide la SoA (estado_implementacion), no el semáforo."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)

    result = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    assert result.semaforo == "amarillo"
    assert result.documents_count == 0
    assert result.requirements_met["evidence_exists"] is False
    assert any("Falta evidencia" in r for r in result.missing_reasons)


@pytest.mark.asyncio
async def test_measure_evidence_infected_rojo(db: AsyncSession) -> None:
    """Evidencia infectada/cuarentena (antivirus) → rojo (no validada · mp.s.5)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.acc.6",
        vigente=True, scan_status="infected",
        fecha_caducidad=date.today() + timedelta(days=365),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    assert result.semaforo == "rojo"
    assert result.requirements_met["all_clean"] is False


@pytest.mark.asyncio
async def test_measure_evidence_scanning_amarillo(db: AsyncSession) -> None:
    """Evidencia con antivirus pendiente (scanning) → amarillo (sin validar aún)."""
    _, project_id_str = await setup_test_project(db)
    project_uuid = uuid.UUID(project_id_str)
    await _create_evidence(
        db, project_id=project_uuid, measure_code="op.acc.6",
        vigente=True, scan_status="scanning",
        fecha_caducidad=date.today() + timedelta(days=365),
    )

    result = await compute_control_status(
        db, project_id=project_uuid, measure_code="op.acc.6",
    )
    assert result.semaforo == "amarillo"
    assert result.requirements_met["all_clean"] is False
    assert any("sin validar" in r.lower() for r in result.missing_reasons)
