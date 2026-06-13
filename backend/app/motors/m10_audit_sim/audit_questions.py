"""Catálogo completo de preguntas de auditor ENAC por medida del Anexo II.

Fuente: CCN-STIC 808 (Verificación del cumplimiento del ENS) + CCN-STIC 824
(Informe del Estado de Seguridad) + Anexo III (lista de comprobación)
+ experiencia de auditores ENAC reales.

Cada medida tiene:
- pregunta: lo que preguntaría un auditor ENAC veterano
- criterio: qué debe existir para considerar conforme
- evidencia_tipos: tipos de evidencia a buscar en Evidence Vault
- documento_esperado: código E-XXX del documento esperado (si aplica)
- familia: agrupación Anexo II
- aplica: categorías a las que aplica

Cobertura COMPLETA del Anexo II ENS RD 311/2022 (16 familias · 73 medidas):
- org (marco organizativo): 4
- op.pl (planificación): 5 · op.acc (control de acceso): 6 · op.exp (explotación): 10
- op.ext (servicios externos): 4 · op.nub (servicios en la nube): 1
- op.cont (continuidad): 4 · op.mon (monitorización): 3
- mp.if (instalaciones): 7 · mp.per (personal): 4 · mp.eq (equipos): 4
- mp.com (comunicaciones): 4 · mp.si (soportes de información): 5
- mp.sw (software): 2 · mp.info (información): 6 · mp.s (servicios): 4

Total: 73 preguntas = las 73 medidas del Anexo II RD 311/2022 (BOE-A-2022-7191).
Alineado 2026-06-07 (antes 58, con códigos RD 3/2010 derogados op.exp.11/op.acc.7).
``nombre`` y ``aplica`` se derivan de ``anexo2_rd311_2022.ANEXO_II_RD311`` (fuente
única) y un assert en import garantiza que las 73 medidas estén cubiertas.
"""
from __future__ import annotations

from typing import Any


