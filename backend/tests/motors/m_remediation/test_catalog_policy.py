"""Tests puros (sin DB) · catálogo + clasificador de riesgo m_remediation (ADR-055).

Verifica que la decisión de riesgo es DETERMINISTA y FAIL-CLOSED:
  - el tier viene del catálogo, nunca se infiere
  - kill-switch en 3 capas (basta una en off → no aplica)
  - acciones desconocidas → DISABLED (nunca auto)
  - BLOCKED prevalece sobre cualquier flag
"""
from __future__ import annotations

import pytest

from backend.app.motors.m_remediation.catalog import (
    ACTION_CATALOG,
    RemediationTier,
    actions_for_provider,
    get_action_spec,
    tier_for,
)
from backend.app.motors.m_remediation.policy import (
    AutoRemediationPolicy,
    ExecutionMode,
    global_remediation_enabled,
    resolve_execution_mode,
)


class TestCatalog:
    def test_catalog_non_empty_and_tiers_valid(self) -> None:
        assert len(ACTION_CATALOG) >= 10
        valid = {t.value for t in RemediationTier}
        for spec in ACTION_CATALOG.values():
            assert spec.tier.value in valid
            assert spec.action_type
            assert spec.desired_assertion
            assert spec.cliente_blurb  # R29 friendly siempre presente

    def test_blocked_actions_are_irreversible(self) -> None:
        for spec in ACTION_CATALOG.values():
            if spec.tier == RemediationTier.BLOCKED:
                assert spec.reversible is False

    def test_tier_for_unknown_is_none(self) -> None:
        assert tier_for("does_not_exist") is None
        assert get_action_spec("does_not_exist") is None

    def test_actions_for_provider(self) -> None:
        aws = actions_for_provider("aws")
        assert any(s.action_type == "enable_bucket_encryption" for s in aws)
        host = actions_for_provider("host")
        assert any(s.action_type == "harden_sshd_root_login" for s in host)


class TestPolicyMatrix:
    """Matriz determinista de resolución (con global kill-switch ON salvo nota)."""

    @pytest.fixture(autouse=True)
    def _global_on(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("FULKRO_REMEDIATION_ENABLED", "true")

    def test_global_default_is_off(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("FULKRO_REMEDIATION_ENABLED", raising=False)
        assert global_remediation_enabled() is False

    def test_safe_auto_full_is_auto(self) -> None:
        m = resolve_execution_mode(
            "enable_bucket_encryption", target_enabled=True, policy="full",
        )
        assert m == ExecutionMode.AUTO

    def test_safe_auto_only_is_auto(self) -> None:
        m = resolve_execution_mode(
            "enable_bucket_encryption",
            target_enabled=True,
            policy=AutoRemediationPolicy.SAFE_AUTO_ONLY,
        )
        assert m == ExecutionMode.AUTO

    def test_guarded_full_requires_authorization(self) -> None:
        m = resolve_execution_mode(
            "require_mfa_enforce", target_enabled=True, policy="full",
        )
        assert m == ExecutionMode.REQUIRE_AUTHORIZATION

    def test_guarded_safe_only_is_disabled(self) -> None:
        m = resolve_execution_mode(
            "require_mfa_enforce", target_enabled=True, policy="safe_auto_only",
        )
        assert m == ExecutionMode.DISABLED

    def test_blocked_always_blocked(self) -> None:
        m = resolve_execution_mode(
            "delete_public_resource", target_enabled=True, policy="full",
        )
        assert m == ExecutionMode.BLOCKED

    def test_unknown_action_disabled(self) -> None:
        m = resolve_execution_mode("nope", target_enabled=True, policy="full")
        assert m == ExecutionMode.DISABLED

    def test_layer2_connector_disabled(self) -> None:
        m = resolve_execution_mode(
            "enable_bucket_encryption", target_enabled=False, policy="full",
        )
        assert m == ExecutionMode.DISABLED

    def test_layer3_policy_off(self) -> None:
        m = resolve_execution_mode(
            "enable_bucket_encryption", target_enabled=True, policy="off",
        )
        assert m == ExecutionMode.DISABLED

    def test_blocked_prevails_over_killswitches(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Aun con global off + conector off + policy off, un destructivo es BLOCKED.
        monkeypatch.delenv("FULKRO_REMEDIATION_ENABLED", raising=False)
        m = resolve_execution_mode(
            "delete_public_resource", target_enabled=False, policy="off",
        )
        assert m == ExecutionMode.BLOCKED


class TestGlobalKillSwitch:
    def test_safe_auto_disabled_when_global_off(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("FULKRO_REMEDIATION_ENABLED", raising=False)
        m = resolve_execution_mode(
            "enable_bucket_encryption", target_enabled=True, policy="full",
        )
        assert m == ExecutionMode.DISABLED
