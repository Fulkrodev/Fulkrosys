"""FASE 3 · puente diagnóstico/pentest → remediación · mapper determinista."""
from backend.app.motors.m_remediation.bridge import (
    build_gap_action_index,
    map_gap_to_action_type,
)
from backend.app.motors.m_remediation.catalog import (
    ACTION_CATALOG,
    RemediationTier,
)


def test_index_excludes_blocked_and_covers_safe_guarded():
    idx = build_gap_action_index()
    assert idx, "el índice no debe estar vacío"
    # Ninguna acción BLOCKED debe estar en el índice (nunca auto-propuesta).
    blocked = {
        a for a, s in ACTION_CATALOG.items()
        if s.tier == RemediationTier.BLOCKED
    }
    indexed = {s.action_type for specs in idx.values() for s in specs}
    assert blocked.isdisjoint(indexed)


def test_mapper_resolves_known_gaps():
    assert map_gap_to_action_type("aws", "mp.si.2", "storage_bucket") == (
        "enable_bucket_encryption"
    )
    assert map_gap_to_action_type("azure", "mp.com.2") == (
        "azure_storage_require_https"
    )
    # Colisión M365 op.acc.6 (report-only SAFE_AUTO + enforce GUARDED) → SAFE_AUTO.
    assert map_gap_to_action_type("microsoft_365", "op.acc.6") == (
        "require_mfa_conditional_access"
    )


def test_mapper_returns_none_for_uncovered():
    assert map_gap_to_action_type("aws", "zz.zz.9") is None
    assert map_gap_to_action_type("nonexistent_provider", "mp.si.2") is None


def test_mapper_prefers_safe_auto_on_collision():
    idx = build_gap_action_index()
    for specs in idx.values():
        if len(specs) > 1:
            # El primero (preferido) nunca debe ser de menor prioridad que el resto.
            tiers = [s.tier for s in specs]
            if RemediationTier.SAFE_AUTO in tiers:
                assert specs[0].tier == RemediationTier.SAFE_AUTO