AUDIT_QUESTIONS: dict[str, dict[str, Any]] = {
    # ═══════════════════ MARCO ORGANIZATIVO (org) ═══════════════════
    "org.1": {
        "pregunta": "¿Existe una Política de Seguridad de la Información aprobada por el órgano superior competente? Muéstreme el documento firmado, el acta de aprobación y evidencia de su difusión al personal.",
        "criterio": "Documento de Política firmado por la dirección + acta de aprobación en Comité + registro de difusión con acuse de recibo",
        "evidencia_tipos": ["politica_seguridad", "acta_aprobacion", "registro_difusion"],
        # FIX(REV-2): org.1 "Política de Seguridad" → E-100 (la Política), no E-001
        # (= "Ficha resumen ejecutivo" · documento equivocado).
        "documento_esperado": "E-100",
        "familia": "org",
        "nombre": "Política de Seguridad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "org.2": {
        "pregunta": "¿Dispone de un cuerpo normativo de seguridad completo y actualizado? Muéstreme el listado maestro de normativa con versiones y fechas de revisión.",
        "criterio": "Listado maestro de políticas + todas las políticas vigentes firmadas + control de versiones + fechas revisión < 12 meses",
        "evidencia_tipos": ["normativa_seguridad", "listado_maestro"],
        "documento_esperado": "E-002",
        "familia": "org",
        "nombre": "Normativa de Seguridad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "org.3": {
        "pregunta": "¿Existen procedimientos operativos de seguridad documentados? Muéstreme los registros de ejecución de los últimos 3-6 meses.",
        "criterio": "Procedimientos firmados + registros de ejecución últimos 6 meses (tickets, actas, logs)",
        "evidencia_tipos": ["procedimiento_operativo", "registro_operativo"],
        "documento_esperado": "E-003",
        "familia": "org",
        "nombre": "Procedimientos de Seguridad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "org.4": {
        "pregunta": "¿Existe un proceso formal de autorización para instalaciones, conexiones y cambios en producción? Muéstreme actas recientes.",
        "criterio": "Procedimiento de autorización + actas de autorización de últimos 3 meses",
        "evidencia_tipos": ["proceso_autorizacion", "acta_autorizacion"],
        "documento_esperado": None,
        "familia": "org",
        "nombre": "Proceso de Autorización",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },

    # ═══════════════════ PLANIFICACIÓN (op.pl) ═══════════════════
    "op.pl.1": {
        "pregunta": "¿Se ha realizado un análisis de riesgos con metodología MAGERIT? Muéstreme el inventario de activos, las amenazas valoradas y el riesgo residual. Si es categoría Alta, ¿tiene el export PILAR?",
        "criterio": "AR completo con inventario activos + amenazas + valoración + riesgo intrínseco/efectivo/residual + aprobación dirección",
        "evidencia_tipos": ["analisis_riesgos", "inventario_activos"],
        "documento_esperado": "E-050",
        "familia": "op.pl",
        "nombre": "Análisis de riesgos",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.pl.2": {
        "pregunta": "¿Dispone de documentación de la arquitectura de seguridad? Muéstreme diagramas de red, zonas de seguridad y flujos de datos.",
        "criterio": "Documento de arquitectura técnica + diagramas de red + zonas + controles perimetrales",
        "evidencia_tipos": ["arquitectura_seguridad", "diagrama_red"],
        "documento_esperado": None,
        "familia": "op.pl",
        "nombre": "Arquitectura de seguridad",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.pl.3": {
        "pregunta": "¿Existe un proceso de adquisición de nuevos componentes que incluya requisitos de seguridad?",
        "criterio": "Procedimiento de adquisición con requisitos de seguridad + evidencia de aplicación reciente",
        "evidencia_tipos": ["proceso_adquisicion"],
        "documento_esperado": None,
        "familia": "op.pl",
        "nombre": "Adquisición de componentes",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.pl.4": {
        "pregunta": "¿La organización se ha dimensionado adecuadamente para la gestión de la seguridad? ¿Cuántas personas se dedican a seguridad?",
        "criterio": "Organigrama de seguridad + perfiles + dedicación documentada",
        "evidencia_tipos": ["dimensionamiento_seguridad"],
        # FIX(catalog): E-005 no existe como plantilla → daba NC falsa. Sin doc
        # dedicado para dimensionamiento → se evalúa por evidencia/criterio.
        "documento_esperado": None,
        "familia": "op.pl",
        "nombre": "Dimensionamiento",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.pl.5": {
        "pregunta": "¿Existe un análisis de impacto en el negocio (BIA) que defina RPO/RTO por servicio?",
        "criterio": "BIA documentado con procesos críticos + RTO/RPO + impacto valorado",
        "evidencia_tipos": ["bia", "analisis_impacto"],
        "documento_esperado": "E-400",
        "familia": "op.pl",
        "nombre": "Análisis de impacto",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ CONTROL DE ACCESO (op.acc) ═══════════════════
    "op.acc.1": {
        "pregunta": "¿Existe un proceso formal de alta, baja y modificación de cuentas de usuario? Muéstreme los registros del último trimestre.",
        "criterio": "Procedimiento de gestión de identidades + registros de altas/bajas últimos 3 meses",
        "evidencia_tipos": ["gestion_identidades", "registro_altas_bajas"],
        "documento_esperado": "E-200",
        "familia": "op.acc",
        "nombre": "Identificación",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.acc.2": {
        "pregunta": "¿Se aplica el principio de mínimo privilegio? ¿Cómo se gestiona la segregación de funciones?",
        "criterio": "Matriz de roles y permisos + evidencia de revisión periódica + SoD documentada",
        "evidencia_tipos": ["matriz_permisos", "revision_accesos", "segregacion_funciones"],
        "documento_esperado": "E-101",
        "familia": "op.acc",
        "nombre": "Requisitos de acceso",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.acc.3": {
        "pregunta": "¿Se realizan revisiones periódicas de derechos de acceso? Muéstreme la última revisión.",
        "criterio": "Registro de revisión de accesos con fecha reciente (<6 meses) + acciones tomadas",
        "evidencia_tipos": ["revision_accesos"],
        "documento_esperado": None,
        "familia": "op.acc",
        "nombre": "Segregación de funciones",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.acc.4": {
        "pregunta": "¿Cuál es la política de contraseñas vigente? ¿Se cumple técnicamente?",
        "criterio": "Política de contraseñas documentada + evidencia técnica de enforcement (GPO, config)",
        "evidencia_tipos": ["politica_contrasenas", "configuracion_contrasenas"],
        "documento_esperado": "E-102",
        "familia": "op.acc",
        "nombre": "Proceso de gestión de derechos",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.acc.5": {
        "pregunta": "¿Está implementado mecanismo de autenticación para usuarios externos? ¿MFA?",
        "criterio": "MFA activo para accesos externos + evidencia técnica (export directorio, config)",
        "evidencia_tipos": ["configuracion_mfa", "export_directorio"],
        "documento_esperado": "E-102",
        "familia": "op.acc",
        "nombre": "Mecanismo de autenticación externos",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.acc.6": {
        "pregunta": "¿Está implementado mecanismo de autenticación para usuarios de la organización? Muéstreme la cobertura de MFA.",
        "criterio": "MFA universal (>=95% cobertura) + evidencia técnica + excepciones justificadas",
        "evidencia_tipos": ["configuracion_mfa", "export_directorio", "cobertura_mfa"],
        "documento_esperado": "E-102",
        "familia": "op.acc",
        "nombre": "Mecanismo de autenticación organización",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ EXPLOTACIÓN (op.exp) ═══════════════════
    "op.exp.1": {
        "pregunta": "¿Existe un inventario de activos actualizado? ¿Quién es responsable de cada activo?",
        "criterio": "Inventario completo con propietario asignado + última revisión <12 meses",
        "evidencia_tipos": ["inventario_activos"],
        "documento_esperado": "E-050",
        "familia": "op.exp",
        "nombre": "Inventario de activos",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.2": {
        "pregunta": "¿Existe un procedimiento de configuración segura (hardening) de los sistemas?",
        "criterio": "Guías de hardening documentadas + evidencia de aplicación (CLARA, Lynis, CIS-CAT)",
        "evidencia_tipos": ["hardening", "configuracion_segura"],
        "documento_esperado": "E-210",
        "familia": "op.exp",
        "nombre": "Configuración de seguridad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.3": {
        "pregunta": "¿Cómo se gestiona la configuración de los sistemas? ¿Existe gestión de cambios formal?",
        "criterio": "Procedimiento de gestión de cambios + registros de cambios últimos 3 meses",
        "evidencia_tipos": ["gestion_cambios", "registro_cambios"],
        "documento_esperado": "E-218",
        "familia": "op.exp",
        "nombre": "Gestión de configuración",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.4": {
        "pregunta": "¿Cuál es la política de gestión de parches? ¿Cuántos parches críticos hay pendientes ahora mismo?",
        "criterio": "Política de parcheo + SLA por criticidad + estado actual de parches (0 críticos pendientes)",
        "evidencia_tipos": ["politica_parcheo", "estado_parches"],
        "documento_esperado": None,
        "familia": "op.exp",
        "nombre": "Mantenimiento",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.5": {
        "pregunta": "¿Existe un proceso formal de gestión de cambios? Muéstreme un cambio reciente documentado.",
        "criterio": "Procedimiento + ticket/registro con solicitud, aprobación, ejecución, verificación",
        "evidencia_tipos": ["gestion_cambios", "registro_cambios"],
        "documento_esperado": "E-218",
        "familia": "op.exp",
        "nombre": "Gestión de cambios",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.exp.6": {
        "pregunta": "¿Qué protección antimalware tiene? ¿Cuál es la cobertura real de endpoints?",
        "criterio": "EDR/AV activo + cobertura 100% endpoints + evidencia de consola centralizada",
        "evidencia_tipos": ["antimalware", "cobertura_edr"],
        "documento_esperado": None,
        "familia": "op.exp",
        "nombre": "Protección frente a código dañino",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.7": {
        "pregunta": "¿Cómo se gestionan los incidentes de seguridad? Muéstreme el registro de incidentes recientes.",
        "criterio": "Procedimiento de incidentes + registro últimos 6 meses + clasificación + acciones",
        "evidencia_tipos": ["gestion_incidentes", "registro_incidentes"],
        "documento_esperado": "E-204",
        "familia": "op.exp",
        "nombre": "Gestión de incidentes",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.8": {
        "pregunta": "¿Se registra la actividad de los usuarios en los sistemas? ¿Qué registros se mantienen y con qué retención?",
        "criterio": "Logging centralizado + retención ENS (6 meses Media, 2 años Alta) + protección integridad logs",
        "evidencia_tipos": ["registro_actividad", "logging", "retencion_logs"],
        "documento_esperado": None,
        "familia": "op.exp",
        "nombre": "Registro de la actividad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.exp.9": {
        "pregunta": "¿Existe registro de gestión de claves criptográficas?",
        "criterio": "Inventario de claves + ciclo de vida documentado + custodia segura",
        "evidencia_tipos": ["gestion_claves"],
        "documento_esperado": None,
        "familia": "op.exp",
        "nombre": "Registro de la gestión de incidentes",
        "aplica": ["ALTA"],
    },
    "op.exp.10": {
        "pregunta": "¿Se protegen las claves criptográficas durante todo su ciclo de vida (generación, distribución, almacenamiento, custodia, archivo y destrucción)? Muéstreme el procedimiento de gestión de claves y dónde se custodian.",
        "criterio": "Procedimiento de gestión de claves criptográficas + almacenamiento protegido (HSM/KMS o equivalente) + rotación + custodia partida en categoría ALTA",
        "evidencia_tipos": ["proteccion_claves", "procedimiento_claves"],
        "documento_esperado": None,
        "familia": "op.exp",
        "nombre": "Protección de claves criptográficas",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },

    # ═══════════════════ SERVICIOS EXTERNOS (op.ext) ═══════════════════
    "op.ext.1": {
        "pregunta": "¿Cómo se controla el acceso de terceros/proveedores a los sistemas? ¿Tienen contratos con cláusulas de seguridad?",
        "criterio": "Inventario proveedores + contratos con cláusulas ENS/RGPD + control accesos terceros",
        "evidencia_tipos": ["gestion_terceros", "contratos_proveedores"],
        "documento_esperado": None,
        "familia": "op.ext",
        "nombre": "Contratación y acuerdos de nivel de servicio",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.ext.2": {
        "pregunta": "¿Se evalúa periódicamente la seguridad de los proveedores externos?",
        "criterio": "Evaluación anual proveedores + cuestionarios seguridad + SLAs monitorizados",
        "evidencia_tipos": ["evaluacion_proveedores"],
        "documento_esperado": None,
        "familia": "op.ext",
        "nombre": "Gestión diaria",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ CONTINUIDAD (op.cont) ═══════════════════
    "op.cont.1": {
        "pregunta": "¿Existe un plan de continuidad/contingencia? ¿Cuándo fue la última prueba de restauración de backups?",
        "criterio": "Plan de continuidad documentado + backups verificados + última prueba restauración <6 meses",
        "evidencia_tipos": ["plan_continuidad", "prueba_restauracion", "backup"],
        "documento_esperado": "E-500",
        "familia": "op.cont",
        "nombre": "Análisis de impacto / Plan de continuidad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.cont.2": {
        "pregunta": "¿Existe un plan de recuperación ante desastres (DRP)? ¿Se ha probado?",
        "criterio": "DRP documentado + probado al menos anualmente + RTO/RPO definidos y cumplibles",
        "evidencia_tipos": ["drp", "prueba_drp"],
        "documento_esperado": "E-500",
        "familia": "op.cont",
        "nombre": "Plan de recuperación ante desastres",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.cont.3": {
        "pregunta": "¿Se realizan pruebas periódicas del plan de continuidad?",
        "criterio": "Registros de pruebas con fecha, resultado, lecciones aprendidas",
        "evidencia_tipos": ["prueba_continuidad"],
        "documento_esperado": None,
        "familia": "op.cont",
        "nombre": "Pruebas periódicas",
        "aplica": ["ALTA"],
    },

    # ═══════════════════ MONITORIZACIÓN (op.mon) ═══════════════════
    "op.mon.1": {
        "pregunta": "¿Dispone de sistema de detección de intrusiones? ¿Qué herramientas usa?",
        "criterio": "IDS/IPS o SIEM con reglas de detección + evidencia de alertas revisadas",
        "evidencia_tipos": ["deteccion_intrusiones", "siem"],
        "documento_esperado": None,
        "familia": "op.mon",
        "nombre": "Detección de intrusión",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.mon.2": {
        "pregunta": "¿Se recogen y analizan métricas de seguridad? ¿Con qué periodicidad?",
        "criterio": "Dashboard de métricas + informes periódicos + tendencias",
        "evidencia_tipos": ["metricas_seguridad"],
        "documento_esperado": None,
        "familia": "op.mon",
        "nombre": "Sistema de métricas",
        "aplica": ["ALTA"],
    },
    "op.mon.3": {
        "pregunta": "¿Existe vigilancia continua sobre la superficie de ataque? ¿Scan de vulnerabilidades periódico?",
        "criterio": "Scans periódicos + seguimiento de hallazgos + evidencia de remediación",
        "evidencia_tipos": ["vigilancia_vulnerabilidades", "scan_periodico"],
        "documento_esperado": "E-702",
        "familia": "op.mon",
        "nombre": "Vigilancia",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ INSTALACIONES (mp.if) ═══════════════════
    "mp.if.1": {
        "pregunta": "¿Existen áreas separadas con control de acceso diferenciado?",
        "criterio": "Plano con zonas de seguridad + control acceso por zona + registros",
        "evidencia_tipos": ["control_acceso_fisico", "plano_zonas"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Áreas separadas y con control de acceso",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.if.2": {
        "pregunta": "¿Se identifica a todas las personas que acceden a las instalaciones?",
        "criterio": "Sistema de identificación + registro de visitas + acompañamiento en zonas restringidas",
        "evidencia_tipos": ["identificacion_personas", "registro_visitas"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Identificación de personas",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.if.3": {
        "pregunta": "¿Existen medidas de protección contra incendios e inundaciones?",
        "criterio": "Sistemas antiincendios + mantenimiento + inspección vigente",
        "evidencia_tipos": ["proteccion_incendios"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Protección frente a incendios e inundaciones",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ PERSONAL (mp.per) ═══════════════════
    "mp.per.1": {
        "pregunta": "¿Existe un procedimiento formal de caracterización del puesto de trabajo desde la perspectiva de seguridad?",
        "criterio": "Procedimiento + definición de perfiles + requisitos de seguridad asociados a cada puesto",
        "evidencia_tipos": ["caracterizacion_puesto", "perfiles_seguridad"],
        # FIX(catalog): E-300 es un register-type de m_live_records, NO una
        # plantilla Document → NC falsa. Se evalúa por evidencia/criterio.
        "documento_esperado": None,
        "familia": "mp.per",
        "nombre": "Caracterización del puesto de trabajo",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.per.2": {
        "pregunta": "¿Todo el personal ha recibido formación específica en seguridad? Muéstreme los registros de formación.",
        "criterio": "Plan de formación + registros de asistencia + evaluación efectividad + recordatorios anuales",
        "evidencia_tipos": ["formacion_seguridad", "registro_asistencia"],
        # FIX(catalog): E-301 es register-type m_live_records, no plantilla →
        # NC falsa. Se evalúa por evidencia (formacion_seguridad/asistencia).
        "documento_esperado": None,
        "familia": "mp.per",
        "nombre": "Formación",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.per.3": {
        "pregunta": "¿Existe un plan de concienciación en seguridad? ¿Con qué periodicidad se refresca?",
        "criterio": "Plan de concienciación + campañas periódicas + evidencia de difusión (emails, carteles, vídeos)",
        "evidencia_tipos": ["concienciacion_seguridad", "campanas"],
        # FIX(catalog): E-302 es register-type m_live_records, no plantilla →
        # NC falsa. Se evalúa por evidencia/criterio.
        "documento_esperado": None,
        "familia": "mp.per",
        "nombre": "Concienciación",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ EQUIPOS (mp.eq) ═══════════════════
    "mp.eq.1": {
        "pregunta": "¿Existe política de puesto de trabajo despejado? ¿Cómo se controla?",
        "criterio": "Política clean desk + clear screen + evidencia de revisiones periódicas",
        "evidencia_tipos": ["puesto_trabajo_despejado", "clean_desk"],
        "documento_esperado": None,
        "familia": "mp.eq",
        "nombre": "Puesto de trabajo despejado",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.eq.2": {
        "pregunta": "¿Cómo se protegen los equipos portátiles? ¿Están cifrados? ¿Tienen MDM?",
        "criterio": "Cifrado de disco (BitLocker/FileVault) + MDM/EDR + política de dispositivos móviles + evidencia cobertura",
        "evidencia_tipos": ["cifrado_portatiles", "mdm", "politica_dispositivos_moviles"],
        "documento_esperado": "E-220",
        "familia": "mp.eq",
        "nombre": "Protección de los equipos portátiles",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.eq.3": {
        "pregunta": "¿Existen medios alternativos de trabajo en caso de indisponibilidad de los equipos habituales?",
        "criterio": "Procedimiento de continuidad operativa + equipos alternativos disponibles + pruebas realizadas",
        "evidencia_tipos": ["medios_alternativos", "continuidad_operativa"],
        "documento_esperado": None,
        "familia": "mp.eq",
        "nombre": "Medios alternativos",
        "aplica": ["ALTA"],
    },

    # ═══════════════════ COMUNICACIONES (mp.com) ═══════════════════
    "mp.com.1": {
        "pregunta": "¿Se protege el perímetro de la red? ¿Existe segmentación?",
        "criterio": "Firewall + reglas documentadas + segmentación VLAN + DMZ si aplica",
        "evidencia_tipos": ["seguridad_perimetral", "configuracion_firewall"],
        "documento_esperado": None,
        "familia": "mp.com",
        "nombre": "Perímetro seguro",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.com.2": {
        "pregunta": "¿Se cifran las comunicaciones? ¿Qué versión de TLS se usa? ¿Tiene DNSSEC?",
        "criterio": "TLS 1.2+ en todos los servicios + certificados vigentes + HSTS + SPF/DKIM/DMARC",
        "evidencia_tipos": ["cifrado_comunicaciones", "testssl", "configuracion_dns"],
        "documento_esperado": None,
        "familia": "mp.com",
        "nombre": "Protección de la confidencialidad",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.com.3": {
        "pregunta": "¿Se protege la autenticidad y la integridad de las comunicaciones?",
        "criterio": "Firma digital + certificados + VPN para accesos remotos",
        "evidencia_tipos": ["integridad_comunicaciones"],
        "documento_esperado": None,
        "familia": "mp.com",
        "nombre": "Protección de la autenticidad y la integridad",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.com.4": {
        "pregunta": "¿Se segregan las redes según su nivel de seguridad?",
        "criterio": "VLANs documentadas + ACLs entre segmentos + microsegmentación (Alta)",
        "evidencia_tipos": ["segregacion_redes"],
        "documento_esperado": None,
        "familia": "mp.com",
        "nombre": "Segregación de redes",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ INFORMACIÓN (mp.info) ═══════════════════
    "mp.info.1": {
        "pregunta": "¿Existe un inventario de información tratada clasificada por nivel de sensibilidad?",
        "criterio": "Inventario de información + clasificación (pública/interna/confidencial/reservada)",
        "evidencia_tipos": ["clasificacion_informacion"],
        "documento_esperado": None,
        "familia": "mp.info",
        "nombre": "Datos de carácter personal",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.info.2": {
        "pregunta": "¿Se aplican mecanismos de calificación de la información?",
        "criterio": "Política de clasificación + etiquetado + procedimiento de manejo por nivel",
        "evidencia_tipos": ["calificacion_informacion"],
        "documento_esperado": "E-107",
        "familia": "mp.info",
        "nombre": "Calificación de la información",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.info.3": {
        "pregunta": "¿Se cifra la información sensible en reposo y en tránsito?",
        "criterio": "Cifrado en reposo (discos, DB, backups) + cifrado en tránsito (TLS) + gestión de claves",
        "evidencia_tipos": ["cifrado_reposo", "cifrado_transito"],
        "documento_esperado": None,
        "familia": "mp.info",
        "nombre": "Cifrado",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.info.4": {
        "pregunta": "¿Se realiza firma electrónica de documentos relevantes?",
        "criterio": "Sistema de firma electrónica + política de firma + registros de uso",
        "evidencia_tipos": ["firma_electronica"],
        "documento_esperado": None,
        "familia": "mp.info",
        "nombre": "Firma electrónica",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.info.5": {
        "pregunta": "¿Se protegen los sellos de tiempo?",
        "criterio": "Sello de tiempo cualificado + autoridad de sellado de confianza",
        "evidencia_tipos": ["sellos_tiempo"],
        "documento_esperado": None,
        "familia": "mp.info",
        "nombre": "Sellos de tiempo",
        "aplica": ["ALTA"],
    },
    "mp.info.6": {
        "pregunta": "¿Se destruye la información de forma segura cuando ya no es necesaria?",
        "criterio": "Procedimiento de borrado seguro + registros de destrucción + certificados de destrucción",
        "evidencia_tipos": ["destruccion_segura"],
        "documento_esperado": None,
        "familia": "mp.info",
        "nombre": "Limpieza de documentos",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },

    # ═══════════════════ SOFTWARE (mp.sw) ═══════════════════
    "mp.sw.1": {
        "pregunta": "¿Se realizan pruebas de seguridad sobre las aplicaciones? ¿SAST/DAST/pentest?",
        "criterio": "Informes de pruebas de seguridad + evidencia de remediación de hallazgos",
        "evidencia_tipos": ["pruebas_seguridad_sw", "pentest_aplicaciones"],
        "documento_esperado": "E-702",
        "familia": "mp.sw",
        "nombre": "Desarrollo de aplicaciones",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.sw.2": {
        "pregunta": "¿Se aceptan los sistemas antes de ponerlos en producción con criterios de seguridad?",
        "criterio": "Procedimiento de aceptación + checklist de seguridad pre-producción + registros",
        "evidencia_tipos": ["aceptacion_sistemas"],
        "documento_esperado": None,
        "familia": "mp.sw",
        "nombre": "Aceptación y puesta en servicio",
        "aplica": ["MEDIA", "ALTA"],
    },

    # ═══════════════════ SERVICIOS (mp.s) ═══════════════════
    "mp.s.1": {
        "pregunta": "¿Cómo se protege la disponibilidad de los servicios frente a ataques de denegación de servicio (DoS)?",
        "criterio": "Medidas anti-DDoS (CDN, WAF, rate-limit) + dimensionamiento adecuado + plan respuesta DoS",
        "evidencia_tipos": ["proteccion_ddos", "waf", "rate_limit"],
        "documento_esperado": None,
        "familia": "mp.s",
        "nombre": "Protección frente a denegación de servicio",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.s.2": {
        "pregunta": "¿Existen medios alternativos para la prestación del servicio en caso de indisponibilidad?",
        "criterio": "Plan de contingencia operativa + infraestructura alternativa + pruebas de conmutación",
        "evidencia_tipos": ["medios_alternativos_servicio", "plan_contingencia_operativa"],
        "documento_esperado": None,
        "familia": "mp.s",
        "nombre": "Medios alternativos",
        "aplica": ["ALTA"],
    },

    # ════ MEDIDAS AÑADIDAS · cobertura completa RD 311/2022 Anexo II (2026-06-07) ════
    # nombre + aplica se fuerzan desde anexo2_rd311_2022.ANEXO_II_RD311 (ver _sync_anexo2).
    "op.ext.3": {
        "pregunta": "¿Cómo gestiona los riesgos de la cadena de suministro TIC (subcontratación, origen de componentes hardware/software, dependencias)? Muéstreme el análisis de la cadena de suministro.",
        "criterio": "Identificación de la cadena de suministro crítica + evaluación de riesgos de subcontratistas + cláusulas de seguridad heredadas a 4ª parte",
        "evidencia_tipos": ["cadena_suministro", "analisis_subcontratistas"],
        "documento_esperado": None,
        "familia": "op.ext",
        "nombre": "Protección de la cadena de suministro",
        "aplica": ["ALTA"],
    },
    "op.ext.4": {
        "pregunta": "¿Existen acuerdos formales para la interconexión con sistemas de terceros? Muéstreme los acuerdos de interconexión y los controles en el punto de unión.",
        "criterio": "Acuerdo de interconexión por cada enlace externo + controles en el perímetro de la interconexión + autorización formal",
        "evidencia_tipos": ["acuerdo_interconexion", "diagrama_red"],
        "documento_esperado": None,
        "familia": "op.ext",
        "nombre": "Interconexión de sistemas",
        "aplica": ["MEDIA", "ALTA"],
    },
    "op.nub.1": {
        "pregunta": "Para los servicios en la nube que utiliza, ¿cómo verifica que el proveedor cumple el ENS y cómo reparte responsabilidades? Muéstreme la certificación ENS del proveedor y el modelo de responsabilidad compartida.",
        "criterio": "Inventario de servicios cloud + certificación ENS (o equivalente) del proveedor + matriz de responsabilidad compartida + configuración de seguridad documentada",
        "evidencia_tipos": ["certificacion_proveedor_cloud", "responsabilidad_compartida", "config_cloud"],
        "documento_esperado": None,
        "familia": "op.nub",
        "nombre": "Protección de servicios en la nube",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "op.cont.4": {
        "pregunta": "¿Dispone de medios alternativos (instalaciones, equipamiento, personal, comunicaciones) que garanticen la continuidad si fallan los habituales? Muéstreme el contrato/acuerdo de respaldo y la última prueba de conmutación.",
        "criterio": "Medios alternativos contratados o disponibles + tiempos de activación acordes al RTO + prueba de conmutación documentada",
        "evidencia_tipos": ["medios_alternativos", "prueba_conmutacion"],
        "documento_esperado": None,
        "familia": "op.cont",
        "nombre": "Medios alternativos",
        "aplica": ["ALTA"],
    },
    "mp.if.4": {
        "pregunta": "¿Cómo garantiza el suministro eléctrico de los sistemas (SAI, grupo electrógeno)? Muéstreme las pruebas de autonomía y el mantenimiento.",
        "criterio": "SAI dimensionado + en categoría ALTA grupo electrógeno + registros de prueba de autonomía y mantenimiento periódico",
        "evidencia_tipos": ["sai_electrico", "prueba_autonomia"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Energía eléctrica",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.if.5": {
        "pregunta": "¿Qué protección frente a incendios tienen las salas técnicas? Muéstreme las revisiones de los sistemas de detección y extinción.",
        "criterio": "Sistema de detección y extinción adecuado a la sala + revisiones periódicas conforme a normativa + registros de mantenimiento",
        "evidencia_tipos": ["proteccion_incendios", "revision_extincion"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Protección frente a incendios",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.if.6": {
        "pregunta": "¿Están protegidas las instalaciones frente a inundaciones (ubicación, detección de agua, drenaje)? Muéstreme las medidas adoptadas.",
        "criterio": "Evaluación del riesgo de inundación + medidas físicas (ubicación elevada, detección de agua, drenaje) acordes al riesgo",
        "evidencia_tipos": ["proteccion_inundaciones"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Protección frente a inundaciones",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.if.7": {
        "pregunta": "¿Se registra la entrada y salida de equipamiento de las instalaciones? Muéstreme el registro de los últimos meses.",
        "criterio": "Procedimiento de control de entrada/salida de equipamiento + registro actualizado con autorización",
        "evidencia_tipos": ["registro_equipamiento"],
        "documento_esperado": None,
        "familia": "mp.if",
        "nombre": "Registro de entrada y salida de equipamiento",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.per.4": {
        "pregunta": "¿Existe un plan de formación en seguridad para el personal con responsabilidades en los sistemas? Muéstreme el plan y los registros de asistencia/aprovechamiento.",
        "criterio": "Plan de formación por rol + registros de impartición + evaluación de aprovechamiento + actualización periódica",
        "evidencia_tipos": ["plan_formacion", "registro_formacion"],
        "documento_esperado": None,
        "familia": "mp.per",
        "nombre": "Formación",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.eq.4": {
        "pregunta": "¿Cómo controla otros dispositivos conectados a la red (impresoras, IoT, dispositivos de planta, periféricos)? Muéstreme el inventario y su segmentación.",
        "criterio": "Inventario de dispositivos no estándar + endurecimiento + segmentación de red + cambio de credenciales por defecto",
        "evidencia_tipos": ["inventario_dispositivos", "segmentacion_red"],
        "documento_esperado": None,
        "familia": "mp.eq",
        "nombre": "Otros dispositivos conectados a la red",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.si.1": {
        "pregunta": "¿Se marcan/etiquetan los soportes de información según su nivel de clasificación? Muéstreme el procedimiento y ejemplos.",
        "criterio": "Procedimiento de marcado de soportes coherente con la calificación de la información + aplicación verificable",
        "evidencia_tipos": ["marcado_soportes"],
        "documento_esperado": None,
        "familia": "mp.si",
        "nombre": "Marcado de soportes",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.si.2": {
        "pregunta": "¿Se cifran los soportes de información que lo requieren según su nivel? Muéstreme la configuración de cifrado y la gestión de claves asociada.",
        "criterio": "Cifrado de soportes con información de nivel medio/alto + algoritmos acreditados CCN + gestión de claves conforme a op.exp.10",
        "evidencia_tipos": ["cifrado_soportes", "config_criptografia"],
        "documento_esperado": None,
        "familia": "mp.si",
        "nombre": "Criptografía",
        "aplica": ["MEDIA", "ALTA"],
    },
    "mp.si.3": {
        "pregunta": "¿Cómo se custodian los soportes de información (acceso restringido, registro)? Muéstreme dónde se guardan y quién accede.",
        "criterio": "Custodia en ubicación con control de acceso + registro de soportes + responsable asignado",
        "evidencia_tipos": ["custodia_soportes", "registro_soportes"],
        "documento_esperado": None,
        "familia": "mp.si",
        "nombre": "Custodia",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.si.4": {
        "pregunta": "¿Cómo se protege la información durante el transporte de soportes fuera de las instalaciones? Muéstreme el procedimiento.",
        "criterio": "Procedimiento de transporte seguro + cifrado/precintado + registro de envío y recepción con acuse",
        "evidencia_tipos": ["transporte_soportes", "registro_transporte"],
        "documento_esperado": None,
        "familia": "mp.si",
        "nombre": "Transporte",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.si.5": {
        "pregunta": "¿Cómo realiza el borrado seguro y la destrucción de soportes al final de su vida útil? Muéstreme los certificados de destrucción.",
        "criterio": "Procedimiento de borrado seguro/destrucción acorde al nivel + certificados de destrucción + registro de soportes dados de baja",
        "evidencia_tipos": ["borrado_seguro", "certificado_destruccion"],
        "documento_esperado": None,
        "familia": "mp.si",
        "nombre": "Borrado y destrucción",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.s.3": {
        "pregunta": "¿Cómo protege la navegación web de los usuarios (proxy, filtrado de contenidos, control de descargas)? Muéstreme la configuración.",
        "criterio": "Proxy/filtrado de navegación + bloqueo de categorías peligrosas + control de descargas + registro de navegación cuando proceda",
        "evidencia_tipos": ["proteccion_navegacion", "config_proxy"],
        "documento_esperado": None,
        "familia": "mp.s",
        "nombre": "Protección de la navegación web",
        "aplica": ["BASICA", "MEDIA", "ALTA"],
    },
    "mp.s.4": {
        "pregunta": "¿Qué medidas tiene frente a la denegación de servicio (DoS/DDoS) en los servicios expuestos? Muéstreme la protección contratada/desplegada y su última activación o prueba.",
        "criterio": "Protección anti-DDoS (servicio o appliance) en servicios expuestos + dimensionamiento + procedimiento de respuesta ante ataque",
        "evidencia_tipos": ["proteccion_dos", "config_antiddos"],
        "documento_esperado": None,
        "familia": "mp.s",
        "nombre": "Protección frente a denegación de servicio",
        "aplica": ["MEDIA", "ALTA"],
    },
}


FAMILIA_LABEL = {
    "org": "Marco organizativo",
    "op.pl": "Planificación",
    "op.acc": "Control de acceso",
    "op.exp": "Explotación",
    "op.ext": "Servicios externos",
    "op.nub": "Servicios en la nube",
    "op.cont": "Continuidad",
    "op.mon": "Monitorización",
    "mp.if": "Instalaciones",
    "mp.per": "Personal",
    "mp.eq": "Equipos",
    "mp.com": "Comunicaciones",
    "mp.si": "Soportes de información",
    "mp.sw": "Software",
    "mp.info": "Información",
    "mp.s": "Servicios",
}


# ── Alineación autoritativa con RD 311/2022 Anexo II (BOE-A-2022-7191) ──
# nombre + aplica se DERIVAN de la tabla oficial (fuente única, anexo2_rd311_2022),
# de modo que este catálogo de preguntas no pueda volver a derivar al RD 3/2010.
# El assert garantiza cobertura completa de las 73 medidas: falla en import si
# falta o sobra alguna (regresión imposible de pasar inadvertida).
from backend.app.motors.m03_dda.anexo2_rd311_2022 import ANEXO_II_RD311  # noqa: E402

_aq_codes = set(AUDIT_QUESTIONS)
_anexo_codes = set(ANEXO_II_RD311)
assert _aq_codes == _anexo_codes, (
    "audit_questions desalineado con RD 311/2022 Anexo II · "
    f"faltan={sorted(_anexo_codes - _aq_codes)} · sobran={sorted(_aq_codes - _anexo_codes)}"
)
for _code, _q in AUDIT_QUESTIONS.items():
    _nombre, _b, _m, _a = ANEXO_II_RD311[_code]
    _q["nombre"] = _nombre
    _q["aplica"] = [c for c, f in (("BASICA", _b), ("MEDIA", _m), ("ALTA", _a)) if f]


def get_questions_for_categoria(categoria: str) -> dict[str, dict]:
    """Filtra preguntas aplicables a la categoría (BASICA/MEDIA/ALTA)."""
    cat = (categoria or "").upper()
    return {
        code: q for code, q in AUDIT_QUESTIONS.items()
        if cat in q["aplica"]
    }


def get_questions_by_family(familia: str) -> dict[str, dict]:
    """Filtra preguntas por familia del Anexo II."""
    return {
        code: q for code, q in AUDIT_QUESTIONS.items()
        if q["familia"] == familia
    }


def get_families() -> list[str]:
    """Lista ordenada de familias cubiertas."""
    return sorted({q["familia"] for q in AUDIT_QUESTIONS.values()})
