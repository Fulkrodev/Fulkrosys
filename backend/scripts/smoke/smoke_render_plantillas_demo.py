"""Smoke render 5 plantillas criticas ENS con cliente piloto sintetico.

Usa el render production-grade de m06 (render_docx + DOCX precompiled en
var/templates_docx/) con contexto Jinja completo de un cliente piloto demo.

Output: DOCX renderizados en /tmp/fulkro-renders/ para inspeccion manual
Marcos. Validacion automatica: bytes > 5KB · sin placeholders leak ·
campos clave presentes.

Usage:
    .venv/bin/python backend/scripts/smoke/smoke_render_plantillas_demo.py
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from docx import Document as DocxDocument

from backend.app.motors.m06_document_factory.rendering import render_docx

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DOCX_DIR = REPO_ROOT / "var" / "templates_docx"
OUTPUT_DIR = Path("/tmp/fulkro-renders")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PLANTILLAS_CRITICAS = [
    ("E-100", "politica_seguridad_ens"),
    ("E-101", "politica_proteccion_datos"),
    ("E-103", "politica_gestion_incidentes"),
    ("E-200", "procedimiento_analisis_riesgos"),
    ("E-214", "procedimiento_gestion_cambios"),
    # sub-lote 1.B.2 BCP/DRP
    ("E-401", "estrategias_continuidad"),
    ("E-402", "bcp_plan_continuidad"),
    ("E-403", "drp_recuperacion_desastres"),
    ("E-404", "plan_comunicaciones_crisis"),
    ("E-405", "plan_pruebas_continuidad"),
    ("E-406", "informe_pruebas_continuidad"),
    # sub-lote 1.B.3 LMS (architect-curated VERBATIM · ADR-LMS-001 OPCION B Moodle)
    ("E-500", "plan_anual_formacion"),
    ("E-501", "catalogo_materiales_formacion"),
    ("E-502", "registro_asistencia_evaluacion"),
    ("E-503", "informe_simulacros_phishing"),
    ("E-504", "cuadro_mando_kpis_lms"),
    # sub-lote 1.B.4 TECNICOS (architect-curated VERBATIM)
    ("E-700", "auditoria_interna_inicial_sgsi"),
    ("E-701", "auditoria_interna_pre_externa"),
    ("E-705", "informe_formal_phishing"),
    ("E-706", "tabletop_gestion_incidente"),
    ("E-707", "prueba_restauracion_backup"),
    ("E-708", "auditoria_externa_ens"),
    ("E-709", "ines_snapshot_anual"),
    # sub-lote 1.B.7.1.1 PROVEEDORES (architect-curated VERBATIM · OPCION C hibrida AMEND-014)
    ("E-600", "inventario_proveedores"),
    ("E-601", "cuestionario_onboarding_proveedor"),
    # sub-lote 1.B.7.1.2 PROVEEDORES (architect-curated VERBATIM · OPCION C hibrida AMEND-014)
    ("E-602", "informe_evaluacion_proveedor"),
    ("E-603", "plan_supervision_proveedor"),
    # sub-lote 1.B.7.1.3 PROVEEDORES (architect-curated VERBATIM · cierre OPCION C)
    ("E-604", "adenda_contractual_ens"),
    # sub-lote 1.B.8.B WHISTLEBLOWING (architect-curated VERBATIM · Ley 2/2023)
    ("W-001", "politica_sistema_interno_informacion"),
    ("W-002", "procedimiento_gestion_denuncias_proteccion_informante"),
    # sub-lote 1.B.8.C WEB-LEGAL (architect-curated VERBATIM · LSSI + RGPD + Guia AEPD Cookies)
    ("LW-001", "politica_privacidad_web"),
    ("LW-002", "politica_cookies"),
    ("LW-003", "aviso_legal_lssi"),
    # sub-lote 1.B.8.D LCSP declaraciones (architect-curated VERBATIM · Ley 9/2017)
    ("L-001", "declaracion_responsable_art140"),
    ("L-003", "compromiso_adscripcion_medios_art762"),
    ("L-004", "acreditacion_solvencia_tecnica_arts89_91"),
    ("L-005", "clausula_confidencialidad_aapp_art133"),
    # sub-lote 1.B.8.E LCSP DEUC aislado (architect-curated VERBATIM · UE 2016/7)
    ("L-002", "modelo_deuc_documento_europeo_unico_contratacion"),
    # sub-lote 1.B.8.F LCSP subrogacion (architect-curated VERBATIM · Ley 9/2017 Art. 130 + ET Art. 44)
    ("L-006", "compromiso_subrogacion_personal_art130_lcsp"),
    ("L-007", "anexo_subrogacion_listado_personal_convenio"),
    # sub-lote 1.B.9.A Gobierno SGSI + actas core (architect-curated VERBATIM)
    ("E-002", "acta_nombramiento_roles_ens"),
    ("E-003", "acta_constitucion_comite_seguridad"),
    ("E-012", "acta_aprobacion_categorizacion_y_da"),
    ("E-090", "informe_diagnostico_inicial_gap"),
    # sub-lote 1.B.9.B Ruta Basica lifecycle (architect-curated VERBATIM · RD 311/2022 art 30/33/35)
    ("E-041", "declaracion_conformidad_ens"),
    ("E-042", "comunicacion_cambio_material_sistema"),
    ("E-043", "renovacion_periodica_conformidad"),
    # sub-lote 1.B.9.C Retainer reporting (architect-curated VERBATIM · entregables periodicos cliente)
    ("E-614", "informe_trimestral_retainer"),
    ("E-615", "informe_anual_retainer"),
]

TODAY_ISO = date.today().isoformat()

CLIENTE_PILOTO_CONTEXT = {
    "cliente": {
        "razon_social": "Empresa Demo SL",
        "nombre_comercial": "Empresa Demo",
        "cif": "B12345678",
        "nif": "B12345678",  # templates ENS usan cliente.nif segun spec CCN-STIC 805
        "sector": "servicios_TIC",
        "categoria_ens": "BASICA",
        "representante_legal": "Director General Demo",
        "organo_aprobador_politicas": "Comite de Direccion de Empresa Demo SL",
        "domicilio_social": "Calle Demo 1, 28001 Madrid",
        "telefono": "+34 910 000 000",
        "email_contacto": "info@empresademo.example",
        "header_brand": "Empresa Demo SL",
        "logo_path": "",
    },
    "proyecto": {
        "codigo_documento_base": "EMP-ENS-2026",
        "version_actual": "1.0",
        "fecha_aprobacion_inicial": TODAY_ISO,
        "fecha_fin": "2026-12-31",
        "proxima_revision": "2027-05-17",
        "categoria_ens": "BASICA",
        "alcance": "Plataforma SaaS Demo (produccion + staging)",
        "sistema_principal": "Plataforma SaaS Demo",
    },
    "responsables": {
        "responsable_seguridad": {
            "nombre": "Marcos Demo",
            "cargo": "CISO interim",
            "email": "marcos.demo@empresademo.example",
            "telefono": "+34 910 000 001",
        },
        "responsable_sistema": {
            "nombre": "Sara Tecnica Demo",
            "cargo": "CTO",
            "email": "sara.demo@empresademo.example",
        },
        "responsable_servicio": {
            "nombre": "Pablo Operaciones Demo",
            "cargo": "Head of Ops",
            "email": "pablo.demo@empresademo.example",
        },
        "responsable_informacion": {
            "nombre": "Lucia Datos Demo",
            "cargo": "DPO",
            "email": "lucia.demo@empresademo.example",
        },
        "comite_seguridad": {
            "presidente": "Director General Demo",
            "secretario": "Marcos Demo",
            "miembros": ["CISO", "CTO", "DPO", "Head of Ops", "Legal"],
            "frecuencia": "semestral",
        },
        "consultor": {
            "nombre": "Marcos Mata Garcia",
            "cargo": "Consultor independiente en ENS",
            "email": "marcosmata@fulkro.es",
            "header_brand": "FULKRO - Marcos Mata",
        },
    },
    "consultor": {
        "nombre": "Marcos Mata Garcia",
        "cargo": "Consultor independiente en ENS",
        "header_brand": "FULKRO - Marcos Mata",
    },
    # BCP/DRP context (sub-lote 1.B.2 · architect-curated · structures para
    # plantillas E-401 a E-406 architect-VERBATIM).
    "procesos_criticos": [
        {"nombre": "Atencion al cliente SaaS", "rto": "4h", "rpo": "1h", "criticidad": "Alta",
         "descripcion": "Plataforma SaaS Demo principal · contrato SLA 99.5%"},
        {"nombre": "Facturacion y cobros", "rto": "24h", "rpo": "8h", "criticidad": "Media",
         "descripcion": "Ciclo mensual de facturacion a clientes"},
        {"nombre": "Soporte tecnico nivel 2", "rto": "8h", "rpo": "N/A", "criticidad": "Media",
         "descripcion": "Resolucion de incidencias clientes"},
    ],
    "estrategias": [
        {"proceso": "Atencion al cliente SaaS", "estrategia": "Redundancia activa multi-AZ",
         "coste_estimado": "Incluido en operacion", "responsable": "CTO", "plazo": "Operativa"},
        {"proceso": "Facturacion y cobros", "estrategia": "Backup diario + procedimiento manual contingencia",
         "coste_estimado": "Bajo", "responsable": "CFO", "plazo": "Operativa"},
        {"proceso": "Soporte tecnico nivel 2", "estrategia": "Teletrabajo desde ubicaciones alternas",
         "coste_estimado": "Minimo", "responsable": "Head of Ops", "plazo": "Operativa"},
    ],
    "ubicaciones_alternas": [
        {"nombre": "Coworking Madrid", "direccion": "Calle Alterna 10, Madrid",
         "capacidad": "10 puestos", "tiempo_activacion": "4h"},
    ],
    "proveedores_criticos": [
        {"nombre": "Hetzner Online GmbH", "tipo_servicio": "Hosting cloud principal",
         "sla": "99.9%", "contacto_emergencia": "+49 911 234 56 78"},
        {"nombre": "Cloudflare", "tipo_servicio": "CDN + WAF + DNS",
         "sla": "99.99%", "contacto_emergencia": "support@cloudflare.com"},
    ],
    "servicios_criticos": [
        {"nombre": "Atencion al cliente SaaS", "rto": "4h", "responsable": "CTO",
         "procedimiento": "Failover automatico multi-AZ + verificacion checklist",
         "recursos": "Equipo TIC + ventana ops"},
        {"nombre": "Facturacion y cobros", "rto": "24h", "responsable": "CFO",
         "procedimiento": "Procedimiento manual desde backup + reconciliacion",
         "recursos": "Equipo Finanzas + acceso bd respaldo"},
    ],
    "sistemas_criticos": [
        {"nombre": "API SaaS Plataforma", "funcion": "Servicio principal cliente",
         "rto": "1h", "rpo": "15min", "mecanismo": "Replicacion multi-AZ con auto-failover"},
        {"nombre": "BD PostgreSQL primaria", "funcion": "Almacenamiento operacional",
         "rto": "30min", "rpo": "5min", "mecanismo": "Streaming replication + PITR"},
        {"nombre": "MinIO almacenamiento", "funcion": "Documentos cliente",
         "rto": "2h", "rpo": "1h", "mecanismo": "Replicacion geo-distribuida"},
    ],
    "ubicaciones": {
        "primario": {"nombre": "Hetzner Helsinki", "direccion": "Helsinki, FI"},
        "secundario": {"nombre": "Hetzner Falkenstein", "direccion": "Falkenstein, DE",
                       "modalidad": "warm", "tiempo_activacion": "2h"},
    },
    "stakeholders": [
        {"tipo": "Empleados internos", "prioridad": "P1", "canal": "Email + Intranet",
         "responsable_interno": "RRHH", "plantilla_ref": "Sec 3.1", "plazo": "Inmediato"},
        {"tipo": "Clientes afectados", "prioridad": "P1", "canal": "Portal cliente + Email",
         "responsable_interno": "Customer Success", "plantilla_ref": "Sec 3.2", "plazo": "<4h"},
        {"tipo": "AEPD (si brecha datos)", "prioridad": "P0", "canal": "Sede AEPD",
         "responsable_interno": "DPO", "plantilla_ref": "Sec 3.3.1", "plazo": "<72h"},
    ],
    "portavoces": [
        {"funcion": "Portavoz general", "titular": "Director General Demo",
         "suplente": "CTO", "audiencia": "Medios + Clientes"},
        {"funcion": "Portavoz tecnico", "titular": "CTO",
         "suplente": "CISO", "audiencia": "Clientes tecnicos + Auditores"},
    ],
    "autoridades_aplicables": [
        {"nombre": "AEPD", "regulacion": "RGPD-ART-33",
         "cuando": "Brecha datos personales con riesgo",
         "canal": "sedeagpd.gob.es", "plazo": "72h"},
        {"nombre": "INCIBE-CERT", "regulacion": "NIS2-ART-23 (si aplica)",
         "cuando": "Incidente significativo si NIS2 aplica",
         "canal": "incibe-cert.es", "plazo": "24h alerta · 72h detalle · 1 mes informe"},
    ],
    "ejercicios_planificados": [
        {"tipo": "Tabletop BCP", "fecha": "2026-Q1", "responsable": "CISO",
         "alcance": "Comite + coordinadores"},
        {"tipo": "Restauracion backup", "fecha": "2026-Q2", "responsable": "DBA",
         "alcance": "BD PostgreSQL"},
        {"tipo": "Failover simulacro", "fecha": "2026-Q3", "responsable": "CTO",
         "alcance": "API + BD primaria"},
        {"tipo": "Phishing campaign", "fecha": "Cada trimestre", "responsable": "CISO",
         "alcance": "Toda la plantilla"},
    ],
    "ejercicio": {
        "tipo": "Tabletop BCP", "fecha": "2026-03-15", "hora_inicio": "10:00", "hora_fin": "12:30",
        "duracion": "2h 30min",
        "escenario": "Ransomware afecta BD primaria · perdida 4h datos",
        "alcance": "Comite Continuidad + Coordinadores BCP/DRP/Operaciones",
        "facilitador": "Marcos Demo (CISO)",
        "observadores": "DPO + Auditor externo",
        "sistemas_involucrados": "BD PostgreSQL + Plataforma SaaS",
        "objetivos": [
            "Validar conocimiento procedimientos BCP por participantes",
            "Verificar plazos comunicacion AEPD <72h",
            "Identificar gaps en cadena de mando durante crisis",
        ],
        "participantes": [
            {"nombre": "Director General Demo", "rol_ejercicio": "Presidente Comite",
             "funcion_habitual": "CEO", "asistencia": "Presente"},
            {"nombre": "Marcos Demo", "rol_ejercicio": "Coordinador BCP",
             "funcion_habitual": "CISO", "asistencia": "Presente"},
            {"nombre": "Sara Tecnica Demo", "rol_ejercicio": "Coordinador DRP",
             "funcion_habitual": "CTO", "asistencia": "Presente"},
        ],
        "tasa_participacion": "100%",
        "cronologia": [
            {"timestamp": "10:00", "descripcion": "Apertura ejercicio · presentacion escenario"},
            {"timestamp": "10:15", "descripcion": "Inyeccion 1 · alerta SIEM ransomware"},
            {"timestamp": "10:30", "descripcion": "Activacion BCP por Comite"},
            {"timestamp": "11:00", "descripcion": "Inyeccion 2 · solicitud AEPD"},
            {"timestamp": "11:45", "descripcion": "Decision comunicacion clientes"},
            {"timestamp": "12:30", "descripcion": "Cierre ejercicio · debrief inicial"},
        ],
    },
    "metricas": {
        "rto_objetivo": "4h", "rto_real": "3h 45min (estimado en ejercicio)", "rto_cumplimiento": "OK Cumple",
        "rpo_objetivo": "1h", "rpo_real": "45min (estimado)", "rpo_cumplimiento": "OK Cumple",
        "checklist_pct": 92, "checklist_estado": "OK Cumple",
        "participacion_pct": 100, "participacion_estado": "OK Cumple",
        "integridad_pct": 98, "integridad_estado": "WARN Revisar 2% inconsistente",
    },
    "observaciones": {
        "positivas": ["Decision rapida activacion BCP <30min", "Comunicacion interna fluida"],
        "negativas": ["Plantilla AEPD no estaba accesible inmediatamente · 15min busqueda"],
        "sorpresas": ["Equipo identifico dependencia no documentada con proveedor Cloudflare"],
    },
    "gaps": [
        {"descripcion": "Plantilla notificacion AEPD no preconfigurada en herramienta crisis",
         "severidad": "Media", "afectado": "Comunicacion AEPD",
         "causa_raiz": "Plantilla en repositorio compartido pero sin acceso desde movil",
         "recomendacion": "Pre-configurar en app movil de crisis"},
        {"descripcion": "Dependencia Cloudflare no figuraba en matriz proveedores criticos",
         "severidad": "Alta", "afectado": "Continuidad servicio",
         "causa_raiz": "Falta auditoria inventario proveedores",
         "recomendacion": "Actualizar inventario proveedores · clasificar Cloudflare como critico"},
    ],
    "acciones_correctivas": [
        {"id": "AC-001", "descripcion": "Pre-cargar plantilla AEPD en app crisis",
         "gap_ref": "Gap 1", "responsable": "DPO", "plazo": "2026-04-15", "estado": "En curso"},
        {"id": "AC-002", "descripcion": "Auditar y actualizar matriz proveedores criticos",
         "gap_ref": "Gap 2", "responsable": "CISO", "plazo": "2026-04-30", "estado": "Pendiente"},
    ],
    "lecciones": [
        "Inventario proveedores criticos debe revisarse trimestralmente",
        "Plantillas legales deben ser accesibles desde dispositivos moviles en crisis",
        "Tabletop semestrales son efectivos para detectar gaps de gobierno",
    ],
    "recomendaciones_siguiente": [
        "Proximo ejercicio Q3 2026 · escenario perdida ubicacion fisica",
        "Incorporar como observador a un cliente externo voluntario",
    ],
    "valoracion_global": "Satisfactorio · 2 gaps detectados con plan accion · sin bloqueantes criticos",
    "conclusion_texto": "El ejercicio ha permitido validar el conocimiento operativo del BCP por parte del Comite de Continuidad y de los coordinadores. Los gaps identificados son menores y se abordan en el plan de accion correctivo. Se recomienda mantener el calendario semestral.",
    # LMS context (sub-lote 1.B.3 · plantillas E-500 a E-504)
    "lms": {"plataforma": "Moodle Workplace", "phishing_plataforma": "GoPhish"},
    "periodo": {"trimestre": "Q1", "anyo": "2026", "fecha_cierre": TODAY_ISO,
                "fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31"},
    "resumen": {"num_sesiones": 12, "num_asistencias": 145, "num_empleados_distintos": 48,
                "tasa_cumplimiento_pct": 92},
    "sesiones": [
        {"fecha": "2026-01-15", "modulo": "M-G1-001 Sesion acogida", "grupo": "G1",
         "convocados": 3, "asistentes": 3, "tasa": 100, "facilitador": "Marcos Demo"},
        {"fecha": "2026-02-10", "modulo": "M-G1-002 Phishing awareness", "grupo": "G1",
         "convocados": 50, "asistentes": 47, "tasa": 94, "facilitador": "RSEG"},
        {"fecha": "2026-03-05", "modulo": "M-G3-001 Config segura", "grupo": "G3",
         "convocados": 12, "asistentes": 11, "tasa": 92, "facilitador": "CTO Demo"},
    ],
    "empleados": [
        {"nombre": "Empleado 001", "rol": "Backend Dev", "grupo": "G3", "horas_plan": 16,
         "horas_completadas": 14, "cumplimiento_pct": 88, "estado": "Parcial"},
        {"nombre": "Empleado 002", "rol": "CTO", "grupo": "G4", "horas_plan": 24,
         "horas_completadas": 26, "cumplimiento_pct": 108, "estado": "Cumple"},
    ],
    "nuevas_incorporaciones": [
        {"nombre": "Nuevo 001", "fecha_alta": "2026-01-20", "fecha_acogida": "2026-02-10",
         "en_plazo": "Si"},
    ],
    "kpi_acogida_pct": "100",
    "evaluaciones": [
        {"modulo": "M-G1-001", "num_participantes": 3, "puntuacion_media": "85",
         "tasa_aprobado": 100},
        {"modulo": "M-G1-002", "num_participantes": 47, "puntuacion_media": "78",
         "tasa_aprobado": 89},
    ],
    "brechas": [
        {"empleado_o_grupo": "Empleado 001", "grupo": "G3",
         "descripcion_brecha": "2h por debajo del minimo anual G3",
         "accion_correctiva": "Completar modulo M-G3-002 antes de Q2",
         "plazo": "2026-06-30"},
    ],
    "observaciones_responsable": "Periodo dentro de objetivos · 1 brecha individual en seguimiento.",
    # E-503 phishing campania
    "campania": {"id": "PH-2026-Q1", "nombre": "Phishing Q1 IT-Sec Helpdesk",
                 "trimestre": "Q1", "anyo": "2026", "plataforma": "GoPhish",
                 "fecha_envio": "2026-02-15", "duracion": "14 dias",
                 "tipo_escenario": "Suplantacion IT-Sec solicitud reset password",
                 "dificultad": "Media", "plantillas": "1 email + landing aprendizaje",
                 "total_destinatarios": 50,
                 "objetivos": ["Medir tasa click trimestral",
                               "Identificar empleados reincidentes"]},
    "segmentos": [
        {"nombre": "Todos empleados", "num_destinatarios": 50,
         "justificacion": "Cobertura total G1"},
    ],
    "resultados": {"entregados": 50, "abiertos": 38, "tasa_abierto": 76,
                   "clicks": 4, "tasa_click": 8, "credenciales": 1, "tasa_credenciales": 2,
                   "reportes": 28, "tasa_reporte": 56, "ignorados": 18, "tasa_ignorados": 36},
    "segmentos_analisis": [
        {"nombre": "Todos empleados", "tasa_click": 8, "tasa_reporte": 56,
         "delta_anterior": "Mejora vs Q4-2025 (12% click)"},
    ],
    "patrones": {"recurrentes": "0 empleados", "areas_alta": "Ninguna",
                 "areas_mejora": "Equipo soporte",
                 "early_reporters": "5 empleados primeros 10min"},
    "acciones_colectivas": [
        {"id": "PH-AC-001", "descripcion": "Pildora refresco phishing Q2",
         "audiencia": "Todos empleados", "responsable": "CISO", "plazo": "2026-04-30"},
    ],
    "recomendaciones": [
        "Mantener frecuencia trimestral",
        "Aumentar dificultad escenario en Q2 (suplantacion proveedor)",
    ],
    # E-504 KPIs consolidados
    "kpis": {
        "cobertura_plan_pct": 92, "acogida_pct": 100, "g3g4_horas_pct": 88,
        "phishing_click_pct": 8, "phishing_reporte_pct": 56, "quiz_aprobado_pct": 91,
        "estado_global": "Satisfactorio",
        "acogida": {"nuevos": 3, "completadas": 3, "fuera_plazo": 0, "estado": "OK"},
        "phishing_tendencia": "Mejora 4pp vs Q4-2025",
    },
    "cobertura_por_grupo": [
        {"grupo": "G1", "asignados": 50, "completados": 47, "cobertura_pct": 94, "estado": "OK"},
        {"grupo": "G3", "asignados": 12, "completados": 11, "cobertura_pct": 92, "estado": "OK"},
        {"grupo": "G4", "asignados": 5, "completados": 5, "cobertura_pct": 100, "estado": "OK"},
    ],
    "g3g4_detalle": [
        {"nombre": "Empleado 001", "grupo": "G3", "plan": 16, "real": 14, "pct": 88,
         "estado": "Parcial"},
        {"nombre": "Empleado 002", "grupo": "G4", "plan": 24, "real": 26, "pct": 108,
         "estado": "OK"},
    ],
    "phishing_campanias": [
        {"nombre": "PH-2026-Q1", "fecha": "2026-02-15", "destinatarios": 50,
         "tasa_click": 8, "tasa_reporte": 56},
    ],
    "quizzes": [
        {"modulo": "M-G1-001", "participantes": 3, "media": "85", "tasa_aprobado": 100},
        {"modulo": "M-G1-002", "participantes": 47, "media": "78", "tasa_aprobado": 89},
    ],
    "conclusiones_texto": "El programa cumple objetivos globales del Plan E-500. Una brecha individual en G3 con plan de accion en curso.",
    "areas_mejora": [
        {"area": "Tasa reporte phishing",
         "descripcion": "56% supera objetivo 50% pero margen de mejora",
         "accion": "Promover canal de reporte rapido tipo boton en cliente email"},
    ],
    "acciones_siguiente": [
        {"id": "AS-Q2-001", "descripcion": "Lanzar pildora refresco G1",
         "responsable": "RSEG", "plazo": "2026-04-30", "estado": "Pendiente"},
    ],
    "elevaciones_comite": ["Aprobar presupuesto pildora Q2",
                            "Decidir incorporacion modulo IA Act"],
}


# Sub-lote 1.B.4 TECNICOS extensions (E-700/E-701/E-705/E-706/E-707/E-708/E-709).
# Aplicadas como mutaciones post-construccion para preservar legibilidad del literal
# original y poder fusionar dicts existentes (cliente, resumen, metricas, campania).
CLIENTE_PILOTO_CONTEXT["cliente"].update({
    "direccion": "Calle Demo 1, 28001 Madrid",
    "ambito_ens": "Plataforma SaaS Demo (produccion + staging)",
    "num_empleados_alcance": 50,
})
CLIENTE_PILOTO_CONTEXT["resumen"].update({
    # E-700 auditoria interna inicial
    "total_auditadas": 73, "conformidad_pct": 85,
    # E-701 pre-externa
    "ncs_iniciales": 6, "ncs_cerradas": 5, "ncs_pendientes": 1, "ncs_nuevas": 2,
    # E-708 externa
    "total": 73,
})
CLIENTE_PILOTO_CONTEXT["metricas"].update({
    # E-707 RTO/RPO restauracion
    "rto_objetivo": "30min", "rto_real": "27min", "rto_cumplimiento": "OK Cumple",
    "rpo_objetivo": "5min", "rpo_real": "4min", "rpo_cumplimiento": "OK Cumple",
    "tiempo_descifrado": "3min", "tiempo_validacion": "8min", "tiempo_funcional": "12min",
})
CLIENTE_PILOTO_CONTEXT["campania"].update({
    # E-705 informe formal phishing (extiende E-503)
    "fecha_inicio": "2026-02-15", "fecha_fin": "2026-02-28",
    "tipo": "Spearphishing simulado (T1566.002)",
    "sector_simulado": "Helpdesk IT-Sec",
    "modalidad": "campania singular ad-hoc pre-auditoria externa",
    "autorizacion": "Comite de Seguridad acta 2026-02-01",
})

CLIENTE_PILOTO_CONTEXT.update({
    # E-700 / E-701 · auditoria interna
    "auditoria": {
        "periodo_inicio": "2025-06-01", "periodo_fin": "2026-05-15",
        "fecha_inicio": "2026-05-10", "fecha_fin": "2026-05-15",
        "equipo_auditor": "Marcos Mata (auditor jefe) + Sara Tecnica (auditor)",
        "auditor_jefe": "Marcos Mata Garcia",
        "e700_ref": "EMP-ENS-2026-700 v1.0",
        "externa_fecha": "2026-06-30",
    },
    "resultados_por_familia": [
        {"nombre": "org", "aplicables": 4, "conformes": 4, "nc_menores": 0,
         "nc_mayores": 0, "observaciones": 0, "no_aplica": 0},
        {"nombre": "op", "aplicables": 28, "conformes": 24, "nc_menores": 3,
         "nc_mayores": 1, "observaciones": 2, "no_aplica": 0},
        {"nombre": "mp", "aplicables": 41, "conformes": 35, "nc_menores": 4,
         "nc_mayores": 0, "observaciones": 5, "no_aplica": 2},
    ],
    "no_conformidades": [
        {"id": "NC-001", "medida": "op.exp.7", "tipo": "menor",
         "descripcion": "Registro incompleto incidente 2025-09",
         "severidad": "Media", "plazo": "2026-06-15"},
        {"id": "NC-002", "medida": "mp.per.3", "tipo": "menor",
         "descripcion": "2 empleados sin formacion anual completa",
         "severidad": "Baja", "plazo": "2026-06-30"},
        {"id": "NC-003", "medida": "op.cont.3", "tipo": "mayor",
         "descripcion": "Prueba restauracion 2025 no documentada formalmente",
         "severidad": "Alta", "plazo": "2026-06-10"},
    ],
    "plan_acciones": [
        {"id": "AC-001", "nc_ref": "NC-001", "descripcion": "Completar registro LUCIA",
         "responsable": "CISO", "plazo": "2026-06-15", "estado": "En curso"},
        {"id": "AC-002", "nc_ref": "NC-002", "descripcion": "Convocar sesion refuerzo",
         "responsable": "RSEG", "plazo": "2026-06-30", "estado": "Planificado"},
        {"id": "AC-003", "nc_ref": "NC-003", "descripcion": "Ejecutar y documentar prueba E-707",
         "responsable": "CTO", "plazo": "2026-06-10", "estado": "En curso"},
    ],
    "conclusion": {
        "estado_global": "Conforme con NCs menores y 1 NC mayor en cierre",
        "texto": "El SGSI esta operativo y razonablemente maduro. Las No Conformidades "
                 "detectadas tienen plan de cierre aprobado y son abordables antes de la "
                 "auditoria externa programada.",
        "recomendacion_externa": "Avanzar con la auditoria externa una vez cerradas las NCs mayores",
        "estado": "Listo con condiciones",
        "recomendacion": "Cierre formal de NC-003 antes de la auditoria externa",
    },
    # E-701 cierre NCs
    "cierre_ncs": [
        {"id": "NC-001", "tipo": "menor", "descripcion": "Registro incidente 2025-09",
         "accion": "Registro completado y verificado", "evidencia": "Captura LUCIA",
         "estado": "Cerrada"},
        {"id": "NC-003", "tipo": "mayor", "descripcion": "Prueba restauracion no documentada",
         "accion": "Ejecutada y documentada", "evidencia": "Informe E-707 v1.0",
         "estado": "Cerrada"},
    ],
    "nuevas_ncs": [
        {"id": "NC-101", "medida": "mp.com.4", "tipo": "menor",
         "descripcion": "Politica cifrado en transito sin revision anual reciente",
         "severidad": "Baja", "plazo": "2026-06-25"},
    ],
    "documentos_revisados": [
        {"nombre": "Politica Seguridad E-100", "version": "1.2",
         "aprobado_por": "Comite Direccion", "fecha": "2025-12-15", "coherencia": "OK"},
        {"nombre": "DdA v3", "version": "3.0",
         "aprobado_por": "CISO", "fecha": "2026-01-10", "coherencia": "OK"},
    ],
    "puntos_riesgo": [
        {"area": "Inventario activos", "descripcion": "3 activos sin clasificacion",
         "mitigacion": "Completar etiquetado antes externa", "plazo": "2026-06-20"},
    ],
    # E-705 phishing formal
    "escenario": {
        "descripcion": "Email simulando IT-Sec solicitando reset password tras supuesto "
                       "intento de acceso no autorizado · landing controlada captura "
                       "comportamiento sin retencion credenciales reales.",
    },
    "infraestructura": {
        "dominio_remitente": "it-secure-demo.example",
        "plataforma_envio": "GoPhish 0.12",
        "landing": "https://landing.it-secure-demo.example/auth",
        "captura": "Token UUID v4 anonimo · sin persistencia credenciales",
        "tracking": "GoPhish events API",
    },
    "segmentacion": [
        {"nombre": "Toda la plantilla", "justificacion": "Ejercicio singular pre-externa",
         "numero": 50},
    ],
    "campanyas_previas": [
        {"id": "PH-2025-Q4", "fecha": "2025-11-15",
         "tasa_click": 12, "tasa_reporte": 48, "variacion": "-"},
        {"id": "PH-2026-Q1", "fecha": "2026-02-15",
         "tasa_click": 8, "tasa_reporte": 56, "variacion": "-4pp click · +8pp reporte"},
    ],
    "tendencia_texto": "Mejora sostenida: tasa click descendio 4 puntos vs Q4-2025 y la "
                        "tasa de reporte ascendio 8 puntos en el mismo intervalo.",
    "analisis_segmentos": [
        {"segmento": "Toda la plantilla",
         "descripcion": "Comportamiento general homogeneo · sin areas criticas"},
    ],
    "señales_detectadas": [
        "Remitente con dominio externo no corporativo",
        "Urgencia injustificada en el cuerpo del mensaje",
        "Enlace no coincide con dominio corporativo al pasar el cursor",
    ],
    "señales_no_detectadas": [
        "Firma visual del 'it-sec' que imitaba la corporativa con un caracter alterado",
    ],
    "valoracion": "Resultado positivo · 56% tasa de reporte por encima del benchmark "
                   "sectorial (~40%) · 8% tasa click dentro de objetivos.",
    # E-706 tabletop
    "inyecciones": [
        {"tiempo": "T+0min", "descripcion": "Alerta SIEM detecta cifrado masivo BD",
         "reaccion_esperada": "Activacion del Comite de Crisis"},
        {"tiempo": "T+30min", "descripcion": "AEPD solicita informacion preliminar",
         "reaccion_esperada": "Preparar notificacion Art.33 RGPD"},
        {"tiempo": "T+90min", "descripcion": "Periodista contacta solicitando declaracion",
         "reaccion_esperada": "Activar portavoz aprobado"},
    ],
    "participantes": [
        {"nombre": "Director General Demo", "rol_ejercicio": "Presidente Comite Crisis",
         "funcion_habitual": "CEO", "asistencia": "Presente"},
        {"nombre": "Marcos Demo", "rol_ejercicio": "Coordinador respuesta",
         "funcion_habitual": "CISO", "asistencia": "Presente"},
        {"nombre": "Lucia Datos Demo", "rol_ejercicio": "Responsable notificacion AEPD",
         "funcion_habitual": "DPO", "asistencia": "Presente"},
    ],
    "cronologia": [
        {"timestamp": "10:00", "descripcion": "Apertura ejercicio · presentacion escenario"},
        {"timestamp": "10:05", "descripcion": "Backup identificado en S3 region eu-west-1"},
        {"timestamp": "10:08", "descripcion": "Aprobado restauracion en entorno aislado"},
        {"timestamp": "10:35", "descripcion": "Restauracion BD PostgreSQL completada"},
        {"timestamp": "10:43", "descripcion": "Validacion hash integridad OK"},
        {"timestamp": "10:55", "descripcion": "Validacion funcional smoke OK"},
        {"timestamp": "11:05", "descripcion": "Destruccion entorno aislado"},
    ],
    "plazos": {
        "aepd_real": "62 min", "aepd_estado": "OK <72h",
        "nis2_inicial": "18 min", "nis2_inicial_estado": "OK <24h",
        "nis2_detallada": "65 min", "nis2_detallada_estado": "OK <72h",
        "interesados": "120 min", "interesados_estado": "OK sin dilacion",
        "lucia": "Registrado T+45min", "lucia_estado": "OK Conforme guia",
        "dora": "N/A", "dora_estado": "No aplica",
    },
    "eficacia_e204": [
        {"apartado": "Deteccion + clasificacion", "aplicado": "Si", "eficaz": "Si",
         "comentario": "Clasificacion en P1 inmediata"},
        {"apartado": "Notificacion AEPD <72h", "aplicado": "Si", "eficaz": "Si",
         "comentario": "Plantilla disponible y completada en plazo"},
        {"apartado": "Comunicacion clientes", "aplicado": "Si", "eficaz": "Parcial",
         "comentario": "Decision retardada 15 min por consulta legal"},
    ],
    "gaps_e706": [
        {"descripcion": "Demora 15 min decision comunicacion clientes",
         "severidad": "Media", "procedimiento": "E-204 sec 3.2",
         "accion": "Pre-aprobar plantillas comunicacion en Comite",
         "responsable": "Legal + Comunicacion", "plazo": "2026-06-30"},
    ],
    # E-707 restauracion backup
    "prueba": {
        "id": "RT-2026-Q2-001",
        "sistema": "BD PostgreSQL primaria Plataforma SaaS",
        "tipo": "Restauracion completa desde backup cifrado",
        "modalidad": "En entorno aislado · no afecta produccion",
        "fecha": "2026-05-12", "hora_inicio": "10:00", "hora_fin": "11:05",
        "duracion": "1h 05min",
        "operador": "Sara Tecnica Demo (DBA)",
        "verificador": "Marcos Demo (CISO)",
    },
    "backup": {
        "id": "BCK-2026-05-11-full", "tipo": "Completa cifrada",
        "fecha": "2026-05-11 02:00 UTC",
        "tamaño": "45 GB", "ubicacion": "S3 eu-west-1 cifrado SSE-KMS",
        "cifrado": "Si", "algoritmo": "AES-256-GCM (KMS)",
        "hash_verificado": "OK SHA256 coincide con manifest",
    },
    "entorno": {
        "tipo": "Instancia EC2 aislada t3.large",
        "aislamiento": "VPC dedicada sin peering",
        "recursos": "4 vCPU · 16 GB RAM · 100 GB SSD",
        "red": "Security Group egress=deny",
        "no_interferencia": "Confirmada · zero impacto produccion",
    },
    "validaciones_integridad": [
        {"prueba": "Hash SHA256 dump", "esperado": "Coincide con manifest backup",
         "obtenido": "OK Coincide", "estado": "OK"},
        {"prueba": "Numero filas tabla principal", "esperado": "12.345.678",
         "obtenido": "12.345.678", "estado": "OK"},
    ],
    "validaciones_funcionales": [
        {"funcionalidad": "Login usuario sintetico", "esperado": "Acceso correcto",
         "obtenido": "OK Acceso correcto", "estado": "OK"},
        {"funcionalidad": "Query SELECT muestra 100 filas", "esperado": "100 filas",
         "obtenido": "100 filas", "estado": "OK"},
    ],
    "incidencias": [
        {"id": "INC-RT-001", "descripcion": "Tiempo descifrado 3min mayor que estimado",
         "causa": "Throughput KMS regional",
         "impacto": "Sin impacto sobre RTO objetivo",
         "resolucion": "Documentar baseline KMS"},
    ],
    "hallazgos": [
        {"descripcion": "Falta documentar baseline tiempo descifrado",
         "severidad": "Baja", "accion": "Anexar tiempos KMS al runbook",
         "responsable": "DBA", "plazo": "2026-06-15", "estado": "Pendiente"},
    ],
    # E-708 auditoria externa
    "auditoria_externa": {
        "entidad_auditora": "Entidad Certificadora Demo ENAC",
        "acreditacion": "ENAC 999/C-AC999",
        "auditor_jefe": "Ana Auditora Externa",
        "equipo": "Ana Auditora + Carlos Auditor Tecnico",
        "fecha_inicio": "2026-06-30", "fecha_fin": "2026-07-02",
        "ciclo": "Auditoria de certificacion inicial",
        "modalidad": "On-site + revision documental remota",
    },
    "resultados_externa_familia": [
        {"nombre": "org", "aplicables": 4, "conformes": 4, "nc_menores": 0,
         "nc_mayores": 0, "no_aplica": 0},
        {"nombre": "op", "aplicables": 28, "conformes": 27, "nc_menores": 1,
         "nc_mayores": 0, "no_aplica": 0},
        {"nombre": "mp", "aplicables": 41, "conformes": 38, "nc_menores": 1,
         "nc_mayores": 0, "no_aplica": 2},
    ],
    "ncs_externas": [
        {"id": "NCE-001", "medida": "op.exp.7", "tipo": "menor",
         "descripcion": "Procedimiento gestion incidentes sin revision anual formal",
         "plazo": "2026-09-30"},
        {"id": "NCE-002", "medida": "mp.info.6", "tipo": "menor",
         "descripcion": "Falta evidencia rotacion claves cifrado backup ultimo trimestre",
         "plazo": "2026-09-15"},
    ],
    "observaciones_externas": [
        {"id": "OBS-E-001", "medida": "mp.per.3",
         "descripcion": "Cobertura formacion 94% · margen mejora hasta 100%",
         "recomendacion": "Lanzar pildora trimestral refuerzo"},
    ],
    "evidencias_revisadas": [
        {"nombre": "Politica Seguridad E-100 v1.2", "tipo": "Politica",
         "periodo": "2025-2026", "estado": "OK Vigente"},
        {"nombre": "Registro incidentes LUCIA", "tipo": "Registro",
         "periodo": "ultimos 12m", "estado": "OK Completo"},
        {"nombre": "Informe E-707 restauracion 2026-05", "tipo": "Informe",
         "periodo": "2026-05", "estado": "OK Conforme"},
    ],
    "dictamen": {
        "resultado": "FAVORABLE CON OBSERVACIONES",
        "fundamentacion": "El sistema cumple los requisitos del ENS para la categoria "
                          "BASICA declarada. Las 2 No Conformidades menores detectadas "
                          "no comprometen la certificacion y se exigen para el proximo "
                          "ciclo. Las observaciones suponen oportunidad de mejora.",
    },
    "propuesta_certificacion": "Procede certificacion ENS categoria BASICA · vigencia 2 anos",
    "vigencia_certificacion": "24 meses desde fecha emision dictamen",
    "proxima_auditoria": "Seguimiento a 12 meses (2027-07)",
    "acciones_correctivas_exigidas": [
        {"id": "ACE-001", "nc_ref": "NCE-001",
         "descripcion": "Realizar revision anual del E-204 y firmar acta",
         "plazo": "2026-09-30",
         "verificacion": "Adjuntar acta firmada a expediente certificacion"},
        {"id": "ACE-002", "nc_ref": "NCE-002",
         "descripcion": "Documentar evidencia rotacion claves KMS",
         "plazo": "2026-09-15",
         "verificacion": "Captura panel KMS + acta CISO"},
    ],
    # E-709 INES snapshot
    "ines": {
        "año": "2026", "fecha_snapshot": "2026-12-31",
        "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31",
        "fecha_envio": "2027-01-31",
    },
    "sistemas_declarados": [
        {"nombre": "Plataforma SaaS Demo", "alcance": "Produccion + staging",
         "categoria": "BASICA", "estado_certificacion": "Certificado",
         "proxima_auditoria": "2027-07"},
    ],
    "madurez": {
        "confidencialidad": {"objetivo": "E3", "real": "E3", "estado": "OK Cumple"},
        "integridad": {"objetivo": "E3", "real": "E3", "estado": "OK Cumple"},
        "disponibilidad": {"objetivo": "E3", "real": "E2", "estado": "WARN -1 nivel"},
        "autenticidad": {"objetivo": "E3", "real": "E3", "estado": "OK Cumple"},
        "trazabilidad": {"objetivo": "E3", "real": "E3", "estado": "OK Cumple"},
    },
    "cumplimiento_familia": [
        {"nombre": "org", "aplicables": 4, "cumplidas": 4, "parciales": 0,
         "no_cumplidas": 0, "pct": 100},
        {"nombre": "op", "aplicables": 28, "cumplidas": 27, "parciales": 1,
         "no_cumplidas": 0, "pct": 96},
        {"nombre": "mp", "aplicables": 41, "cumplidas": 38, "parciales": 1,
         "no_cumplidas": 0, "pct": 95},
    ],
    "cumplimiento_global": 96,
    "incidentes_periodo": [
        {"id": "INC-2026-001", "fecha": "2026-03-10", "tipo": "Phishing exitoso menor",
         "severidad": "Baja", "reportado": "No (no aplicable)", "cerrado": "Si"},
    ],
    "resumen_incidentes": {"total": 3, "notificados": 0},
    "auditorias_periodo": [
        {"tipo": "Auditoria interna inicial", "fecha": "2026-05-15",
         "resultado": "Conforme con NCs menores", "documento": "E-700 v1.0"},
        {"tipo": "Auditoria externa ENAC", "fecha": "2026-07-02",
         "resultado": "FAVORABLE CON OBSERVACIONES", "documento": "E-708 v1.0"},
    ],
    "formacion": {
        "cobertura_pct": 94, "acogida_pct": 100,
        "click_pct": 8, "reporte_pct": 56,
    },
    "riesgos": {
        "total": 42, "alto_residual": 0, "tratados": 18, "seguimiento": 24,
    },
    "inversion": {
        "infraestructura": "EUR 12.500",
        "servicios": "EUR 18.000",
        "formacion": "EUR 3.500",
        "personal": "0,5 FTE",
        "total": "EUR 34.000 + 0,5 FTE",
    },
    "evolucion": [
        {"indicador": "Cumplimiento Anexo II %", "año_anterior": "88%",
         "año_actual": "96%", "variacion": "+8pp"},
        {"indicador": "Incidentes con notificacion", "año_anterior": 1,
         "año_actual": 0, "variacion": "-1"},
    ],
    "hitos_año": [
        "Certificacion ENS BASICA obtenida en julio 2026",
        "Implantacion LMS Moodle Workplace integrado",
        "3 pruebas de restauracion exitosas",
    ],
    "objetivos_proximo": [
        "Mantener certificacion ENS · auditoria seguimiento 2027",
        "Subir Disponibilidad de E2 a E3 (multi-region)",
        "Reducir tasa click phishing por debajo del 5%",
    ],
})


# Sub-lote 1.B.7.1.1 · PROVEEDORES context (E-600 + E-601)
# 3 proveedores sinteticos del target FULKRO empresa privada licitando (AMEND-012).
# Alineado con backend/tests/motors/m06_document_factory/conftest_proveedores.py.
CLIENTE_PILOTO_CONTEXT.update({
    "documento": {
        "codigo": "",  # se rellena en main loop (E-600 / E-601) o se deja vacio
        "version": "1.0",
        "fecha_emision": TODAY_ISO,
    },
    "proveedores": [
        {
            "razon_social": "CloudHost Iberia SL",
            "nif": "B11111111",
            "servicio_descripcion": "Hosting cloud productivo (compute + storage + red)",
            "categoria_servicio": "IaaS multi-tenant tenant aislado",
            "nivel_criticidad": "CRITICO",
            "fecha_inicio": "2025-01-01",
            "fecha_vencimiento": "2028-01-01",
            "next_review_date": "2026-12-31",
            "next_review_type": "Anual + ad-hoc en cambios",
            "next_review_owner": "Marcos Demo (CISO interim)",
            "contacto_operativo": {"nombre": "Juan Cloud", "email": "juan@cloudhost.example"},
            "normativas_aplicables": ["ENS", "RGPD", "NIS2"],
            "es_encargado_rgpd": True,
            "adenda_referencia": "ADENDA-ENS-2026-001",
            "last_assessment_date": "2026-05-15",
            "last_assessment_decision": "APROBADO",
            "observaciones": "Proveedor maduro · ENS ALTA + ISO 27001 + SOC2",
        },
        {
            "razon_social": "SaaS-CRM Solutions",
            "nif": "B22222222",
            "servicio_descripcion": "Plataforma SaaS CRM comercial",
            "categoria_servicio": "SaaS multi-tenant",
            "nivel_criticidad": "ALTO",
            "fecha_inicio": "2025-03-15",
            "fecha_vencimiento": "2027-03-14",
            "next_review_date": "2026-10-15",
            "next_review_type": "Anual",
            "next_review_owner": "Marcos Demo",
            "contacto_operativo": {"nombre": "Maria CRM", "email": "maria@saas-crm.example"},
            "normativas_aplicables": ["RGPD", "NIS2"],
            "es_encargado_rgpd": True,
            "adenda_referencia": None,
            "last_assessment_date": "2026-04-10",
            "last_assessment_decision": "CONDICIONAL",
            "observaciones": "Pendiente formalizar adenda RGPD Art 28",
        },
        {
            "razon_social": "Consultoria Cumplimiento Norte",
            "nif": "B33333333",
            "servicio_descripcion": "Servicios consultivos ENS/RGPD",
            "categoria_servicio": "Consultoria especializada",
            "nivel_criticidad": "MEDIO",
            "fecha_inicio": "2024-06-01",
            "fecha_vencimiento": None,
            "next_review_date": "2027-06-01",
            "next_review_type": "Bienal",
            "next_review_owner": "Lucia Datos Demo (DPO)",
            "contacto_operativo": {"nombre": "Pedro Consultor", "email": "pedro@cumplimiento.example"},
            "normativas_aplicables": ["RGPD"],
            "es_encargado_rgpd": False,
            "adenda_referencia": None,
            "last_assessment_date": "2025-12-01",
            "last_assessment_decision": "APROBADO",
            "observaciones": "Acceso ocasional bajo NDA",
        },
    ],
    "dependencias_criticas": [
        {
            "proveedor": "CloudHost Iberia SL",
            "descripcion_riesgo": "Concentracion infraestructura productiva en proveedor unico",
            "plan_contingencia": "Failover documentado a region eu-central · ejercicio 2026-Q3",
        },
    ],
    "proveedores_desvinculados": [],
    "proveedor": {
        # context single-proveedor para E-601 (cuestionario candidato) y
        # E-602/E-603 (evaluacion + supervision proveedor ya conocido) y
        # E-604 (adenda contractual · sub-lote 1.B.7.1.3 OPCION C cierre).
        # Usa CloudHost Iberia · primer proveedor (CRITICO) para
        # ejercitar branches APROBADO + nivel CRITICO + bloques RGPD+NIS2 (NO DORA).
        "id": "prov-cloudhost-001",
        "razon_social": "CloudHost Iberia SL",
        "nif": "B11111111",
        "servicio_descripcion": "Hosting cloud productivo (compute + storage + red)",
        "categoria_servicio": "IaaS multi-tenant tenant aislado",
        "categoria_servicio_ens": "ALTA",
        "nivel_criticidad": "CRITICO",
        "es_encargado_rgpd": True,
        "subcontrata": True,
        "domicilio": "Calle Cloud 1, 28013 Madrid",
        "pais_sede": "Espana",
        "volumen_eur": "120.000",
        "plazo_respuesta_dias": 20,
        # representante requerido por E-604 seccion 1 (Identificacion partes) + firmas
        "representante": {
            "nombre": "Carmen Cloud (CEO)",
            "cargo": "CEO · representante legal",
        },
        # normativas_aplicables requerido por E-604 condicionales bloques RGPD/NIS2/DORA
        "normativas_aplicables": ["ENS", "RGPD", "NIS2"],
    },
    "assessment": {
        # superset para E-602 · alineado con conftest_proveedores.ASSESSMENT_FULL
        # (no se importa para no acoplar tests-to-script · datos sinteticos).
        "id": "assessment-cloudhost-2026-001",
        "fecha_cuestionario": "2026-05-10",
        "fecha_decision": "2026-05-15",
        "valid_until": "2027-05-15",
        "evaluador": {
            "nombre": "Marcos Mata Garcia",
            "cargo": "Consultor independiente en ENS",
        },
        "aplica_nis2": True,
        "aplica_dora": False,
        "dimension_b": {
            "descripcion": "Declaracion ENS ALTA AENOR + ISO 27001 + SOC 2 Type II vigentes.",
            "evidencias": [
                "Declaracion ENS ALTA AENOR (Anexo B.1)",
                "ISO 27001 alcance Cloud Hosting (Anexo B.1.d)",
                "SOC 2 Type II 2025 (Anexo B.1.d)",
            ],
            "conclusion": "Conforme ENS ALTA · equivalencia clara con categoria ALTA cliente",
        },
        "dimension_c": {
            "descripcion": "Encargado tratamiento RGPD Art.28 con subencargados en EEE.",
            "categorias_datos": ["Identificativos", "Contacto profesional"],
            "transferencias": "Ninguna fuera EEE",
            "conclusion": "Contrato encargado tratamiento firmara como anexo E-604",
        },
        "dimension_d": {
            "descripcion": "Proveedor inscrito NIS2 como entidad esencial sector infra digital.",
            "conclusion": "NIS2 Art.21 acreditado · notificacion 24h aceptada",
        },
        "dimension_f": {
            "conclusion": "Capacidades tecnicas solidas · personal acreditado",
        },
        "certificaciones_vigentes": [
            "ENS ALTA (AENOR · noviembre 2025)",
            "ISO/IEC 27001:2022 (alcance Cloud Hosting)",
            "ISO/IEC 27017 (cloud-specific controls)",
            "SOC 2 Type II (2025)",
        ],
        "rto_horas": 4,
        "rpo_horas": 1,
        "bcp_aportado": True,
        "acepta_salida_30d": True,
        "notificacion_horas": 24,
        "colabora_ines": True,
        "hallazgos_positivos": [
            "Conformidad ENS ALTA directa",
            "RTO 4h dentro umbral CRITICO",
            "BCP documentado + ejercicios trimestrales",
        ],
        "hallazgos_criticos": [
            {
                "titulo": "Subencargado no notificado previamente",
                "descripcion": "CDN provider no declarado en cuestionario inicial.",
                "severidad": "MEDIA",
            },
        ],
        "scoring_por_seccion": {
            "B · ENS conformidad": 95,
            "C · RGPD Art.28": 88,
            "D · NIS2 Art.21": 92,
            "F · Capacidades tecnicas": 90,
            "G · Continuidad + salida": 94,
        },
        "scoring_total": 91,
        "nivel_criticidad_asignado": "CRITICO",
        "nivel_criticidad_justificacion": "Hosting cloud productivo · interrupcion detendria servicios esenciales.",
        "decision": "APROBADO",
        "condiciones": [],
    },
    # adenda + contrato_base requeridos por E-604 (sub-lote 1.B.7.1.3 OPCION C cierre)
    "adenda": {
        "id": "addendum-cloudhost-2026-001",
        "addendum_code": "ADENDA-ENS-2026-001",
        "contract_ref": "CONTRATO-MARCO-2025-CLOUDHOST-001",
        "fecha_vigor": "2026-06-01",
        "vencimiento": "2028-05-31",
        "notificacion_horas": 24,
        "notificacion_horas_rgpd": 24,
        "notificacion_horas_nis2": 12,
        "seguro_cuantia_eur": "1.000.000",
    },
    "contrato_base": {
        "fecha": "2025-01-01",
        "objeto": "Servicios hosting cloud productivo plataforma SaaS Demo",
    },
    "plan_supervision": {
        # superset para E-603 · alineado con conftest_proveedores.PLAN_SUPERVISION_FULL
        "periodo_inicio": "2026-06-01",
        "periodo_fin": "2027-05-31",
        "responsable": {
            "nombre": "Marcos Mata Garcia",
            "cargo": "Responsable de Seguridad (CISO interim)",
        },
        "notificacion_horas": 24,
        "revisiones_documentales": [
            {
                "tipo": "Revision recertificaciones ENS + ISO 27001",
                "periodicidad": "Anual",
                "proxima_fecha": "2026-12-01",
                "responsable": "Marcos Mata",
            },
            {
                "tipo": "Revision SOC 2 Type II + BCP",
                "periodicidad": "Anual",
                "proxima_fecha": "2026-11-15",
                "responsable": "Sara Tecnica (CTO)",
            },
        ],
        "documentos_requeridos": [
            "Declaracion Conformidad ENS vigente",
            "Certificado ISO 27001 + alcance vigente",
            "Reporte SOC 2 Type II del periodo cerrado",
            "Informe auditoria interna del periodo",
            "Registro incidentes que afectaron al servicio",
        ],
        "reuniones_operativas": [
            {
                "frecuencia": "Mensual",
                "participantes_entidad": "Marcos Mata (CISO) + Sara Tecnica (CTO)",
                "participantes_proveedor": "Account Manager + Security Officer",
                "agenda": "SLA + incidentes + cambios + roadmap",
            },
        ],
        "pruebas_tecnicas": [
            {
                "tipo": "Test penetracion interfaces expuestas",
                "periodicidad": "Anual",
                "coordinacion": "Preaviso 30d · ventana mantenimiento",
            },
            {
                "tipo": "Escaneo vulnerabilidades activos servicio",
                "periodicidad": "Trimestral",
                "coordinacion": "Reporte mensual + ventana trimestral coordinada",
            },
        ],
        "kpis_sla": [
            {
                "nombre": "Disponibilidad mensual",
                "objetivo": ">= 99.9%",
                "umbral_alerta": "< 99.5%",
                "origen": "Monitor uptime proveedor + checks Entidad",
            },
            {
                "nombre": "Tiempo medio resolucion incidentes graves",
                "objetivo": "<= 4h",
                "umbral_alerta": "> 6h",
                "origen": "Tickets soporte + correlation logs",
            },
        ],
    },
})

# cliente.responsable_sistemas/direccion/contacto_compliance referenciados por E-600
CLIENTE_PILOTO_CONTEXT["cliente"]["responsable_sistemas"] = {
    "nombre": "Sara Tecnica Demo",
    "cargo": "CTO",
    "email": "sara.demo@empresademo.example",
}
CLIENTE_PILOTO_CONTEXT["cliente"]["direccion"] = {
    "nombre": "Director General Demo",
    "cargo": "Director General",
    "email": "director@empresademo.example",
}
CLIENTE_PILOTO_CONTEXT["cliente"]["contacto_compliance"] = {
    "email": "compliance@empresademo.example",
}
CLIENTE_PILOTO_CONTEXT["cliente"]["responsable_seguridad"] = {
    "nombre": "Marcos Demo",
    "cargo": "CISO interim",
    "email": "marcos.demo@empresademo.example",
    "telefono": "+34 910 000 001",
}

# E-604 firmas requeren cliente.representante + cliente.domicilio (header + sec 1)
# L-001/003/004 LCSP requieren cliente.representante.dni adicional (sub-lote 1.B.8.D)
CLIENTE_PILOTO_CONTEXT["cliente"]["representante"] = {
    "nombre": "Director General Demo",
    "cargo": "Director General · representante legal",
    "dni": "00000000T",
}
CLIENTE_PILOTO_CONTEXT["cliente"]["domicilio"] = "Calle Demo 1, 28001 Madrid"
CLIENTE_PILOTO_CONTEXT["cliente"]["project_id"] = "demo-project-001"
# sector_aplicacion (sub-lote 1.B.8.G LUCIA condicional) · default coherente target empresa privada
CLIENTE_PILOTO_CONTEXT["cliente"]["sector_aplicacion"] = "privado"

# W-001/W-002 Whistleblowing (sub-lote 1.B.8.B · Ley 2/2023 canal denuncias)
# cliente.numero_empleados >= 50 dispara branch obligacion_aplica · 120 = tramo 50-249
CLIENTE_PILOTO_CONTEXT["cliente"]["numero_empleados"] = 120
CLIENTE_PILOTO_CONTEXT["cliente"]["sector_actividad"] = (
    "Servicios profesionales · consultoria TIC"
)
CLIENTE_PILOTO_CONTEXT["cliente"]["canal_denuncias_url"] = (
    "https://canal-denuncias.empresademo.example"
)

# responsables.responsable_compliance + responsable_sii + delegado_proteccion_datos
CLIENTE_PILOTO_CONTEXT["responsables"]["responsable_compliance"] = {
    "nombre": "Marcos Demo",
    "cargo": "Compliance Officer",
}
CLIENTE_PILOTO_CONTEXT["responsables"]["responsable_sii"] = {
    "nombre": "Marcos Demo",
    "cargo": "Compliance Officer · Responsable SII",
    "fecha_designacion": "2026-01-15",
    "mandato_min_3_anios": True,
}
CLIENTE_PILOTO_CONTEXT["responsables"]["delegado_proteccion_datos"] = {
    "nombre": "Lucia Datos Demo",
    "cargo": "DPO",
    "email": "lucia.demo@empresademo.example",
}

# LW-001/002/003 Web-Legal (sub-lote 1.B.8.C · LSSI + RGPD + Guia AEPD Cookies)
# cliente.dominio_web + cliente.contacto_general necesarios · resto opcional
CLIENTE_PILOTO_CONTEXT["cliente"]["dominio_web"] = "www.empresademo.example"
CLIENTE_PILOTO_CONTEXT["cliente"]["contacto_general"] = {
    "email": "info@empresademo.example",
}
# Ramas activas demo: transferencias=True (LW-001 sec 5) + cookies_detail (LW-002 sec 4)
CLIENTE_PILOTO_CONTEXT["cliente"]["tiene_transferencias_internacionales"] = True
CLIENTE_PILOTO_CONTEXT["cliente"]["datos_registrales"] = (
    "Reg. Mercantil Madrid · Tomo 9999 · Folio 1 · Hoja M-12345"
)
CLIENTE_PILOTO_CONTEXT["cliente"]["proposito_sitio_web"] = (
    "presentar la actividad de consultoria en seguridad de la informacion"
)
CLIENTE_PILOTO_CONTEXT["cliente"]["cookies_detail"] = [
    {
        "nombre": "session_id",
        "tipo": "tecnica propia",
        "propietario": "Empresa Demo SL",
        "finalidad": "Mantener sesion del usuario",
        "duracion": "Sesion",
    },
    {
        "nombre": "_ga",
        "tipo": "analitica tercero",
        "propietario": "Google Analytics",
        "finalidad": "Medicion uso anonima del sitio",
        "duracion": "2 anios",
    },
]

# L-001/003/004/005 LCSP declaraciones (sub-lote 1.B.8.D · Ley 9/2017 SP)
# cliente.representante + email_notificaciones + persona_contacto_licitaciones
# + referencias_proyectos + equipo_responsable + certificaciones_vigentes
# + medios_tecnicos_descripcion + subcontratistas_previstos
CLIENTE_PILOTO_CONTEXT["cliente"]["email_notificaciones"] = (
    "licitaciones@empresademo.example"
)
CLIENTE_PILOTO_CONTEXT["cliente"]["persona_contacto_licitaciones"] = {
    "nombre": "Marcos Demo",
    "telefono": "+34 910 000 000",
}
CLIENTE_PILOTO_CONTEXT["cliente"]["referencias_proyectos"] = [
    {
        "cliente": "Ayuntamiento Demo A",
        "objeto": "Consultoria ENS BASICA",
        "importe": "25.000",
        "fecha_inicio": "2025-01",
        "fecha_fin": "2025-06",
    },
    {
        "cliente": "Diputacion Demo B",
        "objeto": "Auditoria interna SGSI",
        "importe": "18.500",
        "fecha_inicio": "2025-03",
        "fecha_fin": "2025-09",
    },
]
CLIENTE_PILOTO_CONTEXT["cliente"]["equipo_responsable"] = [
    {
        "perfil": "Director Proyecto Senior",
        "titulaciones": "Ing. Telecom + MBA",
        "certificaciones": "CISA + CISM + ISO 27001 LA",
        "anios": "12",
    },
]
CLIENTE_PILOTO_CONTEXT["cliente"]["certificaciones_vigentes"] = [
    {
        "norma": "ISO/IEC 27001",
        "alcance": "Servicios consultoria seguridad",
        "entidad": "AENOR",
        "vigencia": "2027-12",
    },
]
CLIENTE_PILOTO_CONTEXT["cliente"]["medios_tecnicos_descripcion"] = (
    "Plataforma Fulkro SaaS + MinIO WORM 7 anios + Caddy + pgAudit"
)
CLIENTE_PILOTO_CONTEXT["cliente"]["subcontratistas_previstos"] = [
    {
        "nombre": "Auditor Externo Demo S.L.",
        "prestacion": "Pentesting + Red Team",
        "importe": "5.000",
    },
]

# licitacion + contrato (necesarios para L-001/003/004/005)
CLIENTE_PILOTO_CONTEXT["licitacion"] = {
    "numero_expediente": "EXP-2026-DEMO-001",
    "organo_contratante": "Ayuntamiento Demo de Madrid",
    "objeto": "Servicios consultoria ENS",
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
    "fecha_firma": TODAY_ISO,
}
CLIENTE_PILOTO_CONTEXT["contrato"] = {
    "referencia": "CT-2026-DEMO-001-AYUN-MADRID",
}

# L-006/L-007 LCSP subrogacion (sub-lote 1.B.8.F · Ley 9/2017 Art. 130 + ET Art. 44)
# E-002/003/012/090 Gobierno SGSI (sub-lote 1.B.9.A · RD 311/2022 + CCN-STIC 801/803/808)
# Templates E-003 esperan comite_seguridad en TOP-LEVEL (no nested bajo responsables)
CLIENTE_PILOTO_CONTEXT["comite_seguridad"] = {
    "fecha_constitucion": "2026-03-10",
    "periodicidad_reuniones": "Trimestral · ordinarias",
    "quorum_minimo": "Mayoria absoluta de los miembros",
    "presidente": {"nombre": "Director General Demo", "cargo": "Director General"},
    "secretario": {"nombre": "Marcos Demo", "cargo": "CISO interim"},
    "miembros": [
        {"nombre": "Marcos Demo", "cargo": "CISO interim"},
        {"nombre": "Sara Tecnica Demo", "cargo": "CTO"},
        {"nombre": "Lucia Datos Demo", "cargo": "DPO"},
    ],
}
# proyecto.categoria_ens ya estaba "BASICA" · sustituir a MEDIA para E-002/E-012/E-090
CLIENTE_PILOTO_CONTEXT["proyecto"]["categoria_ens"] = "MEDIA"
# responsables.responsable_sistema (E-002 RSIS · clave canónica m30)
CLIENTE_PILOTO_CONTEXT["responsables"]["responsable_sistema"] = {
    "nombre": "Sara Tecnica Demo",
    "cargo": "Director TI",
    "dni": "00000001A",
}
# Add DNIs a responsables existentes (E-002 RS + RServ)
CLIENTE_PILOTO_CONTEXT["responsables"]["responsable_seguridad"]["dni"] = "00000002B"
CLIENTE_PILOTO_CONTEXT["responsables"]["responsable_servicio"]["dni"] = "00000003C"
# decision_categorizacion (E-012)
CLIENTE_PILOTO_CONTEXT["decision_categorizacion"] = {
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
}
# diagnostico (E-090)
CLIENTE_PILOTO_CONTEXT["diagnostico"] = {
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
}
# poblacion (E-002/003/012 firma footer)
CLIENTE_PILOTO_CONTEXT["cliente"]["poblacion"] = "Madrid"

# E-041/042/043 Ruta Basica lifecycle (sub-lote 1.B.9.B · RD 311/2022 art 30/33/35)
CLIENTE_PILOTO_CONTEXT["renovacion"] = {
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
}
CLIENTE_PILOTO_CONTEXT["cambio_material"] = {
    "fecha_deteccion": "2026-04-20",
    "fecha_implantacion_prevista": "2026-05-15",
    "descripcion": (
        "Migracion del repositorio documental principal a nueva plataforma "
        "SaaS (Microsoft 365 GCC)"
    ),
    "motivacion": "Consolidacion tecnologica + cumplimiento NIS2",
    "impacto_medidas_afectadas": ["mp.com.3", "mp.s.8", "op.ext.4"],
    "riesgo_residual_estimado": "BAJO tras adopcion medidas adicionales",
    "requiere_recategorizacion": False,
}

# E-614/615 Retainer reporting (sub-lote 1.B.9.C · entregables periodicos cliente)
CLIENTE_PILOTO_CONTEXT["retainer"] = {
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
}

CLIENTE_PILOTO_CONTEXT["subrogacion"] = {
    "aplica": True,
    "convenio_colectivo_aplicable": (
        "Convenio Colectivo Empresas Consultoria TIC · BOE 04/04/2024"
    ),
    "organo_facilitador_info": "Direccion Recursos Humanos del organo contratante",
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
}


PLACEHOLDER_PATTERN = re.compile(r"\{\{|\{%|%\}|\}\}")


def validate_docx(docx_path: Path, expect_present: list[str]) -> dict:
    """Open DOCX with python-docx and validate basic invariants."""
    doc = DocxDocument(str(docx_path))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_text += "\n" + cell.text

    h1_count = sum(1 for p in doc.paragraphs if (p.style and p.style.name == "Heading 1"))
    placeholder_leaks = PLACEHOLDER_PATTERN.findall(all_text)
    present = {s: (s in all_text) for s in expect_present}
    has_ens_ref = "ENS" in all_text or "RD 311/2022" in all_text or "Esquema Nacional" in all_text

    return {
        "size_bytes": docx_path.stat().st_size,
        "h1_count": h1_count,
        "placeholder_leak_count": len(placeholder_leaks),
        "placeholder_leak_sample": placeholder_leaks[:5],
        "presents_required_strings": present,
        "has_ens_normative_ref": has_ens_ref,
        "total_paragraphs": len(doc.paragraphs),
        "total_tables": len(doc.tables),
    }


def run() -> int:
    results: dict[str, dict] = {}
    exit_code = 0

    for codigo, descripcion in PLANTILLAS_CRITICAS:
        print(f"\n=== Rendering {codigo} ({descripcion}) ===")
        template_path = TEMPLATES_DOCX_DIR / f"{codigo}.docx"
        if not template_path.exists():
            print(f"  ✗ DOCX template not found: {template_path}")
            results[codigo] = {"error": "template_not_found", "path": str(template_path)}
            exit_code = 1
            continue

        output_path = OUTPUT_DIR / f"{codigo}_demo.docx"
        try:
            render_docx(
                template_path=template_path,
                context=CLIENTE_PILOTO_CONTEXT,
                output_path=output_path,
            )
        except Exception as exc:
            print(f"  ✗ render_docx raised: {type(exc).__name__}: {exc}")
            results[codigo] = {"error": type(exc).__name__, "msg": str(exc)[:200]}
            exit_code = 1
            continue

        validation = validate_docx(
            output_path,
            expect_present=["Empresa Demo SL", "B12345678", "Marcos Demo"],
        )
        results[codigo] = {"output": str(output_path), **validation}

        issues = []
        if validation["size_bytes"] < 5000:
            issues.append(f"size {validation['size_bytes']}B < 5KB")
        if validation["placeholder_leak_count"] > 0:
            issues.append(f"{validation['placeholder_leak_count']} placeholder leaks: {validation['placeholder_leak_sample']}")
        missing_strs = [s for s, p in validation["presents_required_strings"].items() if not p]
        if missing_strs:
            issues.append(f"missing strings: {missing_strs}")
        if validation["h1_count"] < 1:
            issues.append("no H1 headings")
        if not validation["has_ens_normative_ref"]:
            issues.append("no ENS/RD 311 reference")

        if issues:
            print(f"  ⚠ {codigo} rendered with issues: {issues}")
            results[codigo]["issues"] = issues
        else:
            print(f"  ✓ {codigo} OK · {validation['size_bytes']}B · {validation['h1_count']} H1 · {validation['total_paragraphs']} paragraphs · {validation['total_tables']} tables")

    print("\n=== SUMMARY ===")
    for codigo, r in results.items():
        if "error" in r:
            print(f"  {codigo}: ERROR {r['error']}")
        elif "issues" in r:
            print(f"  {codigo}: ISSUES ({len(r['issues'])}) - rendered at {r['output']}")
        else:
            print(f"  {codigo}: OK - {r['output']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(run())
