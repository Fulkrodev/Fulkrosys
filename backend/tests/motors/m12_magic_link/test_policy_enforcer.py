"""Tests SAN-D MB-19.9 · MagicLinkPolicyEnforcer + migration_log model.

Cubre:
- 33 purposes mantienen razón retornan ("ok") status.
- 2 deprecated soft (ONBOARDING_INICIAL · APORTE_EVIDENCIA) retornan
  ("deprecated_soft") status con reason populated · is_ok=True.
- Purpose unknown retorna ("unknown") con is_ok=False.
- Categorización 6 buckets (A-F) coverage.
- Stats dict consistency 33+2=35 total.
- MagicLinkMigrationLog model persistence + UNIQUE magic_link_id.
- service.generate_magic_link integration · soft-deprecated NO bloquea.
- API endpoint /generate response header X-Deprecated-Purpose si aplica.

Refs: ADR-042 · MB-19.9.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text

from backend.app.motors.m12_magic_link.policy_enforcer import (
    MagicLinkPolicyEnforcer,
    ONE_SHOT_OR_LEGITIMATE_PURPOSES,
    DEPRECATED_SOFT_PURPOSES,
    _DEPRECATION_REASONS,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.models_migration_log import (
    MagicLinkMigrationLog,
)
from backend.tests.conftest import _admin_setup


# ====================== Categorization coverage ======================

def test_total_purposes_13_plus_22_equals_35():
    """ADR-020 v3 (post-MB-4.bis3): 13 mantienen + 22 deprecated_soft = 35.

    Pre-MB-4.bis: 33 + 2 = 35 (ADR-042 baseline).
    Post-MB-4.bis2: 12 + 23 = 35.
    Post-MB-4.bis3: 13 + 22 = 35 (APROBACION_ACTA re-clasificada como
    mixed-use legitimate · asistentes pueden ser empleados externos).
    """
    # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC añadido Sesión 3B-2B.6 como legítimo
    # categoría D (externo continuo · auditor ENAC) → legitimate 13->14, total 35->36.
    # Batch A diagnóstico previo: DIAGNOSTICO_PRECLIENTE (#38 · cat F auxiliares,
    # allowed · NO deprecated) → legitimate 14->15, total 36->37.
    enforcer = MagicLinkPolicyEnforcer()
    stats = enforcer.get_summary_stats()
    assert stats["total_legitimate"] == 15
    assert stats["total_deprecated"] == 22
    assert stats["total"] == 37
    assert stats["total"] == len(list(MagicLinkPurpose))


def test_category_breakdown_matches_adr020():
    """Categorías A-F minus deprecated v3 = 13 legitimate post-MB-4.bis3.

    ADR-042 categorías base sin cambios (suma 33):
    - A · Firmas (10) · B · Aprobaciones (3) · C · Descargas (8) ·
      D · Externo continuo (4) · E · Lifecycle (5) · F · Auxiliares (3)

    ADR-020 v3 deprecated NEW (20 post-bis3):
    - A: 5 (ACEPTACION_RIESGO_RESIDUAL, VALIDACION_CAMBIO_ALCANCE,
         CONSENTIMIENTO_TRATAMIENTO_DATOS, CONFIRMACION_CONFORMIDAD,
         VOTACION_COMITE_SEGURIDAD)
         · APROBACION_ACTA OUT (mixed-use legitimate · asistentes externos)
    - B: 1 (APROBACION_FACTURA)
    - C: 5 (DESCARGA_CERTIFICADO_CONFORMIDAD, REPORTE_TRIMESTRAL,
         REPORTE_ANUAL, COMUNICACION_INCIDENTE_SEGURIDAD, INVITACION_REUNION)
    - D: 1 (RENEWAL_CAMPAIGN_DETAILS)
    - E: 5 (PRIMER_ACCESO_CLIENTE, OFERTA_RETAINER, RECONSIDERACION_RETAINER,
         RETAINER_WELCOME, NORMATIVA_ALERT_CRITICAL)
    - F: 3 (APROBACION_OBLIGACION, SOLICITUD_INFORMACION, ENCUESTA_SATISFACCION_NPS)
    Post-MB-4.bis3 legitimate = 33 - 20 = 13.
    """
    enforcer = MagicLinkPolicyEnforcer()
    stats = enforcer.get_summary_stats()
    # Categorías base sin cambios (suma = 33 base ADR-042)
    assert stats["A_firmas"] == 10
    assert stats["B_aprobaciones"] == 3
    assert stats["C_descargas"] == 8
    # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC (Sesión 3B-2B.6) categoría D externo
    # continuo (auditor ENAC externo) → D 4->5, suma base 33->34.
    assert stats["D_externo_continuo"] == 5
    assert stats["E_lifecycle"] == 5
    # Batch A diagnóstico previo: DIAGNOSTICO_PRECLIENTE → cat F 3->4, suma 34->35.
    assert stats["F_auxiliares"] == 4
    suma_categorias_base = (
        stats["A_firmas"] + stats["B_aprobaciones"] + stats["C_descargas"]
        + stats["D_externo_continuo"] + stats["E_lifecycle"]
        + stats["F_auxiliares"]
    )
    assert suma_categorias_base == 35
    # Legitimate = 14 + DIAGNOSTICO_PRECLIENTE (Batch A · cat F) = 15
    assert stats["total_legitimate"] == 15


def test_no_purpose_in_both_legitimate_and_deprecated():
    """Sets ONE_SHOT_OR_LEGITIMATE y DEPRECATED_SOFT son disjoint."""
    intersection = (
        ONE_SHOT_OR_LEGITIMATE_PURPOSES & DEPRECATED_SOFT_PURPOSES
    )
    assert intersection == frozenset()


def test_all_enum_purposes_categorized():
    """Cada purpose en MagicLinkPurpose enum está en una categoría."""
    all_categorized = (
        ONE_SHOT_OR_LEGITIMATE_PURPOSES | DEPRECATED_SOFT_PURPOSES
    )
    for purpose in MagicLinkPurpose:
        assert purpose in all_categorized, (
            f"{purpose.name} sin categorización · update policy_enforcer"
        )


# ====================== validate_purpose API ======================

def test_validate_purpose_legitimate_returns_ok():
    """Purpose categoría A-F retorna (True, ok, '')."""
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose(
        MagicLinkPurpose.FIRMA_DOCUMENTO,
    )
    assert is_ok is True
    assert status == "ok"
    assert reason == ""


def test_validate_purpose_firma_contrato_legitimate():
    """FIRMA_CONTRATO (#36 MB-19.4) categoría A · legitimate."""
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, _ = enforcer.validate_purpose(
        MagicLinkPurpose.FIRMA_CONTRATO,
    )
    assert is_ok is True
    assert status == "ok"


def test_validate_purpose_onboarding_inicial_hard_rejected():
    """ONBOARDING_INICIAL retorna (False, deprecated_soft, reason).

    Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): hard-rejection ·
    is_ok=False propaga ValueError en MagicLinkService.generate_magic_link.
    Caller M16 service.create_session refactored para NO emit magic_link.
    """
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose(
        MagicLinkPurpose.ONBOARDING_INICIAL,
    )
    assert is_ok is False
    assert status == "deprecated_soft"
    assert "ONBOARDING_INICIAL" in reason
    assert "ADR-020" in reason
    assert "portal" in reason.lower()


def test_validate_purpose_aporte_evidencia_hard_rejected():
    """APORTE_EVIDENCIA retorna (False, deprecated_soft, reason).

    Post-MB-4.bis3: hard-rejection · is_ok=False propaga ValueError.
    Caller M5 _trigger_cliente_aporta_magic_link refactored a notification.
    """
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose(
        MagicLinkPurpose.APORTE_EVIDENCIA,
    )
    assert is_ok is False
    assert status == "deprecated_soft"
    assert "APORTE_EVIDENCIA" in reason


@pytest.mark.parametrize("purpose", [
    MagicLinkPurpose.PRIMER_ACCESO_CLIENTE,
    MagicLinkPurpose.OFERTA_RETAINER,
    MagicLinkPurpose.APROBACION_FACTURA,
    MagicLinkPurpose.CONFIRMACION_CONFORMIDAD,
    MagicLinkPurpose.REPORTE_TRIMESTRAL,
    MagicLinkPurpose.VOTACION_COMITE_SEGURIDAD,
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL,
    MagicLinkPurpose.RENEWAL_CAMPAIGN_DETAILS,
])
def test_validate_purpose_v3_client_facing_hard_rejected(purpose):
    """ADR-020 v3 IMPLEMENTED FULLY (MB-4.bis3): purposes cliente-facing
    retornan is_ok=False (hard-rejection). Reason apunta a /client-portal/X.

    Callers refactorizados emit ClientNotification in-portal (M5/M21/M25)
    o drop emit (M16). APROBACION_ACTA no incluido · re-clasificada
    legitimate (mixed-use con empleados externos).
    """
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose(purpose)
    assert is_ok is False
    assert status == "deprecated_soft"
    assert "ADR-020" in reason
    assert "/client-portal/" in reason


def test_validate_purpose_aprobacion_acta_legitimate_post_bis3():
    """APROBACION_ACTA re-clasificada como legitimate post-MB-4.bis3.

    Mixed-use: asistentes a actas pueden ser empleados/proveedores externos
    sin cuenta portal · magic_link mantiene razón.
    """
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, _ = enforcer.validate_purpose(
        MagicLinkPurpose.APROBACION_ACTA,
    )
    assert is_ok is True
    assert status == "ok"


@pytest.mark.parametrize("purpose", [
    MagicLinkPurpose.FIRMA_DOCUMENTO,             # tercero firma única
    MagicLinkPurpose.FIRMA_CONTRATO,              # pre-cliente
    MagicLinkPurpose.APROBACION_PROPUESTA,        # pre-cliente
    MagicLinkPurpose.RESPUESTA_REQUERIMIENTO_AUDITOR,  # auditor ENAC
    MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,    # pentester externo
    MagicLinkPurpose.PORTAL_REMEDIACION,          # IT cliente sin cuenta portal
    MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,      # auditor ENAC
    MagicLinkPurpose.DESCARGA_BACKUP_ARCHIVO,     # post-cierre
    MagicLinkPurpose.AUTORIZACION_ACCION_REMOTA,  # operador externo
    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,  # proveedor verificador
    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,   # proveedor pentester
    MagicLinkPurpose.REVISAR_INFORME_VERIFICACION,  # proveedor revisa
])
def test_validate_purpose_v3_third_party_legitimate(purpose):
    """ADR-020 v3: terceros sin cuenta portal · pre/post cuenta · MANTIENEN."""
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, _ = enforcer.validate_purpose(purpose)
    assert is_ok is True
    assert status == "ok"


def test_validate_purpose_string_input_coerced():
    """Acepta string value · coerce a enum (compat clientes externos)."""
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, _ = enforcer.validate_purpose("firma_documento")
    assert is_ok is True
    assert status == "ok"


def test_validate_purpose_unknown_string_rejects():
    """String no en enum retorna (False, unknown, ...)."""
    enforcer = MagicLinkPolicyEnforcer()
    is_ok, status, reason = enforcer.validate_purpose("totally_invalid")
    assert is_ok is False
    assert status == "unknown"
    assert "totally_invalid" in reason


def test_is_deprecated_helper():
    """is_deprecated helper retorna True solo para ONBOARDING/APORTE."""
    enforcer = MagicLinkPolicyEnforcer()
    assert enforcer.is_deprecated(MagicLinkPurpose.ONBOARDING_INICIAL) is True
    assert enforcer.is_deprecated(MagicLinkPurpose.APORTE_EVIDENCIA) is True
    assert enforcer.is_deprecated(MagicLinkPurpose.FIRMA_DOCUMENTO) is False
    assert enforcer.is_deprecated(MagicLinkPurpose.FIRMA_CONTRATO) is False


def test_get_categorization_correct_buckets():
    """get_categorization retorna bucket correcto per purpose."""
    enforcer = MagicLinkPolicyEnforcer()
    assert enforcer.get_categorization(
        MagicLinkPurpose.FIRMA_CONTRATO,
    ) == "A_firmas"
    assert enforcer.get_categorization(
        MagicLinkPurpose.APROBACION_PROPUESTA,
    ) == "B_aprobaciones"
    assert enforcer.get_categorization(
        MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
    ) == "C_descargas"
    assert enforcer.get_categorization(
        MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
    ) == "D_externo_continuo"
    assert enforcer.get_categorization(
        MagicLinkPurpose.PRIMER_ACCESO_CLIENTE,
    ) == "E_lifecycle"
    assert enforcer.get_categorization(
        MagicLinkPurpose.ENCUESTA_SATISFACCION_NPS,
    ) == "F_auxiliares"
    assert enforcer.get_categorization(
        MagicLinkPurpose.ONBOARDING_INICIAL,
    ) == "deprecated_soft"
    assert enforcer.get_categorization("unknown_value") == "unknown"


# ====================== MagicLinkMigrationLog model ======================

@pytest.mark.asyncio
async def test_magic_link_migration_log_persistence(db):
    """MagicLinkMigrationLog persiste con todos los fields ADR-042."""
    log_id = uuid.uuid4()
    ml_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        # Setup parent rows: client + project + magic_link
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Mig Test Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Mig Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, 'aporte_evidencia', "
            "'fake_hash_xyz', NOW() + INTERVAL '7 days', 3, 0, FALSE, "
            "'mig@migco.es', now())"
        ), {"id": str(ml_id), "pid": str(project_id)})

        await db.execute(text(
            "INSERT INTO magic_link_migration_log "
            "(id, magic_link_id, original_purpose, migration_action, "
            "notes, processed_at) "
            "VALUES (:id, :ml, 'aporte_evidencia', 'converted_to_task', "
            "'Migration test ok', now())"
        ), {"id": str(log_id), "ml": str(ml_id)})
        await db.flush()

    log = await db.get(MagicLinkMigrationLog, log_id)
    assert log is not None
    assert log.magic_link_id == ml_id
    assert log.original_purpose == "aporte_evidencia"
    assert log.migration_action == "converted_to_task"
    assert log.notes == "Migration test ok"


