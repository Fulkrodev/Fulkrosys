"""WAVE C3 (tracker §2.2 line 341/342 backend slice) — SignableType label
catalog single source of truth in the BACKEND.

The canonical catalog is signable_types.SIGNABLE_TYPE_LABELS. This test pins
that the contract-signing public SSE payload no longer hardcodes its own
"Contrato comercial" string (which drifted from the canonical label) but
derives it from the canonical map, so a future label edit propagates.
"""
from __future__ import annotations

import inspect

from backend.app.motors.m05_signing.signable_types import (
    SIGNABLE_TYPE_LABELS,
    SIGNABLE_TYPES,
)


def test_canonical_catalog_covers_every_signable_type():
    # Every declared type has a label entry (and vice-versa) — one source.
    assert set(SIGNABLE_TYPE_LABELS.keys()) == set(SIGNABLE_TYPES)


def test_contract_signing_sse_uses_canonical_label_not_hardcode():
    """The contract-signing public API must reference the canonical label map,
    not a literal 'Contrato comercial' string."""
    from backend.app.motors.m13_commercial import contract_signing_public_api as mod

    src = inspect.getsource(mod)
    # Wiring present: derives from canonical map.
    assert 'SIGNABLE_TYPE_LABELS["contrato_comercial"]' in src
    # The old drifted hardcode is gone.
    assert '"signable_label": "Contrato comercial"' not in src


def test_canonical_contract_label_is_the_full_branded_one():
    # The canonical label is the branded one; the old hardcode was a truncated
    # "Contrato comercial" that drifted.
    assert (
        SIGNABLE_TYPE_LABELS["contrato_comercial"]
        == "Contrato comercial de servicios FULKRO"
    )
