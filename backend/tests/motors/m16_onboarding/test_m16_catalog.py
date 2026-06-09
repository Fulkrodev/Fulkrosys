"""Tests del catalogo de plantillas M16."""

from backend.app.motors.m16_onboarding.catalog_loader import (
    find_template_for,
    get_template_by_id,
    list_available_sectors,
    load_all_templates,
)
from backend.app.motors.m16_onboarding.enums import Role, Sector


def test_catalog_loads_at_least_3_pilot_templates():
    templates = load_all_templates()
    assert len(templates) >= 3


def test_no_duplicate_template_ids():
    templates = load_all_templates()
    ids = [t.id for t in templates]
    assert len(ids) == len(set(ids))


def test_pilot_templates_for_servicios_profesionales():
    for role in [Role.SPONSOR, Role.TI_CTO, Role.LEGAL_DPO]:
        t = find_template_for(Sector.SERVICIOS_PROFESIONALES, role)
        assert t is not None, f'Falta plantilla piloto para {role.value}'


def test_get_template_by_id_known():
    t = get_template_by_id('onb-servicios_profesionales-sponsor-v1')
    assert t is not None
    assert t.sector == Sector.SERVICIOS_PROFESIONALES
    assert t.role == Role.SPONSOR


def test_get_template_by_id_unknown_returns_none():
    assert get_template_by_id('onb-fake-999') is None


def test_find_template_for_full_matrix_coverage():
    """The 10x7 sector-role matrix is fully covered after the cierre 2% expansion.

    Batch B diagnóstico previo: el sector sintético PRECLIENTE queda FUERA de
    esta matriz in-portal (solo tiene la plantilla sponsor del cuestionario del
    lead account-less · se filtra del catálogo admin).
    L-2/L-3 (FRENTE L): el sector sintético INDIVIDUAL (autónomo/micro) también
    queda fuera · una sola persona cubre todos los roles → solo plantilla sponsor.
    """
    _SYNTHETIC = {Sector.PRECLIENTE, Sector.INDIVIDUAL}
    for sector in Sector:
        if sector in _SYNTHETIC:
            continue
        for role in Role:
            t = find_template_for(sector, role)
            assert t is not None, f"Missing template for ({sector.value}, {role.value})"


def test_available_sectors_includes_pilot():
    sectors = list_available_sectors()
    assert Sector.SERVICIOS_PROFESIONALES in sectors


def test_templates_all_have_at_least_3_questions():
    for t in load_all_templates():
        assert len(t.questions) >= 3, f'{t.id} tiene {len(t.questions)} preguntas'
