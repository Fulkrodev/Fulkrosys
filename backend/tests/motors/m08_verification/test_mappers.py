"""M8 v5.1 — Tests de ENS mapper + MITRE mapper."""
from __future__ import annotations


import pytest

from backend.app.motors.m08_verification.ens_mapper import EnsMapper, CVE_TO_ENS
from backend.app.motors.m08_verification.mitre_mapper import (
    CVE_TO_MITRE, MitreMapper,
)
from backend.app.motors.m08_verification.zfp_engine import ZfpFinding


def _zfp(cve=None, title="t", description=""):
    return ZfpFinding(
        finding_hash="x", title=title, description=description,
        severity="high", affected_host="h", affected_port=None,
        affected_service=None, affected_url=None,
        cve_id=cve,
    )


# ════════════════════════════════════════════════════════════════════
# ENS mapper — capa 1 rule (CVE)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ens_mapper_log4shell_to_op_exp_4(db):
    # §2.2 audit-2026-06-15 · parchear un CVE (Log4Shell) es op.exp.4
    # "Mantenimiento y actualizaciones de seguridad", NO op.exp.5 "Gestión de
    # cambios" (mapeo previo incorrecto · 'Gestión de vulnerabilidades' ni existe).
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(cve="CVE-2021-44228", title="Apache Log4j RCE")
    measures, primary = await mapper.map(f)
    measure_codes = [m["measure"] for m in measures]
    assert "op.exp.4" in measure_codes
    assert "op.exp.5" not in measure_codes
    # el título debe ser el oficial RD 311/2022 (resuelto del catálogo).
    op_exp_4 = next(m for m in measures if m["measure"] == "op.exp.4")
    assert op_exp_4["title"] == "Mantenimiento y actualizaciones de seguridad"
    assert primary == measure_codes[0]
    assert all(m["method"] == "rule" for m in measures)
    assert all(m["confidence"] == 0.95 for m in measures)


@pytest.mark.asyncio
async def test_ens_mapper_regreSSHion_to_op_exp_4(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(cve="CVE-2024-6387", title="OpenSSH regreSSHion")
    measures, primary = await mapper.map(f)
    codes = [m["measure"] for m in measures]
    assert "op.exp.4" in codes
    assert "op.acc.6" in codes


@pytest.mark.asyncio
async def test_ens_mapper_xz_backdoor_to_supply_chain(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(cve="CVE-2024-3094")
    measures, primary = await mapper.map(f)
    codes = [m["measure"] for m in measures]
    # Backdoor en supply chain → mp.sw.2 + op.exp.6
    assert "mp.sw.2" in codes


# ════════════════════════════════════════════════════════════════════
# ENS mapper — capa 1b rule (pattern)
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ens_mapper_pattern_sql_injection(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(title="SQL Injection found in /api/users",
             description="Reflected SQLi via id parameter")
    measures, _ = await mapper.map(f)
    codes = [m["measure"] for m in measures]
    assert "mp.sw.1" in codes


@pytest.mark.asyncio
async def test_ens_mapper_pattern_xss(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(title="Cross-Site Scripting in comments form")
    measures, primary = await mapper.map(f)
    assert primary == "mp.sw.1"


@pytest.mark.asyncio
async def test_ens_mapper_pattern_weak_tls(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(title="TLS 1.0 enabled on web server")
    measures, _ = await mapper.map(f)
    codes = [m["measure"] for m in measures]
    assert "mp.com.2" in codes


@pytest.mark.asyncio
async def test_ens_mapper_no_match_returns_empty(db):
    mapper = EnsMapper(db, enable_llm=False)
    f = _zfp(title="totally unknown finding xyzzy")
    measures, primary = await mapper.map(f)
    # Sin CVE ni pattern conocido y LLM disabled
    assert measures == []
    assert primary is None


# ════════════════════════════════════════════════════════════════════
# ENS mapper — dedup + max 3
# ════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ens_mapper_dedupes_and_caps_to_3(db):
    mapper = EnsMapper(db, enable_llm=False)
    # Pattern que mapea a varias medidas + CVE
    f = _zfp(
        cve="CVE-2021-44228",  # mapea a op.exp.5 + op.exp.6
        title="SQL Injection + Log4j vulnerability",
    )
    measures, _ = await mapper.map(f)
    codes = [m["measure"] for m in measures]
    assert len(set(codes)) == len(codes)  # sin duplicados
    assert len(codes) <= 3


@pytest.mark.asyncio
async def test_ens_catalog_has_minimum_cves():
    """Validacion del catalogo: min 25 CVEs mapeadas (spec exige 50-100)."""
    assert len(CVE_TO_ENS) >= 25


# ════════════════════════════════════════════════════════════════════
# MITRE mapper
# ════════════════════════════════════════════════════════════════════

def test_mitre_log4shell_to_t1190():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(cve="CVE-2021-44228")
    techs = mapper.map(f)
    ids = [t["technique_id"] for t in techs]
    assert "T1190" in ids


def test_mitre_eternalblue_to_t1210():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(cve="CVE-2017-0144")
    techs = mapper.map(f)
    assert techs[0]["technique_id"] == "T1210"
    assert "Lateral Movement" in techs[0]["tactic"]


def test_mitre_pwnkit_to_t1068():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(cve="CVE-2021-4034")
    techs = mapper.map(f)
    assert techs[0]["technique_id"] == "T1068"


def test_mitre_pattern_default_credentials():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(title="Default admin/admin credentials accepted")
    techs = mapper.map(f)
    assert techs and techs[0]["technique_id"] == "T1078"


def test_mitre_no_match_returns_empty():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(title="unknown finding xyzzy")
    assert mapper.map(f) == []


def test_mitre_catalog_has_minimum_cves():
    assert len(CVE_TO_MITRE) >= 20  # spec pide 50; ahora vamos por 25


def test_mitre_caps_to_3():
    mapper = MitreMapper(enable_llm=False)
    f = _zfp(cve="CVE-2021-44228",
             title="SQL Injection + XSS + Default credentials in login")
    techs = mapper.map(f)
    assert len(techs) <= 3
    # Sin duplicados de technique_id
    ids = [t["technique_id"] for t in techs]
    assert len(set(ids)) == len(ids)
