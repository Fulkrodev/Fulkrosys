"""R26 · regression guard for the cemented E-040 identity.

E-040 has ONE canonical identity across registry + dossier + signing:

    E-040 = "Informe Final de Adecuación al ENS", documento de síntesis
    firmado por RSEG que INCLUYE la Declaración de Aplicabilidad (SoA · 73
    medidas del Anexo II) como su Anexo II.

There is NO standalone "Declaración de Aplicabilidad" Document: the SoA
matrix lives in ``dda_entries`` (m03) and is signed as ``dda_snapshot_hash``
via the M03 magic-link flow; the rendered Document E-040 is approved/signed
by the RSEG. This test fails loudly if any future change drifts the label,
folder mapping, canonical-whitelist protection, or signing semantics — the
three views must stay reconciled.

These are pure assertions (no DB) so they run in any context.
"""
from __future__ import annotations


def test_registry_title_is_informe_final() -> None:
    from backend.app.motors.m06_document_factory.template_registry import get_template

    meta = get_template("E-040")
    assert meta is not None, "E-040 debe existir en el registry canónico"
    assert meta["title"] == "INFORME FINAL DE ADECUACIÓN AL ENS"


def test_e040_is_canonical_dossier_artifact_by_code() -> None:
    # E-040 está protegido en el dossier por coincidencia de template_codigo
    # (whitelist), de modo que editar la descripción de la carpeta o los
    # comentarios NUNCA puede dejarlo fuera por tope de tamaño.
    from backend.app.motors.m09_audit_prep.dossier_generator import (
        _CANONICAL_DOSSIER_CODES,
        is_canonical_dossier_artifact,
    )

    assert "E-040" in _CANONICAL_DOSSIER_CODES
    assert is_canonical_dossier_artifact({"template_codigo": "E-040"}) is True
    # Defensa adicional: aunque falte template_codigo, el tipo 'dda'/'soa' protege.
    assert is_canonical_dossier_artifact({"tipo": "dda"}) is True
    assert is_canonical_dossier_artifact({"tipo": "soa"}) is True


def test_e040_dossier_folder_mapping_stable() -> None:
    from backend.app.motors.m09_audit_prep.dossier_generator import (
        DELIVERABLE_TO_FOLDER,
        DOSSIER_STRUCTURE,
    )

    assert DELIVERABLE_TO_FOLDER["E-040"] == "04_DECLARACION_APLICABILIDAD"
    folder = next(
        f for f in DOSSIER_STRUCTURE if f["folder"] == "04_DECLARACION_APLICABILIDAD"
    )
    # La descripción cementa la doble naturaleza (Informe Final que incluye la SoA).
    desc = folder["description"]
    assert "Informe Final" in desc
    assert "Aplicabilidad" in desc
    assert "RSEG" in desc


def test_dda_signable_label_reconciled() -> None:
    from backend.app.motors.m05_signing.signable_types import SIGNABLE_TYPE_LABELS

    label = SIGNABLE_TYPE_LABELS["dda"]
    assert "Aplicabilidad" in label
    assert "SoA" in label
    assert "Anexo II" in label


def test_m03_signing_flow_symbols_intact() -> None:
    # El cement NO debe tocar el flujo de firma m03 (endpoints/scope/symbols).
    from backend.app.motors.m03_dda.signature_integration import (  # noqa: F401
        E040SignatureIntegrationError,
        get_e040_signature_status,
        request_e040_signature,
    )

    # El scope del magic-link es plumbing identity-agnostic: debe permanecer.
    import inspect

    src = inspect.getsource(request_e040_signature)
    assert '"dda_e040_rseg"' in src or "'dda_e040_rseg'" in src
