"""Golden datasets loader · sub-atom 1.E.1.B.3.B.

Carga + valida JSON files en `docs/catalogs/golden_datasets/<agent>/v<version>.json`.

Pattern consistent con `copilot_personas_loader.py` (OPS-026 DRY sostener) ·
singleton cached · Pydantic frozen schemas type-safe.

Golden datasets son curados manualmente per Marcos input session (B.3.C
post-skeleton) · 5-10 entries per agente cubriendo sector mix + severity.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


GOLDEN_DATASETS_ROOT = (
    Path(__file__).resolve().parents[4] / "docs" / "catalogs" /
    "golden_datasets"
)


class GoldenDatasetLoadError(Exception):
    """Raised when golden dataset JSON missing, invalid, or schema mismatch."""


# ════════════════════════════════════════════════════════════════════
# Pydantic schemas (validate JSON structure · type-safe access)
# ════════════════════════════════════════════════════════════════════


class RegressionThresholds(BaseModel):
    """Regression alert thresholds per dataset.

    pass_rate_warn_below: exit code 1 + admin alert si pass_rate <
    pass_rate_alert_below: exit code 2 + immediate alert si pass_rate <
    """

    model_config = ConfigDict(frozen=True)

    pass_rate_warn_below: float = Field(default=0.8, ge=0.0, le=1.0)
    pass_rate_alert_below: float = Field(default=0.6, ge=0.0, le=1.0)


class GoldenRubric(BaseModel):
    """Rubric criteria per entry · empíricamente verificables (NO subjective)."""

    model_config = ConfigDict(frozen=True, extra="allow")

    structure_check: bool = True
    ens_coverage_required_pct: int = Field(default=0, ge=0, le=100)


class GoldenExpectedOutput(BaseModel):
    """Expected output canonical shape · agent-specific extras allowed.

    Schema v1.1 (B.3.C): issues_critical y issues_moderate aceptan list[str]
    (Marcos-identified issues per entry · 10-20 palabras accionables).
    Backward-compat: extra="allow" deja pasar campos legacy o custom.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    verdict: str | None = None
    issues_critical: list[str] = Field(default_factory=list)
    issues_moderate: list[str] = Field(default_factory=list)
    key_phrases_required: list[str] = Field(default_factory=list)
    key_phrases_forbidden: list[str] = Field(default_factory=list)


class GoldenDatasetEntry(BaseModel):
    """One curated example · input + expected_output + rubric.

    Schema v1.1 (B.3.C): extra="allow" para top-level fields como
    `deliverable_type` y `ens_category` que aportan contexto curation sin
    forzar inclusión en `input` dict.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    id: str
    category: str
    input: dict[str, Any]
    expected_output: GoldenExpectedOutput
    rubric: GoldenRubric


class GoldenDataset(BaseModel):
    """Top-level dataset · skeleton or curated."""

    model_config = ConfigDict(frozen=True)

    agent_name: str
    version: str
    created_at: str
    curated_by: str
    purpose: str
    schema_version: str = "1.0"
    regression_thresholds: RegressionThresholds = Field(
        default_factory=RegressionThresholds,
    )
    entries: list[GoldenDatasetEntry] = Field(default_factory=list)


# ════════════════════════════════════════════════════════════════════
# Singleton cache · OPS-026 DRY · pattern copilot_personas_loader
# ════════════════════════════════════════════════════════════════════


_CACHE: dict[tuple[str, str], GoldenDataset] = {}


def load_golden_dataset(
    agent_name: str,
    version: str = "v1",
    *,
    use_cache: bool = True,
    root: Path | None = None,
) -> GoldenDataset:
    """Load + validate golden dataset JSON file.

    Raises GoldenDatasetLoadError si missing / parse error / schema invalid.
    """
    if use_cache:
        cached = _CACHE.get((agent_name, version))
        if cached is not None:
            return cached

    base = root or GOLDEN_DATASETS_ROOT
    path = base / agent_name / f"{version}.json"

    if not path.exists():
        raise GoldenDatasetLoadError(
            f"Golden dataset not found · agent={agent_name} version={version} "
            f"path={path}"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise GoldenDatasetLoadError(
            f"JSON parse error · {path}: {exc}",
        ) from exc

    if not isinstance(data, dict):
        raise GoldenDatasetLoadError(
            f"Dataset root not a dict · {path}",
        )

    try:
        dataset = GoldenDataset.model_validate(data)
    except Exception as exc:
        raise GoldenDatasetLoadError(
            f"Dataset schema validation failed · {path}: {exc}",
        ) from exc

    # Sanity: agent_name in JSON debe coincidir con file path
    if dataset.agent_name != agent_name:
        raise GoldenDatasetLoadError(
            f"agent_name mismatch · file={path} json='{dataset.agent_name}' "
            f"expected='{agent_name}'",
        )

    if use_cache and root is None:
        _CACHE[(agent_name, version)] = dataset

    return dataset


def list_available_datasets(
    *, root: Path | None = None,
) -> list[tuple[str, str]]:
    """Discover all <agent>/<version>.json files · returns list of tuples.

    Returns: [(agent_name, version), ...] sorted alphabetic.
    """
    base = root or GOLDEN_DATASETS_ROOT
    if not base.exists():
        return []

    pairs: list[tuple[str, str]] = []
    for agent_dir in sorted(base.iterdir()):
        if not agent_dir.is_dir():
            continue
        for version_file in sorted(agent_dir.iterdir()):
            if not version_file.is_file():
                continue
            if version_file.suffix != ".json":
                continue
            version = version_file.stem  # "v1" without .json
            pairs.append((agent_dir.name, version))
    return pairs


def clear_cache() -> None:
    """Reset singleton cache · for tests + curation workflow."""
    _CACHE.clear()
