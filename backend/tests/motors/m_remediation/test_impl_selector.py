"""IMPL-4 · selector determinista de implantación + plan dry-run."""
from backend.app.motors.m_remediation.impl_selector import (
    ClientInventory,
    build_dry_run_plan,
)


def test_selects_by_inventory_cloud_and_host():
    inv = ClientInventory(providers=("aws",), host_os_families=("linux",))
    plan = build_dry_run_plan(["mp.si.2", "mp.info.6"], inv)
    actions = {s.action_type for s in plan}
    assert "enable_bucket_encryption" in actions  # cloud:aws · mp.si.2
    assert "configure_host_backup" in actions      # host · mp.info.6
    assert all(s.requires_approval for s in plan)  # nada sin aprobación humana


def test_excludes_templates_not_in_inventory():
    # Solo M365 · NO debe colar plantillas aws ni de host.
    inv = ClientInventory(providers=("microsoft_365",), host_os_families=())
    plan = build_dry_run_plan(["mp.si.2", "mp.info.6"], inv)
    actions = {s.action_type for s in plan}
    assert "enable_bucket_encryption" not in actions
    assert "configure_host_backup" not in actions


def test_missing_required_params_flagged():
    inv = ClientInventory(providers=(), host_os_families=("linux",))
    plan = build_dry_run_plan(["mp.info.6"], inv)
    backup = next(s for s in plan if s.action_type == "configure_host_backup")
    # repo + paths son required sin default → deben marcarse como faltantes.
    assert "repo" in backup.missing_required_params
    assert "paths" in backup.missing_required_params
    # hour tiene default → se rellena.
    assert backup.params.get("hour") == "3"


def test_params_override_from_inventory():
    inv = ClientInventory(
        host_os_families=("linux",),
        params={"configure_host_backup": {"repo": "s3:backups", "paths": "/data"}},
    )
    plan = build_dry_run_plan(["mp.info.6"], inv)
    backup = next(s for s in plan if s.action_type == "configure_host_backup")
    assert backup.params["repo"] == "s3:backups"
    assert backup.missing_required_params == []  # ya provistos


def test_host_os_filter():
    # Playbook solo-linux (firewall baseline) NO aplica a inventario solo-windows.
    inv = ClientInventory(host_os_families=("windows",))
    plan = build_dry_run_plan(["mp.com.1"], inv)
    assert "enable_host_firewall_baseline" not in {s.action_type for s in plan}
