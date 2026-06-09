"""#5 cabo · suelo AAPP tardío · guard por nivel (N1/N2/N2.5/N3).

Verifica el orquestador floor_elevation_service vía el endpoint PUT inherited-floor:
- N2   borradores → ELEVA + regenera propuesta + plan a la categoría nueva.
- N2.5 contrato EN VUELO → BLOQUEA 409 · el retract revoca el magic-link EFECTIVO
       (el cliente que lo abra NO puede firmar) · luego cae a N1 y eleva.
- N3   contrato FIRMADO → BLOQUEA 409 · constancia en adendas · firma INTACTA
       (documento_sha256 / firmado_cliente_at NO se tocan).
"""
import json
import uuid

import pytest
from sqlalchemy import text

from backend.tests.conftest import setup_test_project, _admin_setup


async def _seed_lead(db) -> uuid.UUID:
    lead_id = uuid.uuid4()
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO leads (id, empresa_nombre, created_at) "
                "VALUES (:id, 'Lead Cabo Test', now())"
            ),
            {"id": str(lead_id)},
        )
    return lead_id


# ════════════════════════════════════════════════════════════════════
# N2 · borradores → regenera propuesta + plan a la categoría nueva
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_n2_regenerates_proposal_and_plan_to_new_categoria(async_client, db):
    _, project_id = await setup_test_project(db)
    lead_id = await _seed_lead(db)
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:p"),
            {"p": project_id},
        )
        # propuesta borrador BASICA
        await db.execute(
            text(
                "INSERT INTO proposals (id, lead_id, project_id, version, "
                "categoria_objetivo, pricing_model_id, alcance, importe_total, "
                "estado, superseded, created_at) VALUES (:id, :lid, :pid, 1, "
                "'BASICA', 'basica_fijo', CAST(:alc AS jsonb), 6500, 'draft', "
                "false, now())"
            ),
            {
                "id": str(uuid.uuid4()), "lid": str(lead_id), "pid": project_id,
                "alc": json.dumps({"empleados": 10, "sistemas": 2}),
            },
        )
        # plan borrador BASICA
        await db.execute(
            text(
                "INSERT INTO project_plans (id, project_id, version, categoria, "
                "estado, created_at) VALUES (:id, :pid, 1, 'BASICA', 'active', now())"
            ),
            {"id": str(uuid.uuid4()), "pid": project_id},
        )

    r = await async_client.put(
        f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        json={"categoria_heredada_aapp": "MEDIA"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["level"] == "N2"
    assert data["categoria_objetivo"] == "MEDIA"
    assert "propuesta" in data["regenerated"]
    assert "plan" in data["regenerated"]

    # Propuesta: la vieja BASICA queda superseded · la nueva es MEDIA vigente.
    props = (await db.execute(
        text(
            "SELECT categoria_objetivo, superseded FROM proposals "
            "WHERE project_id = :p ORDER BY version"
        ),
        {"p": project_id},
    )).all()
    pairs = {(row[0], row[1]) for row in props}
    assert ("BASICA", True) in pairs   # vieja superseded
    assert ("MEDIA", False) in pairs   # nueva vigente category-aware

    # Plan: el nuevo vigente es MEDIA · el viejo soft-deleted (traza).
    active_plans = (await db.execute(
        text(
            "SELECT categoria FROM project_plans "
            "WHERE project_id = :p AND deleted_at IS NULL"
        ),
        {"p": project_id},
    )).all()
    assert len(active_plans) == 1 and active_plans[0][0] == "MEDIA"


# ════════════════════════════════════════════════════════════════════
# N2.5 · contrato EN VUELO → bloquea · retract revoca magic-link efectivo
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_n2_5_blocks_in_flight_and_retract_revokes_magic_link(async_client, db):
    from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
    from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
    from backend.app.motors.m12_magic_link.service import MagicLinkService

    _, project_id = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:p"),
            {"p": project_id},
        )

    contract_id = uuid.uuid4()
    # magic-link REAL FIRMA_CONTRATO para el contrato (la puerta de la firma).
    ml = await MagicLinkService(db).generate_magic_link(
        MagicLinkGenerateRequest(
            project_id=uuid.UUID(project_id),
            purpose=MagicLinkPurpose.FIRMA_CONTRATO,
            recipient_email="cliente@test.es",
            scope={"flow": "contract_signing", "contract_id": str(contract_id)},
        ),
        base_url="http://test",
    )
    async with _admin_setup(db):
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, "
                "firmado_cliente_link_id, created_at) VALUES (:id, :pid, 'sent', "
                ":mlid, now())"
            ),
            {"id": str(contract_id), "pid": project_id, "mlid": str(ml.magic_link_id)},
        )

    # PUT floor MEDIA → 409 (contrato en vuelo) · floor NO guardado.
    r = await async_client.put(
        f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        json={"categoria_heredada_aapp": "MEDIA"},
    )
    assert r.status_code == 409
    assert "vuelo" in r.json()["detail"].lower()
    row = (await db.execute(
        text(
            "SELECT categoria_objetivo, categoria_heredada_aapp "
            "FROM projects WHERE id = :p"
        ),
        {"p": project_id},
    )).first()
    assert row[0] == "BASICA" and row[1] is None  # nada cambió · floor NO guardado

    # Retract: revoca el magic-link + anula el contrato.
    from backend.app.motors.m14_contracts.contract_service import ContractService
    await ContractService().retract_in_flight_contract(
        db, contract_id, "recategorizacion",
    )
    await db.flush()

    # El magic-link quedó REVOCADO (barrera efectiva) + contrato anulado.
    mlrow = (await db.execute(
        text("SELECT revocado FROM magic_links WHERE id = :id"),
        {"id": str(ml.magic_link_id)},
    )).first()
    assert mlrow[0] is True
    crow = (await db.execute(
        text("SELECT estado FROM contracts WHERE id = :c"),
        {"c": str(contract_id)},
    )).first()
    assert crow[0] == "anulado_recategorizacion"

    # Ya desbloqueado (N1): re-aplicar el suelo eleva limpio.
    r2 = await async_client.put(
        f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        json={"categoria_heredada_aapp": "MEDIA"},
    )
    assert r2.status_code == 200
    assert r2.json()["categoria_objetivo"] == "MEDIA"

    # CRÍTICO · el cliente que abra el magic-link del contrato anulado NO puede
    # firmar (consume rechaza el link revocado → ContractSigningFlowError).
    from backend.app.motors.m13_commercial.services.contract_signing_flow import (
        ContractSigningFlow,
        ContractSigningFlowError,
    )
    with pytest.raises(ContractSigningFlowError):
        await ContractSigningFlow(db).confirm_signing(
            token=ml.token,
            otp=ml.otp or "000000",
            signature_canvas_dataurl="data:image/png;base64," + ("A" * 40),
            signed_name="Cliente",
            signed_surname="Test",
        )


