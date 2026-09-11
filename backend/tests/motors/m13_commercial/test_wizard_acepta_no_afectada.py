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
    Con NULL, que es lo que el resto del codigo ya asume: los lectores arrancan
    en NO_AFECTADA y solo suben la dimension si ven un nivel de la terna
    (`service.py`, `aplicabilidad.py`, `m03_dda/service.py`). No hay que inventar
    vocabulario nuevo ni migrar ninguna columna.
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


def test_al_persistir_NO_AFECTADA_se_guarda_como_NULL():
    """La capa 2: String(10) no puede con 11 caracteres."""
    from backend.app.motors.m13_commercial.services.project_provisioning_service import (
        _impact_to_valoracion,
    )

    assert _impact_to_valoracion("NO_AFECTADA") is None
    # Y los niveles de verdad siguen pasando tal cual.
    for nivel in ("BAJO", "MEDIO", "ALTO"):
        assert _impact_to_valoracion(nivel) == nivel


def test_la_columna_no_podria_guardar_el_literal():
    """Deja constancia de POR QUE se traduce a NULL y no se guarda el literal."""
    from backend.app.models.core import InformationType

    col = InformationType.__table__.c.valoracion_d
    assert col.type.length == 10, (
        "si esta columna se amplia, revisar si sigue teniendo sentido traducir "
        "NO_AFECTADA a NULL o conviene guardar el literal"
    )
    assert len("NO_AFECTADA") > col.type.length
    assert col.nullable, "NULL es la representacion canonica de 'no afectada'"
