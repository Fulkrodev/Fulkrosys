"""Lo que una pantalla exige, alguien lo tiene que poder producir.

TRES HUECOS DE LA MISMA FORMA
    No eran fallos de backend: el endpoint existía y funcionaba en los tres
    casos. Lo que faltaba era quien lo llamara, de modo que la pantalla pedía
    algo que ella misma no podía arrancar.

    1. ``/plan`` mostraba un Gantt vacío y ninguna acción para generar el plan.
       RESUELTO antes de este bloque: ``PdaGeneratorButton`` ya está montado en
       la página. Aquí sólo se congela para que no se vuelva a caer.
    2. ``/dossier`` era de sólo lectura y no ofrecía crear el
       ``AuditPreparationRun`` que la propia página necesita para mostrar algo.
       El endpoint ``POST /audit-prep/projects/{id}/runs`` existía y no lo
       llamaba nadie — y además exigía una ``categoria`` que la base ya tiene,
       lo que es invitar a la interfaz a inventarla.
    3. **E-808**, la Autoevaluación CCN-STIC 808, obligatoria para cerrar
       BÁSICA: tenía plantilla en el catálogo, tenía un gate de cierre que la
       exige (``conformity_service_paso5._validar_autoevaluacion_808``) y
       **ningún productor**. El docstring de ese gate afirmaba que «el generador
       del E-808 ya existe»; lo que existe es un informe DOCX de M10 que no
       registra fila en ``documents`` ni lleva código E-808, que es justo lo que
       el gate comprueba.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]


def test_la_pantalla_del_plan_ofrece_generarlo():
    pagina = (RAIZ / "frontend" / "app" / "(admin)" / "admin" / "projects"
              / "[id]" / "plan" / "page.tsx").read_text(encoding="utf-8")
    assert "PdaGeneratorButton" in pagina, (
        "/plan vuelve a ser un Gantt sin forma de generar el plan"
    )


def test_la_pantalla_del_dossier_ofrece_arrancar_la_preparacion():
    comp = (RAIZ / "frontend" / "components" / "project"
            / "DossierPreview.tsx").read_text(encoding="utf-8")
    assert "auditPrepApi.createRun" in comp, (
        "/dossier vuelve a ser de sólo lectura sobre una lista que nadie puede "
        "llenar desde la propia pantalla"
    )
    cliente = (RAIZ / "frontend" / "lib" / "api"
               / "audit-prep.ts").read_text(encoding="utf-8")
    assert "createRun" in cliente and 'method: "POST"' in cliente


def test_crear_el_run_no_le_pide_la_categoria_a_la_interfaz():
    """La categoría la sabe el proyecto; pedírsela a la pantalla la invita a inventarla."""
    api = (RAIZ / "backend" / "app" / "motors" / "m09_audit_prep"
           / "api.py").read_text(encoding="utf-8")
    assert "categoria: str | None = Field(default=None" in api, (
        "CreateRunBody vuelve a exigir la categoría"
    )
    assert "_categoria_del_proyecto" in api


def test_el_e808_tiene_productor():
    """El gate de cierre BÁSICA exige un documento E-808: alguien lo emite."""
    servicio = (RAIZ / "backend" / "app" / "motors" / "m03_dda"
                / "service.py").read_text(encoding="utf-8")
    assert 'template_codigo="E-808"' in servicio, (
        "nadie emite la Autoevaluación CCN-STIC 808 y el cierre de BÁSICA la "
        "exige: el proyecto no puede completarse"
    )
    # Y se emite por la fábrica documental, que es la que registra en
    # `documents` — que es exactamente lo que el gate comprueba.
    assert "DocumentFactoryService" in servicio


def test_el_gate_de_cierre_ya_no_afirma_que_el_generador_existe_en_otro_sitio():
    gate = (RAIZ / "backend" / "app" / "motors" / "m27_conformity"
            / "conformity_service_paso5.py").read_text(encoding="utf-8")
    assert "El generador del E-808 ya\n        existe (M10 Audit-Sim" not in gate, (
        "el gate sigue mandando a un generador que no produce un documento "
        "E-808 registrado"
    )
