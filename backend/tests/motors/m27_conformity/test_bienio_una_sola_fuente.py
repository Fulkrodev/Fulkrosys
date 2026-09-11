"""O1 · el bienio del art. 31 se calcula igual en todo el sistema, y son ANYOS.

EL DEFECTO
    El plazo de dos anyos del art. 31 estaba escrito CINCO veces, y ya habia
    divergido:

        conformity_service_paso5.py:64   CERTIFICATION_VALIDITY_MONTHS = 24
        conformity_service_paso5.py:231  timedelta(days=MONTHS * 30)   -> 720 dias
        renewal_scheduler.py:30          CERTIFICATION_VALIDITY_DAYS = 730
        audit_schedule_service.py:25     BIANNUAL_PERIOD_DAYS = 730
        api.py:211                       timedelta(days=730)

    24 * 30 = 720, no 730. La fecha de caducidad grabada en la ruta de
    conformidad iba DIEZ DIAS por delante de la que usaban el planificador de
    renovacion y el calendario de auditoria. Mismo patron que la regla del
    maximo: una constante normativa escrita N veces, se arregla una y las otras
    quedan atras.

Y NINGUNA DE LAS DOS ERA CORRECTA
    El art. 31.1 dice "al menos cada dos anyos". Dos anyos de CALENDARIO, no 730
    dias: 730 = 2x365 y se come el dia bisiesto. Sobre una fecha que caiga antes
    del 29 de febrero de un anyo bisiesto, sumar 730 dias adelanta la caducidad
    un dia. En un plazo regulatorio que se graba en un entregable firmado, eso
    no es despreciable: es una fecha incorrecta.

    La cita literal, del PDF del BOE verificado en N0:
      "Los sistemas de informacion [...] seran objeto de una auditoria regular
       ordinaria, al menos cada dos anyos, que verifique el cumplimiento de los
       requerimientos del ENS."
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]


def test_existe_una_sola_funcion_para_el_bienio():
    from backend.app.motors.m27_conformity.bienio import (
        PERIODO_AUDITORIA_ANYOS,
        proxima_fecha_bienal,
    )

    assert PERIODO_AUDITORIA_ANYOS == 2
    assert callable(proxima_fecha_bienal)


def test_suma_anyos_de_calendario_no_730_dias():
    """El caso que separa las dos aritmeticas: un 1 de marzo pre-bisiesto."""
    from backend.app.motors.m27_conformity.bienio import proxima_fecha_bienal

    # 2026-03-01 + 2 anyos = 2028-03-01. Sumar 730 dias daria 2028-02-29.
    assert proxima_fecha_bienal(date(2026, 3, 1)) == date(2028, 3, 1)
    # 2024-02-29 (bisiesto) + 2 anyos: no existe el 29-02-2026 -> 28-02-2026.
    assert proxima_fecha_bienal(date(2024, 2, 29)) == date(2026, 2, 28)


def test_720_dias_no_reaparece():
    """`MESES * 30` era la aritmetica que daba 720 en vez de 730 ni 2 anyos."""
    ficheros = list((RAIZ / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500
    malos = []
    patron = re.compile(r"timedelta\(\s*days\s*=\s*[^)]*\*\s*30\b")
    for py in ficheros:
        for i, linea in enumerate(py.read_text("utf-8", errors="ignore").splitlines(), 1):
            if patron.search(linea.split("#", 1)[0]):
                malos.append(f"{py.relative_to(RAIZ)}:{i}: {linea.strip()[:80]}")
    assert not malos, "plazos calculados como meses x 30 dias:\n" + "\n".join(malos)


def test_ningun_730_suelto_para_el_bienio():
    ficheros = list((RAIZ / "backend" / "app").rglob("*.py"))
    assert len(ficheros) > 500
    permitido = {"backend/app/motors/m27_conformity/bienio.py"}
    # 730 que NO son el bienio del art. 31. Se declaran POR FICHERO, con su
    # motivo, en vez de con una regex difusa que acabaria tapando el caso real.
    NO_ES_EL_BIENIO = {
        # Tope de un parametro de consulta: dos anyos de historico como limite
        # superior de un rango, no un plazo normativo.
        "backend/app/motors/m_observability/transparency_api.py",
        "backend/app/motors/m_observability/transparency_service.py",
        # Antiguedad maxima de una plantilla de DPA: criterio propio de revision
        # documental (RGPD art. 28), no la auditoria bienal del ENS.
        "backend/app/motors/m_compliance_monitor/checks.py",
        # Retencion minima de registros en ALTA (op.exp.8). Es otro plazo, y su
        # propia divergencia esta anotada aparte como hallazgo ABIERTO.
        "backend/app/motors/m22_discovery/log_assessment.py",
    }
    malos = []
    for py in ficheros:
        rel = str(py.relative_to(RAIZ))
        if rel in permitido:
            continue
        lineas = py.read_text("utf-8", errors="ignore").splitlines()
        for i, linea in enumerate(lineas, 1):
            sin_com = linea.split("#", 1)[0]
            if not re.search(r"\b730\b", sin_com):
                continue
            if rel in NO_ES_EL_BIENIO:
                continue
            malos.append(f"{rel}:{i}: {linea.strip()[:80]}")
    assert not malos, (
        "el bienio del art. 31 vuelve a estar escrito como 730 dias:\n"
        + "\n".join(malos)
    )
