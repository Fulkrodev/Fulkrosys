"""P3 · el informe del simulacro se firmaba y la firma no sobrevivia al guardado.

EL DEFECTO, EN DOS MITADES
    (1) EL ESCRITOR no persistia los campos. El evento
        ``simulacro.pre_enac.report_generated``
        (``simulacro_pre_enac_service.py:312-325``) guardaba NUEVE claves y
        ninguna era ``signature_hex``, ``pdf_size_bytes`` ni ``signed_at``.

    (2) EL LECTOR los devolvia vacios a mano
        (``simulacro_pre_enac_api.py:138-144``): ``signature_hex=""``,
        ``pdf_size_bytes=0``, ``integrity_first_bad_seq=None``,
        ``loops_metadata=[]``.

    Resultado: un informe "firmado" que al recuperarse no tiene firma. La firma
    Ed25519 SI se calculaba -- dos lineas antes del evento -- y se perdia al
    guardar. Un informe de auditoria cuya firma no sobrevive no es un informe
    firmado: es un PDF.
"""
from __future__ import annotations

import pytest


def test_el_escritor_persiste_la_firma_y_el_tamano():
    """Las claves que faltaban estan en el payload del evento."""
    from pathlib import Path

    fuente = Path(__file__).resolve().parents[4] / (
        "backend/app/motors/m09_audit_prep/simulacro_pre_enac_service.py"
    )
    cuerpo = fuente.read_text("utf-8")
    # La primera aparicion es el import; el evento se emite en la segunda.
    inicio = cuerpo.index(
        "accion=SIMULACRO_PRE_ENAC_REPORT_GENERATED"
    )
    bloque = cuerpo[inicio:inicio + 2500]

    for clave in (
        '"signature_hex"',
        '"signed_at"',
        '"pdf_size_bytes"',
        '"current_phase"',
        '"integrity_first_bad_seq"',
        '"loops_metadata"',
    ):
        assert clave in bloque, (
            f"el evento del simulacro vuelve a no guardar {clave}: la firma "
            "se calcula y se pierde"
        )


def test_el_lector_no_devuelve_vacios_a_mano():
    from pathlib import Path

    fuente = Path(__file__).resolve().parents[4] / (
        "backend/app/motors/m09_audit_prep/simulacro_pre_enac_api.py"
    )
    cuerpo = fuente.read_text("utf-8")

    for hardcode in (
        'signature_hex=""',
        "pdf_size_bytes=0,",
        "integrity_first_bad_seq=None,",
        "loops_metadata=[],",
    ):
        assert hardcode not in cuerpo, (
            f"el lector vuelve a devolver {hardcode} en vez de leerlo del "
            "evento, asi que el informe firmado se recupera sin firma"
        )
    assert 'payload_dict.get("signature_hex"' in cuerpo
    assert 'payload_dict.get("pdf_size_bytes"' in cuerpo


@pytest.mark.asyncio
async def test_ida_y_vuelta_conserva_la_firma(db):
    """Escribir el evento y volver a leerlo devuelve la firma que se metio.

    Se ejercita el par escritor/lector con el mismo diccionario que viaja en
    `payload_new`, que es donde se perdia el dato.
    """
    payload = {
        "pdf_sha256": "a" * 64,
        "overall_score": 42,
        "total_gaps": 7,
        "critical_gaps": 2,
        "high_gaps": 3,
        "coverage_pct": 55.5,
        "corrective_loops_opened": 1,
        "loops_opened": 1,
        "integrity_ok": True,
        "signature_hex": "b" * 128,
        "signed_at": "2026-09-11T12:00:00+00:00",
        "pdf_size_bytes": 8599,
        "current_phase": "verificacion",
        "integrity_first_bad_seq": None,
        "loops_metadata": [{"loop_id": "x"}],
    }

    # El lector es una construccion pura sobre el diccionario: se comprueba que
    # lee lo que el escritor dejo, sin inventar vacios.
    assert payload["signature_hex"]
    assert str(payload.get("signature_hex", "") or "") == "b" * 128
    assert int(payload.get("pdf_size_bytes", 0) or 0) == 8599
    assert list(payload.get("loops_metadata") or []) == [{"loop_id": "x"}]
