"""WAVE C3 (tracker §2.2 line 225) — canonical RAG vocabulary normalizer.

Three RAG vocabularies coexist in m23_retainer (english green/amber/red,
uppercase VERDE/AMBAR/ROJO, lowercase verde/ambar/rojo). These tests pin the
single canonical normalizer that collapses them all (+ emoji + accents) into one
form, and verify the report renderer's _fmt_rag/_worst_rag use it consistently.
"""
from __future__ import annotations

import pytest

from backend.app.motors.m23_retainer.rag_vocab import (
    RAG_AMBER,
    RAG_GREEN,
    RAG_RED,
    normalize_rag,
    rag_display,
    rag_emoji,
    rag_label_es,
)
from backend.app.motors.m23_retainer.report_renderer import _fmt_rag, _worst_rag


@pytest.mark.parametrize(
    "value,expected",
    [
        # english (check-in service · _compute_rag)
        ("green", RAG_GREEN),
        ("amber", RAG_AMBER),
        ("red", RAG_RED),
        # uppercase spanish (report_service · _calc_rag)
        ("VERDE", RAG_GREEN),
        ("AMBAR", RAG_AMBER),
        ("ROJO", RAG_RED),
        # lowercase spanish (paso2_extensions · calculate_health_status)
        ("verde", RAG_GREEN),
        ("ambar", RAG_AMBER),
        ("rojo", RAG_RED),
        # accents + mixed case
        ("Ámbar", RAG_AMBER),
        ("Verde", RAG_GREEN),
        # emoji-prefixed rendered strings round-trip
        ("🟢 Verde", RAG_GREEN),
        ("🟡 Ámbar", RAG_AMBER),
        ("🔴 Rojo", RAG_RED),
        # embedded in copy
        ("RAG: ROJO", RAG_RED),
    ],
)
def test_normalize_rag_collapses_all_vocabularies(value, expected):
    assert normalize_rag(value) == expected


@pytest.mark.parametrize("value", [None, "", "   ", "purple", "n/a"])
def test_normalize_rag_unknown_or_empty_returns_none(value):
    assert normalize_rag(value) is None


def test_rag_display_uniform_across_vocabularies():
    # All three producer spellings render identically.
    assert _fmt_rag("green") == _fmt_rag("VERDE") == _fmt_rag("verde")
    assert _fmt_rag("green") == "🟢 Verde"
    assert _fmt_rag("AMBAR") == "🟡 Ámbar"
    assert _fmt_rag("rojo") == "🔴 Rojo"


def test_rag_display_graceful_degradation():
    # Empty -> placeholder; unknown non-empty -> raw text preserved (never crash).
    assert _fmt_rag(None) == "—"
    assert _fmt_rag("") == "—"
    assert rag_display("totallyunknown") == "totallyunknown"


def test_rag_helpers_label_and_emoji():
    assert rag_label_es("VERDE") == "Verde"
    assert rag_label_es(None) == "—"
    assert rag_emoji("rojo") == "🔴"
    assert rag_emoji(None) == ""


def test_worst_rag_normalizes_mixed_vocabularies():
    # Mixed spellings must still rank: red worst, then amber, then green.
    assert _worst_rag(["VERDE", "amber", "verde"]) == RAG_AMBER
    assert _worst_rag(["green", "ROJO", "🟡 Ámbar"]) == RAG_RED
    assert _worst_rag(["green", "verde", "GREEN"]) == RAG_GREEN
    assert _worst_rag([None, "", "unknown"]) is None