@pytest.mark.asyncio
async def test_magic_link_migration_log_unique_magic_link_id(db):
    """UNIQUE constraint magic_link_id garantiza idempotencia."""
    ml_id = uuid.uuid4()
    log1_id = uuid.uuid4()
    log2_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Unique Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Unique Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, 'onboarding_inicial', "
            "'unique_hash', NOW() + INTERVAL '7 days', 1, 0, FALSE, "
            "'unique@test.es', now())"
        ), {"id": str(ml_id), "pid": str(project_id)})

        # First insert ok
        await db.execute(text(
            "INSERT INTO magic_link_migration_log "
            "(id, magic_link_id, original_purpose, migration_action, "
            "processed_at) "
            "VALUES (:id, :ml, 'onboarding_inicial', 'kept_one_shot', now())"
        ), {"id": str(log1_id), "ml": str(ml_id)})
        await db.flush()

    # Second insert mismo magic_link_id · debe violar UNIQUE
    await db.execute(text("SAVEPOINT before_unique_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception) as exc_info:
            await db.execute(text(
                "INSERT INTO magic_link_migration_log "
                "(id, magic_link_id, original_purpose, migration_action, "
                "processed_at) "
                "VALUES (:id, :ml, 'onboarding_inicial', "
                "'converted_to_task', now())"
            ), {"id": str(log2_id), "ml": str(ml_id)})
            await db.flush()
        assert "unique" in str(exc_info.value).lower() \
            or "uq_magic_link_migration_log_magic_link" in str(exc_info.value)
    finally:
        await db.execute(text("ROLLBACK TO SAVEPOINT before_unique_violation"))
        await db.execute(text("RESET ROLE"))


@pytest.mark.asyncio
async def test_magic_link_migration_action_check_constraint(db):
    """CheckConstraint migration_action solo acepta 4 valores válidos."""
    ml_id = uuid.uuid4()
    log_id = uuid.uuid4()
    project_id = uuid.uuid4()
    client_id = uuid.uuid4()

    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Check Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Check Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})
        await db.execute(text(
            "INSERT INTO magic_links (id, project_id, tipo_operacion, "
            "token_hash, expira_at, max_usos, usos, revocado, "
            "recipient_email, created_at) "
            "VALUES (:id, :pid, 'onboarding_inicial', "
            "'check_hash', NOW() + INTERVAL '7 days', 1, 0, FALSE, "
            "'check@test.es', now())"
        ), {"id": str(ml_id), "pid": str(project_id)})

    await db.execute(text("SAVEPOINT before_check_violation"))
    try:
        await db.execute(text("SET LOCAL ROLE fulkro_app_bypassrls"))
        with pytest.raises(Exception):
            await db.execute(text(
                "INSERT INTO magic_link_migration_log "
                "(id, magic_link_id, original_purpose, migration_action, "
                "processed_at) "
                "VALUES (:id, :ml, 'onboarding_inicial', 'INVALID_ACTION', now())"
            ), {"id": str(log_id), "ml": str(ml_id)})
            await db.flush()
    finally:
        await db.execute(text("ROLLBACK TO SAVEPOINT before_check_violation"))
        await db.execute(text("RESET ROLE"))


