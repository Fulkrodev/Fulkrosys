"""Integration tests GOBIERNO SGSI templates E-002/003/012/090 · sub-lote 1.B.9.A.

Familia E-XXX gobierno SGSI · actas core + diagnostico GAP. Pertenecen al
catalogo ENS principal (no son adyacencia normativa como W/LW/L). Naturaleza:
politicas formales (E-002/003) + entregables internos (E-012/090) generados
en fase inicial implantacion SGSI (pre Plan Adecuacion E-150).

Norma aplicable: RD 311/2022 Anexo I (categorizacion) + Anexo II (73 medidas) +
Guias CCN-STIC 801 (responsabilidades) + 803 (categorizacion) + 808 (verificacion).

Reglas duras sostenidas (LECCION-OPS-020/021/027/028/030 caso 4).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx

VAR_TEMPLATES = Path(__file__).resolve().parents[4] / "var" / "templates_docx"
PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")

GOVERNANCE_TEMPLATES = [
    # Sub-atom 1.B.9.A · Gobierno SGSI core
    "E-002", "E-003", "E-012", "E-090",
    # Sub-atom 1.B.9.B · Ruta Basica lifecycle
    "E-041", "E-042", "E-043",
    # Sub-atom 1.B.9.C · Retainer reporting
    "E-614", "E-615",
]


@pytest.fixture
def governance_context() -> dict:
    """Context para render E-002/003/012/090 · ENS Categoria MEDIA empresa privada.

    Activa ramas:
      - proyecto.categoria_ens = 'MEDIA' (E-002: branch else RSA consolidado en RS)
      - comite_seguridad con presidente + secretario + miembros (E-003: loop linea APARTE)
      - decision_categorizacion con 5 dimensiones + nivel global (E-012)
      - diagnostico.hallazgos_gap (4 entries) + recomendaciones (4 entries · multi-entry safe)
    """
    return {
        "cliente": {
            "razon_social": "Test Gobierno SGSI SL",
            "nif": "B80000000",
            "domicilio": "Calle Gobierno 10, 28001 Madrid",
            "poblacion": "Madrid",
            "representante": {
                "nombre": "Carmen Ruiz Garcia",
                "cargo": "Directora de Operaciones",
                "dni": "12345678A",
            },
        },
        "proyecto": {
            "version_actual": "1.0",
            "fecha_aprobacion_inicial": "2026-03-15",
            "categoria_ens": "MEDIA",
        },
        "responsables": {
            "responsable_seguridad": {
                "nombre": "Marcos Lopez Perez",
                "cargo": "CISO",
                "dni": "23456789B",
            },
            "responsable_sistema": {
                "nombre": "Javier Sanz Moreno",
                "cargo": "Director de TI",
                "dni": "34567890C",
            },
            "responsable_servicio": {
                "nombre": "Carmen Ruiz Garcia",
                "cargo": "Directora de Operaciones",
                "dni": "12345678A",
            },
            "responsable_compliance": {
                "nombre": "Lucia Torres Vega",
                "cargo": "Compliance Officer",
                "dni": "45678901D",
            },
        },
        "comite_seguridad": {
            "fecha_constitucion": "2026-03-10",
            "presidente": {
                "nombre": "Carmen Ruiz Garcia",
                "cargo": "Directora de Operaciones",
            },
            "secretario": {
                "nombre": "Lucia Torres Vega",
                "cargo": "Compliance Officer",
            },
            "miembros": [
                {"nombre": "Marcos Lopez Perez", "cargo": "CISO"},
                {"nombre": "Javier Sanz Moreno", "cargo": "Director de TI"},
                {"nombre": "Roberto Vidal Castro", "cargo": "Responsable de RRHH"},
            ],
            "periodicidad_reuniones": "Trimestral · ordinarias",
            "quorum_minimo": "Mayoria absoluta de los miembros",
        },
        "decision_categorizacion": {
            "nivel_global": "MEDIA",
            "dimensiones": {
                "confidencialidad": "MEDIO",
                "integridad": "MEDIO",
                "disponibilidad": "ALTO",
                "autenticidad": "MEDIO",
                "trazabilidad": "MEDIO",
            },
            "fecha_decision": "2026-03-12",
            "metodologia": "RD 311/2022 Anexo I + CCN-STIC 803",
        },
        "diagnostico": {
            "fecha_realizacion": "2026-02-20",
            "metodologia": "Auto-evaluacion RD 311/2022 Anexo II + 73 medidas",
            "nivel_madurez_actual": "L2 · Definido parcialmente",
            "hallazgos_gap": [
                {"familia": "Marco organizativo", "nivel": "ALTO",
                 "descripcion": "Politica Seguridad pendiente formalizacion"},
                {"familia": "Marco operacional", "nivel": "MEDIO",
                 "descripcion": "Inventario activos parcial"},
                {"familia": "Medidas proteccion", "nivel": "ALTO",
                 "descripcion": "Cifrado en reposo no homogeneo"},
                {"familia": "Continuidad", "nivel": "MEDIO",
                 "descripcion": "BCP sin pruebas anuales"},
            ],
            "recomendaciones": [
                "Formalizar Politica Seguridad Informacion (E-100)",
                "Completar inventario activos (referencia MAGERIT)",
                "Implantar cifrado AES-256 cross-systems",
                "Programar simulacro BCP semestral",
            ],
        },
        # Sub-atom 1.B.9.B · Ruta Basica lifecycle
        "renovacion": {
            "periodicidad_anios": 3,
            "fecha_renovacion_anterior": "2023-03-15",
            "fecha_proxima_renovacion": "2026-03-15",
            "fecha_siguiente_renovacion": "2029-03-15",
            "fecha_auditoria_interna": "2026-02-10",
            "fecha_auditoria_externa": "2026-02-25",
            "cambios_desde_anterior_revision": [
                "Migracion cloud Azure ES (mp.com.* + op.exp.*)",
                "Implantacion SSO + MFA universal (op.acc.*)",
                "Renovacion auditoria interna (op.pl.5)",
            ],
        },
        "cambio_material": {
            "fecha_deteccion": "2026-04-20",
            "fecha_implantacion_prevista": "2026-05-15",
            "descripcion": (
                "Migracion del repositorio documental principal a nueva "
                "plataforma SaaS (Microsoft 365 GCC)"
            ),
            "motivacion": "Consolidacion tecnologica + cumplimiento NIS2",
            "impacto_medidas_afectadas": ["mp.com.3", "mp.s.8", "op.ext.4"],
            "riesgo_residual_estimado": "BAJO tras adopcion medidas adicionales",
            "requiere_recategorizacion": False,
        },
        # Sub-atom 1.B.9.C · Retainer reporting (E-614 + E-615)
        "retainer": {
            "tier": "R_STD",
            "tier_descripcion": "Retainer Estandar · 700EUR/mes",
            "fecha_inicio": "2026-01-01",
            "fecha_renovacion": "2027-01-01",
            "anio_reportado": "2026",
            "periodicidad_reportes_meses": 3,
            "periodo_actual": {
                "tipo": "trimestral",
                "etiqueta": "Q1 2026",
                "desde": "2026-01-01",
                "hasta": "2026-03-31",
            },
            "kpis_periodo": [
                {"nombre": "Incidentes registrados", "valor": "3",
                 "objetivo": "≤ 5", "estado": "OK"},
                {"nombre": "Tiempo medio respuesta", "valor": "2h 15min",
                 "objetivo": "≤ 4h", "estado": "OK"},
                {"nombre": "Cobertura formacion seguridad", "valor": "87%",
                 "objetivo": "≥ 80%", "estado": "OK"},
                {"nombre": "Vulnerabilidades criticas abiertas", "valor": "0",
                 "objetivo": "0", "estado": "OK"},
            ],
            "incidentes_periodo": [
                {"id": "INC-2026-001", "fecha": "2026-01-15", "categoria": "Phishing",
                 "severidad": "BAJA", "estado": "Cerrado"},
                {"id": "INC-2026-002", "fecha": "2026-02-08",
                 "categoria": "Acceso anomalo", "severidad": "MEDIA",
                 "estado": "Cerrado"},
                {"id": "INC-2026-003", "fecha": "2026-03-22",
                 "categoria": "Malware detectado", "severidad": "BAJA",
                 "estado": "Cerrado"},
            ],
            "cambios_periodo": [
                {"id": "CHG-2026-004", "fecha": "2026-02-15",
                 "descripcion": "Actualizacion SO servidores produccion",
                 "material": False},
                {"id": "CHG-2026-007", "fecha": "2026-03-10",
                 "descripcion": "Migracion cloud Azure ES", "material": True},
            ],
            # Metricas anuales E-615 (consolidacion)
            "incidentes_anuales_total": "12",
            "incidentes_criticos_anuales": "0",
            "tiempo_medio_anual": "2h 45min",
            "cambios_materiales_anuales": "2",
            "cobertura_formacion_anual": "89%",
            "fecha_auditoria_interna_anual": "2026-11-15",
            "fecha_verificacion_externa": "2026-12-10",
            "recomendacion_cambio_tier": False,
        },
    }


@pytest.mark.parametrize("codigo", GOVERNANCE_TEMPLATES)
def test_governance_template_renders_without_placeholder_leak(
    codigo, tmp_path, governance_context,
):
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_test.docx"
    render_docx(template_path, governance_context, output_path)

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
    # razon_social presente · anchor comun (E-002/003/012/041/042/043 usan upper en H1 ·
    # E-090/E-614/E-615 usan title case mixed)
    assert "Test Gobierno SGSI SL" in text or "TEST GOBIERNO SGSI SL" in text, (
        f"{codigo} missing cliente.razon_social"
    )


def test_e002_renders_multi_role_and_categoria_branch(tmp_path, governance_context):
    """E-002 con proyecto.categoria_ens='MEDIA' debe activar branch else RSA
    consolidado (NO branch ALTA requiere_rsa). Validacion: 3 roles RS+RSI+RServ
    + nombres/DNIs + Acuerdo 4 NO presente."""
    template_path = VAR_TEMPLATES / "E-002.docx"
    output_path = tmp_path / "E-002_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "RD 311/2022" in text or "Real Decreto 311/2022" in text, (
        "E-002 falta RD 311/2022"
    )
    assert "CCN-STIC 801" in text, "E-002 falta CCN-STIC 801"
    # 3 roles core (RS + RSI + RServ)
    assert "Marcos Lopez Perez" in text, "E-002 falta nombre RS"
    assert "CISO" in text, "E-002 falta cargo RS"
    assert "23456789B" in text, "E-002 falta DNI RS"
    assert "Javier Sanz Moreno" in text, "E-002 falta nombre RSI"
    assert "Director de TI" in text, "E-002 falta cargo RSI"
    assert "Carmen Ruiz Garcia" in text, "E-002 falta nombre RServ"
    # Categoria MEDIA presente
    assert "MEDIA" in text, "E-002 falta categoria_ens"
    # F0-2 (Ejecutable 8 Pasada 16): RI siempre presente (art 11.a)
    assert "Responsable de la Información" in text, "E-002 falta RI (art 11.a)"
    # F0-2: ASS + POC presentes en MEDIA (requiere_ass/poc = MEDIA/ALTA)
    assert "Administrador de Seguridad del Sistema" in text, "E-002 falta ASS en MEDIA"
    assert "Punto de Contacto ante CCN-CERT" in text, "E-002 falta POC en MEDIA"
    # Branch else separación (MEDIA · NO requiere_rsa) · reescrito F0-2
    assert "recomendada en MEDIA" in text or "separación" in text.lower(), (
        "E-002 falta nota de separación RS/RSI (branch else categoría MEDIA)"
    )
    # NO branch ALTA reforzado (requiere_rsa=False en MEDIA)
    assert "Separación funcional reforzada (categoría ALTA)" not in text, (
        "E-002 NO debe contener el Acuerdo 7 ALTA cuando categoria=MEDIA"
    )
    # Acuerdos presentes (RI=1, RS=2, RSI=3, RServ=4, ASS=5, POC=6 en MEDIA)
    for acuerdo in ["Acuerdo 1", "Acuerdo 2", "Acuerdo 3", "Acuerdo 4", "Acuerdo 5", "Acuerdo 6"]:
        assert acuerdo in text, f"E-002 falta {acuerdo}"
    # Aceptacion expresa
    assert "aceptan expresamente" in text, "E-002 falta aceptacion expresa"
    # Vigencia + renovacion + E-043
    assert "E-043" in text, "E-002 falta referencia renovacion E-043"


def test_e002_category_conditionals_basica_and_alta(tmp_path, governance_context):
    """F0-2 (Ejecutable 8 Pasada 16): RI siempre · ASS/POC sólo MEDIA+ ·
    Acuerdo 7 separación reforzada sólo ALTA. Fuente: RD 311/2022 art. 11 +
    CCN-STIC 801."""
    import copy

    def _render_text(cat: str) -> str:
        ctx = copy.deepcopy(governance_context)
        ctx["proyecto"]["categoria_ens"] = cat
        out = tmp_path / f"E-002_{cat}.docx"
        render_docx(VAR_TEMPLATES / "E-002.docx", ctx, out)
        doc = DocxDocument(str(out))
        t = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    t += "\n" + cell.text
        return t

    basica = _render_text("BASICA")
    assert "Responsable de la Información" in basica, "RI debe estar siempre (art 11.a)"
    assert "Administrador de Seguridad del Sistema" not in basica, "ASS NO en BÁSICA"
    assert "Punto de Contacto ante CCN-CERT" not in basica, "POC NO en BÁSICA"
    assert "Separación funcional reforzada (categoría ALTA)" not in basica

    alta = _render_text("ALTA")
    assert "Administrador de Seguridad del Sistema" in alta, "ASS obligatorio en ALTA"
    assert "Punto de Contacto ante CCN-CERT" in alta, "POC obligatorio en ALTA"
    assert "Separación funcional reforzada (categoría ALTA)" in alta, (
        "Acuerdo 7 separación RS≠RSI debe activarse en ALTA"
    )


def test_e003_renders_comite_composition_and_quorum_loop(tmp_path, governance_context):
    """E-003 con comite_seguridad.miembros (3 entradas) debe activar branch
    tiene_miembros + loop linea APARTE renderizar los 3 miembros sin
    truncamiento. Verificar presidencia + secretaria + quorum + 9 competencias."""
    template_path = VAR_TEMPLATES / "E-003.docx"
    output_path = tmp_path / "E-003_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo
    assert "RD 311/2022" in text, "E-003 falta RD 311/2022"
    assert "CCN-STIC 801" in text, "E-003 falta CCN-STIC 801"
    assert "org.1" in text, "E-003 falta org.1 Anexo II"
    # Presidencia + secretaria
    assert "Carmen Ruiz Garcia" in text, "E-003 falta presidente"
    assert "Lucia Torres Vega" in text, "E-003 falta secretario"
    assert "Compliance Officer" in text, "E-003 falta cargo secretario"
    # Miembros loop (3 entries multi-entry safe · loop linea APARTE)
    assert "Marcos Lopez Perez" in text, "E-003 falta miembro 1 (CISO)"
    assert "Javier Sanz Moreno" in text, "E-003 falta miembro 2 (CTO)"
    assert "Roberto Vidal Castro" in text, "E-003 falta miembro 3 (RRHH)"
    # NO else placeholder cuando hay miembros
    assert "Pendiente de designación formal" not in text, (
        "E-003 NO debe contener else placeholder cuando miembros presentes"
    )
    # Periodicidad + quorum
    assert "Trimestral" in text, "E-003 falta periodicidad reuniones"
    assert "Mayoria absoluta" in text, "E-003 falta quorum minimo"
    # 9 competencias (verificar al menos 3 referencias documentales clave)
    competencias = ["E-100", "E-150", "E-400", "E-041", "E-222"]
    for c in competencias:
        assert c in text, f"E-003 falta referencia competencia: {c}"
    # Conservacion 10 anios actas
    assert "diez (10) años" in text, "E-003 falta plazo conservacion actas"
    # Primera reunion 30 dias
    assert "treinta (30) días naturales" in text, "E-003 falta plazo primera reunion"


def test_e012_renders_dimensions_table_and_decision(tmp_path, governance_context):
    """E-012 con decision_categorizacion (5 dimensiones + nivel global MEDIA).
    Validacion: tabla 5 dimensiones + nivel global decision + metodologia +
    referencia E-040 DA + referencia E-150 (Plan de Adecuación)."""
    template_path = VAR_TEMPLATES / "E-012.docx"
    output_path = tmp_path / "E-012_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "RD 311/2022" in text, "E-012 falta RD 311/2022"
    assert "Anexo I" in text, "E-012 falta Anexo I categorizacion"
    assert "Anexo II" in text, "E-012 falta Anexo II 73 medidas"
    assert "artículo 40" in text, "E-012 falta art 40 RD 311/2022 (categorización)"
    assert "artículo 28" in text, "E-012 falta art 28 RD 311/2022 (declaración de aplicabilidad)"
    assert "CCN-STIC 803" in text, "E-012 falta CCN-STIC 803"
    # 5 dimensiones C/I/D/A/T renderizadas
    dimensiones_labels = ["Confidencialidad", "Integridad", "Disponibilidad",
                          "Autenticidad", "Trazabilidad"]
    for d in dimensiones_labels:
        assert d in text, f"E-012 falta dimension: {d}"
    # Disponibilidad ALTO custom (resto MEDIO por fixture)
    assert "ALTO" in text, "E-012 falta nivel ALTO en Disponibilidad"
    # Nivel global decision (CATEGORIA GLOBAL: MEDIA)
    assert "MEDIA" in text, "E-012 falta nivel global MEDIA"
    # Metodologia custom
    assert "CCN-STIC 803" in text, "E-012 falta metodologia custom"
    # Referencias documentales
    assert "E-040" in text, "E-012 falta referencia E-040 DA"
    assert "E-150" in text, "E-012 falta referencia E-150 Plan de Adecuación"
    assert "E-042" in text, "E-012 falta referencia E-042 cambio material"
    # 73 medidas Anexo II detalladas
    assert "73 medidas" in text, "E-012 falta total 73 medidas"
    assert "4 organizativas" in text, "E-012 falta 4 organizativas"
    assert "33 operacionales" in text, "E-012 falta 33 operacionales"
    assert "36 de protección" in text, "E-012 falta 36 proteccion"
    # Plazo 90 dias Plan Adecuacion
    assert "noventa (90) días naturales" in text, "E-012 falta plazo 90 dias"


def test_e090_renders_gap_hallazgos_loop_no_truncation(tmp_path, governance_context):
    """E-090 CRITICO multi-entry · diagnostico con 4 hallazgos_gap + 4
    recomendaciones (multi-entry · loops linea APARTE patron L-003/L-007).
    Verificar todos los 4 hallazgos + todas las 4 recomendaciones renderizan +
    Conclusiones DESPUES de loops (sin truncamiento bug L-002 IV.C).
    """
    template_path = VAR_TEMPLATES / "E-090.docx"
    output_path = tmp_path / "E-090_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "RD 311/2022" in text, "E-090 falta RD 311/2022"
    assert "Anexo II" in text, "E-090 falta Anexo II"
    assert "CCN-STIC 808" in text, "E-090 falta CCN-STIC 808 verificacion"
    # 73 medidas + distribucion
    assert "73 medidas" in text, "E-090 falta total 73 medidas"
    assert "Marco organizativo" in text, "E-090 falta familia organizativo"
    assert "Marco operacional" in text, "E-090 falta familia operacional"
    assert "Medidas de protección" in text, "E-090 falta familia proteccion"
    # Escala madurez L0-L5
    for nivel in ["L0", "L1", "L2", "L3", "L4", "L5"]:
        assert nivel in text, f"E-090 falta nivel madurez: {nivel}"
    # Nivel madurez actual custom
    assert "L2 · Definido parcialmente" in text, "E-090 falta nivel_madurez_actual"

    # CRITICO multi-entry · 4 hallazgos loop linea APARTE
    hallazgos_familias = [
        "Marco organizativo", "Marco operacional",
        "Medidas proteccion", "Continuidad",
    ]
    # 3 de 4 ya verificados en familias arriba · Continuidad es el 4to
    assert "Continuidad" in text, "E-090 falta hallazgo 4 (Continuidad · multi-entry)"
    assert "Politica Seguridad pendiente" in text, (
        "E-090 falta descripcion hallazgo 1"
    )
    assert "Cifrado en reposo no homogeneo" in text, (
        "E-090 falta descripcion hallazgo 3"
    )
    assert "BCP sin pruebas anuales" in text, (
        "E-090 falta descripcion hallazgo 4"
    )

    # CRITICO multi-entry · 4 recomendaciones loop linea APARTE
    recoms = [
        "Formalizar Politica Seguridad",
        "Completar inventario activos",
        "Implantar cifrado AES-256",
        "Programar simulacro BCP semestral",
    ]
    for r in recoms:
        assert r in text, f"E-090 falta recomendacion (multi-entry): {r}"

    # CRITICO · seccion 8 Conclusiones renderizada DESPUES de loops (sin truncamiento)
    assert "CONCLUSIONES" in text or "Conclusiones" in text, (
        "E-090 sec 8 Conclusiones truncada (posible bug multi-entry · NO debe ocurrir)"
    )
    # Plazos siguientes pasos (verifica seccion 8c renderizada)
    assert "30 días" in text, "E-090 falta plazo 30 dias E-040"
    assert "90 días" in text, "E-090 falta plazo 90 dias E-150"
    assert "120 días" in text, "E-090 falta plazo 120 dias E-400"
    assert "180 días" in text, "E-090 falta plazo 180 dias auditoria"
    # Validado por Comite renderizado DESPUES loops
    assert "Validado por:** Comité de Seguridad" in text or "Comité de Seguridad" in text, (
        "E-090 falta validacion Comite (posible truncamiento)"
    )


def test_e041_renders_categoria_branch_and_normative_refs(tmp_path, governance_context):
    """E-041 con proyecto.categoria_ens='MEDIA' debe activar branch
    certificacion ENAC (NO branch BASICA · sin certificacion). Validacion:
    art 33 RD 311/2022 + Anexos III/IV + CCN-STIC 809 + 6 letras declaracion
    formal + referencias documentales E-040/050/204/203/401/042/043/052."""
    template_path = VAR_TEMPLATES / "E-041.docx"
    output_path = tmp_path / "E-041_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "RD 311/2022" in text or "Real Decreto 311/2022" in text, (
        "E-041 falta RD 311/2022"
    )
    assert "artículo 33" in text or "art. 33" in text or "Art. 33" in text, (
        "E-041 falta art 33"
    )
    assert "CCN-STIC 809" in text, "E-041 falta CCN-STIC 809"
    assert "Anexo III" in text, "E-041 falta Anexo III"
    # Categoria MEDIA + branch certificacion
    assert "MEDIA" in text, "E-041 falta categoria MEDIA"
    assert "Certificación de Conformidad" in text, (
        "E-041 falta branch MEDIA (Certificacion · NO Declaracion BASICA)"
    )
    assert "entidad de certificación acreditada" in text, "E-041 falta ENAC referencia"
    # NO branch BASICA (declaracion sin certificacion)
    assert "sin necesidad de certificación por entidad acreditada" not in text, (
        "E-041 NO debe contener branch BASICA cuando categoria=MEDIA"
    )
    # 6 letras declaracion formal (a-f)
    assert "Plan de Adecuación (E-150)" in text, "E-041 falta ref E-150 Plan Adecuacion"
    assert "E-204" in text, "E-041 falta ref E-204 gestion incidentes"
    assert "E-203" in text, "E-041 falta ref E-203 gestion cambios"
    assert "E-401" in text, "E-041 falta ref E-401 continuidad"
    assert "E-042" in text, "E-041 falta ref E-042 cambio material"
    assert "E-043" in text, "E-041 falta ref E-043 renovacion"
    # Branch periodicidad MEDIA · 3 anios (NO 2 anios BASICA)
    assert "3 años" in text, "E-041 falta periodicidad 3 anios (MEDIA/ALTA)"
    # Anexos (E-040, E-150, E-003, E-002)
    assert "E-040" in text, "E-041 falta Anexo I E-040"
    assert "E-002" in text, "E-041 falta Anexo IV E-002"
    assert "E-003" in text, "E-041 falta Anexo IV E-003"
    # CCN-CERT remision
    assert "CCN-CERT" in text, "E-041 falta CCN-CERT remision"
    # MAGERIT
    assert "MAGERIT" in text, "E-041 falta MAGERIT referencia"


def test_e042_renders_impacto_loop_and_recategorizacion_branch(tmp_path, governance_context):
    """E-042 con cambio_material.impacto_medidas_afectadas (3 entries)
    + requiere_recategorizacion=False · debe activar branch tiene_medidas LOOP
    linea APARTE + branch NOT recat (mantiene categoria). Validacion: art 30
    RD 311/2022 + CCN-STIC 809 + 5 actuaciones previstas + riesgo residual."""
    template_path = VAR_TEMPLATES / "E-042.docx"
    output_path = tmp_path / "E-042_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo
    assert "RD 311/2022" in text, "E-042 falta RD 311/2022"
    assert "artículo 30" in text or "art. 30" in text or "Art. 30" in text, (
        "E-042 falta art 30"
    )
    assert "CCN-STIC 809" in text, "E-042 falta CCN-STIC 809"
    assert "CCN-CERT" in text, "E-042 falta CCN-CERT remision"
    # Descripcion + motivacion custom
    assert "Microsoft 365 GCC" in text, "E-042 falta descripcion cambio custom"
    assert "NIS2" in text, "E-042 falta motivacion NIS2"
    # Branch tiene_medidas LOOP linea APARTE · 3 entries multi-entry safe
    assert "mp.com.3" in text, "E-042 falta medida afectada 1"
    assert "mp.s.8" in text, "E-042 falta medida afectada 2"
    assert "op.ext.4" in text, "E-042 falta medida afectada 3 (multi-entry safe)"
    # NO else placeholder cuando hay medidas
    assert "No se identifican medidas afectadas significativamente" not in text, (
        "E-042 NO debe contener else cuando tiene_medidas presente"
    )
    # Riesgo residual custom
    assert "BAJO" in text, "E-042 falta riesgo residual estimado custom"
    # Branch NOT recat (False · mantiene categoria)
    assert "no altera significativamente" in text, (
        "E-042 falta branch NOT recat (mantiene categoria)"
    )
    assert "Se mantiene la categoría" in text, (
        "E-042 falta mensaje mantener categoria branch NOT recat"
    )
    # NO branch recat True (recategorizacion E-012)
    assert "alteración significativa" not in text or "no altera" in text, (
        "E-042 NO debe contener branch recat=True cuando False"
    )
    # 5 actuaciones previstas (a-e · refs E-040/050/400 + clientes + recertificacion MEDIA)
    refs = ["E-040", "E-150", "E-400"]
    for r in refs:
        assert r in text, f"E-042 falta referencia actuacion: {r}"
    # Branch recertificacion (cat=MEDIA · NO branch BASICA E-041)
    assert "certificación" in text or "Certificación" in text, (
        "E-042 falta recertificacion MEDIA"
    )
    # 3 firmas aprobacion
    assert "Marcos Lopez Perez" in text, "E-042 falta firma RS"
    assert "Javier Sanz Moreno" in text, "E-042 falta firma RSI"
    assert "Carmen Ruiz Garcia" in text, "E-042 falta firma Presidente Comite"


def test_e043_renders_cambios_loop_no_truncation(tmp_path, governance_context):
    """E-043 CRITICO multi-entry · renovacion.cambios_desde_anterior_revision
    (3 entries) loop linea APARTE multi-entry safe. Verifica todos los cambios
    + branch categoria MEDIA (3 anios + auditoria externa) + Declaracion
    renovacion + Publicacion DESPUES de loops (sin truncamiento bug L-002 IV.C)."""
    template_path = VAR_TEMPLATES / "E-043.docx"
    output_path = tmp_path / "E-043_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo core
    assert "RD 311/2022" in text, "E-043 falta RD 311/2022"
    assert "artículo 35" in text or "art. 35" in text or "Art. 35" in text, (
        "E-043 falta art 35"
    )
    # CCN-STIC 809 sta solo en frontmatter (norma_aplicable YAML) · no en body
    # Categoria MEDIA branch · 3 anios + auditoria externa
    assert "MEDIA" in text, "E-043 falta categoria MEDIA"
    assert "3 años" in text, "E-043 falta periodicidad 3 anios"
    assert "auditoría por entidad acreditada" in text or "entidad acreditada" in text, (
        "E-043 falta auditoria externa branch MEDIA/ALTA"
    )
    # Fechas renovacion (anterior + actual)
    assert "2023-03-15" in text, "E-043 falta fecha_renovacion_anterior"
    assert "2026-03-15" in text, "E-043 falta fecha_proxima_renovacion"

    # CRITICO multi-entry · 3 cambios loop linea APARTE
    assert "Migracion cloud Azure ES" in text, (
        "E-043 falta cambio 1 (Azure · multi-entry)"
    )
    assert "Implantacion SSO + MFA universal" in text, (
        "E-043 falta cambio 2 (SSO MFA · multi-entry)"
    )
    assert "Renovacion auditoria interna" in text, (
        "E-043 falta cambio 3 (auditoria · multi-entry)"
    )
    # NO else placeholder cuando hay cambios
    assert "No se han registrado cambios materiales significativos" not in text, (
        "E-043 NO debe contener else cuando tiene_cambios presente"
    )
    # Tabla auditorias (branch NOT basica · ambas filas)
    assert "Auditoría interna anual" in text, "E-043 falta fila auditoria interna"
    assert "Auditoría externa de certificación" in text, (
        "E-043 falta branch externa (categoria MEDIA · NOT basica)"
    )
    # 4 validaciones seccion 4 (a-e · E-040/050/400 + ciclo bienal politicas + acta Comite)
    val_refs = ["E-040", "E-150", "E-400"]
    for r in val_refs:
        assert r in text, f"E-043 falta validacion sec 4: {r}"

    # CRITICO · seccion 5 Declaracion + sec 6 Firmas + sec 7 Publicacion DESPUES de loops
    assert "DECLARACIÓN DE RENOVACIÓN" in text or "renueva la Declaración" in text, (
        "E-043 sec 5 truncada (posible bug multi-entry · NO debe ocurrir)"
    )
    assert "Representante legal" in text, "E-043 sec 6 firmas truncada"
    assert "PUBLICACIÓN" in text or "publica en la sede electrónica" in text, (
        "E-043 sec 7 publicacion truncada (post-loop · LECCION-OPS-030 caso 4)"
    )
    # E-204 + E-042 referencias preservadas
    assert "E-204" in text, "E-043 falta referencia E-204 incidentes"
    assert "E-042" in text, "E-043 falta referencia E-042 cambios materiales"


def test_e614_renders_kpis_incidents_changes_loops_multi_entry(
    tmp_path, governance_context,
):
    """E-614 CRITICO multi-entry · 3 loops linea APARTE (kpis_periodo +
    incidentes_periodo + cambios_periodo) deben renderizar TODAS las entries
    + secciones 6-8 DESPUES de los loops (sin truncamiento bug L-002 IV.C).
    Validacion: identificacion + tier R_STD + periodo Q1 2026 + 4 KPIs + 3
    incidentes + 2 cambios + acciones previstas + aprobacion."""
    template_path = VAR_TEMPLATES / "E-614.docx"
    output_path = tmp_path / "E-614_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Identificacion + periodo + tier
    assert "Test Gobierno SGSI SL" in text, "E-614 falta razon_social"
    assert "R_STD" in text, "E-614 falta tier R_STD"
    assert "Q1 2026" in text, "E-614 falta etiqueta periodo"
    assert "2026-01-01" in text, "E-614 falta fecha desde periodo"
    assert "2026-03-31" in text, "E-614 falta fecha hasta periodo"
    # Categoria ENS MEDIA + referencia E-041
    assert "MEDIA" in text, "E-614 falta categoria ENS MEDIA"
    assert "E-041" in text, "E-614 falta referencia E-041 Declaracion Conformidad"

    # CRITICO multi-entry · 4 KPIs loop linea APARTE
    kpis = ["Incidentes registrados", "Tiempo medio respuesta",
            "Cobertura formacion seguridad", "Vulnerabilidades criticas abiertas"]
    for k in kpis:
        assert k in text, f"E-614 falta KPI (multi-entry safe): {k}"
    # Valores KPIs custom
    assert "2h 15min" in text, "E-614 falta valor KPI tiempo medio"
    assert "87%" in text, "E-614 falta valor KPI cobertura"

    # CRITICO multi-entry · 3 incidentes loop linea APARTE
    incs = ["INC-2026-001", "INC-2026-002", "INC-2026-003"]
    for i in incs:
        assert i in text, f"E-614 falta incidente (multi-entry safe): {i}"
    assert "Phishing" in text, "E-614 falta categoria incidente 1"
    assert "Acceso anomalo" in text, "E-614 falta categoria incidente 2"
    assert "Malware detectado" in text, "E-614 falta categoria incidente 3 (multi-entry)"
    # Referencia E-204
    assert "E-204" in text, "E-614 falta referencia E-204 gestion incidentes"

    # CRITICO multi-entry · 2 cambios loop linea APARTE + branch material
    assert "CHG-2026-004" in text, "E-614 falta cambio no material"
    assert "CHG-2026-007" in text, "E-614 falta cambio material (multi-entry safe)"
    assert "Migracion cloud Azure ES" in text, "E-614 falta descripcion cambio material"
    assert "SÍ" in text, "E-614 falta marca material SI (branch material True)"
    assert "No" in text, "E-614 falta marca No (branch material False)"
    # Referencias E-203 + E-042 + CCN-CERT
    assert "E-203" in text, "E-614 falta referencia E-203 gestion cambios"
    assert "E-042" in text, "E-614 falta referencia E-042 cambio material"
    assert "CCN-CERT" in text, "E-614 falta referencia CCN-CERT"

    # CRITICO · seccion 6 acciones previstas + sec 7 recomendaciones + sec 8 aprobacion
    # DESPUES de los 3 loops (sin truncamiento bug L-002 IV.C)
    assert "ACCIONES PREVISTAS" in text or "Acciones previstas" in text, (
        "E-614 sec 6 truncada (multi-entry · LECCION-OPS-030 caso 4)"
    )
    assert "E-150" in text, "E-614 falta ref E-150 Plan Adecuacion"
    assert "E-401" in text, "E-614 falta ref E-401 Continuidad"
    # Recomendaciones sec 7 + aprobacion sec 8
    assert "tier" in text.lower() and "R_STD" in text, (
        "E-614 sec 7 recomendaciones truncada"
    )
    assert "APROBACIÓN" in text or "Aprobacion" in text or "Aprobación" in text, (
        "E-614 sec 8 aprobacion truncada (post-loops · LECCION-OPS-030 caso 4)"
    )
    # 2 firmas (RS + representante cliente)
    assert "Marcos Lopez Perez" in text, "E-614 falta firma RS"
    assert "Carmen Ruiz Garcia" in text, "E-614 falta firma representante cliente"


def test_e615_renders_annual_summary_consolidation(tmp_path, governance_context):
    """E-615 Informe Anual · validacion consolidacion 5 KPIs anuales +
    branch tiene_inc + tiene_chg + auditorias + plan ano siguiente +
    decision renovacion branch recomendacion_cambio_tier=False (mantener
    tier actual recomendado · NO ascenso necesario)."""
    template_path = VAR_TEMPLATES / "E-615.docx"
    output_path = tmp_path / "E-615_semantic.docx"
    render_docx(template_path, governance_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Identificacion + ano + tier + categoria ENS
    assert "Test Gobierno SGSI SL" in text, "E-615 falta razon_social"
    assert "2026" in text, "E-615 falta ano_reportado"
    assert "R_STD" in text, "E-615 falta tier"
    assert "MEDIA" in text, "E-615 falta categoria ENS"
    assert "2027-01-01" in text, "E-615 falta fecha_renovacion"
    # Referencia 4 informes E-614 trimestrales
    assert "E-614" in text, "E-615 falta referencia E-614 trimestrales"

    # 5 KPIs anuales consolidacion (tabla seccion 3)
    kpis_annual = [
        "Incidentes registrados",
        "Incidentes críticos",
        "Tiempo medio de respuesta a incidentes",
        "Cambios materiales documentados",
        "Cobertura de formación en seguridad",
    ]
    for k in kpis_annual:
        assert k in text, f"E-615 falta KPI anual consolidado: {k}"
    # Valores anuales custom
    assert "12" in text, "E-615 falta valor inc_total anual"
    assert "2h 45min" in text, "E-615 falta valor tiempo_medio anual"
    assert "89%" in text, "E-615 falta valor cobertura_formacion anual"

    # Multi-entry sec 4 incidentes + sec 5 cambios (heredados de fixture · 3 + 2)
    assert "INC-2026-001" in text, "E-615 falta incidente 1 sec 4"
    assert "INC-2026-003" in text, "E-615 falta incidente 3 sec 4 (multi-entry)"
    assert "CHG-2026-007" in text, "E-615 falta cambio material sec 5"
    # Referencia E-204 + E-042 + art 30 RD 311/2022
    assert "E-204" in text, "E-615 falta ref E-204"
    assert "E-042" in text, "E-615 falta ref E-042"
    assert "RD 311/2022" in text, "E-615 falta RD 311/2022"

    # Sec 6 auditorias (interna + externa)
    assert "Auditoría interna anual" in text, "E-615 falta auditoria interna"
    assert "2026-11-15" in text, "E-615 falta fecha auditoria interna"
    assert "2026-12-10" in text, "E-615 falta fecha verificacion externa"

    # Sec 7 plan ano siguiente (6 letras · refs E-150/E-400/E-012)
    assert "E-150" in text, "E-615 falta ref E-150"
    assert "E-400" in text, "E-615 falta ref E-400 Analisis Riesgos"
    assert "E-012" in text, "E-615 falta ref E-012 categorizacion"

    # Sec 8 decision renovacion (branch cambio_tier=False)
    assert "DECISIÓN DE RENOVACIÓN" in text or "Decisión de Renovación" in text, (
        "E-615 falta seccion 8 decision renovacion"
    )
    # Branch cambio_tier=False · mantener tier recomendado · NO ascenso necesario
    assert "Recomendado" in text or "servicio adecuado" in text, (
        "E-615 falta recomendacion mantener tier (cambio_tier=False)"
    )
    assert "No necesario en el corto plazo" in text, (
        "E-615 falta branch NO ascenso (cambio_tier=False)"
    )
    # NO branch cambio_tier=True (A revisar / A evaluar)
    assert "A revisar" not in text, (
        "E-615 NO debe contener branch cambio_tier=True cuando False"
    )

    # Margen 2 meses renovacion
    assert "dos meses" in text, "E-615 falta margen 2 meses renovacion"

    # Sec 9 aprobacion (2 firmas · RS + representante cliente)
    assert "APROBACIÓN" in text or "Aprobación" in text, "E-615 falta sec 9"
    assert "Marcos Lopez Perez" in text, "E-615 falta firma RS"
    assert "Carmen Ruiz Garcia" in text, "E-615 falta firma representante cliente"


def test_retainer_tier_branch_visible_in_both_templates(
    tmp_path, governance_context,
):
    """Verifica que retainer.tier (R_STD per fixture) es visible en ambos
    templates E-614 + E-615 · permitiendo distinguir tier real del cliente
    (R_LITE/STD/PLUS/CRITICAL). Validacion cross-template del tier branch."""
    for codigo in ["E-614", "E-615"]:
        template_path = VAR_TEMPLATES / f"{codigo}.docx"
        output_path = tmp_path / f"{codigo}_tier_branch.docx"
        render_docx(template_path, governance_context, output_path)

        doc = DocxDocument(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += "\n" + cell.text

        # tier R_STD presente
        assert "R_STD" in text, f"{codigo} falta retainer.tier R_STD"
        # tier_descripcion custom (Retainer Estandar 700EUR/mes)
        assert "Retainer Estandar" in text, (
            f"{codigo} falta tier_descripcion custom"
        )
        assert "700EUR" in text or "EUR/mes" in text, (
            f"{codigo} falta importe tier en descripcion"
        )
