"""FULKRO logos · inline base64 + context-aware helpers (mini-atom round 2).

Reads the 4 SVG variants from ``frontend/public/brand/`` and exposes them
as base64 data URIs ready to drop into ``<mj-image src="...">`` (or any
``<img>``) — email clients strip external image links, so inlining the
SVG via data URI is the email-safe approach.

Public helpers:

- ``FulkroLogos.MONO_WHITE_BASE64`` / ``BLACK_BASE64`` / ``LIGHT_BASE64`` /
  ``DARK_BASE64`` — direct access to each variant data URI.

- ``FulkroLogos.for_background(bg_hex)`` — picks the highest-contrast
  variant for a given background color (WCAG AA target ≥ 4.5:1).

- ``FulkroLogos.for_severity_header(severity)`` — convenience for
  severity-coded headers (HIGH/CRITICAL/MEDIUM/LOW/INFO).

The four variants:

| Variant     | Strokes/text       | Background expected         |
|-------------|--------------------|-----------------------------|
| mono_white  | All white          | Dark (slate-900 · severity) |
| light       | Indigo + slate     | Light (white card)          |
| dark        | Self-contained card (#0F0F12) | Standalone — embed only when standalone is wanted |
| black       | All black          | Light (also OK)             |
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path


# Resolve frontend brand dir from this file: backend/app/motors/m_compliance/
# email_design/ → project root → frontend/public/brand/.
_BRAND_DIR = (
    Path(__file__).resolve().parents[5] / "frontend" / "public" / "brand"
)


def _file_to_data_uri(path: Path) -> str:
    """Encode an SVG file as a ``data:image/svg+xml;base64,...`` URI."""
    if not path.exists():
        # Fallback: empty 1x1 transparent SVG so the email still renders.
        return (
            "data:image/svg+xml;base64,"
            "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciLz4="
        )
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


@lru_cache(maxsize=8)
def _data_uri(variant: str) -> str:
    return _file_to_data_uri(_BRAND_DIR / f"fulkro-logo-{variant}.svg")


class FulkroLogos:
    """Brand logo variants encoded as inline data URIs."""

    # ── Direct accessors (lazy via cached helper) ──────────────────

    @classmethod
    def mono_white(cls) -> str:
        """White-only logo for dark backgrounds (slate-900, severity colors)."""
        return _data_uri("mono-white")

    @classmethod
    def black(cls) -> str:
        """All-black logo for very light backgrounds (≥ 95% luminance)."""
        return _data_uri("black")

    @classmethod
    def light(cls) -> str:
        """Indigo + dark text logo for white / off-white card backgrounds."""
        return _data_uri("light")

    @classmethod
    def dark(cls) -> str:
        """Self-contained card logo with embedded dark background (standalone)."""
        return _data_uri("dark")

    # ── Backwards-compatible class-attribute style for templates ──

    @property
    def MONO_WHITE_BASE64(self) -> str:  # noqa: N802 — uppercase by intent
        return self.mono_white()

    @property
    def BLACK_BASE64(self) -> str:  # noqa: N802
        return self.black()

    @property
    def LIGHT_BASE64(self) -> str:  # noqa: N802
        return self.light()

    @property
    def DARK_BASE64(self) -> str:  # noqa: N802
        return self.dark()

    # ── Context-aware selectors ───────────────────────────────────

    @classmethod
    def for_background(cls, bg_hex: str) -> str:
        """Return the variant with best contrast on the given background.

        Threshold: pick ``mono_white`` whenever the background luminance is
        below 50 % (dark backgrounds), otherwise pick ``black`` (best
        contrast on white cards). Both variants are transparent so the
        email's underlying background color shows through.
        """
        bg = bg_hex.lstrip("#")
        if len(bg) == 3:
            bg = "".join(c * 2 for c in bg)
        if len(bg) != 6:
            return cls.mono_white()
        try:
            r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
        except ValueError:
            return cls.mono_white()
        # Relative luminance (sRGB approximation) per W3C WCAG 2.x.
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
        return cls.mono_white() if luminance < 0.5 else cls.black()

    @classmethod
    def for_severity_header(cls, severity: str) -> str:
        """Convenience: every severity header is dark, so always mono_white."""
        # All current severity solids (HIGH/CRITICAL/MEDIUM/LOW/INFO) are
        # bright/dark enough that the white variant wins. Kept as a separate
        # helper so future palette changes have a single touch point.
        _ = severity  # reserved for future palette-aware switching
        return cls.mono_white()


LOGOS = FulkroLogos()
"""Singleton instance ready to use as ``LOGOS.MONO_WHITE_BASE64`` etc."""