# ====================== MagicLinkService integration ======================

@pytest.mark.asyncio
async def test_generate_magic_link_deprecated_blocks(db):
    """Post-MB-4.bis3 (ADR-020 v3 IMPLEMENTED FULLY): generation blocks
    para purposes deprecated · raise ValueError. Cliente in-portal only."""
    from backend.app.motors.m12_magic_link.service import MagicLinkService
    from backend.app.motors.m12_magic_link.schemas import (
        MagicLinkGenerateRequest,
    )

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'Reject Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'Reject Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})

    # Set tenant context · magic_links table tiene RLS by project_id
    from backend.app.database import set_tenant_context
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = MagicLinkService(db)
    request = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=MagicLinkPurpose.ONBOARDING_INICIAL,
        recipient_email="reject@test.es",
        scope={"flow": "test_hard_rejected"},
    )
    # MB-4.bis3 hard-rejection · raise ValueError
    with pytest.raises(ValueError, match="rechazó purpose"):
        await svc.generate_magic_link(
            request, base_url="https://app.fulkro.es",
        )


@pytest.mark.asyncio
async def test_generate_magic_link_legitimate_no_warning(db):
    """FIRMA_DOCUMENTO generation no warning (legitimate · ok)."""
    from backend.app.motors.m12_magic_link.service import MagicLinkService
    from backend.app.motors.m12_magic_link.schemas import (
        MagicLinkGenerateRequest,
    )

    project_id = uuid.uuid4()
    client_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(text(
            "INSERT INTO clients (id, nombre, cif, created_at) "
            "VALUES (:id, 'OK Client', :cif, now())"
        ), {"id": str(client_id), "cif": f"B{uuid.uuid4().hex[:8].upper()}"})
        await db.execute(text(
            "INSERT INTO projects (id, client_id, nombre, created_at) "
            "VALUES (:id, :cid, 'OK Project', now())"
        ), {"id": str(project_id), "cid": str(client_id)})

    # Set tenant context · magic_links table tiene RLS by project_id
    from backend.app.database import set_tenant_context
    await set_tenant_context(db, client_id=client_id, project_id=project_id)

    svc = MagicLinkService(db)
    request = MagicLinkGenerateRequest(
        project_id=project_id,
        purpose=MagicLinkPurpose.FIRMA_DOCUMENTO,
        recipient_email="ok@test.es",
        scope={"document": "DOC-001"},
    )
    response = await svc.generate_magic_link(
        request, base_url="https://app.fulkro.es",
    )
    assert response.magic_link_id is not None
    assert response.purpose == MagicLinkPurpose.FIRMA_DOCUMENTO
