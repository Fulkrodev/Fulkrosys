"""Integration tests SGSI core templates E-150/160/170/180 · sub-atom 1.D.F.tris.B-bis.

Familia SGSI core ruta normal (vs ruta basica governance E-002/003/012/041/042/043/090
Cluster A). Naturaleza: documentacion estructural SGSI generada en fase de plan +
manual + roadmap trianual + declaracion autoevaluacion.

Plantillas cubiertas:
  E-150 Plan de Adecuacion al ENS (entregable core M04 deriva)
  E-160 Manual del SGSI (gobierno SGSI structure formal · CCN-STIC 805)
  E-170 Plan Director de Seguridad trianual (roadmap CCN-STIC 806/815)
  E-180 Declaracion Conformidad SGSI · autoevaluacion BASICA CCN-STIC 809
        (complementaria a E-041 que es certificacion ENAC MEDIA/ALTA)

Norma aplicable: RD 311/2022 + CCN-STIC 805/806/809/815/824/825/844 + ISO 27001 mapping.

Reglas duras sostenidas (LECCION-OPS-020/021/027/028/030 caso 4 · pattern reuse
test_governance_templates_render.py · OPS-045 30ª).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx

VAR_TEMPLATES = Path(__file__).resolve().parents[4] / "var" / "templates_docx"
PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")

SGSI_CORE_TEMPLATES = ["E-150", "E-160", "E-170", "E-180"]


def _build_sgsi_context(categoria: str) -> dict:
    """Contexto comun SGSI core E-150/160/170/180 · BASICA o MEDIA."""
    return {
        # Identificacion comun
        "client_name": "Test SGSI Core SL",
        "client_cif": "B80000000",
        "client_domicilio": "Calle Test 25, 28001 Madrid",
        "system_name": "Sistema Informacion ENS Test",
        "system_category": categoria,
        "version": "1.0",
        "today": "2026-05-21",
        "expiry_date": "2028-05-21",
        "template_version": "1.0",
        "cert_id": "FULKRO-CERT-2026-00042",
        "project_id": "proj-test-sgsi-001",
        "psi_version": "2.0",
        "public_badge_url": "https://test-sgsi-core.es/distintivo-ens",

        # Resumenes (E-160 + E-180)
        "services_summary": "Servicios consultoria + soporte tecnico + cloud",
        "information_summary": "Datos clientes + administrativos + transaccionales",
        "assets_essential_count": "12",
        "exclusions_text": (
            "Quedan fuera del alcance los sistemas legacy on-premise "
            "previstos para retirada en H2 2026 (migracion cloud aprobada)."
        ),

        # E-150 Plan de Adecuacion · Info+Services loops
        "information_types": [
            {"name": "Datos de clientes (RGPD)",
             "description": "Identificacion + facturacion + comunicaciones"},
            {"name": "Datos de empleados",
             "description": "Nomina + acceso a sistemas + contratos"},
            {"name": "Datos operacionales",
             "description": "Logs + metricas + monitorizacion sistemas"},
        ],
        "services": [
            {"name": "Plataforma SaaS principal",
             "description": "Acceso 24x7 a clientes y operadores"},
            {"name": "API publica de integracion",
             "description": "Endpoints REST autenticados con OAuth 2.0"},
            {"name": "Portal administrativo interno",
             "description": "Backoffice gestion clientes + facturacion"},
        ],

        # E-150 Categorizacion · dimensions loop
        "dimensions": [
            {"code": "D", "name": "Disponibilidad", "level": "MEDIO",
             "justification": "Servicio 8x5 con tolerancia 4h indisponibilidad"},
            {"code": "I", "name": "Integridad", "level": "ALTO" if categoria == "MEDIA" else "MEDIO",
             "justification": "Datos transaccionales financieros · alteracion=fraude"},
            {"code": "C", "name": "Confidencialidad", "level": "MEDIO",
             "justification": "Datos personales RGPD + comerciales sensibles"},
            {"code": "A", "name": "Autenticidad", "level": "MEDIO",
             "justification": "Firma electronica clientes + auditoria operadores"},
            {"code": "T", "name": "Trazabilidad", "level": "MEDIO",
             "justification": "Audit log obligatorio retencion 5 anios"},
        ],

        # E-150 DdA totales
        "dda_total": "73",
        "dda_aplicables": "55" if categoria == "BASICA" else "65",
        "dda_con_refuerzos": "8" if categoria == "BASICA" else "20",
        "dda_no_aplica": "18" if categoria == "BASICA" else "8",
        "risk_scenarios_count": "18",

        # E-150 + E-180 Gap analysis + autoevaluacion
        "gap_summary": [
            {"family": "Marco organizativo", "aplicables": 4,
             "conformes": 4, "no_conformes": 0, "pct_conformidad": 100},
            {"family": "Marco operacional", "aplicables": 33,
             "conformes": 28, "no_conformes": 5, "pct_conformidad": 84},
            {"family": "Medidas proteccion", "aplicables": 36,
             "conformes": 30, "no_conformes": 6, "pct_conformidad": 83},
        ],
        "conformes_count": "62",
        "no_conformes_count": "11",
        "pct_conformidad": "85",

        # E-150 Plan tasks loop multi-entry
        "plan_tasks": [
            {"code": "PA-001", "title": "Implantar MFA universal",
             "ens_measure": "op.acc.6", "responsible_role": "Responsable Seguridad",
             "priority": "ALTA", "effort_hours": "40",
             "target_date": "2026-07-15", "cost_eur": "3500",
             "description": "MFA TOTP + WebAuthn para administradores Yubikey"},
            {"code": "PA-002", "title": "Cifrado en reposo AES-256",
             "ens_measure": "mp.info.3", "responsible_role": "Responsable Sistema",
             "priority": "ALTA", "effort_hours": "60",
             "target_date": "2026-08-30", "cost_eur": "5800",
             "description": "Cifrado homogeneo bases datos + backups + S3 buckets"},
            {"code": "PA-003", "title": "Procedimiento gestion incidentes",
             "ens_measure": "op.exp.7", "responsible_role": "Responsable Seguridad",
             "priority": "MEDIA", "effort_hours": "30",
             "target_date": "2026-09-15", "cost_eur": "2200",
             "description": "Formalizar E-204 + integrar con CCN-CERT LUCIA"},
            {"code": "PA-004", "title": "Auditoria interna SGSI anual",
             "ens_measure": "op.pl.5", "responsible_role": "Responsable Seguridad",
             "priority": "MEDIA", "effort_hours": "80",
             "target_date": "2026-11-30", "cost_eur": "7500",
             "description": "Plan auditoria + ejecucion + informe + plan acciones"},
        ],
        "training_plan": {
            "sessions_count": "4",
            "lms_provider": "FULKRO LMS",
            "next_session_date": "2026-06-15",
        },

        # E-160 Manual SGSI · Roles table loop
        "roles_table": [
            {"role_name": "Responsable de Seguridad (RSEG)",
             "person": "Marcos Lopez Perez", "email": "marcos@test-sgsi.es",
             "functions": "Politica + monitor SGSI + comite seguridad + auditorias"},
            {"role_name": "Responsable del Sistema (RSIS)",
             "person": "Javier Sanz Moreno", "email": "javier@test-sgsi.es",
             "functions": "Operacion + cambios + incidentes + continuidad tecnica"},
            {"role_name": "Responsable del Servicio (RServ)",
             "person": "Carmen Ruiz Garcia", "email": "carmen@test-sgsi.es",
             "functions": "SLA + relacion cliente + escalado incidentes"},
            {"role_name": "Delegado Proteccion Datos (DPD)",
             "person": "Lucia Torres Vega", "email": "dpd@test-sgsi.es",
             "functions": "RGPD compliance + brechas datos + AEPD coordinacion"},
        ],

        # E-170 Plan Director · roadmap trianual
        "year_start": "2026",
        "year_start_plus_1": "2027",
        "year_end": "2028",
        "target_maturity_level": "L3 · Definido cuantitativamente",
        "target_cmm": "3",
        "target_cmm_y2": "2",
        "kpi_y1": "85",
        "kpi_y2_level": "3",
        "kpi_disponibilidad": "99.5",
        "kpi_mttr": "4",
        "kpi_cumplimiento": "95",
        "kpi_madurez": "3",
        "strategic_lines": [
            {"title": "Cumplimiento ENS sostenido",
             "description": "Mantener conformidad continua + dossier ENAC ready"},
            {"title": "Cifrado y privacidad by-design",
             "description": "Cifrado homogeneo + minimizacion datos + RGPD compliance"},
            {"title": "Concienciacion y formacion personal",
             "description": "100% cobertura anual + phishing simulado trimestral"},
            {"title": "Madurez SOC + monitorizacion 24x7",
             "description": "Detection + response capabilities + threat hunting"},
        ],
        "capex_y1": "25000", "opex_y1": "18000", "total_y1": "43000",
        "capex_y2": "15000", "opex_y2": "20000", "total_y2": "35000",
        "capex_y3": "8000", "opex_y3": "22000", "total_y3": "30000",
        "total_3y": "108000",
        "sponsor_name": "Carmen Ruiz Garcia (CEO)",
        "comite_chair": "Carmen Ruiz Garcia",
        "rseg_name": "Marcos Lopez Perez",

        # E-180 Declaracion conformidad SGSI · branch sector
        "rseg_email": "marcos@test-sgsi.es",
        "cliente": {
            "sector_aplicacion": "privado",  # Branch LUCIA recomendado vs obligatorio
        },
    }


@pytest.fixture
def sgsi_basica_context() -> dict:
    """Contexto Categoria BASICA · ruta autoevaluacion sin ENAC."""
    return _build_sgsi_context("BASICA")


@pytest.fixture
def sgsi_media_context() -> dict:
    """Contexto Categoria MEDIA · ruta certificacion ENAC requerida."""
    return _build_sgsi_context("MEDIA")


@pytest.mark.parametrize("codigo", SGSI_CORE_TEMPLATES)
def test_sgsi_core_renders_basica_without_placeholder_leak(
    codigo, tmp_path, sgsi_basica_context,
):
    """SGSI core E-150/160/170/180 con categoria BASICA · render limpio sin leaks."""
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    assert template_path.exists(), f"Missing precompiled template: {template_path}"

    output_path = tmp_path / f"{codigo}_basica.docx"
    render_docx(template_path, sgsi_basica_context, output_path)

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
    assert len(leaks) == 0, f"{codigo} BASICA placeholder leaks: {leaks[:5]}"
    assert "Test SGSI Core SL" in text, f"{codigo} BASICA missing client_name"


@pytest.mark.parametrize("codigo", SGSI_CORE_TEMPLATES)
def test_sgsi_core_renders_media_without_placeholder_leak(
    codigo, tmp_path, sgsi_media_context,
):
    """SGSI core E-150/160/170/180 con categoria MEDIA · render limpio sin leaks."""
    template_path = VAR_TEMPLATES / f"{codigo}.docx"
    output_path = tmp_path / f"{codigo}_media.docx"
    render_docx(template_path, sgsi_media_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    leaks = PLACEHOLDER_PATTERN.findall(text)
    assert len(leaks) == 0, f"{codigo} MEDIA placeholder leaks: {leaks[:5]}"
    assert "Test SGSI Core SL" in text, f"{codigo} MEDIA missing client_name"
    # E-170 Plan Director roadmap NO renders system_category (doc trianual NO categoria-aware)
    if codigo != "E-170":
        assert "MEDIA" in text, f"{codigo} MEDIA missing system_category"


def test_e150_renders_plan_acciones_loop_multi_entry(tmp_path, sgsi_media_context):
    """E-150 Plan Adecuacion CRITICO multi-entry · 4 plan_tasks + 3 gap_summary +
    3 information_types + 3 services + 5 dimensions loops linea APARTE."""
    template_path = VAR_TEMPLATES / "E-150.docx"
    output_path = tmp_path / "E-150_semantic.docx"
    render_docx(template_path, sgsi_media_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo
    assert "RD 311/2022" in text or "ENS" in text, "E-150 falta marco ENS"
    assert "CCN-STIC 806" in text, "E-150 falta CCN-STIC 806"
    # 5 dimensiones CIDAT renderizadas
    for d in ["Disponibilidad", "Integridad", "Confidencialidad",
              "Autenticidad", "Trazabilidad"]:
        assert d in text, f"E-150 falta dimension: {d}"
    # 4 plan tasks loop multi-entry (verifica los 4 codes presentes)
    for code in ["PA-001", "PA-002", "PA-003", "PA-004"]:
        assert code in text, f"E-150 falta plan task: {code}"
    # Plan task contenido critico
    assert "MFA" in text, "E-150 falta PA-001 MFA"
    assert "op.acc.6" in text, "E-150 falta medida ENS PA-001"
    assert "AES-256" in text, "E-150 falta PA-002 cifrado"
    # 3 info types + 3 services loops
    assert "Datos de clientes (RGPD)" in text, "E-150 falta info type 1"
    assert "Plataforma SaaS principal" in text, "E-150 falta servicio 1"
    # 3 gap_summary entries
    assert "Marco organizativo" in text, "E-150 falta gap fam organizativo"
    assert "Marco operacional" in text, "E-150 falta gap fam operacional"
    assert "Medidas proteccion" in text, "E-150 falta gap fam proteccion"
    # Training plan branch (truthy)
    assert "FULKRO LMS" in text, "E-150 falta training_plan branch"
    # Aprobacion + footer
    assert "Aprobaci" in text or "APROBACI" in text, "E-150 falta seccion aprobacion"


def test_e160_renders_roles_table_and_4_docs_levels(tmp_path, sgsi_basica_context):
    """E-160 Manual SGSI · roles_table loop 4 entries + 4 niveles documentacion
    CCN-STIC 805 + procesos SGSI + PDCA."""
    template_path = VAR_TEMPLATES / "E-160.docx"
    output_path = tmp_path / "E-160_semantic.docx"
    render_docx(template_path, sgsi_basica_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo + multi-citas
    assert "RD 311/2022" in text, "E-160 falta RD 311/2022"
    assert "CCN-STIC 801" in text, "E-160 falta CCN-STIC 801"
    assert "ISO" in text and "27001" in text, "E-160 falta ISO 27001 mapping"
    # 4 roles loop multi-entry
    for rname in ["Marcos Lopez Perez", "Javier Sanz Moreno",
                  "Carmen Ruiz Garcia", "Lucia Torres Vega"]:
        assert rname in text, f"E-160 falta rol: {rname}"
    # Procesos SGSI 5 sub-secciones
    for proceso in ["MAGERIT", "E204", "E203", "E216"]:
        assert proceso in text, f"E-160 falta proceso ref: {proceso}"
    # 4 niveles documentacion CCN-STIC 805
    assert "Pol" in text and "Seguridad" in text, "E-160 falta nivel 1 Politica"
    assert "Procedimiento" in text, "E-160 falta nivel 3 Procedimientos"
    # Mejora continua PDCA
    assert "PDCA" in text, "E-160 falta ciclo PDCA"
    assert "INES" in text, "E-160 falta referencia INES"


def test_e170_renders_strategic_lines_loop_and_trianual_kpis(
    tmp_path, sgsi_media_context,
):
    """E-170 Plan Director · strategic_lines 4 entries loop multi-entry +
    KPIs trianuales + inversion capex/opex + responsables."""
    template_path = VAR_TEMPLATES / "E-170.docx"
    output_path = tmp_path / "E-170_semantic.docx"
    render_docx(template_path, sgsi_media_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo
    assert "RD 311/2022" in text, "E-170 falta RD 311/2022"
    assert "CCN-STIC 806" in text or "CCN-STIC 815" in text, "E-170 falta CCN-STIC"
    # CIDAT mencionado
    assert "CIDAT" in text or "disponibilidad" in text.lower(), "E-170 falta CIDAT"
    # 4 strategic_lines loop multi-entry
    for title in ["Cumplimiento ENS sostenido", "Cifrado y privacidad",
                  "Concienciacion y formacion", "Madurez SOC"]:
        assert title in text, f"E-170 falta linea estrategica: {title}"
    # KPIs trianuales
    assert "99.5" in text, "E-170 falta KPI disponibilidad"
    assert "INES" in text, "E-170 falta INES anual"
    # Inversion capex/opex (3 anios)
    assert "43000" in text, "E-170 falta total y1"
    assert "108000" in text, "E-170 falta total 3y"
    # Responsables alta direccion
    assert "Carmen Ruiz Garcia" in text, "E-170 falta sponsor"
    assert "Marcos Lopez Perez" in text, "E-170 falta RSEG"
    # Revision art. 31
    assert "31" in text, "E-170 falta art 31 cambios sustanciales"


def test_e180_renders_autoevaluacion_and_sector_branch(tmp_path, sgsi_basica_context):
    """E-180 Declaracion Conformidad SGSI · autoevaluacion BASICA CCN-STIC 809 +
    branch cliente.sector_aplicacion (privado = LUCIA recomendado · publico = obligatorio).
    Distintivo + compromiso mantenimiento + firma RSEG."""
    template_path = VAR_TEMPLATES / "E-180.docx"
    output_path = tmp_path / "E-180_semantic.docx"
    render_docx(template_path, sgsi_basica_context, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Marco normativo
    assert "RD 311/2022" in text, "E-180 falta RD 311/2022"
    assert "CCN-STIC 809" in text, "E-180 falta CCN-STIC 809 autoevaluacion"
    # Identificacion entidad
    assert "B80000000" in text, "E-180 falta CIF cliente"
    assert "FULKRO-CERT-2026-00042" in text, "E-180 falta cert_id"
    # Resultado autoevaluacion
    assert "73" in text, "E-180 falta dda_total"
    assert "85" in text, "E-180 falta pct_conformidad"
    # Distintivo
    assert "Ed25519" in text, "E-180 falta firma Ed25519"
    assert "test-sgsi-core.es" in text, "E-180 falta public_badge_url"
    # Branch sector privado · LUCIA recomendado (NO obligatorio)
    assert "sector privado" in text or "recomendado" in text, (
        "E-180 falta branch sector privado · LUCIA recomendado"
    )
    # Branch sector privado: "Notificar a CCN-CERT cualquier incidente" + "LUCIA aplica con caracter recomendado"
    assert "Notificar a CCN-CERT" in text, "E-180 falta notificacion CCN-CERT base"
    assert "recomendado" in text, "E-180 sector privado falta LUCIA recomendado"
    # Compromiso mantenimiento + art 31/33
    assert "art" in text.lower() and "33" in text, "E-180 falta art 33 incidentes"
    assert "art" in text.lower() and "31" in text, "E-180 falta art 31 cambios"
    # Firma RSEG
    assert "Marcos Lopez Perez" in text, "E-180 falta firma RSEG nombre"
    assert "marcos@test-sgsi.es" in text, "E-180 falta firma RSEG email"


def test_e180_sector_publico_branch_activates_lucia_obligatorio(tmp_path):
    """E-180 con cliente.sector_aplicacion='publico' · branch LUCIA obligatorio
    art. 33 RD 311/2022 (vs sector privado · recomendado)."""
    ctx = _build_sgsi_context("BASICA")
    ctx["cliente"]["sector_aplicacion"] = "publico"

    template_path = VAR_TEMPLATES / "E-180.docx"
    output_path = tmp_path / "E-180_publico.docx"
    render_docx(template_path, ctx, output_path)

    doc = DocxDocument(str(output_path))
    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text

    # Branch sector publico activado · LUCIA obligatorio
    assert "LUCIA" in text, "E-180 sector publico falta LUCIA referencia"
    assert "art. 33" in text or "33 RD" in text, "E-180 falta art 33"
    # NO branch sector privado (recomendado bajo ENS)
    assert "LUCIA aplica con car" not in text, (
        "E-180 NO debe contener branch privado cuando sector=publico"
    )
