"""O2 · el asistente deja crear un proyecto con una dimension NO AFECTADA.

EL FLECO, y por que es el nucleo del encargo
    La interfaz del asistente (/admin/projects/new, paso 3) SI ofrece el boton
    "No afectada" por dimension, calcula bien la categoria sugerida ignorandola y
    la muestra en la pantalla de revision. Pero al pulsar "Crear cliente +
    proyecto" el backend devolvia **422**: el contrato de entrada solo aceptaba
    BAJO/MEDIO/ALTO.

    O sea: la opcion existe en la pantalla y no se puede materializar. Todo el
    trabajo del bloque N sobre el Anexo I punto 3 era inalcanzable desde la
    interfaz; solo se llegaba por psql.

DOS CAPAS, y arreglar solo la primera empeora el fallo
    CAPA 1 · `admin_diagnostico_wizard.py:59` — el Literal del contrato.
    CAPA 2 · `project_provisioning_service.py:49` — `_impact_to_valoracion` era
             la identidad, y `information_types.valoracion_*` es String(10).
             "NO_AFECTADA" son 11 caracteres: ampliar solo el Literal cambia el
             422 por un 500 StringDataRightTruncation.

COMO SE REPRESENTA "no afectada" EN PERSISTENCIA
    O2 lo resolvio con NULL, porque la columna no daba para mas. Q1 amplio la
    columna (migracion `no_afectada_cabe_001`) y guarda el LITERAL: NULL tenia
    que significar dos cosas a la vez -- "sin dato" y "no afectada" -- y de esa
    ambiguedad salio el `or "BAJO"` que metia un nivel inventado en el acta
    E-012 firmada. Los lectores siguen tratando NULL como no afectada, asi que
    lo escrito antes se lee igual.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_el_contrato_del_asistente_acepta_NO_AFECTADA():
    from backend.app.api.v1.admin_diagnostico_wizard import EnsDimsValoracion

    dims = EnsDimsValoracion(
        confidencialidad="MEDIO",
        integridad="MEDIO",
        disponibilidad="NO_AFECTADA",
        autenticidad="BAJO",
        trazabilidad="MEDIO",
    )
    assert dims.disponibilidad == "NO_AFECTADA"


def test_el_contrato_sigue_rechazando_un_valor_inventado():
    """Relajar el tipo no puede convertirlo en un campo libre."""
    from backend.app.api.v1.admin_diagnostico_wizard import EnsDimsValoracion

    with pytest.raises(ValidationError):
        EnsDimsValoracion(confidencialidad="REGULAR")


def test_al_persistir_NO_AFECTADA_se_guarda_el_literal():
    """Q1 · la decision se registra; ya no se colapsa contra "sin dato"."""
    from backend.app.motors.m13_commercial.services.project_provisioning_service import (
        _impact_to_valoracion,
    )

    assert _impact_to_valoracion("NO_AFECTADA") == "NO_AFECTADA"
    # Y los niveles de verdad siguen pasando tal cual.
    for nivel in ("BAJO", "MEDIO", "ALTO"):
        assert _impact_to_valoracion(nivel) == nivel
    # "sin dato" sigue siendo NULL, y no es lo mismo.
    assert _impact_to_valoracion(None) is None


def test_la_columna_cabe_el_literal():
    """El defecto era el ancho de la columna: 11 caracteres en VARCHAR(10)."""
    from backend.app.models.core import InformationType, Service

    for modelo in (InformationType, Service):
        col = modelo.__table__.c.valoracion_d
        assert col.type.length >= len("NO_AFECTADA"), (
            f"{modelo.__tablename__}.valoracion_d es VARCHAR({col.type.length}) "
            "y 'NO_AFECTADA' no cabe: el estado que define el Anexo I punto 3 "
            "vuelve a ser irrepresentable"
        )
        assert col.nullable, "NULL sigue significando 'sin dato'"
