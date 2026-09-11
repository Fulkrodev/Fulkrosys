"""Fechas de certificacion para probar el calendario de renovacion.

O1 · el bienio del art. 31 es de ANYOS de calendario, no de un numero fijo de
dias, asi que no vale restar una constante: el numero de dias depende de si el
tramo cruza un 29 de febrero. Se busca la fecha cuyo aniversario REAL cae donde
hace falta, preguntandoselo a la funcion canonica.

Vive aqui y no en cada fichero de test porque copiarlo en dos sitios es
exactamente el patron que se ha estado cerrando toda la sesion.
"""
from __future__ import annotations

from datetime import date, timedelta

from backend.app.motors.m27_conformity.bienio import proxima_fecha_bienal


def certificado_para_que_falten(dias: int) -> date:
    """Fecha de certificacion tal que HOY falten ``dias`` para el aniversario."""
    objetivo = date.today() + timedelta(days=dias)
    for delta in range(-3, 4):
        candidata = objetivo.replace(year=objetivo.year - 2) + timedelta(days=delta)
        if proxima_fecha_bienal(candidata) == objetivo:
            return candidata
    raise AssertionError(f"no hay fecha cuyo bienio caiga en {objetivo}")
