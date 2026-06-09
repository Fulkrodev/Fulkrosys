"""#19 Ola 7 · guard de deprecación de vuln_orchestrator.

El path canónico de vuln-scan es VerificationService.create_run + endpoints
/projects/{id}/verification/* + runners gated por USE_MCP_REAL. El módulo
vuln_orchestrator quedó huérfano y se deprecó: este guard impide que vuelva a
cablearse desde el api/service del motor (evita reintroducir un segundo camino
de scan · OPS-048 cross-motor consistency style).
"""
from __future__ import annotations

import pathlib

import backend.app.motors.m08_verification as m08pkg


def test_vuln_orchestrator_not_wired_in_app():
    base = pathlib.Path(m08pkg.__file__).parent
    for fname in ("api.py", "service.py", "mcp_executor_service.py"):
        path = base / fname
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8")
        assert "vuln_orchestrator" not in src, (
            f"{fname} no debe importar/cablear vuln_orchestrator (deprecado #19 · "
            "usa VerificationService como path canónico)"
        )
        assert "run_vuln_audit" not in src, (
            f"{fname} no debe invocar run_vuln_audit (deprecado #19)"
        )


def test_vuln_orchestrator_still_imports_as_low_level_utility():
    """Se conserva (no se borra) · debe seguir importando para los tests que
    ejercen OpenvasRunner a bajo nivel."""
    from backend.app.motors.m08_verification.vuln_orchestrator import (
        run_vuln_audit,
        should_trigger,
    )

    assert callable(run_vuln_audit)
    assert callable(should_trigger)
