"""FULKRO email brand tokens (mini-atom · email design system).

Centralised design tokens used by every MJML template under
``email_design/templates/``. Updating the brand here cascades to all
5 compliance emails plus future templates (M18 communications, M31
WhatsApp digest, etc).

The tokens are intentionally plain ``str`` constants so they can be
substituted into MJML attribute values via Jinja2 ``{{ tokens.PRIMARY }}``
without any conversion layer.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrandTokens:
    # ── Primary palette ───────────────────────────────────────────
    PRIMARY: str = "#0f172a"            # slate-900 (FULKRO dark)
    PRIMARY_HOVER: str = "#1e293b"      # slate-800
    PRIMARY_LIGHT: str = "#475569"      # slate-600 (subtle text)
    ACCENT: str = "#2563eb"             # blue-600 (links + secondary CTA)
    ACCENT_LIGHT: str = "#60a5fa"       # blue-400 (footer links on dark bg)

    # ── Severity palette (WCAG AA contrast on white) ──────────────
    SEVERITY_HIGH: str = "#dc2626"      # red-600
    SEVERITY_HIGH_BG: str = "#fee2e2"   # red-100
    SEVERITY_HIGH_TEXT: str = "#7f1d1d" # red-900
    # WCAG AA fix · #ea580c → #c2410c (orange-700) gives 6.5:1 contrast
    # against white text · MEDIUM borderline contrast catch round 2.
    SEVERITY_MEDIUM: str = "#c2410c"    # orange-700
    SEVERITY_MEDIUM_BG: str = "#ffedd5" # orange-100
    SEVERITY_MEDIUM_TEXT: str = "#7c2d12"
    SEVERITY_LOW: str = "#16a34a"       # green-600
    SEVERITY_LOW_BG: str = "#dcfce7"    # green-100
    SEVERITY_LOW_TEXT: str = "#166534"
    SEVERITY_INFO: str = "#2563eb"      # blue-600
    SEVERITY_INFO_BG: str = "#dbeafe"   # blue-100
    SEVERITY_INFO_TEXT: str = "#1e3a8a"

    # ── Outcome semaphore (Self-Monitoring) ───────────────────────
    OUTCOME_GREEN_BG: str = "#dcfce7"
    OUTCOME_GREEN_TEXT: str = "#166534"
    OUTCOME_YELLOW_BG: str = "#fef3c7"
    OUTCOME_YELLOW_TEXT: str = "#92400e"
    OUTCOME_RED_BG: str = "#fee2e2"
    OUTCOME_RED_TEXT: str = "#991b1b"
    OUTCOME_UNKNOWN_BG: str = "#e2e8f0"
    OUTCOME_UNKNOWN_TEXT: str = "#1e293b"

    # ── Layout palette ────────────────────────────────────────────
    BG_BODY: str = "#f3f4f6"            # gray-100
    BG_CARD: str = "#ffffff"
    BG_SECTION_SUBTLE: str = "#f8fafc"  # slate-50
    BORDER_SUBTLE: str = "#e5e7eb"      # gray-200
    BORDER_STRONG: str = "#cbd5e1"      # slate-300

    # ── Typography ────────────────────────────────────────────────
    FONT_FAMILY: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "Helvetica, Arial, sans-serif"
    )
    FONT_MONO: str = (
        "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace"
    )
    TEXT_PRIMARY: str = "#0f172a"
    TEXT_SECONDARY: str = "#475569"
    TEXT_MUTED: str = "#94a3b8"
    TEXT_ON_DARK: str = "#ffffff"
    TEXT_ON_DARK_MUTED: str = "#cbd5e1"

    # ── Sizing ────────────────────────────────────────────────────
    CONTAINER_WIDTH: str = "600px"
    PADDING_SECTION: str = "24px"

    # ── DPO + contact info (single source) ────────────────────────
    BRAND_NAME: str = "FULKRO"
    BRAND_TAGLINE: str = "Consultor servicios IT · ENS"
    DPO_EMAIL: str = "dpo@fulkro.es"
    SECURITY_EMAIL: str = "security@fulkro.es"
    LEGAL_BASE_URL: str = "https://fulkro.es"


TOKENS = BrandTokens()


def severity_bg(level: str) -> str:
    return {
        "high": TOKENS.SEVERITY_HIGH_BG,
        "critical": TOKENS.SEVERITY_HIGH_BG,
        "medium": TOKENS.SEVERITY_MEDIUM_BG,
        "low": TOKENS.SEVERITY_LOW_BG,
        "info": TOKENS.SEVERITY_INFO_BG,
    }.get(level.lower(), TOKENS.OUTCOME_UNKNOWN_BG)


def severity_solid(level: str) -> str:
    return {
        "high": TOKENS.SEVERITY_HIGH,
        "critical": TOKENS.SEVERITY_HIGH,
        "medium": TOKENS.SEVERITY_MEDIUM,
        "low": TOKENS.SEVERITY_LOW,
        "info": TOKENS.SEVERITY_INFO,
    }.get(level.lower(), TOKENS.PRIMARY_LIGHT)


def outcome_bg(status: str) -> str:
    return {
        "green": TOKENS.OUTCOME_GREEN_BG,
        "yellow": TOKENS.OUTCOME_YELLOW_BG,
        "red": TOKENS.OUTCOME_RED_BG,
        "unknown": TOKENS.OUTCOME_UNKNOWN_BG,
    }.get(status.lower(), TOKENS.OUTCOME_UNKNOWN_BG)


def outcome_text(status: str) -> str:
    return {
        "green": TOKENS.OUTCOME_GREEN_TEXT,
        "yellow": TOKENS.OUTCOME_YELLOW_TEXT,
        "red": TOKENS.OUTCOME_RED_TEXT,
        "unknown": TOKENS.OUTCOME_UNKNOWN_TEXT,
    }.get(status.lower(), TOKENS.OUTCOME_UNKNOWN_TEXT)
