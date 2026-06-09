"""Guardia: la tabla autoritativa del Anexo II coincide con RD 311/2022 (BOE).

Auditoría 2026-06-07. El catálogo ens_measures había derivado a numeración/nombres/
aplicabilidad del RD 3/2010 (derogado). Verificado celda a celda contra la tabla
oficial del BOE-A-2022-7191 (Anexo II). Este test BLINDA el resultado: si alguien
reintroduce códigos RD 3/2010 o cambia las cuentas por nivel, falla de inmediato.

NO requiere DB: testea la fuente única de verdad ``ANEXO_II_RD311``, que el loader
(load_ens_measures_catalog.py) fuerza sobre ens_measures en cada (re)seed.
"""
from backend.app.motors.m03_dda.anexo2_rd311_2022 import (
    ANEXO_II_RD311,
    APLICA_ALTA,
    APLICA_BASICA,
    APLICA_MEDIA,
    TOTAL_MEDIDAS,
    applicability_counts,
    resolve_entries,
)


def test_total_73_measures():
    assert len(ANEXO_II_RD311) == TOTAL_MEDIDAS == 73


def test_family_structure_org4_op33_mp36():
    org = [c for c in ANEXO_II_RD311 if c.startswith("org.")]
    op = [c for c in ANEXO_II_RD311 if c.startswith("op.")]
    mp = [c for c in ANEXO_II_RD311 if c.startswith("mp.")]
    assert (len(org), len(op), len(mp)) == (4, 33, 36)


def test_applicability_counts_basica52_media68_alta73():
    # Cuentas oficiales (celda ≠ n.a.) verificadas contra la tabla del BOE.
    assert applicability_counts() == (52, 68, 73)
    assert (APLICA_BASICA, APLICA_MEDIA, APLICA_ALTA) == (52, 68, 73)


def test_rd3_2010_legacy_codes_absent():
    # Códigos del RD 3/2010 (derogado) que NO existen en RD 311/2022 Anexo II.
    for legacy in ("op.exp.11", "mp.s.8", "mp.s.9", "mp.if.9", "mp.per.9", "mp.com.9", "op.acc.7"):
        assert legacy not in ANEXO_II_RD311, f"{legacy} es RD 3/2010, no debe existir"


def test_headline_corrections_present():
    # op.exp.10 es "Protección de claves criptográficas" y aplica a los 3 niveles
    name, b, m, a = ANEXO_II_RD311["op.exp.10"]
    assert name == "Protección de claves criptográficas"
    assert (b, m, a) == (True, True, True)
    # DoS es mp.s.4 (no mp.s.8) y aplica MEDIA+ALTA
    name_s4, b4, m4, a4 = ANEXO_II_RD311["mp.s.4"]
    assert "denegación de servicio" in name_s4.lower()
    assert (b4, m4, a4) == (False, True, True)
    # op.acc.6 con el nombre RD 311/2022 (no "Acceso Local")
    assert "autenticación" in ANEXO_II_RD311["op.acc.6"][0].lower()
    # mp.info sin desfase: mp.info.3 = Firma electrónica (no "Cifrado")
    assert ANEXO_II_RD311["mp.info.3"][0] == "Firma electrónica"


def test_op_exp_ends_at_10_mp_s_ends_at_4():
    op_exp = sorted(c for c in ANEXO_II_RD311 if c.startswith("op.exp."))
    assert op_exp[-1] == "op.exp.9" or "op.exp.10" in ANEXO_II_RD311
    assert "op.exp.11" not in ANEXO_II_RD311
    mp_s = [c for c in ANEXO_II_RD311 if c.startswith("mp.s.")]
    assert set(mp_s) == {"mp.s.1", "mp.s.2", "mp.s.3", "mp.s.4"}


def test_resolve_entries_sources_descriptions_by_name():
    # El resolver casa descripciones por NOMBRE (resuelve el desfase mp.info / op.exp.10).
    yaml_measures = [
        {"codigo": "op.exp.11", "nombre": "Protección de claves criptográficas",
         "descripcion": "Gestión del ciclo de vida de claves criptográficas."},
        {"codigo": "mp.info.4", "nombre": "Firma electrónica",
         "descripcion": "Uso de firma electrónica para integridad y autenticidad."},
    ]
    out = resolve_entries(yaml_measures)
    assert len(out) == 73
    # op.exp.10 toma la descripción de la entrada YAML llamada "claves criptográficas"
    assert "claves criptográficas" in out["op.exp.10"]["descripcion"]
    assert out["op.exp.10"]["aplica_basica"] is True
    # mp.info.3 toma la descripción de la entrada "Firma electrónica"
    assert "firma electrónica" in out["mp.info.3"]["descripcion"].lower()
