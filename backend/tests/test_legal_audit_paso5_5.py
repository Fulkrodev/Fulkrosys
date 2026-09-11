"""Tests Paso 5.5 — 4 fixes del legal audit.

- 5.5.1: Politicas E-117/118/119/120/125 referencian RD 311/2022.
- 5.5.2: is_aapp helper (CIF prefixes + keywords) + C-001 con Anexo A LCSP.
- 5.5.3: add_days_es filter + P-001 caducidad 30d explicita.
- 5.5.4: C-003 OBLIGACIONES con remision a C-001 + SLA + cambios materiales.
- 5.5.5: Legal audit re-run alcanza 100/100.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
POLICIES = (
    ROOT / "backend" / "app" / "motors" / "m06_document_factory"
    / "templates" / "policies"
)
COMMERCIAL = (
    ROOT / "backend" / "app" / "motors" / "m06_document_factory"
    / "templates" / "commercial"
)


# ══════════════════════════════════════════════════════════════════════
# 5.5.1 — Politicas con referencia RD 311/2022
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("stem", [
    "E117_politica_de_gestion_de_privilegios_y_pam",
    "E118_politica_de_byod_bring_your_own_device",
    "E119_politica_de_respuesta_a_brechas_de_datos_personale",
    "E120_politica_de_gestion_de_claves_criptograficas",
    "E125_politica_de_mesa_limpia_y_pantalla_limpia",
])
def test_policy_references_rd_311_2022(stem):
    content = (POLICIES / f"{stem}.md").read_text(encoding="utf-8")
    assert "RD 311/2022" in content or "Real Decreto 311/2022" in content
    assert "## MARCO NORMATIVO" in content
    # Anexo II referenced
    assert "Anexo II" in content


def test_e117_references_op_acc_measures():
    content = (POLICIES / "E117_politica_de_gestion_de_privilegios_y_pam.md").read_text()
    assert "op.acc.3" in content
    assert "op.acc.4" in content


def test_e119_references_rgpd_articles():
    content = (POLICIES / "E119_politica_de_respuesta_a_brechas_de_datos_personale.md").read_text()
    assert "Artículo 33 RGPD" in content or "artículos 33" in content
    assert "AEPD" in content


def test_e120_references_crypto_measures():
    """La politica de claves cita la medida de cifrado del Anexo II.

    O1 · este test aseveraba `mp.info.9`, que NO EXISTE en el Anexo II: no esta
    entre las 73 medidas del PDF del BOE (`backend/tests/fixtures/
    anexo2_boe_verificado.json`). La plantilla la citaba, se corrigio a
    `op.exp.10` -- que si existe y es Cifrado -- y el test se quedo aseverando
    el codigo fantasma. Un test que exige una medida inventada en una politica
    firmable es peor que no tenerlo.
    """
    content = (POLICIES / "E120_politica_de_gestion_de_claves_criptograficas.md").read_text()
    assert "op.exp.10" in content
    assert "mp.info.9" not in content, (
        "vuelve a citarse una medida que no esta en el Anexo II"
    )


def test_e125_references_clean_desk_measures():
    content = (POLICIES / "E125_politica_de_mesa_limpia_y_pantalla_limpia.md").read_text()
    assert "mp.eq.1" in content


# ══════════════════════════════════════════════════════════════════════
# 5.5.2 — is_aapp helper
# ══════════════════════════════════════════════════════════════════════


class TestIsAapp:
    def test_cif_prefix_p_ayuntamiento(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(cif="P1234567A") is True

    def test_cif_prefix_q_organismo(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(cif="Q2345678B") is True

    def test_cif_prefix_s_admin_estado(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(cif="S3456789C") is True

    def test_cif_prefix_b_sl_privada(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(cif="B12345678") is False

    def test_cif_prefix_a_sa_privada(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(cif="A12345678") is False

    def test_keyword_ayuntamiento(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(
            razon_social="Ayuntamiento de Ciempozuelos",
        ) is True

    def test_keyword_diputacion(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(
            tipo_organizacion="Diputación Provincial",
        ) is True

    def test_keyword_universidad_publica(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(
            razon_social="Universidad Pública de Navarra",
        ) is True

    def test_keyword_generalitat(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(
            razon_social="Generalitat de Catalunya",
        ) is True

    def test_keyword_xunta(self):
        from backend.app.core.legal import is_aapp_by_fields
        assert is_aapp_by_fields(
            razon_social="Xunta de Galicia",
        ) is True

    def test_from_dict(self):
        from backend.app.core.legal import is_aapp
        assert is_aapp({"cif": "P99", "razon_social": "Ayuntamiento test"}) is True
        assert is_aapp({"cif": "B12", "razon_social": "Empresa SL"}) is False

    def test_from_none_returns_false(self):
        from backend.app.core.legal import is_aapp
        assert is_aapp(None) is False


def test_c001_has_lcsp_anexo_a():
    content = (COMMERCIAL / "C001_contrato_de_prestacion_de_servicios_de_consultoria.md").read_text()
    assert "{% if cliente.is_aapp %}" in content
    assert "ANEXO A" in content
    assert "Ley 9/2017" in content or "LCSP" in content
    assert "198.4" in content  # Art. 198.4 LCSP
    assert "Facturae" in content


# ══════════════════════════════════════════════════════════════════════
# 5.5.3 — add_days_es filter + P-001 caducidad
# ══════════════════════════════════════════════════════════════════════


class TestAddDaysEs:
    def test_basic_addition_from_date(self):
        from backend.app.motors.m06_document_factory.filters import add_days_es
        assert add_days_es(date(2026, 4, 22), 30) == "22/05/2026"

    def test_from_iso_string(self):
        from backend.app.motors.m06_document_factory.filters import add_days_es
        assert add_days_es("2026-04-22", 30) == "22/05/2026"

    def test_from_es_string(self):
        from backend.app.motors.m06_document_factory.filters import add_days_es
        assert add_days_es("22/04/2026", 30) == "22/05/2026"

    def test_from_none_returns_empty(self):
        from backend.app.motors.m06_document_factory.filters import add_days_es
        assert add_days_es(None, 30) == ""

    def test_zero_days(self):
        from backend.app.motors.m06_document_factory.filters import add_days_es
        assert add_days_es(date(2026, 4, 22), 0) == "22/04/2026"

    def test_registered_in_es_filters(self):
        from backend.app.motors.m06_document_factory.filters import ES_FILTERS
        assert "add_days_es" in ES_FILTERS


def test_p001_has_caducidad_header():
    content = (COMMERCIAL / "P001_propuesta_comercial_maestra_de_servicios_ens.md").read_text()
    assert "Validez de la oferta" in content
    assert "30 días naturales" in content
    assert "add_days_es(30)" in content


def test_p001_has_section_validez_y_caducidad():
    content = (COMMERCIAL / "P001_propuesta_comercial_maestra_de_servicios_ens.md").read_text()
    assert "## 11. VALIDEZ Y CADUCIDAD DE LA OFERTA" in content
    assert "1.262 del Código Civil" in content or "1.262 del Codigo Civil" in content


# ══════════════════════════════════════════════════════════════════════
# 5.5.4 — C-003 OBLIGACIONES
# ══════════════════════════════════════════════════════════════════════


def _read_c003():
    return (
        COMMERCIAL
        / "C003_contrato_de_servicios_de_mantenimiento_continuo_re.md"
    ).read_text(encoding="utf-8")


class TestC003Obligaciones:
    def test_has_quinta_obligaciones_section(self):
        content = _read_c003()
        assert "QUINTA — OBLIGACIONES DE LAS PARTES" in content

    def test_has_conditional_c001_previous(self):
        content = _read_c003()
        assert "{% if contrato.contrato_implantacion_previo %}" in content
        assert "{% else %}" in content
        assert "{% endif %}" in content

    def test_references_c001_clauses_when_previous(self):
        content = _read_c003()
        assert "Cláusula SEXTA de C-001" in content or "Clausula SEXTA de C-001" in content
        assert "Cláusula OCTAVA de C-001" in content or "Clausula OCTAVA de C-001" in content

    def test_has_sla_by_tier_table(self):
        content = _read_c003()
        assert "R_MICRO" in content
        assert "R_LITE" in content
        assert "R_STD" in content
        assert "R_PLUS" in content
        assert "R_CRITICAL" in content

    def test_has_15d_notificacion_cambios_materiales(self):
        content = _read_c003()
        assert "15 días naturales" in content or "15 dias naturales" in content
        assert "cambios materiales" in content.lower()

    def test_has_fuero_competente(self):
        content = _read_c003()
        assert "Fuero competente" in content or "fuero competente" in content


# ══════════════════════════════════════════════════════════════════════
# 5.5.5 — Legal audit score 100
# ══════════════════════════════════════════════════════════════════════


def test_legal_audit_score_100():
    """Ejecuta el auditor legal automatico y valida score == 100."""
    result = subprocess.run(
        [sys.executable, "-m", "backend.scripts.legal_audit_77_templates"],
        cwd=str(ROOT),
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(ROOT),
        },
        capture_output=True,
        text=True,
    )
    # The script may be launched directly as file
    if result.returncode != 0:
        result = subprocess.run(
            [sys.executable, "backend/scripts/legal_audit_77_templates.py"],
            cwd=str(ROOT),
            env={
                **__import__("os").environ,
                "PYTHONPATH": str(ROOT),
            },
            capture_output=True,
            text=True,
        )
    assert result.returncode == 0, result.stderr
    report = json.loads(
        (ROOT / "progress" / "legal_audit_autocheck.json").read_text()
    )
    assert report["global_score_0_100"] == 100.0, (
        f"Score {report['global_score_0_100']} != 100. "
        f"Totals: {report['totals']}"
    )
    assert report["totals"]["CRITICAL"] == 0
    assert report["totals"]["HIGH"] == 0
    assert report["totals"]["MEDIUM"] == 0
    assert report["totals"]["LOW"] == 0
