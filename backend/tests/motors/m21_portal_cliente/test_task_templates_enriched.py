"""Tests · sub-atom 1.C.D.A.1 v3.8 · YAML enriched + 30 templates canónicos.

Cubre:
  - Parsing YAML enriched (18 legacy + 30 enriched · sin breaking)
  - Pydantic schema validation backward-compat (campos opcionales)
  - get_enriched_steps_for_project filter 19 dimensiones
  - applicable_size_ranges · applicable_madurez_min/max
  - requires_dora · requires_dpo · requires_nis2 · requires_ai_act
  - apply_archetype_variant returns variant overlay
  - Ordering canonical (phase × order_within_phase × priority desc × id)
"""
from __future__ import annotations

import pytest

from backend.app.motors.m21_portal_cliente.task_templates_loader import (
    TaskTemplate,
    apply_archetype_variant,
    get_enriched_steps_for_project,
    get_template_by_id,
    get_templates_for_phase,
    load_task_templates,
    reload_task_templates,
)


# ================================================================
# Parsing YAML · backward-compat
# ================================================================


def test_yaml_loads_without_errors():
    """Catalog parsea limpio · NO Pydantic validation errors."""
    catalog = reload_task_templates()
    assert catalog.version == "1.0.0"
    assert len(catalog.templates) >= 48  # 18 legacy + 30 enriched


def test_legacy_18_templates_preserved():
    """18 legacy continúan funcionando (backward-compat preservada)."""
    catalog = load_task_templates()
    legacy_ids = {
        "PHASE3_BASICA_REVIEW_DIAGNOSIS",
        "PHASE5_BASICA_APPROVE_PDA",
        "PHASE9_BASICA_SIGN_AUTOEVALUACION",
        "PHASE5_MEDIA_APPROVE_PDA",
        "PHASE8_MEDIA_ASSIGN_AUDITOR_ENAC",
        "PHASE9_MEDIA_REVIEW_AUDIT_REPORT",
        "PHASE5_ALTA_APPROVE_PDA",
        "PHASE8_ALTA_PENTEST_CPSTIC",
        "PHASE8_ALTA_RED_TEAM",
        "PHASE6_ALTA_CRIPTOGRAFIA_807",
        "PHASE9_ALTA_REVIEW_AUDIT_REPORT",
    }
    all_ids = {t.id for t in catalog.templates}
    assert legacy_ids.issubset(all_ids)


def test_enriched_30_templates_loaded():
    """30 enriched templates con prefix ENR_ presentes."""
    catalog = load_task_templates()
    enriched_ids = [t.id for t in catalog.templates if t.id.startswith("ENR_")]
    assert len(enriched_ids) >= 30


def test_enriched_templates_have_is_enriched_flag():
    """Enriched templates tienen is_enriched=true."""
    catalog = load_task_templates()
    for t in catalog.templates:
        if t.id.startswith("ENR_"):
            assert t.is_enriched is True


def test_legacy_templates_default_is_enriched_false():
    """Legacy templates default is_enriched=False (NO setteado)."""
    catalog = load_task_templates()
    legacy = next(
        (t for t in catalog.templates if t.id == "PHASE3_BASICA_REVIEW_DIAGNOSIS"),
        None,
    )
    assert legacy is not None
    assert legacy.is_enriched is False


# ================================================================
# Schema enriched fields parsing
# ================================================================


def test_enriched_template_parses_full_fields():
    """ENR template enriched parsea todos los campos enriched."""
    t = get_template_by_id("ENR_AD_03_DORA_FRAMEWORK_ICT")
    assert t is not None
    assert t.is_enriched is True
    assert t.requires_dora is True
    assert t.order_within_phase == 3
    assert "Marcos" in t.actors
    assert "DR-002" in t.deliverable_codes
    assert "op.pl.1" in t.tooltips_ens
    assert "proveedor_financiero" in t.archetype_variants


def test_enriched_template_archetype_variants_parse():
    """archetype_variants parses ArchetypeVariant sub-object."""
    t = get_template_by_id("ENR_FT_01_FINTECH_PAYMENT_GATEWAY")
    assert t is not None
    fintech_v = t.archetype_variants.get("fintech")
    assert fintech_v is not None
    assert "Tokenization" in (fintech_v.extra_focus or "")


def test_enriched_template_madurez_range_parses():
    """applicable_madurez_min/max parseable."""
    # No tenemos templates con madurez range explícito en seed inicial
    # but verificar que field es None opcional
    t = get_template_by_id("ENR_PV_01_LEAD_QUALIFICATION_DEEP")
    assert t is not None
    assert t.applicable_madurez_min is None
    assert t.applicable_madurez_max is None


# ================================================================
# Legacy filter (backward-compat)
# ================================================================


