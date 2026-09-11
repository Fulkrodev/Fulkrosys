"""Tests M9-B · MANIFEST Ed25519 signed (Sesión 3B-2B.6 Cluster 1 Phase 1).

Verifica:
1. sign_manifest=True + force=True raises DossierError (incompatibility)
2. MANIFEST.json firmado contiene `_signature` block con algorithm + signature_hex + public_key_pem
3. Signature válida verifica canonical payload con M05 public key
4. SHA-256 hash per file mantiene formato 64 hex chars cross-archivo
5. unsigned manifest (sign_manifest=False default) NO contiene `_signature` block (backward compat)
"""
from __future__ import annotations

import io
import json
import uuid
import zipfile

import pytest

from backend.app.motors.m09_audit_prep import dossier_generator
from backend.app.motors.m05_signing.keypair import verify_signature


pytestmark = pytest.mark.asyncio


async def _create_run_helper(async_client, project_id: str, categoria: str = "BASICA") -> str:
    """Mirror of test_m09_dossier._create_run · POST /runs returns run_id."""
    resp = await async_client.post(
        f"/api/v1/audit-prep/projects/{project_id}/runs",
        json={"categoria": categoria},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


async def _set_tenant_helper(db, project_id: str) -> None:
    from sqlalchemy import text as sa_text
    await db.execute(
        sa_text("SELECT set_config('app.current_project_id', :pid, true)"),
        {"pid": project_id},
    )


async def test_sign_manifest_with_force_raises(async_client, db):
    """sign_manifest=True + force=True → DossierError (BORRADOR no firma)."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)

    with pytest.raises(dossier_generator.DossierError, match="incompatible"):
        await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id),
            force=True, sign_manifest=True,
        )


async def test_unsigned_manifest_has_no_signature_block(async_client, db):
    """Default (sign_manifest=False) · manifest sin `_signature` (backward-compat)."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    manifest = json.loads(z.read("MANIFEST.json"))
    assert "_signature" not in manifest, "default manifest no debe traer _signature"
    # files SHA-256 hash format (64 hex chars) preserved
    assert all(len(f["sha256"]) == 64 for f in manifest["files"])


async def test_signed_manifest_contains_signature_block(async_client, db, monkeypatch):
    """sign_manifest=True · _signature block presente · ed25519 + hex + PEM."""
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)

    # Bypass checklist blockers · empirical test cliente piloto setup minimal.
    # Path B real cliente sí cumplirá checklist · this test foca en signing logic.
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id),
        force=False, sign_manifest=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    manifest = json.loads(z.read("MANIFEST.json"))

    assert "_signature" in manifest
    sig = manifest["_signature"]
    assert sig["algorithm"] == "Ed25519"
    assert len(sig["signature_hex"]) == 128  # 64 bytes hex
    assert sig["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
    assert "signed_at" in sig
    assert "canonical_format" in sig


async def test_signed_manifest_signature_verifies(async_client, db, monkeypatch):
    """Roundtrip · re-compute canonical payload + verify_signature via M05 pubkey."""
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id),
        force=False, sign_manifest=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    manifest = json.loads(z.read("MANIFEST.json"))

    sig_block = manifest.pop("_signature")
    signature_bytes = bytes.fromhex(sig_block["signature_hex"])

    # Reconstruct canonical payload exactly as signing code does
    canonical_payload = json.dumps(
        manifest, indent=None, separators=(",", ":"),
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")

    assert verify_signature(canonical_payload, signature_bytes) is True


async def test_signed_manifest_sha256_integrity_per_file(async_client, db, monkeypatch):
    """Cada archivo ZIP tiene SHA-256 64-hex en files[] · integridad preservada."""
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service
    import hashlib

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id),
        force=False, sign_manifest=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    manifest = json.loads(z.read("MANIFEST.json"))

    # Verify ALL files claim sha256 64 hex chars
    assert len(manifest["files"]) > 0
    for file_entry in manifest["files"]:
        assert len(file_entry["sha256"]) == 64
        assert all(c in "0123456789abcdef" for c in file_entry["sha256"])
        # Verify actual ZIP content matches claimed hash for sample file
        actual_bytes = z.read(file_entry["file"])
        actual_hash = hashlib.sha256(actual_bytes).hexdigest()
        assert actual_hash == file_entry["sha256"], (
            f"hash mismatch para {file_entry['file']}"
        )


