"""IMPL · coherencia de playbooks de host + matriz de cobertura 'no falta ni uno'."""
from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311
from backend.app.motors.m_remediation.agent_protocol import PLAYBOOK_ALLOWLIST
from backend.app.motors.m_remediation.catalog import ACTION_CATALOG
from backend.app.motors.m_remediation.host_playbooks import HOST_PLAYBOOKS
from backend.app.motors.m_remediation.impl_coverage import (
    compute_implementation_coverage,
)


def _host_actions() -> set[str]:
    return {a for a, s in ACTION_CATALOG.items() if s.provider == "host"}


def test_host_playbooks_allowlist_catalog_in_sync():
    """Las 3 fuentes de verdad de host deben coincidir EXACTAS (anti-drift)."""
    host_actions = _host_actions()
    assert set(HOST_PLAYBOOKS.keys()) == host_actions, (
        "host_playbooks vs ACTION_CATALOG provider=host divergen"
    )
    assert host_actions <= set(PLAYBOOK_ALLOWLIST), (
        "hay acciones host fuera de la PLAYBOOK_ALLOWLIST (el agente las rechazaría)"
    )
    assert set(PLAYBOOK_ALLOWLIST) == set(HOST_PLAYBOOKS.keys()), (
        "PLAYBOOK_ALLOWLIST y HOST_PLAYBOOKS divergen"
    )


def test_host_playbook_check_assertion_matches_catalog():
    """Cada playbook host comprueba la misma desired_assertion que su acción."""
    for action_type, spec in ACTION_CATALOG.items():
        if spec.provider != "host":
            continue
        pb = HOST_PLAYBOOKS[action_type]
        assert pb.check_assertion == spec.desired_assertion, action_type


def test_host_playbooks_have_steps_and_params():
    """Plantillas verificadas: pasos idempotentes como datos (no shell libre)."""
    for pb in HOST_PLAYBOOKS.values():
        assert pb.ansible_steps, pb.playbook_id
        assert all("module" in s and "args" in s for s in pb.ansible_steps)
        if pb.reversible:
            assert pb.rollback_steps, pb.playbook_id
        assert pb.dry_run_summary


def test_coverage_no_measure_uncovered_all_levels():
    """'No falta ni uno': cada medida aplicable B/M/A tiene camino (auto o guiada)."""
    expected_totals = {}  # informativo
    for level in ("BASICA", "MEDIA", "ALTA"):
        cov = compute_implementation_coverage(level)
        assert cov["uncovered"] == [], (level, cov["uncovered"])
        # Toda medida aplicable del Anexo II está en la matriz.
        applicable = [
            c for c, e in ANEXO_II_RD311.items()
            if e[{"BASICA": 1, "MEDIA": 2, "ALTA": 3}[level]]
        ]
        assert cov["total_applicable"] == len(applicable)
        assert cov["auto_count"] >= 1  # hay implantación técnica real
        assert cov["auto_count"] + cov["guided_count"] == cov["total_applicable"]
        expected_totals[level] = cov["total_applicable"]
    # Coherencia con los totales ENS RD 311/2022 (52/68/73).
    assert expected_totals["BASICA"] == 52
    assert expected_totals["MEDIA"] == 68
    assert expected_totals["ALTA"] == 73


def test_coverage_auto_measures_have_real_actions():
    cov = compute_implementation_coverage("MEDIA")
    for row in cov["rows"]:
        if row["coverage"] == "auto":
            assert row["actions"], row["measure"]
            for a in row["actions"]:
                assert a["action_type"] in ACTION_CATALOG
