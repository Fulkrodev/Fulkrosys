"""MJML → email-safe HTML compiler (mini-atom · email design system).

Two-stage pipeline:

1. Render MJML source through Jinja2 (variable substitution + ``severity_*``
   / ``outcome_*`` helpers exposed in the env globals).
2. Compile the resulting MJML string into email-safe HTML using
   ``mjml-python`` (Rust-backed wrapper of the official MJML compiler).

Templates extend a single ``_email_base.mjml`` chrome and override the
``content`` block. Brand tokens are available as ``tokens.*``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import mjml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.app.motors.m_compliance.email_design.brand_tokens import (
    TOKENS,
    outcome_bg,
    outcome_text,
    severity_bg,
    severity_solid,
)
from backend.app.motors.m_compliance.email_design.logos import FulkroLogos


_TEMPLATES_DIR = Path(__file__).parent / "templates"


class MJMLCompilationError(Exception):
    """Raised when MJML compilation fails (syntax or schema)."""


@lru_cache(maxsize=1)
def _env() -> Environment:
    """Lazy-built Jinja2 environment with brand tokens + helpers exposed."""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        # Autoescape ACTIVADO para .mjml: antes estaba deshabilitado para esa
        # extensión, por lo que las variables ({{ breach.description }},
        # {{ rejection_reason }}, {{ cliente_email }}…) se interpolaban sin escapar
        # → XSS en el email renderizado. El markup MJML estático de la plantilla
        # NO se ve afectado (autoescape solo escapa interpolaciones); si alguna
        # variable debe ser HTML crudo, debe marcarse explícitamente con |safe.
        autoescape=select_autoescape(enabled_extensions=("mjml", "html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(
        tokens=TOKENS,
        severity_bg=severity_bg,
        severity_solid=severity_solid,
        outcome_bg=outcome_bg,
        outcome_text=outcome_text,
        logos=FulkroLogos,
    )
    return env


def render_email(template_name: str, context: dict[str, Any]) -> str:
    """Compile an MJML template under ``email_design/templates/`` to HTML.

    ``template_name`` is the bare filename relative to the templates dir
    (e.g. ``"compliance_alert.mjml"``). The default header background is
    slate-900 (dark), so callers that don't pass ``logo_base64`` get the
    mono-white variant automatically.
    """
    template = _env().get_template(template_name)
    ctx = {
        "logo_base64": FulkroLogos.for_background(TOKENS.PRIMARY),
        # Identidad fiscal opcional (punto #44): default None para que las
        # plantillas que la usen degraden con ``fiscal.x or '...'`` aunque el
        # caller no la pase (``None.attr`` → undefined → fallback).
        "fiscal": None,
        **context,
    }
    mjml_source = template.render(**ctx)
    html = mjml.mjml2html(mjml_source)
    if not html or not html.strip():
        raise MJMLCompilationError(
            f"MJML compiler returned empty output for {template_name}"
        )
    return html
