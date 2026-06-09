"""Abstract base for compliance norma plugins (mini-atom 3).

Each regulatory framework (RGPD, NIS2, ISO 27001 etc.) ships as a
standalone plugin module under this package. Plugins are auto-discovered
on import (see ``normas/__init__.py``) and register themselves with
``NormaRegistry``.

The pattern is intentionally Open/Closed:
- Adding a new framework = new ``.py`` file + ``NormaRegistry.register()``.
- Removing a framework = delete the file.
- The motor core (``ComplianceMonitorService``,
  ``ComplianceNormaReportsService``) never imports plugin classes
  directly — it consumes the registry.

Subclasses MUST set the class-level metadata attributes and implement
``calculate_score`` and ``generate_report_md``. ``check_weights``,
when provided, must sum to ``1.0`` (validated at registration time).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal


# ── String literal types ──────────────────────────────────────────────


Frequency = Literal["weekly", "monthly", "quarterly"]
Priority = Literal["critical", "high", "medium", "low"]
CheckStatus = Literal["green", "yellow", "red", "unknown"]


# ── Result + outcome dataclasses ──────────────────────────────────────


@dataclass(frozen=True)
class CheckOutcome:
    """One snapshot used as input by ``calculate_score`` / ``generate_report_md``.

    A thin per-check view independent from the SQLAlchemy ``ComplianceCheck``
    model so plugins can be unit-tested without a DB.
    """

    check_name: str
    status: CheckStatus
    message: str
    last_run_at: datetime | None
    regulatory_basis: str | None = None


# ── Abstract base ─────────────────────────────────────────────────────


class NormaModule(ABC):
    """Abstract base class for a regulatory norma plugin.

    Subclasses MUST set the class attributes below and implement the two
    abstract methods. Subclass instances are registered exactly once via
    ``NormaRegistry.register(instance)`` from inside the plugin file.
    """

    # Mandatory metadata · subclasses MUST override.
    norma_key: str = ""
    norma_name: str = ""
    regulatory_basis_url: str = ""
    applies_to: list[str] = []
    frequency: Frequency = "monthly"
    priority: Priority = "medium"
    checks_owned: list[str] = []

    # Optional · per-check weights, must sum to 1.0 when present. If left
    # empty an even weight is used for all owned checks.
    check_weights: dict[str, float] = {}

    # ── Scoring + reporting ───────────────────────────────────────

    def _normalize_weights(self) -> dict[str, float]:
        if self.check_weights:
            return dict(self.check_weights)
        if not self.checks_owned:
            return {}
        even = 1.0 / len(self.checks_owned)
        return {name: even for name in self.checks_owned}

    def calculate_score(self, outcomes: list[CheckOutcome]) -> float:
        """Weighted % score (0.0-100.0) using ``check_weights``.

        Status → coefficient mapping:
        - ``green``   → 1.00
        - ``yellow``  → 0.50
        - ``red``     → 0.00
        - ``unknown`` → 0.50 (precaución, no penalisa al 100 %)

        Outcomes not in ``checks_owned`` are silently ignored. Missing
        owned checks count as ``unknown`` so the score reflects "we
        don't know" rather than "we passed".
        """
        weights = self._normalize_weights()
        coef = {"green": 1.0, "yellow": 0.5, "unknown": 0.5, "red": 0.0}
        by_name = {o.check_name: o for o in outcomes}
        total = 0.0
        for name, weight in weights.items():
            outcome = by_name.get(name)
            status = outcome.status if outcome else "unknown"
            total += weight * coef.get(status, 0.0) * 100
        return round(total, 2)

    @abstractmethod
    def generate_report_md(
        self,
        outcomes: list[CheckOutcome],
        period_start: datetime,
        period_end: datetime,
    ) -> str:
        """Build the human-readable Markdown report for this norma."""

    def generate_report_json(
        self,
        outcomes: list[CheckOutcome],
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """Default JSON representation used for BD persistence + UI feeds."""
        score = self.calculate_score(outcomes)
        return {
            "norma_key": self.norma_key,
            "norma_name": self.norma_name,
            "regulatory_basis_url": self.regulatory_basis_url,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "score": score,
            "status": self.score_to_status(score),
            "checks": [
                {
                    "check_name": o.check_name,
                    "status": o.status,
                    "message": o.message,
                    "last_run_at": (o.last_run_at.isoformat() if o.last_run_at else None),
                    "regulatory_basis": o.regulatory_basis,
                }
                for o in outcomes
                if o.check_name in self._normalize_weights()
            ],
        }

    # ── Scheduling ────────────────────────────────────────────────

    def get_scheduler_config(self) -> dict[str, Any]:
        """Return a JSON-safe description of when this norma reports.

        The actual Celery ``crontab`` object is built by the celery_app
        module from this dict, avoiding a hard dependency from plugin
        modules on the Celery library (plugins stay importable in tests
        without Celery installed).
        """
        cron_by_freq: dict[Frequency, dict[str, Any]] = {
            "weekly": {
                "hour": 7,
                "minute": 0,
                "day_of_week": "monday",
            },
            "monthly": {
                "hour": 6,
                "minute": 0,
                "day_of_month": "1",
            },
            "quarterly": {
                "hour": 8,
                "minute": 0,
                "day_of_month": "1",
                "month_of_year": "1,4,7,10",
            },
        }
        return {
            "task": "compliance.generate_norma_report",
            "args": [self.norma_key],
            "cron": cron_by_freq[self.frequency],
        }

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def score_to_status(score: float) -> CheckStatus:
        if score >= 85:
            return "green"
        if score >= 70:
            return "yellow"
        if score > 0:
            return "red"
        return "unknown"

    @classmethod
    def validate(cls) -> None:
        """Sanity-check on metadata called at registration time."""
        if not cls.norma_key:
            raise ValueError(f"{cls.__name__}: norma_key is empty")
        if not cls.norma_name:
            raise ValueError(f"{cls.__name__}: norma_name is empty")
        if cls.frequency not in ("weekly", "monthly", "quarterly"):
            raise ValueError(
                f"{cls.__name__}: invalid frequency {cls.frequency!r}"
            )
        if cls.check_weights:
            total = sum(cls.check_weights.values())
            if abs(total - 1.0) > 1e-3:
                raise ValueError(
                    f"{cls.__name__}: check_weights sum to {total:.3f}, "
                    f"expected 1.0"
                )
            for name in cls.check_weights:
                if name not in cls.checks_owned:
                    raise ValueError(
                        f"{cls.__name__}: weight defined for {name!r} which "
                        f"is not in checks_owned"
                    )
