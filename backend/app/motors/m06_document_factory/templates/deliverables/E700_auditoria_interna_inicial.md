# INFORME DE AUDITORÍA INTERNA INICIAL DEL SGSI DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-700 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Auditoría Interna Inicial ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

## 1. OBJETO Y MARCO NORMATIVO

El presente Informe documenta los resultados de la Auditoría Interna Inicial del Sistema de Gestión de la Seguridad de la Información (SGSI) de {{ cliente.razon_social }} sobre el sistema {{ proyecto.sistema_principal }}, en cumplimiento de:

- **Esquema Nacional de Seguridad** (Real Decreto 311/2022), **Artículo 31** (auditoría de la seguridad) y **Anexo III** (Auditoría de la seguridad), que fija los términos en que se audita.
- **CCN-STIC-802** Guía de auditoría del ENS.
- **UNE-EN ISO/IEC 27001:2023** Cláusula 9.2 (auditoría interna).

La auditoría se realiza con carácter previo a la auditoría externa de certificación ENAC y constituye evidencia formal del estado de implantación del SGSI.

## 2. ALCANCE DE LA AUDITORÍA

| Campo | Valor |
|---|---|
| Sistema auditado | {{ proyecto.sistema_principal }} |
| Alcance ENS | {{ proyecto.alcance }} |
| Categoría declarada | {{ proyecto.categoria_ens }} |
| Periodo cubierto | {{ auditoria.periodo_inicio }} a {{ auditoria.periodo_fin }} |
| Fecha de ejecución | {{ auditoria.fecha_inicio }} a {{ auditoria.fecha_fin }} |
| Equipo auditor interno | {{ auditoria.equipo_auditor }} |
| Auditor jefe | {{ auditoria.auditor_jefe }} |

La auditoría cubre las medidas del Anexo II del RD 311/2022 aplicables a la categoría declarada y a los refuerzos asociados.

## 3. METODOLOGÍA

La auditoría se ha conducido conforme a la metodología de CCN-STIC-802 con las siguientes técnicas:

- **Revisión documental** de políticas, procedimientos, declaración de aplicabilidad (DdA), registros del SGSI y evidencias de los últimos 12 meses.
- **Entrevistas** con responsables de los procesos auditados y con personal operativo seleccionado.
- **Observación directa** de la ejecución de procedimientos críticos.
- **Pruebas de cumplimiento** sobre una muestra representativa de controles.
- **Análisis de logs y registros automáticos** de sistemas relevantes.

## 4. CRITERIOS DE EVALUACIÓN

Para cada medida auditada se determina su estado conforme a la siguiente escala:

| Estado | Definición |
|:---:|---|
| **Conforme** | Implantado, documentado, en operación y con evidencias suficientes |
| **No conforme menor** | Implantado pero con desviaciones limitadas que no comprometen la eficacia |
| **No conforme mayor** | Ausente, no implantado o con deficiencias significativas que comprometen la eficacia |
| **Observación** | Conforme con oportunidad de mejora identificada |
| **No aplica** | Justificadamente excluido en la DdA |

## 5. RESULTADOS POR FAMILIA DE MEDIDAS (ANEXO II)

| Familia | Medidas aplicables | Conformes | NC menores | NC mayores | Observaciones | No aplica |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
{% for fam in resultados_por_familia %}| {{ fam.nombre }} | {{ fam.aplicables }} | {{ fam.conformes }} | {{ fam.nc_menores }} | {{ fam.nc_mayores }} | {{ fam.observaciones }} | {{ fam.no_aplica }} |
{% endfor %}

**Total medidas auditadas**: {{ resumen.total_auditadas }}. **Conformidad global del sistema**: {{ resumen.conformidad_pct }}%.

## 6. NO CONFORMIDADES DETECTADAS

| ID | Medida | Tipo | Descripción | Severidad | Plazo cierre |
|---|:---:|:---:|---|:---:|:---:|
{% for nc in no_conformidades %}| {{ nc.id }} | {{ nc.medida }} | {{ nc.tipo }} | {{ nc.descripcion }} | {{ nc.severidad }} | {{ nc.plazo }} |
{% endfor %}

Cada No Conformidad incluye su evidencia de soporte (referencia documental o de observación) en el repositorio de evidencias de la auditoría.

## 7. OBSERVACIONES Y OPORTUNIDADES DE MEJORA

{% for obs in observaciones %}- **{{ obs.id }}** ({{ obs.medida }}): {{ obs.descripcion }}. Recomendación: {{ obs.recomendacion }}.
{% endfor %}

## 8. PLAN DE ACCIONES CORRECTIVAS

| ID | NC relacionada | Acción | Responsable | Plazo | Estado |
|---|:---:|---|---|---|:---:|
{% for ac in plan_acciones %}| {{ ac.id }} | {{ ac.nc_ref }} | {{ ac.descripcion }} | {{ ac.responsable }} | {{ ac.plazo }} | {{ ac.estado }} |
{% endfor %}

Las acciones se gestionan en el registro de NCs del SGSI con seguimiento mensual hasta su cierre verificado.

## 9. CONCLUSIÓN DEL AUDITOR JEFE

**Estado global del SGSI**: {{ conclusion.estado_global }}.

{{ conclusion.texto }}

**Recomendación para certificación externa**: {{ conclusion.recomendacion_externa }}.

## 10. ANEXOS

- **Anexo A**: Plan de auditoría aprobado previamente al ejercicio.
- **Anexo B**: Lista de evidencias revisadas (con referencia y fecha).
- **Anexo C**: Lista de personas entrevistadas y fecha.
- **Anexo D**: Registro de NCs detalladas con evidencia probatoria.
- **Anexo E**: Histórico de acciones correctivas (estado actualizado).

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
