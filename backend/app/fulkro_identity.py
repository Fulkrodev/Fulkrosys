"""Fulkro identity · single source of truth backend.

Sesión 3B-4 Ejecutable 7.6 (2026-05-27).

DOCTRINE INVIOLABLE: Marcos Mata · autónomo Madrid · consultor ENS.
Fulkro identity propagation cross-system (PDFs · emails · WhatsApp · copilots ·
sede artifacts) MUST reference these constants · NO hardcoded duplicates.

Outcome-as-a-Service framing: cliente VE info Fulkro consultora claramente ·
trust building. "Fulkro shown not sold" doctrine.

Module path `backend.app.fulkro_identity` (NO `backend.app.config.X` para evitar
naming collision con existing `backend/app/config.py` module file).
"""
from __future__ import annotations


FULKRO_PHONE: str = "+34 637 165 328"
"""Teléfono profesional Marcos Mata · Fulkro consultora ENS."""

FULKRO_WEB: str = "www.fulkro.es"
"""Web corporativa Fulkro · sin protocolo prefix (UI agnostic)."""

FULKRO_WEB_URL: str = "https://www.fulkro.es"
"""Web corporativa Fulkro · URL completo con HTTPS para links clickables."""

FULKRO_EMAIL: str = "marcosmata@fulkro.es"
"""Email profesional · corporate domain post-migration de gmail."""

FULKRO_BRAND_TAGLINE: str = "Rigor · velocidad · proactividad"
"""Tagline interno · 'Fulkro shown not sold' doctrine."""

FULKRO_DISTINTIVO_COLOR_PANTONE_ORANGE_021C: str = "#FE5000"
"""Color canónico del distintivo de conformidad ENS · Pantone Orange 021C
(CCN-STIC 809) · ÚNICO para todas las categorías (BÁSICA/MEDIA/ALTA), NO por
categoría. Distinto del violeta de marca UI (#6C63FF). Ejecutable 8 Pasada 16
(F-14-06)."""

FULKRO_AUTHOR_NAME: str = "Marcos Mata"
"""Arquitecto + consultor autónomo Madrid."""

FULKRO_AUTHOR_ROLE: str = "Consultor de Fulkro"
"""Rol estándar referenced en outputs."""

FULKRO_FOOTER_TEXT: str = (
    f"Fulkro · {FULKRO_PHONE} · {FULKRO_WEB} · {FULKRO_EMAIL}"
)
"""Footer canónico cross outputs · usado en PDFs + emails + frontend footer."""

FULKRO_EMAIL_SIGNATURE_HTML: str = (
    f'<p>Un saludo,<br>'
    f'<strong>{FULKRO_AUTHOR_NAME}</strong> · {FULKRO_AUTHOR_ROLE}<br>'
    f'📞 {FULKRO_PHONE} · '
    f'<a href="mailto:{FULKRO_EMAIL}">{FULKRO_EMAIL}</a> · '
    f'<a href="{FULKRO_WEB_URL}">{FULKRO_WEB}</a></p>'
)
"""HTML signature canónico email templates m20 notifications."""

FULKRO_EMAIL_SIGNATURE_TEXT: str = (
    f"Un saludo,\n"
    f"{FULKRO_AUTHOR_NAME} · {FULKRO_AUTHOR_ROLE}\n"
    f"Tel: {FULKRO_PHONE}\n"
    f"Email: {FULKRO_EMAIL}\n"
    f"Web: {FULKRO_WEB}"
)
"""Plain-text signature canónico email templates m20 notifications fallback."""

FULKRO_COPILOT_PRIMARY_CONTEXT: str = (
    f"Fulkro es una consultora ENS · contacto: {FULKRO_PHONE} · "
    f"{FULKRO_WEB} · {FULKRO_EMAIL}. "
    f"{FULKRO_AUTHOR_NAME} es el arquitecto + consultor autónomo en Madrid."
)
"""Primary context wired en copilots system prompts (agent_14 + cliente copilot)
para empirical-grounded responses cuando usuario pregunta '¿cómo contactaros?'.
NO hallucination · canonical Fulkro identity."""