# ════════════════════════════════════════════════════════════════════
# N3 · contrato FIRMADO → bloquea 409 · constancia · firma INTACTA
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_n3_blocks_signed_contract_records_and_never_touches_signature(
    async_client, db,
):
    _, project_id = await setup_test_project(db)
    contract_id = uuid.uuid4()
    sha = "a" * 64
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:p"),
            {"p": project_id},
        )
        await db.execute(
            text(
                "INSERT INTO contracts (id, project_id, estado, firmado_cliente_at, "
                "documento_sha256, hash_sha256, created_at) VALUES (:id, :pid, "
                "'vigente', now(), :sha, :sha, now())"
            ),
            {"id": str(contract_id), "pid": project_id, "sha": sha},
        )

    # PUT floor MEDIA → 409 (contrato firmado).
    r = await async_client.put(
        f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        json={"categoria_heredada_aapp": "MEDIA"},
    )
    assert r.status_code == 409
    assert "firmado" in r.json()["detail"].lower()

    # El proyecto queda EXACTAMENTE como estaba (floor NO guardado · sin limbo).
    prow = (await db.execute(
        text(
            "SELECT categoria_objetivo, categoria_heredada_aapp "
            "FROM projects WHERE id = :p"
        ),
        {"p": project_id},
    )).first()
    assert prow[0] == "BASICA" and prow[1] is None

    # La firma es INTOCABLE + queda constancia del intento en adendas.
    crow = (await db.execute(
        text(
            "SELECT documento_sha256, firmado_cliente_at, estado, adendas "
            "FROM contracts WHERE id = :c"
        ),
        {"c": str(contract_id)},
    )).first()
    assert crow[0] == sha            # documento_sha256 INTACTO
    assert crow[1] is not None       # firmado_cliente_at INTACTO
    assert crow[2] == "vigente"      # estado INTACTO (no se anula un firmado)
    adendas = crow[3] or {}
    intentos = adendas.get("intentos_elevacion_bloqueados", [])
    assert len(intentos) == 1
    assert intentos[0]["suelo_aapp"] == "MEDIA"
    assert intentos[0]["categoria_contrato"] == "BASICA"


@pytest.mark.asyncio
async def test_n3_invoice_emitida_refuerza_bloqueo(async_client, db):
    """Factura con verifactu_hash (sin contrato firmado) también bloquea (fiscal)."""
    _, project_id = await setup_test_project(db)
    async with _admin_setup(db):
        await db.execute(
            text("UPDATE projects SET categoria_objetivo='BASICA' WHERE id=:p"),
            {"p": project_id},
        )
        client_id = (await db.execute(
            text("SELECT client_id FROM projects WHERE id=:p"), {"p": project_id},
        )).scalar()
        await db.execute(
            text(
                "INSERT INTO invoices (id, client_id, project_id, verifactu_hash, "
                "created_at) VALUES (:id, :cid, :pid, :vh, now())"
            ),
            {
                "id": str(uuid.uuid4()), "cid": str(client_id), "pid": project_id,
                "vh": "f" * 64,
            },
        )

    r = await async_client.put(
        f"/api/v1/categorization/projects/{project_id}/inherited-floor",
        json={"categoria_heredada_aapp": "MEDIA"},
    )
    assert r.status_code == 409
    prow = (await db.execute(
        text("SELECT categoria_objetivo FROM projects WHERE id = :p"),
        {"p": project_id},
    )).first()
    assert prow[0] == "BASICA"  # sin cambios
