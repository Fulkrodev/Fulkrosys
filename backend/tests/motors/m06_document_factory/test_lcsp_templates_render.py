"""Integration tests LCSP templates L-001 + L-003 + L-004 + L-005 · sub-lote 1.B.8.D.

Adyacencia normativa NO-ENS (Ley 9/2017 Contratos del Sector Publico)
para entregables firmados por cliente en procedimientos de licitacion AAPP.

Codigos L-001 (Declaracion Responsable art 140) · L-003 (Compromiso adscripcion
medios art 76.2) · L-004 (Solvencia tecnica arts 89-91) · L-005 (Clausula
confidencialidad art 133). Familia 'deliverables/' (entregables firmados
cliente · no politicas internas). Segregados del rango E-1XX/E-2XX y W-* y
LW-* por clara separacion normativa (AMEND-016 v2 + LECCION-OPS-032).

L-002 (DEUC) se gestiona en sub-lote 1.B.8.E separado.

Reglas duras sostenidas (LECCION-OPS-020 / 021 / 027 / 028 / 030).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx

VAR_TEMPLATES = Path(__file__).resolve().parents[4] / "var" / "templates_docx"
PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")

LCSP_TEMPLATES = ["L-001", "L-002", "L-003", "L-004", "L-005", "L-006", "L-007"]


@pytest.fixture
def lcsp_context() -> dict:
    """Context para render L-001/002/003/004/005 · cliente licitador AAPP.

    Activa ramas:
      - licitacion.exige_ens=True (L-001 sec SEPTIMO · RD 311/2022 + categoria)
      - licitacion.medios_personales + medios_materiales loops (L-003 sec 2+3)
      - licitacion.permite_subcontratacion=True (L-003 sec 7 + L-004 sec 7)
      - cliente.referencias_proyectos + equipo_responsable + certificaciones_vigentes
        + medios_tecnicos_descripcion + subcontratistas_previstos (L-004 todos los loops
        + L-002 Parte IV.C/D loops · keys L-002-specific anadidas backward-compat)
      - contrato.referencia custom (L-005)
      - L-002 PARTE II.D activada (tiene_subcontratistas)

    NOTA: lists usan keys L-004 + keys L-002-specific superpuestos (backward-compat).
    """
    return {
        "cliente": {
            "razon_social": "Test LCSP Integration SL",
            "nif": "B73500000",
            "domicilio": "Calle LCSP Test 5, 28001 Madrid",
            "forma_juridica": "Sociedad Limitada",
            "poblacion": "Madrid",
            "representante": {
                "nombre": "Don Test Representante LCSP",
                "dni": "12345678Z",
                "cargo": "Administrador Unico",
                "tipo_poder": "Poder solidario notarial",
            },
            "email_notificaciones": "licitaciones@test-lcsp-int.example",
            "persona_contacto_licitaciones": {
                "nombre": "Maria Test Licitaciones",
                "telefono": "+34 910 555 100",
            },
            "referencias_proyectos": [
                {
                    "cliente": "Ayuntamiento Demo A",
                    "objeto": "Consultoria ENS BASICA",
                    "descripcion": "Consultoria ENS BASICA",
                    "importe": "25.000",
                    "fecha_inicio": "2025-01",
                    "fecha_fin": "2025-06",
                    "fecha": "2025-06",
                },
                {
                    "cliente": "Diputacion Demo B",
                    "objeto": "Auditoria interna SGSI",
                    "descripcion": "Auditoria interna SGSI",
                    "importe": "18.500",
                    "fecha_inicio": "2025-03",
                    "fecha_fin": "2025-09",
                    "fecha": "2025-09",
                },
            ],
            "equipo_responsable": [
                {
                    "perfil": "Director Proyecto Senior",
                    "nombre": "Marcos Demo",
                    "cargo": "Director Proyecto Senior",
                    "titulaciones": "Ing. Telecom + MBA",
                    "certificaciones": "CISA + CISM + ISO 27001 LA",
                    "experiencia_descripcion": "12 anios consultoria ENS + AAPP",
                    "anios": "12",
                },
            ],
            "certificaciones_vigentes": [
                {
                    "nombre": "ISO/IEC 27001",
                    "norma": "ISO/IEC 27001",
                    "alcance": "Servicios consultoria seguridad",
                    "entidad": "AENOR",
                    "vigencia": "2027-12",
                },
                {
                    "nombre": "Esquema Nacional Seguridad",
                    "norma": "Esquema Nacional Seguridad",
                    "alcance": "Servicios profesionales AAPP",
                    "entidad": "AENOR",
                    "vigencia": "2027-06",
                },
            ],
            "medios_tecnicos_descripcion": (
                "Plataforma Fulkro SaaS + MinIO WORM 7 anios + Caddy + pgAudit"
            ),
            "subcontratistas_previstos": [
                {
                    "nombre": "Auditor Externo Demo S.L.",
                    "razon_social": "Auditor Externo Demo S.L.",
                    "prestacion": "Pentesting + Red Team",
                    "actividad": "Pentesting + Red Team",
                    "importe": "5.000",
                    "porcentaje": "10",
                },
            ],
        },
        "proyecto": {
            "version_actual": "1.0",
            "fecha_aprobacion_inicial": "2026-05-18",
        },
        "licitacion": {
            "numero_expediente": "EXP-2026-LCSP-001",
            "organo_contratante": "Ayuntamiento de Madrid",
            "objeto": "Servicios de consultoria ENS",
            "exige_ens": True,
            "categoria_ens": "MEDIA",
            "anios_referencia": 3,
            "permite_subcontratacion": True,
            "medios_personales": [
                {
                    "perfil": "Director Proyecto",
                    "cualificacion": "Ing. Telecom + CISM",
                    "experiencia": "10 anios",
                    "dedicacion": "20%",
                },
                {
                    "perfil": "Consultor Senior ENS",
                    "cualificacion": "CISA + ISO 27001 LA",
                    "experiencia": "5 anios",
                    "dedicacion": "50%",
                },
            ],
            "medios_materiales": [
                "Plataforma SaaS Fulkro v1.0",
                "Repositorio MinIO con cifrado WORM",
            ],
            "lugar_firma": "Madrid",
            "fecha_firma": "2026-05-18",
        },
        "contrato": {
            "referencia": "CT-2026-LCSP-001-AYUN-MADRID",
            "objeto": "Servicios consultoria ENS",
            "poder_adjudicador": "Ayuntamiento de Madrid",
            "tipo_procedimiento": "Abierto SARA",
            "referencia_doue": "2026/S 100-123456",
            "referencia_pcsp": "PCSP-2026-001",
        },
        "subrogacion": {
            "aplica": True,
            "convenio_colectivo_aplicable": (
                "Convenio Colectivo Empresas Consultoria TIC · BOE 04/04/2024"
            ),
            "organo_facilitador_info": (
                "Direccion Recursos Humanos del organo contratante"
            ),
            "fecha_info_recibida": "2026-02-15",
            "centro_trabajo_destino": "Madrid · Sede principal cliente",
            "personal_subrogable": [
                {
                    "puesto": "Tecnico de Sistemas Senior",
                    "antiguedad_anios": 7,
                    "tipo_contrato": "Indefinido tiempo completo",
                    "jornada_anual_horas": 1750,
                    "retribucion_bruta_anual": "38.500 EUR",
                    "complementos": "Plus disponibilidad + plus nocturnidad ocasional",
                    "convenio_categoria": "Grupo 2 · Nivel 3",
                },
                {
                    "puesto": "Analista Funcional",
                    "antiguedad_anios": 4,
                    "tipo_contrato": "Indefinido tiempo completo",
                    "jornada_anual_horas": 1750,
                    "retribucion_bruta_anual": "32.000 EUR",
                    "complementos": "—",
                    "convenio_categoria": "Grupo 2 · Nivel 4",
                },
            ],
        },
    }


@pytest.mark.parametrize("codigo", LCSP_TEMPLATES)
def test_lcsp_template_renders_without_placeholder_leak(
    codigo, tmp_path, lcsp_context,
):
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_test.docx"
    render_docx(template_path, lcsp_context, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 5000, (
        f"{codigo} DOCX too small ({output_path.stat().st_size} bytes)"
    )

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    leaks = PLACEHOLDER_PATTERN.findall(text)
    assert len(leaks) == 0, f"{codigo} has placeholder leaks: {leaks[:5]}"
    # cliente.razon_social presente · validacion anchor comun
    assert "Test LCSP Integration SL" in text, (
        f"{codigo} missing cliente.razon_social"
    )


def test_l001_renders_art140_lcsp_nine_apartados_and_ens_branch(
    tmp_path, lcsp_context,
):
    """L-001 con licitacion.exige_ens=True debe activar branch ENS RD 311/2022
    + categoria MEDIA. Validacion ademas: 9 apartados declaracion + Ley 9/2017
    + arts 65/71/84/86-91/140 + expediente + representante + notificaciones."""
    template_path = VAR_TEMPLATES / "L-001.docx"
    output_path = tmp_path / "L-001_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "Ley 9/2017" in text, "L-001 falta Ley 9/2017"
    assert "140" in text, "L-001 falta art 140 LCSP"
    # 9 apartados declaracion (PRIMERO-NOVENO)
    apartados = ["PRIMERO", "SEGUNDO", "TERCERO", "CUARTO",
                 "QUINTO", "SEXTO", "SÉPTIMO", "OCTAVO", "NOVENO"]
    for apt in apartados:
        assert apt in text, f"L-001 falta apartado declaracion: {apt}"
    # Arts LCSP citados
    arts_citados = ["65", "71", "84", "150.2"]
    for art in arts_citados:
        assert art in text, f"L-001 falta cita art LCSP: {art}"
    # Branch exige_ens=True activado
    assert "311/2022" in text, "L-001 falta RD 311/2022 (branch exige_ens=True)"
    assert "MEDIA" in text, "L-001 falta categoria_ens MEDIA"
    # NO branch generico (medidas adecuadas) cuando exige_ens=True
    assert "medidas técnicas y organizativas adecuadas" not in text, (
        "L-001 NO debe contener branch else cuando exige_ens=True"
    )
    # Representante + expediente + objeto
    assert "Test Representante LCSP" in text, "L-001 falta representante"
    assert "12345678Z" in text, "L-001 falta DNI representante"
    assert "EXP-2026-LCSP-001" in text, "L-001 falta expediente"
    assert "Servicios de consultoria ENS" in text, "L-001 falta objeto contrato"
    # Notificaciones
    assert "licitaciones@test-lcsp-int.example" in text, "L-001 falta email notif"


def test_l003_renders_art762_lcsp_medios_loops_and_subcontratacion_branch(
    tmp_path, lcsp_context,
):
    """L-003 con licitacion.medios_personales + medios_materiales debe activar
    branches loop (no else placeholder). Validacion ademas: art 76.2 LCSP +
    caracter esencial + branch permite_subcontratacion=True."""
    template_path = VAR_TEMPLATES / "L-003.docx"
    output_path = tmp_path / "L-003_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "76.2" in text, "L-003 falta art 76.2 LCSP"
    assert "Ley 9/2017" in text, "L-003 falta Ley 9/2017"
    # Caracter esencial obligacion
    assert "carácter esencial" in text or "esencial" in text, (
        "L-003 falta caracter esencial obligacion"
    )
    # Branch medios_personales loop (2 entries renderizados)
    assert "Director Proyecto" in text, "L-003 falta perfil 1 medios_personales"
    assert "Consultor Senior ENS" in text, "L-003 falta perfil 2 medios_personales"
    assert "CISM" in text, "L-003 falta cualificacion perfil 1"
    # NO else placeholder cuando medios_personales presente
    assert "[Director de proyecto]" not in text, (
        "L-003 NO debe contener else placeholder medios_personales"
    )
    # Branch medios_materiales loop
    assert "Plataforma SaaS Fulkro" in text, "L-003 falta medios_materiales 1"
    assert "MinIO" in text, "L-003 falta medios_materiales 2"
    # Branch permite_subcontratacion=True
    assert "podrá subcontratar prestaciones accesorias" in text, (
        "L-003 falta branch subcontratacion=True"
    )
    assert "asumirá íntegramente la ejecución del contrato sin recurrir" not in text, (
        "L-003 NO debe contener branch else cuando subcontratacion=True"
    )
    # Sustituciones (perfil equivalente o superior)
    assert "equivalente o superior" in text, "L-003 falta criterio sustituciones"


def test_l004_renders_arts89_91_lcsp_all_loops_and_subcontratistas(
    tmp_path, lcsp_context,
):
    """L-004 con todas las ramas activas: referencias_proyectos +
    equipo_responsable + certificaciones_vigentes + medios_tecnicos_descripcion
    + subcontratistas_previstos AND permite_subcontratacion=True."""
    template_path = VAR_TEMPLATES / "L-004.docx"
    output_path = tmp_path / "L-004_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo arts 89-91 LCSP
    assert "89 a 91" in text, "L-004 falta arts 89-91 LCSP"
    # Arts subsidiarios citados
    arts_sub = ["90.1.a", "90.1.d", "90.1.e", "93", "150.2"]
    for art in arts_sub:
        assert art in text, f"L-004 falta cita art LCSP: {art}"
    # Branch anios_referencia=3 (no default 5)
    assert "3 años" in text or "últimos 3" in text, (
        "L-004 falta anios_referencia=3 custom"
    )
    # Branch referencias_proyectos loop (2 entries)
    assert "Ayuntamiento Demo A" in text, "L-004 falta referencia proyecto 1"
    assert "Diputacion Demo B" in text, "L-004 falta referencia proyecto 2"
    assert "Consultoria ENS BASICA" in text, "L-004 falta objeto proyecto 1"
    # Branch equipo_responsable loop
    assert "Director Proyecto Senior" in text, "L-004 falta equipo perfil"
    assert "ISO 27001 LA" in text, "L-004 falta certificacion equipo"
    # Branch certificaciones_vigentes loop (2 entries)
    assert "ISO/IEC 27001" in text, "L-004 falta certificacion 1"
    assert "Esquema Nacional Seguridad" in text, "L-004 falta certificacion 2"
    assert "AENOR" in text, "L-004 falta entidad certificadora"
    # Branch medios_tecnicos_descripcion custom (no else lista)
    assert "Plataforma Fulkro SaaS" in text, "L-004 falta medios_tecnicos custom"
    assert "WORM 7 anios" in text, "L-004 falta detalle medios_tecnicos"
    # Branch permite_subcontratacion=True AND subcontratistas_previstos
    assert "Auditor Externo Demo S.L." in text, "L-004 falta subcontratista 1"
    assert "Pentesting + Red Team" in text, "L-004 falta prestacion subcontratista"
    # NO else generico subcontratistas cuando ambas ramas presentes
    assert "no prevé recurrir a subcontratación" not in text, (
        "L-004 NO debe contener else subcontratistas cuando ambas ramas presentes"
    )


def test_l005_renders_art133_lcsp_duration_sanctions_and_contrato_ref(
    tmp_path, lcsp_context,
):
    """L-005 con contrato.referencia custom debe renderizar 9 apartados clausula
    + duracion 5 anios art 133.2 + sanciones (arts 211 + 71 LCSP + Ministerio
    Fiscal) + plazo 30 dias destruccion."""
    template_path = VAR_TEMPLATES / "L-005.docx"
    output_path = tmp_path / "L-005_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "133" in text, "L-005 falta art 133 LCSP"
    assert "Ley 9/2017" in text, "L-005 falta Ley 9/2017"
    # contrato.referencia custom renderizado
    assert "CT-2026-LCSP-001-AYUN-MADRID" in text, (
        "L-005 falta contrato.referencia custom"
    )
    # organo_contratante presente
    assert "Ayuntamiento de Madrid" in text, "L-005 falta organo contratante"
    # 5 categorias info confidencial (apartado 1 a-e)
    cats_info = [
        "vulnerabilidades", "credenciales",
        "RGPD", "LOPDGDD",
    ]
    for cat in cats_info:
        assert cat in text, f"L-005 falta categoria info confidencial: {cat}"
    # Duracion 5 anios art 133.2
    assert "cinco (5) años" in text, "L-005 falta duracion 5 anios"
    assert "133.2" in text, "L-005 falta art 133.2 LCSP"
    # Plazo destruccion 30 dias naturales
    assert "treinta (30) días naturales" in text, "L-005 falta plazo 30 dias"
    # Sanciones incumplimiento (arts 211 + 71 + Ministerio Fiscal)
    assert "211" in text, "L-005 falta art 211 LCSP resolucion"
    assert "71" in text, "L-005 falta art 71 LCSP prohibicion contratar"
    assert "Ministerio Fiscal" in text, "L-005 falta Ministerio Fiscal"
    # Incumplimiento esencial
    assert "incumplimiento esencial" in text, "L-005 falta incumplimiento esencial"


def test_l002_renders_deuc_six_parts_and_visor_guide_branch(
    tmp_path, lcsp_context,
):
    """L-002 DEUC declarativo equivalente · estructura espejo formulario oficial:
      - 6 marcadores PARTE I a PARTE VI (espejo Reglamento UE 2016/7)
      - Seccion 9 GUIA cumplimentacion visor eDEUC + URL oficial
      - Reglamento (UE) 2016/7 + Directiva 2014/24/UE + LCSP arts 140-141
      - Branch licit.exige_ens=True · RD 311/2022 + categoria_ens (MEDIA)
      - Branch tiene_subcontratistas (cliente.subcontratistas_previstos non-empty)
        · activa Apartado II.D + "prevé subcontratar".

    Post-fix 1.B.8.G BLOQUE 4b · L-002 IV.C loops reformateados a patron L-003
    (`{% for %}` en linea aparte) · ya NO requiere fixture single-entry
    workaround · lcsp_context multi-entry renderiza integro.
    """
    template_path = VAR_TEMPLATES / "L-002.docx"
    output_path = tmp_path / "L-002_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # 6 marcadores PARTE I a PARTE VI (espejo formulario UE)
    partes = ["PARTE I", "PARTE II", "PARTE III", "PARTE IV", "PARTE V", "PARTE VI"]
    for parte in partes:
        assert parte in text, f"L-002 falta marcador estructural: {parte}"

    # Seccion 9 GUIA cumplimentacion visor eDEUC
    assert "GUÍA DE CUMPLIMENTACIÓN DEL VISOR" in text, (
        "L-002 falta titulo seccion 9 guia visor"
    )
    # URL visor oficial
    assert "visor.registrodelicitadores.gob.es" in text, (
        "L-002 falta URL visor eDEUC oficial"
    )
    # Marco normativo core
    assert "Reglamento de Ejecución (UE) 2016/7" in text or "2016/7" in text, (
        "L-002 falta Reglamento UE 2016/7"
    )
    assert "Directiva 2014/24/UE" in text, "L-002 falta Directiva 2014/24/UE"
    assert "Ley 9/2017" in text, "L-002 falta LCSP 9/2017"
    assert "140" in text and "141" in text, (
        "L-002 falta arts 140-141 LCSP"
    )
    # eForms 2024 + Orden HFP/1499/2021 (norma tecnica)
    assert "eForms 2024" in text, "L-002 falta eForms 2024"
    assert "HFP/1499/2021" in text, "L-002 falta Orden HFP/1499/2021"

    # Branch licit.exige_ens=True · ENS + RD 311/2022 + categoria
    assert "Esquema Nacional de Seguridad" in text or "ENS" in text, (
        "L-002 falta ENS"
    )
    assert "311/2022" in text or "RD 311/2022" in text, (
        "L-002 falta RD 311/2022 (branch exige_ens=True)"
    )
    assert "MEDIA" in text, "L-002 falta categoria_ens MEDIA"
    # NO branch else cuando exige_ens=True
    assert "Apartados ENS no aplicables" not in text, (
        "L-002 NO debe contener else ENS cuando exige_ens=True"
    )
    assert "No procede declaración específica adicional ENS" not in text, (
        "L-002 NO debe contener else ENS cuando exige_ens=True"
    )

    # Branch tiene_subcontratistas (Apartado II.D activada)
    assert "II.D" in text, "L-002 falta apartado II.D subcontratistas"
    assert "prevé subcontratar" in text, (
        "L-002 falta branch subcontratistas non-empty (prevé subcontratar)"
    )
    assert "Auditor Externo Demo S.L." in text, (
        "L-002 falta razon_social subcontratista loop"
    )
    # NO else branch cuando tiene_subcontratistas True
    assert "no prever la subcontratación" not in text, (
        "L-002 NO debe contener else cuando tiene_subcontratistas=True"
    )

    # Partes integrales formulario DEUC
    apartados = ["II.A", "II.B", "II.C", "III.A", "III.B", "III.C", "III.D",
                 "IV.A", "IV.B", "IV.C", "IV.D"]
    for apt in apartados:
        assert apt in text, f"L-002 falta apartado DEUC: {apt}"

    # Cliente core + representante
    assert "Test LCSP Integration SL" in text, "L-002 falta razon_social"
    assert "B73500000" in text, "L-002 falta NIF"
    assert "Don Test Representante LCSP" in text, "L-002 falta representante"
    assert "CT-2026-LCSP-001-AYUN-MADRID" in text, "L-002 falta contrato.referencia"

    # Naturaleza anexo (no sustituye)
    assert "complementa al DEUC oficial" in text or "complementa" in text, (
        "L-002 falta naturaleza anexo complementa"
    )
    assert "No sustituye al DEUC oficial" in text or "NO sustituye" in text.upper() or "no sustituye" in text.lower(), (
        "L-002 falta clausula no sustituye DEUC oficial"
    )


def test_l002_renders_multi_entry_no_truncation_after_fix(tmp_path, lcsp_context):
    """L-002 IV.C post-fix 1.B.8.G BLOQUE 4b · loops multi-entry sin truncamiento.

    Antes del fix: {% for %} concatenado con fila |...| en misma linea provocaba
    pandoc DOCX truncamiento tras IV.C (perdida PARTE V/VI/sec 9).
    Despues del fix: {% for %} en linea aparte (patron L-003) renderiza
    multi-entry integro · firma final + checklist visor + reservas
    presentes despues de todos los loops.

    Validacion CRITICA: con lcsp_context (2 referencias_proyectos + 1 equipo
    + 2 certificaciones + 1 subcontratista) el render debe contener:
      - Ambas referencias_proyectos (Ayuntamiento Demo A + Diputacion Demo B)
      - Ambas certificaciones_vigentes (ISO/IEC 27001 + ENS)
      - PARTE V + PARTE VI marcadores
      - Seccion 9 GUIA visor URL
      - Checklist 10 puntos
      - Firma final
    """
    template_path = VAR_TEMPLATES / "L-002.docx"
    output_path = tmp_path / "L-002_multi_entry.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Multi-entry referencias_proyectos (ambos)
    assert "Ayuntamiento Demo A" in text, "L-002 falta referencia 1 (multi-entry)"
    assert "Diputacion Demo B" in text, "L-002 falta referencia 2 (multi-entry · bug L-002 IV.C)"
    # Multi-entry certificaciones_vigentes (ambas)
    assert "ISO/IEC 27001" in text, "L-002 falta certificacion 1 (multi-entry)"
    assert "Esquema Nacional Seguridad" in text, "L-002 falta certificacion 2 (multi-entry · bug L-002 IV.C)"
    # CRITICO · PARTE V + VI presentes despues de loops IV.C
    assert "PARTE V" in text, (
        "L-002 PARTE V truncado (FIX 1.B.8.G BLOQUE 4b NO aplicado correctamente)"
    )
    assert "PARTE VI" in text, "L-002 PARTE VI truncado"
    # CRITICO · seccion 9 guia visor presente
    assert "visor.registrodelicitadores.gob.es" in text, (
        "L-002 sec 9 guia visor truncado (FIX 1.B.8.G BLOQUE 4b NO aplicado)"
    )
    # Checklist 10 puntos verificacion presente despues seccion 9
    assert "Certificado electrónico del representante legal" in text, (
        "L-002 checklist truncado"
    )
    # Firma final presente DESPUES de todos los loops + secciones
    assert "Firmado en" in text, "L-002 firma final truncada"


def test_l006_renders_art130_lcsp_compromise_and_responsabilidad_branch(
    tmp_path, lcsp_context,
):
    """L-006 Compromiso Subrogacion Art. 130 LCSP · validacion ramas activas:
      - subrogacion.convenio_colectivo_aplicable custom renderizado
      - subrogacion.organo_facilitador_info renderizado en secciones 3/4/7
      - Marco normativo: LCSP 9/2017 art 130 + ET art 44
      - Garantias laborales (5 obligaciones) + caracter declarativo
      - Limitacion responsabilidad art 130.6 LCSP (info incompleta no imputable)
      - Referencia documento anexo L-007.
    """
    template_path = VAR_TEMPLATES / "L-006.docx"
    output_path = tmp_path / "L-006_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "Art. 130" in text or "artículo 130" in text or "artículo 130" in text, (
        "L-006 falta art 130 LCSP"
    )
    assert "Ley 9/2017" in text, "L-006 falta LCSP 9/2017"
    assert "Estatuto de los Trabajadores" in text, "L-006 falta ET referencia"
    assert "artículo 44" in text or "art. 44" in text or "Art. 44" in text, (
        "L-006 falta ET art 44 sucesion empresa"
    )
    # Convenio colectivo custom presente
    assert "Convenio Colectivo Empresas Consultoria TIC" in text, (
        "L-006 falta convenio_colectivo_aplicable custom"
    )
    assert "BOE 04/04/2024" in text, "L-006 falta fecha BOE convenio"
    # organo_facilitador_info custom
    assert "Direccion Recursos Humanos" in text, (
        "L-006 falta organo_facilitador_info custom"
    )
    # Compromiso formal core
    assert "subrogarse" in text.lower(), "L-006 falta verbo subrogarse"
    assert "Licitador" in text, "L-006 falta Licitador"
    # 5 garantias laborales (secciones 5.a-e)
    garantias = [
        "Respetar íntegramente las condiciones laborales",
        "No introducir modificaciones sustanciales",
        "Cumplir las obligaciones de información",
        "Asumir las obligaciones laborales",
        "Mantener al personal afectado",
    ]
    for g in garantias:
        assert g in text, f"L-006 falta garantia laboral: {g[:50]}"
    # Limitacion art 130.6 LCSP (info incompleta no imputable)
    assert "130.6" in text or "apartado 6" in text, (
        "L-006 falta limitacion art 130.6 LCSP"
    )
    assert "no podrá imputarse" in text or "no podra imputarse" in text.lower(), (
        "L-006 falta clausula no imputable"
    )
    # Referencia documento anexo L-007
    assert "L-007" in text, "L-006 falta referencia anexo L-007"
    # Cliente + representante + contrato
    assert "Test LCSP Integration SL" in text, "L-006 falta razon_social"
    assert "B73500000" in text, "L-006 falta NIF"
    assert "CT-2026-LCSP-001-AYUN-MADRID" in text, "L-006 falta contrato.referencia"
    assert "Madrid · Sede principal cliente" in text, "L-006 falta centro_trabajo"


def test_l007_renders_listado_multi_entry_no_truncation(
    tmp_path, lcsp_context,
):
    """L-007 Anexo subrogacion · validacion CRITICA multi-entry loop NO trunca
    (leccion aprendida bug L-002 IV.C · patron L-003 loop linea aparte aplicado):

      - 2 empleados renderizan ambos integros (Tecnico Sistemas Senior + Analista
        Funcional · puesto/antiguedad/retribucion/categoria)
      - Marco normativo: LCSP 130.3 + ET 44 + Convenio + RGPD
      - Seccion 5 Verificacion + plazo 15 dias habiles discrepancias
      - Seccion 6 RGPD tabla 6 conceptos (responsable/base/finalidad/categorias/
        conservacion/cesiones)
      - Seccion 7 Declaracion final
      - Referencia documento madre L-006
      - Multi-entry verificado: PARTE final + firma renderizados despues del loop
        (vs bug L-002 IV.C que truncaba).
    """
    template_path = VAR_TEMPLATES / "L-007.docx"
    output_path = tmp_path / "L-007_semantic.docx"
    render_docx(template_path, lcsp_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # CRITICO · multi-entry loop renderiza ambos empleados
    assert "Tecnico de Sistemas Senior" in text, (
        "L-007 falta empleado 1 (Tecnico Sistemas Senior)"
    )
    assert "Analista Funcional" in text, (
        "L-007 falta empleado 2 (Analista Funcional)"
    )
    # Antiguedades + retribuciones de ambos
    assert "7 años" in text or "7 anios" in text, "L-007 falta antiguedad emp1"
    assert "4 años" in text or "4 anios" in text, "L-007 falta antiguedad emp2"
    assert "38.500" in text, "L-007 falta retribucion emp1"
    assert "32.000" in text, "L-007 falta retribucion emp2"
    assert "Grupo 2" in text, "L-007 falta categoria convenio"

    # CRITICO · seccion 7 firma debe estar DESPUES del loop (no truncamiento)
    assert "DECLARACIÓN FINAL" in text or "DECLARACION FINAL" in text, (
        "L-007 NO renderiza seccion 7 (posible truncamiento multi-entry · bug L-002)"
    )
    # Tras seccion 7 viene firma
    assert "Firmado en" in text, "L-007 falta firma (posible truncamiento)"

    # Marco normativo
    assert "Ley 9/2017" in text, "L-007 falta LCSP 9/2017"
    assert "130" in text, "L-007 falta art 130 LCSP"
    assert "Estatuto de los Trabajadores" in text, "L-007 falta ET referencia"
    assert "RGPD" in text, "L-007 falta RGPD"
    assert "LOPDGDD" in text, "L-007 falta LOPDGDD"

    # Convenio custom
    assert "Convenio Colectivo Empresas Consultoria TIC" in text, (
        "L-007 falta convenio_colectivo_aplicable custom"
    )

    # Numero personal renderizado
    assert "2" in text, "L-007 falta num_personal (2)"

    # Seccion 5 verificacion 15 dias habiles
    assert "quince (15) días hábiles" in text or "15) días hábiles" in text, (
        "L-007 falta plazo 15 dias habiles discrepancias"
    )

    # Seccion 6 RGPD - 6 conceptos tabla
    rgpd_concepts = ["Responsable del tratamiento", "Base jurídica", "Finalidad",
                     "Categorías de datos", "Plazo de conservación", "Cesiones"]
    for concept in rgpd_concepts:
        assert concept in text, f"L-007 falta concepto RGPD: {concept}"

    # Referencia documento madre L-006
    assert "L-006" in text, "L-007 falta referencia documento madre L-006"

    # Cliente core
    assert "Test LCSP Integration SL" in text, "L-007 falta razon_social"
    assert "B73500000" in text, "L-007 falta NIF"
    assert "CT-2026-LCSP-001-AYUN-MADRID" in text, "L-007 falta contrato.referencia"