async def test_signed_dossier_embeds_real_binaries(
    async_client, db, monkeypatch, minio_disponible,
):
    """#33 (FRENTE B): el dossier FIRMADO embebe los binarios REALES (PDF/DOCX)
    desde MinIO (durables · #31), no solo el .json de metadata. El manifest
    reporta binaries_included (DEC-4 topes con omisión graceful anotada)."""
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service
    from backend.app.motors.m24_idms.idms_service import IDMSService
    from backend.app.core.storage.minio_client import (
        BUCKET_DOCUMENTS,
        remove_object,
    )
    from backend.app.database import set_tenant_context

    client_id, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    contenido = b"%PDF-1.4 #33 binario real dossier ENS entregable\n"
    intake = await IDMSService().intake_document(
        db,
        project_id=uuid.UUID(project_id),
        nombre="E-100_politica.pdf",
        contenido=contenido,
        tipo_mime="application/pdf",
    )
    storage_path = intake["document"].storage_path

    try:
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id),
            force=False, sign_manifest=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(z.read("MANIFEST.json"))

        # binario embebido (no solo .json de metadata)
        assert manifest["binaries_included"] >= 1
        assert manifest["binaries_total_bytes"] >= len(contenido)
        bin_entries = [
            n for n in z.namelist()
            if n.endswith(".pdf") and "E-100" in n
        ]
        assert bin_entries, z.namelist()
        # bytes EXACTOS del binario real (round-trip MinIO → ZIP)
        assert z.read(bin_entries[0]) == contenido
    finally:
        key = storage_path[len("minio://"):].partition("/")[2]
        remove_object(BUCKET_DOCUMENTS, key)


async def test_dec4_caps_resolve_by_level_and_env(monkeypatch):  # noqa: RUF029
    """DEC-4 (a): topes configurables por nivel + override ENV."""
    from backend.app.motors.m09_audit_prep import dossier_generator as dg

    monkeypatch.delenv("FULKRO_DOSSIER_SINGLE_BINARY_MB", raising=False)
    monkeypatch.delenv("FULKRO_DOSSIER_TOTAL_BINARY_MB", raising=False)
    _, basica_total = dg.resolve_dossier_caps("BASICA")
    _, alta_total = dg.resolve_dossier_caps("ALTA")
    assert alta_total > basica_total  # ALTA genera más evidencia
    monkeypatch.setenv("FULKRO_DOSSIER_TOTAL_BINARY_MB", "1")
    single, total = dg.resolve_dossier_caps("MEDIA")
    assert total == 1 * 1024 * 1024  # override ENV respetado


async def test_dec4_canonical_whitelist_predicate():  # noqa: RUF029
    """DEC-4 (b): la Declaración de Conformidad / SoA / pentest / certificado son
    canónicos; un anexo en bruto NO."""
    from backend.app.motors.m09_audit_prep import dossier_generator as dg

    assert dg.is_canonical_dossier_artifact({"template_codigo": "E-041"})  # Conf.
    assert dg.is_canonical_dossier_artifact({"template_codigo": "E-040"})  # SoA/DdA
    assert dg.is_canonical_dossier_artifact({"template_codigo": "E-808C"})  # BÁSICA
    assert dg.is_canonical_dossier_artifact({"tipo": "certificado"})
    assert not dg.is_canonical_dossier_artifact({"template_codigo": "E-300"})
    assert not dg.is_canonical_dossier_artifact({"tipo": "anexo_logs"})


