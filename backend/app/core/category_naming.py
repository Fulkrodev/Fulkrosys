"""#39 Ola9 · Nomenclatura canónica de categoría ENS · puente entre 2 convenciones.

Coexisten dos formas históricas:
- PROYECTO / negocio: BASICA · MEDIA · ALTA (projects.categoria_objetivo · RD 311/2022).
- m08 verification (VerificationRun.category): BASICO · MEDIO · ALTO.

Decisión #39: NO renombrar el enum m08 (rename + data migration de
VerificationRun.category = riesgo alto, beneficio sólo cosmético) sino proveer este
puente canónico para comparaciones seguras entre ambos planos.

Verificado empíricamente: el flujo de pentest (pentest_auto_trigger crea la run en
'ALTO' y el gate alta_pentest_cpstic la chequea en 'ALTO') es internamente
consistente · NO existe el fire-failure que sugería el audit (la afirmación
'pentest ALTA nunca dispara' era inexacta · el trigger compara
project.categoria_objetivo == 'ALTA' correctamente).
"""
from __future__ import annotations

PROJECT_CATEGORIES = ("BASICA", "MEDIA", "ALTA")
VERIFICATION_CATEGORIES = ("BASICO", "MEDIO", "ALTO")

_PROJECT_BY_VERIFICATION = {"BASICO": "BASICA", "MEDIO": "MEDIA", "ALTO": "ALTA"}
_VERIFICATION_BY_PROJECT = {v: k for k, v in _PROJECT_BY_VERIFICATION.items()}


def to_project_category(value: str | None) -> str | None:
    """Normaliza a la forma de PROYECTO (BASICA/MEDIA/ALTA). Acepta ambas formas
    (case-insensitive). None si no reconoce el valor."""
    if not value:
        return None
    v = value.strip().upper()
    if v in PROJECT_CATEGORIES:
        return v
    return _PROJECT_BY_VERIFICATION.get(v)


def to_verification_category(value: str | None) -> str | None:
    """Normaliza a la forma de m08 verification (BASICO/MEDIO/ALTO). Acepta ambas
    formas (case-insensitive). None si no reconoce el valor."""
    if not value:
        return None
    v = value.strip().upper()
    if v in VERIFICATION_CATEGORIES:
        return v
    return _VERIFICATION_BY_PROJECT.get(v)
