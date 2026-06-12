"""Master registry for the M06 Document Factory templates.

The Jinja2 bodies live next to each module as .md files (see templates/<kind>/).
TEMPLATE_REGISTRY maps the canonical template ID (e.g. "E-100") to metadata
and the dotted-path module that exposes TEMPLATE_BODY.
"""
from __future__ import annotations

import importlib
from typing import Any, Optional


TEMPLATE_REGISTRY: dict[str, dict[str, Any]] = {
    "C-001": {
        "body_path": "commercial/C001_contrato_de_prestacion_de_servicios_de_consultoria.md",
        "module": "commercial.C001_contrato_de_prestacion_de_servicios_de_consultoria",
        "source": "F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md",
        "title": "CONTRATO DE PRESTACIÓN DE SERVICIOS DE CONSULTORÍA ENS",
        "type": "commercial"
    },
    "C-003": {
        "body_path": "commercial/C003_contrato_de_servicios_de_mantenimiento_continuo_re.md",
        "module": "commercial.C003_contrato_de_servicios_de_mantenimiento_continuo_re",
        "source": "F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md",
        "title": "CONTRATO DE SERVICIOS DE MANTENIMIENTO CONTINUO (RETAINER POST-CERTIFICACIÓN)",
        "type": "commercial"
    },
    "E-001": {
        "body_path": "deliverables/E001_ficha_resumen_ejecutivo_del_proyecto_ens.md",
        "module": "deliverables.E001_ficha_resumen_ejecutivo_del_proyecto_ens",
        "source": "F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md",
        "title": "FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS",
        "type": "deliverables"
    },
    "E-002": {
        "body_path": "policies/E002_acta_nombramiento_roles_ens.md",
        "module": "policies.E002_acta_nombramiento_roles_ens",
        "source": "1B9A_governance_SGSI_core.md",
        "title": "ACTA DE NOMBRAMIENTO DE ROLES DEL SISTEMA (ENS)",
        "type": "policies"
    },
    "E-003": {
        "body_path": "policies/E003_acta_constitucion_comite_seguridad.md",
        "module": "policies.E003_acta_constitucion_comite_seguridad",
        "source": "1B9A_governance_SGSI_core.md",
        "title": "ACTA DE CONSTITUCIÓN DEL COMITÉ DE SEGURIDAD DE LA INFORMACIÓN",
        "type": "policies"
    },
    "E-010": {
        # R24 · decisión formal y firmable de la Dirección de adecuar al ENS
        # (org.1 · compromiso de la Dirección). FASE 0 · firmable acta_decision_direccion.
        "body_path": "policies/E010_acta_decision_adecuacion_direccion.md",
        "module": "policies.E010_acta_decision_adecuacion_direccion",
        "source": "RD_311_2022_org1_compromiso_direccion",
        "title": "ACTA DE DECISIÓN DE ADECUACIÓN AL ENS DE LA DIRECCIÓN",
        "type": "policies"
    },
    "E-012": {
        "body_path": "deliverables/E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad.md",
        "module": "deliverables.E012_acta_aprobacion_categorizacion_y_declaracion_aplicabilidad",
        "source": "1B9A_governance_SGSI_core.md",
        "title": "ACTA DE APROBACIÓN DE LA CATEGORIZACIÓN Y DECLARACIÓN DE APLICABILIDAD",
        "type": "deliverables"
    },
    "E-040": {
        "body_path": "deliverables/E040_informe_final_de_adecuacion_al_ens.md",
        "module": "deliverables.E040_informe_final_de_adecuacion_al_ens",
        "source": "F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md",
        "title": "INFORME FINAL DE ADECUACIÓN AL ENS",
        "type": "deliverables"
    },
    "E-808": {
        "body_path": "deliverables/E808_autoevaluacion_dda_anual.md",
        "module": "deliverables.E808_autoevaluacion_dda_anual",
        "source": "#4 Ola8 revision anual AR/DdA (CCN-STIC 808)",
        "title": "AUTOEVALUACIÓN ANUAL DE LA DECLARACIÓN DE APLICABILIDAD",
        "type": "deliverables"
    },
    "E-041": {
        "body_path": "deliverables/E041_declaracion_conformidad_ens.md",
        "module": "deliverables.E041_declaracion_conformidad_ens",
        "source": "1B9B_ruta_basica_lifecycle.md",
        "title": "DECLARACIÓN DE CONFORMIDAD CON EL ENS",
        "type": "deliverables"
    },
    "E-042": {
        "body_path": "deliverables/E042_comunicacion_cambio_material_sistema.md",
        "module": "deliverables.E042_comunicacion_cambio_material_sistema",
        "source": "1B9B_ruta_basica_lifecycle.md",
        "title": "COMUNICACIÓN DE CAMBIO MATERIAL EN EL SISTEMA",
        "type": "deliverables"
    },
    "E-043": {
        "body_path": "deliverables/E043_renovacion_periodica_conformidad.md",
        "module": "deliverables.E043_renovacion_periodica_conformidad",
        "source": "1B9B_ruta_basica_lifecycle.md",
        "title": "RENOVACIÓN PERIÓDICA DE LA CONFORMIDAD CON EL ENS",
        "type": "deliverables"
    },
    "E-050": {
        "body_path": "deliverables/E050_informe_de_auditoria_interna_del_sgsi.md",
        "module": "deliverables.E050_informe_de_auditoria_interna_del_sgsi",
        "source": "F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md",
        "title": "INFORME DE AUDITORÍA INTERNA DEL SGSI",
        "type": "deliverables"
    },
    "E-090": {
        "body_path": "deliverables/E090_informe_diagnostico_inicial.md",
        "module": "deliverables.E090_informe_diagnostico_inicial",
        "source": "1B9A_governance_SGSI_core.md",
        "title": "INFORME DE DIAGNÓSTICO INICIAL · GAP ANALYSIS FRENTE AL ENS",
        "type": "deliverables"
    },
    "E-401": {
        "body_path": "deliverables/E401_estrategias_de_continuidad.md",
        "module": "deliverables.E401_estrategias_de_continuidad",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "ESTRATEGIAS DE CONTINUIDAD",
        "type": "deliverables"
    },
    "E-402": {
        "body_path": "deliverables/E402_bcp_plan_continuidad_negocio.md",
        "module": "deliverables.E402_bcp_plan_continuidad_negocio",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "PLAN DE CONTINUIDAD DEL NEGOCIO (BCP)",
        "type": "deliverables"
    },
    "E-403": {
        "body_path": "deliverables/E403_drp_plan_recuperacion_desastres.md",
        "module": "deliverables.E403_drp_plan_recuperacion_desastres",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "PLAN DE RECUPERACIÓN DE DESASTRES TIC (DRP)",
        "type": "deliverables"
    },
    "E-404": {
        "body_path": "deliverables/E404_plan_comunicaciones_crisis.md",
        "module": "deliverables.E404_plan_comunicaciones_crisis",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "PLAN DE COMUNICACIONES EN CRISIS",
        "type": "deliverables"
    },
    "E-405": {
        "body_path": "deliverables/E405_plan_pruebas_continuidad.md",
        "module": "deliverables.E405_plan_pruebas_continuidad",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "PLAN DE PRUEBAS DE CONTINUIDAD",
        "type": "deliverables"
    },
    "E-406": {
        "body_path": "deliverables/E406_informe_pruebas_continuidad.md",
        "module": "deliverables.E406_informe_pruebas_continuidad",
        "source": "FULKRO architect curated · sub-lote 1.B.2",
        "title": "INFORME DE PRUEBAS DE CONTINUIDAD",
        "type": "deliverables"
    },
    "E-500": {
        "body_path": "deliverables/E500_plan_anual_formacion.md",
        "module": "deliverables.E500_plan_anual_formacion",
        "source": "FULKRO architect curated · sub-lote 1.B.3",
        "title": "PLAN ANUAL DE FORMACIÓN Y CONCIENCIACIÓN",
        "type": "deliverables"
    },
    "E-501": {
        "body_path": "deliverables/E501_catalogo_materiales_formacion.md",
        "module": "deliverables.E501_catalogo_materiales_formacion",
        "source": "FULKRO architect curated · sub-lote 1.B.3",
        "title": "CATÁLOGO DE MATERIALES DE FORMACIÓN",
        "type": "deliverables"
    },
    "E-502": {
        "body_path": "deliverables/E502_registro_asistencia_evaluacion.md",
        "module": "deliverables.E502_registro_asistencia_evaluacion",
        "source": "FULKRO architect curated · sub-lote 1.B.3",
        "title": "REGISTRO DE ASISTENCIA Y EVALUACIÓN DE LA FORMACIÓN",
        "type": "deliverables"
    },
    "E-503": {
        "body_path": "deliverables/E503_informe_simulacros_phishing.md",
        "module": "deliverables.E503_informe_simulacros_phishing",
        "source": "FULKRO architect curated · sub-lote 1.B.3",
        "title": "INFORME DE SIMULACROS DE PHISHING",
        "type": "deliverables"
    },
    "E-504": {
        "body_path": "deliverables/E504_cuadro_mando_kpis_lms.md",
        "module": "deliverables.E504_cuadro_mando_kpis_lms",
        "source": "FULKRO architect curated · sub-lote 1.B.3",
        "title": "CUADRO DE MANDO DE KPIs DEL PROGRAMA DE FORMACIÓN Y CONCIENCIACIÓN",
        "type": "deliverables"
    },
    "E-600": {
        "body_path": "deliverables/E600_inventario_proveedores.md",
        "module": "deliverables.E600_inventario_proveedores",
        "source": "1B711_proveedores_architect_VERBATIM.md",
        "title": "INVENTARIO DE PROVEEDORES ENS",
        "type": "deliverables"
    },
    "E-601": {
        "body_path": "deliverables/E601_cuestionario_onboarding_proveedor.md",
        "module": "deliverables.E601_cuestionario_onboarding_proveedor",
        "source": "1B711_proveedores_architect_VERBATIM.md",
        "title": "CUESTIONARIO DE EVALUACIÓN INICIAL DEL PROVEEDOR",
        "type": "deliverables"
    },
    "E-602": {
        "body_path": "deliverables/E602_informe_evaluacion_proveedor.md",
        "module": "deliverables.E602_informe_evaluacion_proveedor",
        "source": "1B711_proveedores_architect_VERBATIM.md",
        "title": "INFORME DE EVALUACIÓN DE PROVEEDOR",
        "type": "deliverables"
    },
    "E-603": {
        "body_path": "deliverables/E603_plan_supervision_proveedor.md",
        "module": "deliverables.E603_plan_supervision_proveedor",
        "source": "1B711_proveedores_architect_VERBATIM.md",
        "title": "PLAN DE SUPERVISIÓN DE PROVEEDOR",
        "type": "deliverables"
    },
    "E-604": {
        "body_path": "deliverables/E604_adenda_contractual_ens.md",
        "module": "deliverables.E604_adenda_contractual_ens",
        "source": "1B711_proveedores_architect_VERBATIM.md",
        "title": "ADENDA CONTRACTUAL DE CUMPLIMIENTO ENS / RGPD / NIS2 / DORA",
        "type": "deliverables"
    },
    "E-614": {
        "body_path": "deliverables/E614_informe_trimestral_retainer.md",
        "module": "deliverables.E614_informe_trimestral_retainer",
        "source": "1B9C_retainer_reporting.md",
        "title": "INFORME TRIMESTRAL DE RETAINER",
        "type": "deliverables"
    },
    "E-615": {
        "body_path": "deliverables/E615_informe_anual_retainer.md",
        "module": "deliverables.E615_informe_anual_retainer",
        "source": "1B9C_retainer_reporting.md",
        "title": "INFORME ANUAL DE RETAINER",
        "type": "deliverables"
    },
    "E-700": {
        "body_path": "deliverables/E700_auditoria_interna_inicial.md",
        "module": "deliverables.E700_auditoria_interna_inicial",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME DE AUDITORÍA INTERNA INICIAL DEL SGSI",
        "type": "deliverables"
    },
    "E-701": {
        "body_path": "deliverables/E701_auditoria_interna_pre_externa.md",
        "module": "deliverables.E701_auditoria_interna_pre_externa",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME DE AUDITORÍA INTERNA PRE-EXTERNA",
        "type": "deliverables"
    },
    "E-702": {
        "body_path": "deliverables/E702_informe_verificacion_tecnica.md",
        "module": "deliverables.E702_informe_verificacion_tecnica",
        "source": "m08_verification_checkpoint_3_spec.md",
        "title": "INFORME DE VERIFICACIÓN TÉCNICA",
        "type": "deliverables"
    },
    "E-703": {
        "body_path": "deliverables/E703_resumen_ejecutivo_verificacion.md",
        "module": "deliverables.E703_resumen_ejecutivo_verificacion",
        "source": "m08_verification_checkpoint_3_spec.md",
        "title": "RESUMEN EJECUTIVO DE LA VERIFICACIÓN TÉCNICA",
        "type": "deliverables"
    },
    "E-704": {
        "body_path": "deliverables/E704_informe_red_team.md",
        "module": "deliverables.E704_informe_red_team",
        "source": "m08_verification_checkpoint_3_spec.md",
        "title": "INFORME DE VERIFICACIÓN RED TEAM EXTERNA",
        "type": "deliverables"
    },
    "E-705": {
        "body_path": "deliverables/E705_informe_formal_campania_phishing.md",
        "module": "deliverables.E705_informe_formal_campania_phishing",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME FORMAL DE CAMPAÑA DE PHISHING",
        "type": "deliverables"
    },
    "E-706": {
        "body_path": "deliverables/E706_tabletop_incidente.md",
        "module": "deliverables.E706_tabletop_incidente",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME DE EJERCICIO TABLETOP DE GESTIÓN DE INCIDENTE",
        "type": "deliverables"
    },
    "E-707": {
        "body_path": "deliverables/E707_informe_restauracion_backup.md",
        "module": "deliverables.E707_informe_restauracion_backup",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME DE PRUEBA DE RESTAURACIÓN DESDE COPIA DE SEGURIDAD",
        "type": "deliverables"
    },
    "E-708": {
        "body_path": "deliverables/E708_auditoria_externa_ens.md",
        "module": "deliverables.E708_auditoria_externa_ens",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME DE AUDITORÍA EXTERNA DEL ENS",
        "type": "deliverables"
    },
    "E-709": {
        "body_path": "deliverables/E709_ines_snapshot.md",
        "module": "deliverables.E709_ines_snapshot",
        "source": "FULKRO architect curated · sub-lote 1.B.4",
        "title": "INFORME INES SNAPSHOT ANUAL DEL ESTADO DEL ENS",
        "type": "deliverables"
    },
    "E-100": {
        "body_path": "policies/E100_politica_de_seguridad_de_la_informacion.md",
        "module": "policies.E100_politica_de_seguridad_de_la_informacion",
        "source": "F1_1_POLITICAS_CRITICAS_E100_E104 (1).md",
        "title": "POLÍTICA DE SEGURIDAD DE LA INFORMACIÓN",
        "type": "policies"
    },
    "E-101": {
        "body_path": "policies/E101_politica_de_control_de_acceso.md",
        "module": "policies.E101_politica_de_control_de_acceso",
        "source": "F1_1_POLITICAS_CRITICAS_E100_E104 (1).md",
        "title": "POLÍTICA DE CONTROL DE ACCESO",
        "type": "policies"
    },
    "E-102": {
        "body_path": "policies/E102_politica_de_contrasenas_y_autenticacion.md",
        "module": "policies.E102_politica_de_contrasenas_y_autenticacion",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE CONTRASEÑAS Y AUTENTICACIÓN",
        "type": "policies"
    },
    "E-103": {
        "body_path": "policies/E103_politica_de_uso_aceptable_de_los_recursos.md",
        "module": "policies.E103_politica_de_uso_aceptable_de_los_recursos",
        "source": "F1_2_POLITICAS_CRITICAS_E105_E108 (1).md",
        "title": "POLÍTICA DE USO ACEPTABLE DE LOS RECURSOS",
        "type": "policies"
    },
    "E-104": {
        "body_path": "policies/E104_politica_de_clasificacion_y_tratamiento_de_la_info.md",
        "module": "policies.E104_politica_de_clasificacion_y_tratamiento_de_la_info",
        "source": "F1_2_POLITICAS_CRITICAS_E105_E108 (1).md",
        "title": "POLÍTICA DE CLASIFICACIÓN Y TRATAMIENTO DE LA INFORMACIÓN",
        "type": "policies"
    },
    "E-105": {
        "body_path": "policies/E105_politica_de_tratamiento_de_datos_personales_rgpd.md",
        "module": "policies.E105_politica_de_tratamiento_de_datos_personales_rgpd",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE TRATAMIENTO DE DATOS PERSONALES (RGPD)",
        "type": "policies"
    },
    "E-106": {
        "body_path": "policies/E106_politica_de_copias_de_seguridad.md",
        "module": "policies.E106_politica_de_copias_de_seguridad",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE COPIAS DE SEGURIDAD",
        "type": "policies"
    },
    "E-107": {
        "body_path": "policies/E107_politica_de_cifrado_y_gestion_de_claves_criptograf.md",
        "module": "policies.E107_politica_de_cifrado_y_gestion_de_claves_criptograf",
        "source": "F1_2_POLITICAS_CRITICAS_E105_E108 (1).md",
        "title": "POLÍTICA DE CIFRADO Y GESTIÓN DE CLAVES CRIPTOGRÁFICAS",
        "type": "policies"
    },
    "E-108": {
        "body_path": "policies/E108_politica_de_gestion_de_incidentes_de_seguridad.md",
        "module": "policies.E108_politica_de_gestion_de_incidentes_de_seguridad",
        "source": "F1_1_POLITICAS_CRITICAS_E100_E104 (1).md",
        "title": "POLÍTICA DE GESTIÓN DE INCIDENTES DE SEGURIDAD",
        "type": "policies"
    },
    "E-109": {
        "body_path": "policies/E109_politica_de_continuidad_del_servicio.md",
        "module": "policies.E109_politica_de_continuidad_del_servicio",
        "source": "F1_1_POLITICAS_CRITICAS_E100_E104 (1).md",
        "title": "POLÍTICA DE CONTINUIDAD DEL SERVICIO",
        "type": "policies"
    },
    "E-110": {
        "body_path": "policies/E110_politica_de_teletrabajo_y_movilidad.md",
        "module": "policies.E110_politica_de_teletrabajo_y_movilidad",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE TELETRABAJO Y MOVILIDAD",
        "type": "policies"
    },
    "E-111": {
        "body_path": "policies/E111_politica_de_uso_de_servicios_cloud.md",
        "module": "policies.E111_politica_de_uso_de_servicios_cloud",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE USO DE SERVICIOS CLOUD",
        "type": "policies"
    },
    "E-112": {
        "body_path": "policies/E112_politica_de_seguridad_en_las_relaciones_con_provee.md",
        "module": "policies.E112_politica_de_seguridad_en_las_relaciones_con_provee",
        "source": "F1_2_POLITICAS_CRITICAS_E105_E108 (1).md",
        "title": "POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES",
        "type": "policies"
    },
    "E-113": {
        "body_path": "policies/E113_politica_de_adquisicion_de_tecnologia.md",
        "module": "policies.E113_politica_de_adquisicion_de_tecnologia",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE ADQUISICIÓN DE TECNOLOGÍA",
        "type": "policies"
    },
    "E-114": {
        "body_path": "policies/E114_politica_de_desarrollo_seguro_ssdlc.md",
        "module": "policies.E114_politica_de_desarrollo_seguro_ssdlc",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE DESARROLLO SEGURO (SSDLC)",
        "type": "policies"
    },
    "E-115": {
        "body_path": "policies/E115_politica_de_gestion_de_vulnerabilidades.md",
        "module": "policies.E115_politica_de_gestion_de_vulnerabilidades",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE GESTIÓN DE VULNERABILIDADES",
        "type": "policies"
    },
    "E-116": {
        "body_path": "policies/E116_politica_de_gestion_de_cambios.md",
        "module": "policies.E116_politica_de_gestion_de_cambios",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE GESTIÓN DE CAMBIOS",
        "type": "policies"
    },
    "E-117": {
        "body_path": "policies/E117_politica_de_gestion_de_privilegios_y_pam.md",
        "module": "policies.E117_politica_de_gestion_de_privilegios_y_pam",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y PAM",
        "type": "policies"
    },
    "E-118": {
        "body_path": "policies/E118_politica_de_byod_bring_your_own_device.md",
        "module": "policies.E118_politica_de_byod_bring_your_own_device",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE BYOD (Bring Your Own Device)",
        "type": "policies"
    },
    "E-119": {
        "body_path": "policies/E119_politica_de_respuesta_a_brechas_de_datos_personale.md",
        "module": "policies.E119_politica_de_respuesta_a_brechas_de_datos_personale",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE RESPUESTA A BRECHAS DE DATOS PERSONALES",
        "type": "policies"
    },
    "E-120": {
        "body_path": "policies/E120_politica_de_gestion_de_claves_criptograficas.md",
        "module": "policies.E120_politica_de_gestion_de_claves_criptograficas",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE GESTIÓN DE CLAVES CRIPTOGRÁFICAS",
        "type": "policies"
    },
    "E-121": {
        "body_path": "policies/E121_politica_de_redes_y_comunicaciones.md",
        "module": "policies.E121_politica_de_redes_y_comunicaciones",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE REDES Y COMUNICACIONES",
        "type": "policies"
    },
    "E-122": {
        "body_path": "policies/E122_politica_de_gestion_de_soportes.md",
        "module": "policies.E122_politica_de_gestion_de_soportes",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE GESTIÓN DE SOPORTES",
        "type": "policies"
    },
    "E-123": {
        "body_path": "policies/E123_politica_de_seguridad_fisica.md",
        "module": "policies.E123_politica_de_seguridad_fisica",
        "source": "CORRECCION_5A_7_POLITICAS_ALTA_PRIORIDAD.md",
        "title": "POLÍTICA DE SEGURIDAD FÍSICA",
        "type": "policies"
    },
    "E-124": {
        "body_path": "policies/E124_politica_de_seguridad_del_personal.md",
        "module": "policies.E124_politica_de_seguridad_del_personal",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE SEGURIDAD DEL PERSONAL",
        "type": "policies"
    },
    "E-125": {
        "body_path": "policies/E125_politica_de_mesa_limpia_y_pantalla_limpia.md",
        "module": "policies.E125_politica_de_mesa_limpia_y_pantalla_limpia",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE MESA LIMPIA Y PANTALLA LIMPIA",
        "type": "policies"
    },
    "E-126": {
        "body_path": "policies/E126_politica_de_borrado_seguro_y_destruccion_de_inform.md",
        "module": "policies.E126_politica_de_borrado_seguro_y_destruccion_de_inform",
        "source": "CORRECCION_5B_12_POLITICAS_RESTANTES.md",
        "title": "POLÍTICA DE BORRADO SEGURO Y DESTRUCCIÓN DE INFORMACIÓN",
        "type": "policies"
    },
    "E-127": {
        "body_path": "policies/E127_politica_de_registro_de_actividad_retencion_y_ntp.md",
        "module": "policies.E127_politica_de_registro_de_actividad_retencion_y_ntp",
        "source": "#1 Ola7 op.exp.8 retencion logs >=12m + NTP",
        "title": "POLÍTICA DE REGISTRO DE ACTIVIDAD: RETENCIÓN Y SINCRONIZACIÓN HORARIA",
        "type": "policies"
    },
    "E-150": {
        "body_path": "policies/E150_plan_adecuacion.md",
        "module": "policies.E150_plan_adecuacion",
        "source": "1DFtrisBbis_SGSI_core_curated.md",
        "title": "PLAN DE ADECUACIÓN AL ENS",
        "type": "policies"
    },
    "E-155": {
        # F-14-05 (Ejecutable 8 Pasada 16): Documento de Alcance del SGSI
        # (CCN-STIC 805/809). type=deliverables (NO policies) para no alterar
        # los contadores tier-aware de políticas en policy_signoff_service.
        "body_path": "deliverables/E155_documento_alcance_sgsi.md",
        "module": "deliverables.E155_documento_alcance_sgsi",
        "source": "CCN-STIC-805_809_alcance_sgsi",
        "title": "DOCUMENTO DE ALCANCE DEL SGSI",
        "type": "deliverables"
    },
    "E-160": {
        "body_path": "policies/E160_manual_sgsi.md",
        "module": "policies.E160_manual_sgsi",
        "source": "1DFtrisBbis_SGSI_core_curated.md",
        "title": "MANUAL DEL SGSI",
        "type": "policies"
    },
    "E-170": {
        "body_path": "policies/E170_plan_director.md",
        "module": "policies.E170_plan_director",
        "source": "1DFtrisBbis_SGSI_core_curated.md",
        "title": "PLAN DIRECTOR DE SEGURIDAD (TRIANUAL)",
        "type": "policies"
    },
    "E-180": {
        "body_path": "policies/E180_declaracion_conformidad.md",
        "module": "policies.E180_declaracion_conformidad",
        "source": "1DFtrisBbis_SGSI_core_curated.md",
        "title": "DECLARACIÓN DE CONFORMIDAD SGSI (AUTOEVALUACIÓN BÁSICA CCN-STIC 809)",
        "type": "policies"
    },
    "E-200": {
        "body_path": "procedures/E200_procedimiento_de_alta_de_personal.md",
        "module": "procedures.E200_procedimiento_de_alta_de_personal",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE ALTA DE PERSONAL",
        "type": "procedures"
    },
    "E-201": {
        "body_path": "procedures/E201_procedimiento_de_baja_de_personal.md",
        "module": "procedures.E201_procedimiento_de_baja_de_personal",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE BAJA DE PERSONAL",
        "type": "procedures"
    },
    "E-202": {
        "body_path": "procedures/E202_procedimiento_de_cambio_de_rol.md",
        "module": "procedures.E202_procedimiento_de_cambio_de_rol",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE CAMBIO DE ROL",
        "type": "procedures"
    },
    "E-203": {
        "body_path": "procedures/E203_procedimiento_de_gestion_de_cambios.md",
        "module": "procedures.E203_procedimiento_de_gestion_de_cambios",
        "source": "F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE CAMBIOS",
        "type": "procedures"
    },
    "E-204": {
        "body_path": "procedures/E204_procedimiento_de_gestion_de_incidentes_de_segurida.md",
        "module": "procedures.E204_procedimiento_de_gestion_de_incidentes_de_segurida",
        "source": "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE INCIDENTES DE SEGURIDAD",
        "type": "procedures"
    },
    "E-204-A": {
        "body_path": "procedures/E204A_procedimiento_de_recopilacion_y_custodia_de_eviden.md",
        "module": "procedures.E204A_procedimiento_de_recopilacion_y_custodia_de_eviden",
        "source": "F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md",
        "title": "PROCEDIMIENTO DE RECOPILACIÓN Y CUSTODIA DE EVIDENCIAS",
        "type": "procedures"
    },
    "E-205": {
        "body_path": "procedures/E205_procedimiento_de_gestion_de_vulnerabilidades_y_par.md",
        "module": "procedures.E205_procedimiento_de_gestion_de_vulnerabilidades_y_par",
        "source": "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES",
        "type": "procedures"
    },
    "E-206": {
        "body_path": "procedures/E206_procedimiento_de_aplicacion_de_parches.md",
        "module": "procedures.E206_procedimiento_de_aplicacion_de_parches",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE APLICACIÓN DE PARCHES",
        "type": "procedures"
    },
    "E-207": {
        "body_path": "procedures/E207_procedimiento_de_copias_de_seguridad_y_restauracio.md",
        "module": "procedures.E207_procedimiento_de_copias_de_seguridad_y_restauracio",
        "source": "F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md",
        "title": "PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN",
        "type": "procedures"
    },
    "E-208": {
        "body_path": "procedures/E208_procedimiento_de_restauracion.md",
        "module": "procedures.E208_procedimiento_de_restauracion",
        "source": "E208_PROCEDIMIENTO_RESTAURACION.md",
        "title": "PROCEDIMIENTO DE RESTAURACIÓN",
        "type": "procedures"
    },
    "E-209": {
        "body_path": "procedures/E209_procedimiento_de_pruebas_de_continuidad.md",
        "module": "procedures.E209_procedimiento_de_pruebas_de_continuidad",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD",
        "type": "procedures"
    },
    "E-210": {
        "body_path": "procedures/E210_procedimiento_de_revision_periodica_de_accesos.md",
        "module": "procedures.E210_procedimiento_de_revision_periodica_de_accesos",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS",
        "type": "procedures"
    },
    "E-211": {
        "body_path": "procedures/E211_procedimiento_de_gestion_de_cuentas_privilegiadas.md",
        "module": "procedures.E211_procedimiento_de_gestion_de_cuentas_privilegiadas",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS",
        "type": "procedures"
    },
    "E-212": {
        "body_path": "procedures/E212_procedimiento_de_respuesta_a_brechas_rgpd.md",
        "module": "procedures.E212_procedimiento_de_respuesta_a_brechas_rgpd",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE RESPUESTA A BRECHAS RGPD",
        "type": "procedures"
    },
    "E-213": {
        "body_path": "procedures/E213_procedimiento_de_notificacion_de_brechas_a_la_aepd.md",
        "module": "procedures.E213_procedimiento_de_notificacion_de_brechas_a_la_aepd",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD",
        "type": "procedures"
    },
    "E-214": {
        "body_path": "procedures/E214_procedimiento_de_destruccion_segura.md",
        "module": "procedures.E214_procedimiento_de_destruccion_segura",
        "source": "E214_PROCEDIMIENTO_DESTRUCCION_SEGURA.md",
        "title": "PROCEDIMIENTO DE DESTRUCCIÓN SEGURA",
        "type": "procedures"
    },
    "E-215": {
        "body_path": "procedures/E215_procedimiento_de_gestion_de_soportes_extraibles.md",
        "module": "procedures.E215_procedimiento_de_gestion_de_soportes_extraibles",
        "source": "E215_PROCEDIMIENTO_GESTION_SOPORTES_EXTRAIBLES.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES",
        "type": "procedures"
    },
    "E-216": {
        "body_path": "procedures/E216_procedimiento_de_gestion_operativa_de_proveedores.md",
        "module": "procedures.E216_procedimiento_de_gestion_operativa_de_proveedores",
        "source": "E216_PROCEDIMIENTO_GESTION_OPERATIVA_PROVEEDORES.md",
        "title": "PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES",
        "type": "procedures"
    },
    "E-217": {
        "body_path": "procedures/E217_procedimiento_de_evaluacion_y_seguimiento_de_prove.md",
        "module": "procedures.E217_procedimiento_de_evaluacion_y_seguimiento_de_prove",
        "source": "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
        "title": "PROCEDIMIENTO DE EVALUACIÓN Y SEGUIMIENTO DE PROVEEDORES",
        "type": "procedures"
    },
    "E-218": {
        "body_path": "procedures/E218_procedimiento_de_auditoria_interna_del_sgsi.md",
        "module": "procedures.E218_procedimiento_de_auditoria_interna_del_sgsi",
        "source": "F2_2_PROCEDIMIENTOS_CRITICOS_E206_E234 (1).md",
        "title": "PROCEDIMIENTO DE AUDITORÍA INTERNA DEL SGSI",
        "type": "procedures"
    },
    "E-219": {
        "body_path": "procedures/E219_procedimiento_de_revision_por_la_direccion.md",
        "module": "procedures.E219_procedimiento_de_revision_por_la_direccion",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN",
        "type": "procedures"
    },
    "E-220": {
        "body_path": "procedures/E220_procedimiento_de_gestion_de_no_conformidades.md",
        "module": "procedures.E220_procedimiento_de_gestion_de_no_conformidades",
        "source": "CORRECCION_6A_11_PROCEDIMIENTOS_ALTA.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES",
        "type": "procedures"
    },
    "E-221": {
        "body_path": "procedures/E221_procedimiento_de_gestion_de_la_informacion_documen.md",
        "module": "procedures.E221_procedimiento_de_gestion_de_la_informacion_documen",
        "source": "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE LA INFORMACIÓN DOCUMENTADA DEL SGSI",
        "type": "procedures"
    },
    "E-222": {
        "body_path": "procedures/E222_procedimiento_de_gestion_de_excepciones.md",
        "module": "procedures.E222_procedimiento_de_gestion_de_excepciones",
        "source": "E222_PROCEDIMIENTO_GESTION_EXCEPCIONES.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES",
        "type": "procedures"
    },
    "E-223": {
        "body_path": "procedures/E223_procedimiento_de_revision_de_logs.md",
        "module": "procedures.E223_procedimiento_de_revision_de_logs",
        "source": "E223_PROCEDIMIENTO_REVISION_LOGS.md",
        "title": "PROCEDIMIENTO DE REVISIÓN DE LOGS",
        "type": "procedures"
    },
    "E-224": {
        "body_path": "procedures/E224_procedimiento_de_despliegue_de_software.md",
        "module": "procedures.E224_procedimiento_de_despliegue_de_software",
        "source": "E224_PROCEDIMIENTO_DESPLIEGUE_SOFTWARE.md",
        "title": "PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE",
        "type": "procedures"
    },
    "E-225": {
        "body_path": "procedures/E225_procedimiento_de_pruebas_pre_produccion.md",
        "module": "procedures.E225_procedimiento_de_pruebas_pre_produccion",
        "source": "E225_PROCEDIMIENTO_PRUEBAS_PREPRODUCCION.md",
        "title": "PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN",
        "type": "procedures"
    },
    "E-226": {
        "body_path": "procedures/E226_procedimiento_de_teletrabajo.md",
        "module": "procedures.E226_procedimiento_de_teletrabajo",
        "source": "E226_PROCEDIMIENTO_TELETRABAJO.md",
        "title": "PROCEDIMIENTO DE TELETRABAJO",
        "type": "procedures"
    },
    "E-227": {
        "body_path": "procedures/E227_procedimiento_de_uso_de_cloud.md",
        "module": "procedures.E227_procedimiento_de_uso_de_cloud",
        "source": "E227_PROCEDIMIENTO_USO_CLOUD.md",
        "title": "PROCEDIMIENTO DE USO DE CLOUD",
        "type": "procedures"
    },
    "E-228": {
        "body_path": "procedures/E228_procedimiento_de_gestion_de_dispositivos_moviles.md",
        "module": "procedures.E228_procedimiento_de_gestion_de_dispositivos_moviles",
        "source": "E228_PROCEDIMIENTO_GESTION_DISPOSITIVOS_MOVILES.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE DISPOSITIVOS MÓVILES",
        "type": "procedures"
    },
    "E-229": {
        "body_path": "procedures/E229_procedimiento_de_monitorizacion_de_seguridad.md",
        "module": "procedures.E229_procedimiento_de_monitorizacion_de_seguridad",
        "source": "E229_PROCEDIMIENTO_MONITORIZACION_SEGURIDAD.md",
        "title": "PROCEDIMIENTO DE MONITORIZACIÓN DE SEGURIDAD",
        "type": "procedures"
    },
    "E-230": {
        "body_path": "procedures/E230_procedimiento_de_bastionado_de_sistemas.md",
        "module": "procedures.E230_procedimiento_de_bastionado_de_sistemas",
        "source": "E230_PROCEDIMIENTO_BASTIONADO_SISTEMAS.md",
        "title": "PROCEDIMIENTO DE BASTIONADO DE SISTEMAS",
        "type": "procedures"
    },
    "E-231": {
        "body_path": "procedures/E231_procedimiento_de_gestion_de_cuentas_y_accesos.md",
        "module": "procedures.E231_procedimiento_de_gestion_de_cuentas_y_accesos",
        "source": "F2_1_PROCEDIMIENTOS_CRITICOS_E200_E218 (1).md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS",
        "type": "procedures"
    },
    "E-232": {
        "body_path": "procedures/E232_procedimiento_de_gestion_de_certificados_digitales.md",
        "module": "procedures.E232_procedimiento_de_gestion_de_certificados_digitales",
        "source": "E232_PROCEDIMIENTO_GESTION_CERTIFICADOS_DIGITALES.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE CERTIFICADOS DIGITALES",
        "type": "procedures"
    },
    "E-233": {
        "body_path": "procedures/E233_procedimiento_de_seguridad_en_redes_inalambricas.md",
        "module": "procedures.E233_procedimiento_de_seguridad_en_redes_inalambricas",
        "source": "E233_PROCEDIMIENTO_SEGURIDAD_REDES_INALAMBRICAS.md",
        "title": "PROCEDIMIENTO DE SEGURIDAD EN REDES INALÁMBRICAS",
        "type": "procedures"
    },
    "E-234": {
        "body_path": "procedures/E234_procedimiento_de_gestion_de_apis.md",
        "module": "procedures.E234_procedimiento_de_gestion_de_apis",
        "source": "E234_PROCEDIMIENTO_GESTION_APIS.md",
        "title": "PROCEDIMIENTO DE GESTIÓN DE APIs",
        "type": "procedures"
    },
    "E-235": {
        "body_path": "procedures/E235_procedimiento_de_sellado_de_tiempo.md",
        "module": "procedures.E235_procedimiento_de_sellado_de_tiempo",
        "source": "#37 OlaIV mp.info.5 sellos de tiempo (procedimiento documentado; TSA cualificada defer ALTA)",
        "title": "PROCEDIMIENTO DE SELLADO DE TIEMPO",
        "type": "procedures"
    },
    "E-400": {
        "body_path": "deliverables/E400_analisis_de_impacto_en_el_negocio_bia.md",
        "module": "deliverables.E400_analisis_de_impacto_en_el_negocio_bia",
        "source": "F3_2_PLANTILLAS_ENTREGABLES_E001_E040_E050_E400 (1).md",
        "title": "ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)",
        "type": "deliverables"
    },
    "P-001": {
        "body_path": "commercial/P001_propuesta_comercial_maestra_de_servicios_ens.md",
        "module": "commercial.P001_propuesta_comercial_maestra_de_servicios_ens",
        "source": "F3_1_PLANTILLAS_COMERCIALES_P001_C001_C003 (1).md",
        "title": "PROPUESTA COMERCIAL MAESTRA DE SERVICIOS ENS",
        "type": "commercial"
    }
}


def get_template(template_id: str) -> Optional[dict[str, Any]]:
    """Return metadata for a template ID."""
    return TEMPLATE_REGISTRY.get(template_id)


def list_templates(template_type: Optional[str] = None) -> list[dict[str, Any]]:
    """List all templates, optionally filtered by type."""
    items = (
        {"id": tid, **meta}
        for tid, meta in TEMPLATE_REGISTRY.items()
    )
    if template_type:
        return [it for it in items if it["type"] == template_type]
    return list(items)


def load_template_module(template_id: str):
    """Import the Python module that exposes TEMPLATE_BODY for the given ID."""
    meta = TEMPLATE_REGISTRY.get(template_id)
    if not meta:
        return None
    module_dotted = "backend.app.motors.m06_document_factory.templates." + meta["module"]
    return importlib.import_module(module_dotted)