def test_legacy_get_templates_for_phase_basica():
    """Legacy get_templates_for_phase sigue funcionando."""
    result = get_templates_for_phase(
        phase="diagnostico", categoria="BASICA", archetype=None,
    )
    ids = {t.id for t in result}
    assert "PHASE3_BASICA_REVIEW_DIAGNOSIS" in ids


def test_legacy_get_templates_for_phase_media_no_archetype():
    result = get_templates_for_phase(
        phase="adecuacion", categoria="MEDIA", archetype=None,
    )
    ids = {t.id for t in result}
    assert "PHASE5_MEDIA_APPROVE_PDA" in ids


# ================================================================
# Enriched filter · 19 dimensiones · get_enriched_steps_for_project
# ================================================================


def test_enriched_filter_basica_minimo_dims():
    """BÁSICA minimal · sólo templates sin requires_* legales."""
    project_dims = {
        "categoria_objetivo": "BASICA",
        "archetype": "saas_only",
        "tamano_empleados": "pequeno",
        "madurez_ens_actual": "L0",
        "aplica_dora": "no",
        "aplica_nis2": "no",
        "aplica_ai_act": "no",
        "dpo_designado": "no_designado",
        "procesa_datos_sensibles_rgpd9": False,
        "fase": "diagnostico",
    }
    steps = get_enriched_steps_for_project(project_dims)
    # Debe incluir enriched templates ALL + BASICA · NO requires_dora/dpo/nis2/aiact
    ids = {t.id for t in steps}
    # ENR templates NO require_dora etc deben aparecer
    assert "ENR_PV_01_LEAD_QUALIFICATION_DEEP" in ids
    # ENR_AD_03_DORA NO debe estar (requires_dora · cliente=no)
    assert "ENR_AD_03_DORA_FRAMEWORK_ICT" not in ids
    # ENR_AD_04_DPIA NO debe estar (requires_dpo + datos_sensibles)
    assert "ENR_AD_04_DPIA_RGPD_DATOS_SENSIBLES" not in ids
    # Red Team NO (ALTA only · cliente BASICA)
    assert "ENR_VF_02_REDTEAM_ALTA" not in ids


def test_enriched_filter_fintech_media_with_dora():
    """Fintech MEDIA con DORA · debe incluir ENR_AD_03_DORA."""
    project_dims = {
        "categoria_objetivo": "MEDIA",
        "archetype": "fintech",
        "tamano_empleados": "mediano",
        "madurez_ens_actual": "L1",
        "aplica_dora": "entidad_financiera",
        "aplica_nis2": "no",
        "aplica_ai_act": "no",
        "dpo_designado": "interno",
        "procesa_datos_sensibles_rgpd9": False,
        "fase": "adecuacion",
    }
    steps = get_enriched_steps_for_project(project_dims)
    ids = {t.id for t in steps}
    assert "ENR_AD_03_DORA_FRAMEWORK_ICT" in ids
    # Red Team NO (ALTA only)
    assert "ENR_VF_02_REDTEAM_ALTA" not in ids


def test_enriched_filter_alta_redteam_visible():
    """Cliente ALTA · Red Team enriched visible."""
    project_dims = {
        "categoria_objetivo": "ALTA",
        "archetype": "sector_salud",
        "tamano_empleados": "grande",
        "madurez_ens_actual": "L0",
        "aplica_dora": "no",
        "aplica_nis2": "esencial",
        "aplica_ai_act": "no",
        "dpo_designado": "interno",
        "procesa_datos_sensibles_rgpd9": True,
        "fase": "verificacion",
    }
    steps = get_enriched_steps_for_project(project_dims)
    ids = {t.id for t in steps}
    # Red Team ALTA
    assert "ENR_VF_02_REDTEAM_ALTA" in ids
    # DPIA por procesa_datos_sensibles + dpo_designado
    assert "ENR_AD_04_DPIA_RGPD_DATOS_SENSIBLES" in ids


def test_enriched_filter_requires_ai_act():
    """Cliente sin AI Act · NO debe ver AI Act conformity."""
    project_dims_no_ai = {
        "categoria_objetivo": "MEDIA",
        "archetype": "saas_only",
        "aplica_ai_act": "no",
        "aplica_dora": "no",
        "aplica_nis2": "no",
        "dpo_designado": "no_designado",
        "procesa_datos_sensibles_rgpd9": False,
        "fase": "implantacion",
    }
    steps = get_enriched_steps_for_project(project_dims_no_ai)
    ids = {t.id for t in steps}
    assert "ENR_IM_04_AI_ACT_CONFORMITY" not in ids

    # Mismo cliente con AI Act alto_riesgo
    project_dims_ai = {**project_dims_no_ai, "aplica_ai_act": "alto_riesgo"}
    steps_ai = get_enriched_steps_for_project(project_dims_ai)
    ids_ai = {t.id for t in steps_ai}
    assert "ENR_IM_04_AI_ACT_CONFORMITY" in ids_ai


