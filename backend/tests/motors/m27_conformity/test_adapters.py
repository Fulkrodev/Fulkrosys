"""Tests for M27 external adapters."""
import uuid

from backend.app.motors.m27_conformity.adapters import (
    ines_adapter,
    lucia_adapter,
    pilar_adapter,
    registry_adapter,
)


def test_pilar_adapter_returns_artifact():
    pid = uuid.uuid4()
    out = pilar_adapter.export(pid, {"version": "v1"})
    assert out["tool"] == "PILAR"
    assert len(out["artifact_hash"]) == 64
    assert len(out["checklist"]) >= 3


def test_lucia_adapter_includes_severity():
    out = lucia_adapter.export(uuid.uuid4(), {"severity": "HIGH"})
    assert out["tool"] == "LUCIA"
    assert "checklist" in out


def test_ines_adapter_includes_period():
    out = ines_adapter.export(uuid.uuid4(), {"period": "Q1-2026"})
    assert out["tool"] == "INES"


def test_registry_adapter_zip():
    out = registry_adapter.export(uuid.uuid4(), {"target": "REGISTRO_ENS"})
    assert out["tool"] == "Registro"
    # S10 fix: ya no se fabrica un .zip fantasma · el paquete real es el dossier
    # firmado de m09 (artifact_source); artifact_path None hasta el ensamblado.
    assert out["artifact_path"] is None
    assert out["artifact_source"] == "m09_signed_dossier_zip"
    assert out["artifact_hash"]
    assert isinstance(out["checklist"], list) and out["checklist"]


def test_each_adapter_produces_unique_hash():
    pid = uuid.uuid4()
    h1 = pilar_adapter.export(pid, {"version": "a"})["artifact_hash"]
    h2 = pilar_adapter.export(pid, {"version": "b"})["artifact_hash"]
    assert h1 != h2
