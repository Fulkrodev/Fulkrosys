"""L-3 (FRENTE L) · plantilla de onboarding del perfil autónomo/microempresa
(Sector.INDIVIDUAL · L-2). Una persona cubre todos los roles · onboarding ligero.
"""
from __future__ import annotations

from backend.app.motors.m16_onboarding.catalog_loader import (
    find_template_for,
    load_all_templates,
)
from backend.app.motors.m16_onboarding.enums import Role, Sector


def test_l2_sector_individual_exists():
    assert Sector.INDIVIDUAL.value == "individual"


def test_l3_individual_sponsor_template_loads():
    t = find_template_for(Sector.INDIVIDUAL, Role.SPONSOR)
    assert t is not None
    assert t.id == "onb-individual-sponsor-v1"
    assert t.sector == Sector.INDIVIDUAL
    assert len(t.questions) >= 8
    # cubre la acumulación de roles (Art.11) · pieza nuclear del perfil
    qids = {q.id for q in t.questions}
    assert "q-acumulacion_roles" in qids
    assert "q-nivel_objetivo" in qids  # soporta elegir los 3 niveles


def test_l3_catalog_still_valid_no_duplicates():
    # el catálogo entero sigue cargando + validando (sin ids/keys duplicados)
    tpls = load_all_templates()
    assert len(tpls) >= 70
    ids = [t.id for t in tpls]
    assert len(ids) == len(set(ids))
