"""Unit tests for M12 magic-link rich HTML email renderer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.motors.m12_magic_link.emails.renderer import (
    render_email_for_magic_link,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose


CLIENTE = {
    "razon_social": "DataForma Galicia SL",
    "cif": "B72634815",
    "sector": "salud",
}
PROYECTO = {"nombre": "Certificación ENS Media — 2026", "codigo_documento_base": "POL"}
DESTINATARIO = {
    "nombre": "Jorge Fernández Rodríguez",
    "cargo": "Responsable de Seguridad de la Información",
    "email": "rseg@dataforma.es",
}


def _render(purpose: MagicLinkPurpose, **extra):
    return render_email_for_magic_link(
        purpose=purpose,
        link_url="https://fulkro.es/ml/consume?token=abc",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
        cliente=CLIENTE,
        proyecto=PROYECTO,
        destinatario=DESTINATARIO,
        otp="123456",
        **extra,
    )


def test_firma_documento_html_structure():
    subject, html, text = _render(
        MagicLinkPurpose.FIRMA_DOCUMENTO,
        documento={"codigo": "E-100", "titulo": "Política de Seguridad"},
    )
    assert "E-100" in subject
    assert "DataForma Galicia SL" in subject
    assert "<!DOCTYPE html>" in html
    assert "Jorge Fernández Rodríguez" in html
    assert "Firmar el documento" in html
    assert "QUÉ debe hacer" in html
    assert "POR QUÉ" in html
    assert "CUÁNDO" in html
    assert "abc" in html  # token appears in link
    assert "123456" in html  # OTP rendered
    assert "Marcos Mata García" in html
    assert "Consultor independiente" in html
    # Must NOT leak internal refs
    for forbidden in ("FULKRO", "Motor ", "Agente ", "Document Factory", "Copiloto"):
        assert forbidden not in html, f"leaked {forbidden!r}"


def test_aporte_evidencia_interpolation():
    subject, html, text = _render(
        MagicLinkPurpose.APORTE_EVIDENCIA,
        medida={"codigo": "op.acc.6"},
        fecha_objetivo="2026-05-20",
    )
    assert "op.acc.6" in subject
    assert "op.acc.6" in html
    assert "Subir evidencias" in html


def test_autorizar_pentest_externo_renders_security_note():
    """Verifica AUTORIZAR_PENTEST_EXTERNO email config (M8 v5.1 superseded
    AUTORIZACION_PENTEST legacy · removed SAN-B.MB-6.6)."""
    subject, html, text = _render(
        MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
        alcance_corto="dataforma.es + 10.20.0.0/24",
        ventana_inicio="2026-05-02 22:00 UTC",
    )
    # Subject usa {cliente_razon} desde fixture CLIENTE (DataForma Galicia SL)
    assert "pentesting externo" in subject.lower()
    assert "DataForma Galicia SL" in subject
    assert "<!DOCTYPE html>" in html


def test_text_fallback_includes_url_and_otp():
    subject, html, text = _render(
        MagicLinkPurpose.DESCARGA_DOSSIER_FINAL,
    )
    assert "https://fulkro.es/ml/consume?token=abc" in text
    assert "Código de un solo uso: 123456" in text
    assert "Marcos Mata García" in text
    # plain text version must NOT contain HTML tags
    assert "<html>" not in text.lower()
    assert "<p>" not in text.lower()


# Sprint Polish block 3 · Opción α (2026-05-12):
# Configs eliminadas en renderer.py para purposes hard-revoked por
# ADR-020 v3 SAN-E v3.MB-4.bis3 · render_email_for_magic_link debe
# lanzar ValueError("No email template for purpose: ...") al recibirlos.
_DEPRECATED_V3_NO_EMAIL: frozenset[MagicLinkPurpose] = frozenset({
    MagicLinkPurpose.APROBACION_FACTURA,
    MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE,
    MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL,
    MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS,
})


def test_all_purposes_render_without_error():
    """Test invariante: los purposes activos del enum renderizan sin error
    con context completo · los deprecated v3 sin config lanzan ValueError.

    Historial:
    - SAN-B.MB-6.6 (drop AUTORIZACION_PENTEST legacy): 34 purposes
    - SAN-D MB-19.4 (FIRMA_CONTRATO purpose nuevo · ADR-041): 35 purposes
    - Sprint Polish block 3 Opción α: 31 con config + 4 deprecated v3
      sin config (`_DEPRECATED_V3_NO_EMAIL`) · hard-rejected.

    Si len(MagicLinkPurpose) cambia, este test debe actualizar la
    assertion + completar las variables del context kwargs según las
    nuevas variables Jinja-style de los emails.
    """
    # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC añadido Sesión 3B-2B.6 · 35 -> 36.
    # Batch A diagnóstico previo: DIAGNOSTICO_PRECLIENTE añadido (#38) · 36 -> 37.
    assert len(list(MagicLinkPurpose)) == 37
    render_kwargs = dict(
        documento={"codigo": "E-100", "titulo": "Política"},
        medida={"codigo": "op.acc.6"},
        acta={"codigo": "ACT-001"},
        requerimiento={"ref": "REQ-2026-03"},
        obligacion={"codigo": "OBL-001"},
        alcance_corto="scope-demo",
        ventana_inicio="2026-05-01 21:00",
        fecha_objetivo="2026-05-30",
        reunion_titulo="Comité Directivo Q2",
        reunion_fecha="2026-05-20",
        propuesta_codigo="P-001-2026",
        factura_codigo="F-2026-042",
        factura_importe="9.500,00 €",
        asunto_corto="inventario de activos",
        cambio_codigo="CCA-2026-003",
        riesgo_codigo="R-AR-017",
        incidente_codigo="INC-2026-009",
        severidad="ALTA",
        acta_codigo="Acta-Comite-2026-04",
        sesion_fecha="2026-04-15",
    )
    for purpose in MagicLinkPurpose:
        # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC es legítimo pero de entrega OUT-OF-BAND
        # (admin comparte link al auditor externo · sin template email) → renderiza ValueError
        # igual que los deprecated v3.
        # DIAGNOSTICO_PRECLIENTE (Batch A): template de email pendiente Batch B
        # (envío real al lead vía outreach) · de momento sin template → ValueError.
        if (
            purpose in _DEPRECATED_V3_NO_EMAIL
            or purpose == MagicLinkPurpose.AUDITOR_PORTAL_ENAC
            or purpose == MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE
        ):
            with pytest.raises(ValueError, match="No email template for purpose"):
                _render(purpose, **render_kwargs)
            continue
        subject, html, text = _render(purpose, **render_kwargs)
        assert "<!DOCTYPE html>" in html
        assert subject
        assert "Marcos Mata García" in html
        assert "Marcos Mata García" in text


# ════════════════════════════════════════════════════════════════════
# M8 v5.1 — Verificacion Tecnica (Sesion 7) — 5 magic links
# ════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("purpose", [
    MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
    MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
    MagicLinkPurpose.PORTAL_REMEDIACION,
    MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
    MagicLinkPurpose.REVISAR_INFORME_VERIFICACION,
])
def test_m8_v51_purpose_renders_no_leaks(purpose):
    subject, html, text = _render(
        purpose,
        alcance_corto="Sistemas clinicos digitales (192.168.10.0/24)",
        ventana_inicio="2026-05-02 22:00",
        fecha_objetivo="2026-06-15",
    )
    # Estructura HTML rica
    assert "<!DOCTYPE html>" in html
    assert "DataForma Galicia SL" in html
    assert "QUÉ debe hacer" in html
    assert "POR QUÉ" in html
    assert "CUÁNDO" in html
    assert "Marcos Mata García" in html
    # 0 leaks internos (regla inviolable)
    for forbidden in (
        "FULKRO", "Motor 8", "Motor 12", "Document Factory",
        "Copiloto", "M8 v", "v5.1", "v4.2",
    ):
        assert forbidden not in html, f"leak {forbidden!r} en {purpose.value}"
        assert forbidden not in subject, f"leak {forbidden!r} en subject"


def test_autorizar_verificacion_tecnica_otp_required():
    """Purpose autorizar_verificacion_tecnica exige OTP por sensibilidad."""
    from backend.app.motors.m12_magic_link.purposes import get_config
    cfg = get_config(MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA)
    assert cfg["requires_otp"] is True
    assert cfg["ttl_hours"] == 48
    assert cfg["max_uses"] == 1


def test_autorizar_pentest_externo_72h_otp():
    from backend.app.motors.m12_magic_link.purposes import get_config
    cfg = get_config(MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO)
    assert cfg["ttl_hours"] == 72
    assert cfg["requires_otp"] is True
    assert cfg["max_uses"] == 1


def test_portal_remediacion_90d_no_otp():
    """Portal remediacion: cliente entra repetidamente sin OTP."""
    from backend.app.motors.m12_magic_link.purposes import get_config
    cfg = get_config(MagicLinkPurpose.PORTAL_REMEDIACION)
    assert cfg["ttl_hours"] == 90 * 24
    assert cfg["requires_otp"] is False
    assert cfg["max_uses"] >= 100  # uso libre durante 90 dias


def test_portal_pentester_60d_otp():
    from backend.app.motors.m12_magic_link.purposes import get_config
    cfg = get_config(MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO)
    assert cfg["ttl_hours"] == 60 * 24
    assert cfg["requires_otp"] is True
    assert cfg["max_uses"] >= 100


def test_revisar_informe_verificacion_15d():
    from backend.app.motors.m12_magic_link.purposes import get_config
    cfg = get_config(MagicLinkPurpose.REVISAR_INFORME_VERIFICACION)
    assert cfg["ttl_hours"] == 15 * 24
    assert cfg["requires_otp"] is True


def test_autorizar_pentest_externo_html_security_note():
    subject, html, text = _render(
        MagicLinkPurpose.AUTORIZAR_PENTEST_EXTERNO,
        alcance_corto="Sistemas clinicos + portal pacientes",
        ventana_inicio="2026-06-01",
        fecha_objetivo="2026-06-30",
    )
    assert "OSCP" in html  # menciona certificacion del pentester
    assert "NO autorice" in html  # security note
    assert "VPN" in html or "vpn" in html  # mencion al acceso


def test_portal_remediacion_mentions_sla():
    subject, html, text = _render(
        MagicLinkPurpose.PORTAL_REMEDIACION,
    )
    assert "SLA" in html or "sla" in html.lower()
    assert "remediación" in html.lower() or "remediacion" in html.lower()
    assert "Ya lo he arreglado" in html  # menciona el flujo


def test_portal_pentester_mentions_engagement_documents():
    subject, html, text = _render(
        MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
        fecha_objetivo="2026-06-30",
    )
    # El pentester recibe documentos completos del engagement
    for keyword in ("alcance", "inventario", "credenciales", "pentest"):
        assert keyword in html.lower(), f"missing {keyword}"


def test_revisar_informe_mentions_e702_e703():
    subject, html, text = _render(
        MagicLinkPurpose.REVISAR_INFORME_VERIFICACION,
    )
    assert "E-702" in html
    assert "E-703" in html
    assert "RD 311/2022" in html  # cita normativa


def test_unknown_placeholder_does_not_raise():
    subject, html, _ = _render(
        MagicLinkPurpose.FIRMA_DOCUMENTO,
        # Note: we DO NOT pass ``documento`` so {doc_codigo} is missing.
    )
    # Should still render without raising — the missing placeholder
    # collapses to an empty string (no unresolved ``{...}`` leaked).
    assert "{" not in subject
    assert subject.startswith("Firma del documento")
    assert "DataForma Galicia SL" in subject
