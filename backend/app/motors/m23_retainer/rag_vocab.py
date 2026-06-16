"""Canonical RAG (Red/Amber/Green) vocabulary normalizer for Motor 23.

WAVE C3 (tracker §2.2 line 225) — three RAG vocabularies historically coexist
inside m23_retainer, each producer/consumer pair self-consistent but fragmented:

  (a) ``retainer_checkin_service._compute_rag``  -> english  ``green/amber/red``
      (persisted to ``retainer_quarterly_reports.rag_overall``)
  (b) ``report_service._calc_rag``               -> uppercase ``VERDE/AMBAR/ROJO``
      (stored in ``ReportPayload.rag_global`` -> ``RetainerReport.payload_jsonb``)
  (c) ``paso2_extensions.calculate_health_status`` -> lowercase ``verde/ambar/rojo``

This module is the SINGLE canonical source of truth that any consumer can use to
collapse all three vocabularies (plus emoji-prefixed strings and accent/case
variants) into one normalized form. It is intentionally side-effect free and
deterministic.

Canonical internal token = english ``green | amber | red`` (matches the DB
column ``rag_overall`` written by the check-in service, so the persisted value
flows through unchanged).
"""
from __future__ import annotations

from typing import Optional

# Canonical internal tokens (english · matches rag_overall DB column).
RAG_GREEN = "green"
RAG_AMBER = "amber"
RAG_RED = "red"

CANONICAL_RAG = (RAG_GREEN, RAG_AMBER, RAG_RED)

# Every accepted spelling -> canonical token. Lookup is case-insensitive and
# accent/emoji tolerant (see normalize_rag for the cleaning step).
_RAG_ALIASES: dict[str, str] = {
    # english
    "green": RAG_GREEN,
    "amber": RAG_AMBER,
    "red": RAG_RED,
    # spanish (with and without accents)
    "verde": RAG_GREEN,
    "ambar": RAG_AMBER,
    "ámbar": RAG_AMBER,
    "rojo": RAG_RED,
    # occasional synonyms seen in copy
    "ok": RAG_GREEN,
    "warning": RAG_AMBER,
    "yellow": RAG_AMBER,
    "critical": RAG_RED,
    "critico": RAG_RED,
}

# Emoji code points used as prefixes in rendered strings (e.g. "🟢 Verde").
_RAG_EMOJI_TO_TOKEN: dict[str, str] = {
    "\U0001F7E2": RAG_GREEN,  # 🟢
    "\U0001F7E1": RAG_AMBER,  # 🟡
    "\U0001F534": RAG_RED,    # 🔴
}

# Display vocabularies derived from the canonical token (one source of truth).
_RAG_LABEL_ES: dict[str, str] = {
    RAG_GREEN: "Verde",
    RAG_AMBER: "Ámbar",
    RAG_RED: "Rojo",
}

_RAG_EMOJI: dict[str, str] = {
    RAG_GREEN: "\U0001F7E2",
    RAG_AMBER: "\U0001F7E1",
    RAG_RED: "\U0001F534",
}


def normalize_rag(value: Optional[str]) -> Optional[str]:
    """Collapse any RAG spelling/case/accent/emoji into a canonical token.

    Returns one of ``green | amber | red`` or ``None`` when the value is empty
    or unrecognized. Never raises — unknown inputs degrade to ``None`` so callers
    can fall back to raw text.
    """
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    # 1) Emoji prefix (or anywhere in the string) wins — most explicit signal.
    for emoji, token in _RAG_EMOJI_TO_TOKEN.items():
        if emoji in raw:
            return token

    # 2) Word lookup: take the last alphabetic word, lowercased.
    #    Handles "🟢 Verde" (after emoji strip), "RAG: ROJO", plain "amber".
    cleaned = raw.lower()
    # Strip any leftover non-letter chars around the candidate word.
    words = [w for w in _split_words(cleaned) if w]
    for word in words:
        token = _RAG_ALIASES.get(word)
        if token is not None:
            return token
    # 3) Whole-string direct lookup fallback (e.g. unusual spacing).
    return _RAG_ALIASES.get(cleaned)


def _split_words(text: str) -> list[str]:
    """Split into alphabetic tokens, keeping accented latin letters."""
    out: list[str] = []
    cur: list[str] = []
    for ch in text:
        if ch.isalpha():
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def rag_label_es(value: Optional[str], *, fallback: str = "—") -> str:
    """Human-readable Spanish label, e.g. 'Verde'. Falls back to ``fallback``."""
    token = normalize_rag(value)
    if token is None:
        return fallback
    return _RAG_LABEL_ES[token]


def rag_emoji(value: Optional[str], *, fallback: str = "") -> str:
    """Emoji for the RAG value, e.g. '🟢'. Falls back to ``fallback``."""
    token = normalize_rag(value)
    if token is None:
        return fallback
    return _RAG_EMOJI[token]


def rag_display(value: Optional[str], *, fallback: str = "—") -> str:
    """Emoji + Spanish label, e.g. '🟢 Verde'. Falls back to ``fallback``.

    This is the canonical replacement for the ad-hoc ``_fmt_rag`` maps that only
    understood the english spelling. Any of the three vocabularies (or an
    emoji-prefixed string) now renders identically.
    """
    token = normalize_rag(value)
    if token is None:
        # Preserve the original text if it was non-empty (graceful degradation),
        # else use the fallback placeholder.
        if value and str(value).strip():
            return str(value)
        return fallback
    return f"{_RAG_EMOJI[token]} {_RAG_LABEL_ES[token]}"


__all__ = [
    "RAG_GREEN",
    "RAG_AMBER",
    "RAG_RED",
    "CANONICAL_RAG",
    "normalize_rag",
    "rag_label_es",
    "rag_emoji",
    "rag_display",
]