async def test_dec4_canonical_artifact_never_omitted_over_cap(
    async_client, db, monkeypatch, minio_disponible,
):
    """DEC-4 (b) CRÍTICO: un artefacto CANÓNICO (E-041) que SUPERA el tope se
    incluye IGUAL en el dossier firmado (whitelist) · un NO-canónico grande se
    omite. Forzamos el tope a ~0 vía ENV para que el binario lo supere."""
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service
    from backend.app.motors.m24_idms.idms_service import IDMSService
    from backend.app.core.storage.minio_client import (
        BUCKET_DOCUMENTS, remove_object,
    )
    from backend.app.database import set_tenant_context
    from sqlalchemy import text as sa_text

    # Tope diminuto → cualquier binario lo supera (prueba la whitelist canónica).
    monkeypatch.setenv("FULKRO_DOSSIER_SINGLE_BINARY_MB", "0")
    monkeypatch.setenv("FULKRO_DOSSIER_TOTAL_BINARY_MB", "0")

    client_id, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await set_tenant_context(
        db, client_id=uuid.UUID(client_id), project_id=uuid.UUID(project_id),
    )
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    # Canónico (E-041) + no-canónico (E-300), ambos con binario en MinIO.
    canon_bytes = b"%PDF-1.4 CANONICAL Declaracion Conformidad ENS\n" + b"x" * 200
    other_bytes = b"%PDF-1.4 anexo secundario en bruto\n" + b"y" * 200
    canon = await IDMSService().intake_document(
        db, project_id=uuid.UUID(project_id), nombre="E-041_conformidad.pdf",
        contenido=canon_bytes, tipo_mime="application/pdf",
    )
    other = await IDMSService().intake_document(
        db, project_id=uuid.UUID(project_id), nombre="anexo_secundario.pdf",
        contenido=other_bytes, tipo_mime="application/pdf",
    )
    # Marca template_codigo para que el clasificador los distinga.
    await db.execute(sa_text(
        "UPDATE documents SET template_codigo='E-041' WHERE id=:id"
    ), {"id": str(canon["document"].id)})
    await db.execute(sa_text(
        "UPDATE documents SET template_codigo='E-300' WHERE id=:id"
    ), {"id": str(other["document"].id)})
    await db.flush()

    try:
        data = await dossier_generator.generate_dossier(
            db, uuid.UUID(project_id), uuid.UUID(run_id),
            force=False, sign_manifest=True,
        )
        z = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(z.read("MANIFEST.json"))
        names = z.namelist()

        # El CANÓNICO entra pese al tope 0 (forzado) · NUNCA omitido
        assert any(n.endswith(".pdf") and "E-041" in n for n in names), names
        assert manifest["binaries_canonical_forced"] >= 1
        assert manifest["canonical_omitted_count"] == 0
        # El NO-canónico grande SÍ se omite por tope
        assert any(
            o.get("template_codigo") == "E-300"
            and o.get("reason") == "supera_tope_por_documento"
            for o in manifest["binaries_omitted"]
        ), manifest["binaries_omitted"]
    finally:
        for r in (canon, other):
            sp = r["document"].storage_path
            remove_object(BUCKET_DOCUMENTS, sp[len("minio://"):].partition("/")[2])


async def test_dossier_includes_compliance_declaration_f9(
    async_client, db, monkeypatch,
):
    """F9 (FRENTE F): el dossier incluye 13_INFORMES_TECNICOS/
    compliance_declaration.json con pentest_status + nota honesta + flag ALTA
    (pentester EXTERNO obligatorio). SIEMPRE presente (reporta a auditoría)."""
    from sqlalchemy import text as sa_text
    from backend.tests.conftest import setup_test_project
    from backend.app.motors.m09_audit_prep import checklist_service

    _, project_id = await setup_test_project(db)
    await db.execute(sa_text(
        "UPDATE projects SET categoria_objetivo = 'ALTA' WHERE id = :pid"
    ), {"pid": project_id})
    await db.flush()
    run_id = await _create_run_helper(async_client, project_id, "ALTA")
    await _set_tenant_helper(db, project_id)
    monkeypatch.setattr(
        checklist_service, "require_complete_audit_prep", lambda run: [],
    )

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id),
        force=False, sign_manifest=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    assert "13_INFORMES_TECNICOS/compliance_declaration.json" in z.namelist()
    cd = json.loads(z.read("13_INFORMES_TECNICOS/compliance_declaration.json"))
    assert "pentest_status" in cd
    assert cd["alta_external_pentest_required"] is True  # ALTA
    assert "EXTERNO" in cd["pentest_status"]["nota_honesta"]


async def test_unsigned_dossier_omits_binaries(async_client, db):
    """#33: el dossier BORRADOR (sign_manifest=False) NO embebe binarios
    (solo metadata · los binarios son para la entrega firmada ENAC)."""
    from backend.tests.conftest import setup_test_project

    _, project_id = await setup_test_project(db)
    run_id = await _create_run_helper(async_client, project_id, "BASICA")
    await _set_tenant_helper(db, project_id)

    data = await dossier_generator.generate_dossier(
        db, uuid.UUID(project_id), uuid.UUID(run_id), force=True,
    )
    z = zipfile.ZipFile(io.BytesIO(data))
    manifest = json.loads(z.read("MANIFEST.json"))
    assert manifest["binaries_included"] == 0
