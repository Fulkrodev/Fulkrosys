"""#30 Ola8 · el reporte trimestral del retainer está declarado en el beat.

El task generate_quarterly_reports ya era real (RetainerCheckinService) pero no
tenía entrada en celery beat_schedule → nunca se disparaba solo. Este test fija
que la entrada existe en el source de celery_app con el task y cadencia correctos.

Nota: en el venv de test celery NO está instalado → celery_app es un stub con
beat_schedule vacío (el dict real con crontab() solo se evalúa en producción con
celery). Por eso verificamos la declaración en el source, no en runtime.
"""
from __future__ import annotations

import pathlib

import backend.app.core.celery_app as celery_mod

_SRC = pathlib.Path(celery_mod.__file__).read_text(encoding="utf-8")


def test_quarterly_reports_entry_declared():
    assert '"retainer-quarterly-reports":' in _SRC, (
        "falta la entrada del reporte trimestral en beat_schedule (#30)"
    )
    # task correcto + cadencia trimestral (1er día Ene/Abr/Jul/Oct)
    # NOTA: el BEAT-BUG fix cambió los dotted-paths por NOMBRES REGISTRADOS
    # (m23.generate_X) · estos asserts se actualizaron en consecuencia (#37).
    assert '"m23.generate_quarterly_reports"' in _SRC
    assert 'month_of_year="1,4,7,10"' in _SRC


def test_monthly_invoices_entry_still_declared():
    # #31 · el billing mensual sigue declarado (no se rompió al añadir #30)
    assert '"retainer-monthly-invoices":' in _SRC
    assert '"m23.generate_monthly_invoices"' in _SRC


def test_annual_reports_entry_declared():
    # #37 (FRENTE C) · informe ANUAL E-802 declarado en beat (15 enero)
    assert '"retainer-annual-reports":' in _SRC, (
        "falta la entrada del informe anual E-802 en beat_schedule (#37)"
    )
    assert '"m23.generate_annual_reports"' in _SRC
    assert 'day_of_month="15"' in _SRC and 'month_of_year="1"' in _SRC
