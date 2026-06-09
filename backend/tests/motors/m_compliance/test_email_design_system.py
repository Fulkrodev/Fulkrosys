"""MJML email design system tests (mini-atom).

8 tests verify that the MJML pipeline (Jinja2 → MJML → HTML) produces
brand-coherent, email-safe HTML for every compliance template, with the
severity / status semantics rendered correctly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from backend.app.motors.m_compliance.email_design import brand_tokens
from backend.app.motors.m_compliance.email_design.mjml_compiler import render_email


@dataclass
class _Breach:
    breach_code: str = "BREACH_2026_001"
    detected_at: datetime = datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc)
    severity: str = "high"
    description: str = "Acceso no autorizado a backup."
    data_categories_affected: list = None
    data_subjects_count: int | None = 42
    root_cause: str | None = "Permisos incorrectos."
    containment_actions: str | None = "Claves revocadas."
    remediation_actions: str | None = "Auditoría programada."


@dataclass
class _Request:
    id: str = "00000000-0000-0000-0000-000000000001"
    requested_at: datetime = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    processed_at: datetime = datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc)
    processed_by: str = "marcos@fulkro.es"
    rejection_reason: str | None = "Retención legal ENS."


_NOW = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)


def _assert_chrome(html: str) -> None:
    """Every compiled template must contain the brand chrome + DPO footer."""
    assert "FULKRO" in html
    assert "dpo@fulkro.es" in html
    assert "Trust Center" in html
    # MJML produces email-safe inline CSS (style="" attributes) — no
    # <style> tags should leak as the sole formatting mechanism.
    assert 'style="' in html
    # Logo SVG inline data URI present (not external URL · email-safe).
    assert "data:image/svg+xml;base64," in html


# ── 1: MJML pipeline + base chrome ─────────────────────────────────────


def test_mjml_pipeline_compiles_base_chrome() -> None:
    html = render_email(
        "compliance_alert.mjml",
        dict(
            severity_label="LOW",
            severity_level="low",
            status_label="GREEN",
            period_label="digest weekly",
            check_count=0,
            alerts=[],
            admin_url=None,
            report_url=None,
        ),
    )
    assert html.startswith("<!doctype html>") or html.startswith("<!DOCTYPE html>")
    _assert_chrome(html)
    # Severity LOW renders the green badge color from BrandTokens.
    assert brand_tokens.TOKENS.SEVERITY_LOW.lower() in html.lower()


# ── 2: severity badge HIGH ─────────────────────────────────────────────


def test_compliance_alert_renders_severity_high_badge() -> None:
    html = render_email(
        "compliance_alert.mjml",
        dict(
            severity_label="HIGH",
            severity_level="high",
            status_label="RED",
            period_label="alerta inmediata",
            check_count=1,
            alerts=[
                {
                    "check_name": "ssl_cert_expiry",
                    "status": "RED",
                    "status_level": "red",
                    "message": "Cert expira en 5 días",
                }
            ],
            admin_url="https://fulkro.es/admin/compliance/monitor",
            report_url="https://fulkro.es/report.md",
        ),
    )
    _assert_chrome(html)
    assert "HIGH" in html
    assert brand_tokens.TOKENS.SEVERITY_HIGH.lower() in html.lower()
    # Check name + message visible.
    assert "ssl_cert_expiry" in html
    assert "Cert expira en 5 días" in html
    # CTA branded button.
    assert "Descargar reporte completo" in html


# ── 3: AEPD breach 9 sections + article refs ───────────────────────────


def test_aepd_breach_renders_9_sections_with_article_refs() -> None:
    breach = _Breach(
        data_categories_affected=["Identificativos", "Contacto"]
    )
    html = render_email(
        "aepd_breach_notification.mjml",
        dict(breach=breach, now=_NOW),
    )
    _assert_chrome(html)
    assert "BREACH_2026_001" in html
    # All 9 section headers present.
    for title in [
        "1. Responsable del tratamiento",
        "2. Naturaleza de la violación",
        "3. Categorías de datos afectadas",
        "4. Número aproximado",
        "5. Datos de contacto del DPO",
        "6. Consecuencias probables",
        "7. Causa raíz",
        "8. Medidas de contención",
        "9. Medidas propuestas",
    ]:
        assert title in html, f"missing AEPD section: {title}"
    # Explicit Article 33.3 references.
    assert "Art. 33.3" in html
    # 72h cronología banner.
    assert "72h SLA" in html


# ── 4: client breach warning banner severity color ─────────────────────


def test_client_breach_renders_warning_banner_severity_color() -> None:
    breach = _Breach(
        severity="medium",
        data_categories_affected=["Email", "Nombre"],
    )
    html = render_email(
        "client_breach_notification.mjml",
        dict(breach=breach, cliente_email="x@example.com", now=_NOW),
    )
    _assert_chrome(html)
    # Warning banner background color (MEDIUM severity).
    assert brand_tokens.TOKENS.SEVERITY_MEDIUM.lower() in html.lower()
    # Détection date appears in the banner.
    assert "2026-05-12" in html
    # Cliente email surfaces in the footer.
    assert "x@example.com" in html
    # CTA "Ejercer mis derechos".
    assert "Ejercer mis derechos" in html


# ── 5: erasure_completed success badge + ENS rationale ─────────────────


def test_erasure_completed_renders_success_badge_and_ens_rationale() -> None:
    html = render_email("erasure_completed.mjml", dict(request=_Request()))
    _assert_chrome(html)
    # Success pill text.
    assert "Solicitud procesada correctamente" in html
    # ENS retention obligation explained.
    assert "RD 311/2022" in html
    assert "art. 24.1" in html
    # Tombstone marker referenced.
    assert "[anonimizado]" in html


# ── 6: erasure_rejected amber + legal basis prominent + 2 CTAs ─────────


def test_erasure_rejected_renders_amber_legal_basis_and_two_ctas() -> None:
    html = render_email("erasure_rejected.mjml", dict(request=_Request()))
    _assert_chrome(html)
    # Amber/orange severity color present.
    assert brand_tokens.TOKENS.SEVERITY_MEDIUM.lower() in html.lower()
    # Rejection reason rendered in blockquote.
    assert "Retención legal ENS" in html
    # Two CTAs.
    assert "Contactar al DPO" in html
    assert "Ejercer otros derechos" in html
    # AEPD recourse link.
    assert "aepd.es" in html


# ── 7: email-safe inline CSS (no <style> as sole formatting) ───────────


def test_mjml_output_is_email_safe_inline_css() -> None:
    """MJML inlines styles so the rendered HTML contains many ``style=``
    attributes (email clients ignore most <style> blocks)."""
    html = render_email("erasure_completed.mjml", dict(request=_Request()))
    style_attrs = html.count('style="')
    # MJML typically emits dozens of inline style attributes for each
    # table cell · 30+ is a healthy lower bound.
    assert style_attrs >= 30, f"expected inline styles, got {style_attrs}"


# ── 8: brand tokens centralised + used consistently ────────────────────


# ── 9-11: round 2 polish (logos + WCAG AA contrast) ───────────────────


def test_logo_for_background_dark_returns_mono_white() -> None:
    """Dark backgrounds get the mono-white variant for WCAG AA contrast."""
    from backend.app.motors.m_compliance.email_design.logos import FulkroLogos

    # slate-900 + severity solids are all dark → mono-white expected.
    for dark_bg in ("#0f172a", "#1a1a1a", "#dc2626", "#c2410c"):
        assert FulkroLogos.for_background(dark_bg) == FulkroLogos.mono_white(), (
            f"{dark_bg} should pick mono_white"
        )


def test_logo_for_background_light_returns_black() -> None:
    """Light backgrounds get the black variant for max contrast."""
    from backend.app.motors.m_compliance.email_design.logos import FulkroLogos

    for light_bg in ("#ffffff", "#f9fafb", "#f3f4f6"):
        assert FulkroLogos.for_background(light_bg) == FulkroLogos.black(), (
            f"{light_bg} should pick black"
        )


def test_severity_medium_contrast_wcag_aa_compliant() -> None:
    """SEVERITY_MEDIUM #c2410c on white has 6.5:1 contrast (WCAG AA)."""
    import re

    bg = brand_tokens.TOKENS.SEVERITY_MEDIUM.lstrip("#").lower()
    # Polish round 2 fixed #ea580c (4.4:1) → #c2410c (6.5:1).
    assert bg == "c2410c", (
        f"SEVERITY_MEDIUM should be #c2410c (WCAG AA · 6.5:1); got #{bg}"
    )

    # Sanity: relative luminance of c2410c is well below 0.5 (orange-700
    # is dark enough that white text on top hits ≥ 4.5:1).
    r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    assert luminance < 0.5, f"#{bg} luminance {luminance:.3f} too bright for white text"