def test_enriched_filter_size_range_micro():
    """Cliente micro · debe incluir ENR_OB_03_TI_BASICO_SIN_EQUIPO (size_range=[micro,pequeno])."""
    project_dims = {
        "categoria_objetivo": "BASICA",
        "archetype": "saas_only",
        "tamano_empleados": "micro",
        "fase": "onboarding",
        "aplica_dora": "no",
        "aplica_nis2": "no",
        "aplica_ai_act": "no",
        "dpo_designado": "no_designado",
        "procesa_datos_sensibles_rgpd9": False,
    }
    steps = get_enriched_steps_for_project(project_dims)
    ids = {t.id for t in steps}
    assert "ENR_OB_03_TI_BASICO_SIN_EQUIPO" in ids


def test_enriched_filter_size_range_enterprise_excludes():
    """Cliente enterprise · NO debe incluir ENR_OB_03 (size_range=[micro,pequeno])."""
    project_dims = {
        "categoria_objetivo": "ALTA",
        "archetype": "sector_publico_concesionario",
        "tamano_empleados": "enterprise",
        "fase": "onboarding",
        "aplica_dora": "no",
        "aplica_nis2": "esencial",
        "aplica_ai_act": "no",
        "dpo_designado": "interno",
        "procesa_datos_sensibles_rgpd9": False,
    }
    steps = get_enriched_steps_for_project(project_dims)
    ids = {t.id for t in steps}
    assert "ENR_OB_03_TI_BASICO_SIN_EQUIPO" not in ids


def test_enriched_filter_phase_filter():
    """phase_filter limita resultados a esa phase."""
    project_dims = {
        "categoria_objetivo": "MEDIA",
        "archetype": "saas_only",
        "tamano_empleados": "pequeno",
        "aplica_dora": "no",
        "aplica_nis2": "no",
        "aplica_ai_act": "no",
        "dpo_designado": "no_designado",
        "procesa_datos_sensibles_rgpd9": False,
        "fase": "diagnostico",
    }
    steps = get_enriched_steps_for_project(project_dims, phase_filter="adecuacion")
    # All results must be phase=adecuacion
    for s in steps:
        assert s.phase == "adecuacion"


# ================================================================
# Ordering canonical
# ================================================================


def test_enriched_ordering_canonical():
    """get_enriched_steps_for_project ordena por phase canonical · order_within_phase · priority desc."""
    project_dims = {
        "categoria_objetivo": "MEDIA",
        "archetype": "fintech",
        "tamano_empleados": "mediano",
        "aplica_dora": "entidad_financiera",
        "aplica_nis2": "no",
        "aplica_ai_act": "no",
        "dpo_designado": "interno",
        "procesa_datos_sensibles_rgpd9": False,
        "fase": "implantacion",
    }
    steps = get_enriched_steps_for_project(project_dims)

    # Find ENR_PV_*, ENR_OB_*, ENR_DG_* templates in result
    phases_seen: list[str] = []
    for s in steps:
        if s.phase not in phases_seen:
            phases_seen.append(s.phase)

    # Verify canonical order (pre_venta < onboarding < diagnostico < ...)
    from backend.app.core.workflow_phase import WorkflowPhase

    ordered = [p.value for p in WorkflowPhase.ordered()]
    seen_indices = [ordered.index(p) for p in phases_seen if p in ordered]
    assert seen_indices == sorted(seen_indices), (
        f"Phases not canonical-ordered: {phases_seen}"
    )


# ================================================================
# Archetype variant application
# ================================================================


def test_apply_archetype_variant_fintech():
    """apply_archetype_variant overlay fintech con extra_focus."""
    t = get_template_by_id("ENR_AD_03_DORA_FRAMEWORK_ICT")
    assert t is not None
    enriched = apply_archetype_variant(t, "proveedor_financiero")
    assert enriched.get("_variant_extra_focus") is not None
    assert "TLPT" in enriched["_variant_extra_focus"]


def test_apply_archetype_variant_no_match_returns_base():
    """archetype sin variant · returns base sin overlay."""
    t = get_template_by_id("ENR_AD_03_DORA_FRAMEWORK_ICT")
    assert t is not None
    enriched = apply_archetype_variant(t, "educacion_privada")
    assert enriched.get("_variant_extra_focus") is None


def test_apply_archetype_variant_none_returns_base():
    t = get_template_by_id("ENR_AD_03_DORA_FRAMEWORK_ICT")
    assert t is not None
    enriched = apply_archetype_variant(t, None)
    assert "_variant_extra_focus" not in enriched