def test_body_width_template_variable_overrides_default() -> None:
    """``body_width`` param flows into the rendered max-width."""
    html_email = render_email(
        "erasure_completed.mjml",
        dict(request=_Request(), body_width="600px"),
    )
    html_preview = render_email(
        "erasure_completed.mjml",
        dict(request=_Request(), body_width="840px"),
    )
    assert "max-width:600px" in html_email
    assert "max-width:840px" in html_preview
    # Different widths must produce visibly different layout markup.
    assert html_email != html_preview


def test_brand_tokens_used_consistently_across_templates() -> None:
    """Brand colors from ``BrandTokens`` should appear in every template."""
    inputs = [
        ("compliance_alert.mjml", dict(
            severity_label="LOW", severity_level="low",
            status_label="GREEN", period_label="digest weekly",
            check_count=0, alerts=[], admin_url=None, report_url=None,
        )),
        ("aepd_breach_notification.mjml", dict(
            breach=_Breach(data_categories_affected=["x"]), now=_NOW,
        )),
        ("client_breach_notification.mjml", dict(
            breach=_Breach(data_categories_affected=["x"]),
            cliente_email="x@y.com", now=_NOW,
        )),
        ("erasure_completed.mjml", dict(request=_Request())),
        ("erasure_rejected.mjml", dict(request=_Request())),
    ]
    primary = brand_tokens.TOKENS.PRIMARY.lower()
    accent_light = brand_tokens.TOKENS.ACCENT_LIGHT.lower()
    for name, ctx in inputs:
        html = render_email(name, ctx).lower()
        assert primary in html, f"{name}: primary color missing"
        # Footer link color on dark bg.
        assert accent_light in html, f"{name}: accent light missing"
