# INFORME DE PRUEBAS DE CONTINUIDAD DE {{ cliente.razon_social|upper }}

Documento {{ proyecto.codigo_documento_base }}-406 — Versión {{ proyecto.version_actual }}

## CONTROL DE CAMBIOS

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| {{ proyecto.version_actual }} | {{ proyecto.fecha_aprobacion_inicial }} | {{ responsables.consultor.nombre }} | Versión inicial |

## REGISTRO DE APROBACIÓN

El presente Informe de Pruebas de Continuidad ha sido elaborado por {{ responsables.consultor.nombre }} en su condición de {{ responsables.consultor.cargo }}, revisado por {{ responsables.responsable_seguridad.nombre }} ({{ responsables.responsable_seguridad.cargo }}) y aprobado por {{ cliente.organo_aprobador_politicas }} de {{ cliente.razon_social }}.

Este Informe constituye evidencia auditable del cumplimiento de la medida **op.cont.4 Medios alternativos** del Anexo II del RD 311/2022 y de los requisitos de pruebas periódicas del SGSI conforme a UNE-ISO 22301:2020 Cláusula 8.5.

## 1. FICHA TÉCNICA DEL EJERCICIO

| Campo | Valor |
|---|---|
| Tipo de ejercicio | {{ ejercicio.tipo }} |
| Fecha de ejecución | {{ ejercicio.fecha }} |
| Hora de inicio | {{ ejercicio.hora_inicio }} |
| Hora de finalización | {{ ejercicio.hora_fin }} |
| Duración total | {{ ejercicio.duracion }} |
| Escenario | {{ ejercicio.escenario }} |
| Alcance | {{ ejercicio.alcance }} |
| Facilitador | {{ ejercicio.facilitador }} |
| Observadores | {{ ejercicio.observadores }} |
| Sistemas/procesos involucrados | {{ ejercicio.sistemas_involucrados }} |

## 2. OBJETIVOS PLANTEADOS

El ejercicio fue diseñado conforme al **E-405 Plan de Pruebas de Continuidad** con los siguientes objetivos específicos:

{% for obj in ejercicio.objetivos %}- {{ obj }}
{% endfor %}

## 3. PARTICIPANTES

| Nombre | Rol en el ejercicio | Función habitual | Asistencia |
|---|---|---|---|
{% for part in ejercicio.participantes %}| {{ part.nombre }} | {{ part.rol_ejercicio }} | {{ part.funcion_habitual }} | {{ part.asistencia }} |
{% endfor %}

**Tasa de participación**: {{ ejercicio.tasa_participacion }} (objetivo ≥ 90%).

## 4. CRONOLOGÍA DEL EJERCICIO

{% for evento in ejercicio.cronologia %}- **{{ evento.timestamp }}** — {{ evento.descripcion }}
{% endfor %}

## 5. MÉTRICAS OBTENIDAS

| Métrica | Objetivo | Valor real | Cumplimiento |
|---|---|---|---|
| RTO técnico | {{ metricas.rto_objetivo }} | {{ metricas.rto_real }} | {{ metricas.rto_cumplimiento }} |
| RPO técnico | {{ metricas.rpo_objetivo }} | {{ metricas.rpo_real }} | {{ metricas.rpo_cumplimiento }} |
| Checklist completado | 100% | {{ metricas.checklist_pct }}% | {{ metricas.checklist_estado }} |
| Participación efectiva | ≥ 90% | {{ metricas.participacion_pct }}% | {{ metricas.participacion_estado }} |
| Integridad de datos restaurados | 100% | {{ metricas.integridad_pct }}% | {{ metricas.integridad_estado }} |

## 6. OBSERVACIONES

### 6.1 Qué funcionó correctamente

{% for obs in observaciones.positivas %}- {{ obs }}
{% endfor %}

### 6.2 Qué falló o presentó dificultades

{% for obs in observaciones.negativas %}- {{ obs }}
{% endfor %}

### 6.3 Sorpresas y hallazgos no esperados

{% for obs in observaciones.sorpresas %}- {{ obs }}
{% endfor %}

## 7. GAPS IDENTIFICADOS

| Gap | Severidad | Proceso/Sistema afectado | Causa raíz | Recomendación |
|---|:---:|---|---|---|
{% for gap in gaps %}| {{ gap.descripcion }} | {{ gap.severidad }} | {{ gap.afectado }} | {{ gap.causa_raiz }} | {{ gap.recomendacion }} |
{% endfor %}

**Severidad**: Crítica (impacto inmediato en RTO/RPO), Alta (impacto en eficacia), Media (mejora relevante), Baja (oportunidad de mejora).

## 8. PLAN DE ACCIÓN CORRECTIVO

| ID | Acción | Gap relacionado | Responsable | Plazo | Estado |
|---|---|---|---|---|---|
{% for acc in acciones_correctivas %}| {{ acc.id }} | {{ acc.descripcion }} | {{ acc.gap_ref }} | {{ acc.responsable }} | {{ acc.plazo }} | {{ acc.estado }} |
{% endfor %}

Las acciones se gestionan en el **registro de no conformidades** del SGSI hasta su cierre verificado.

## 9. LECCIONES APRENDIDAS

{% for leccion in lecciones %}- {{ leccion }}
{% endfor %}

## 10. RECOMENDACIONES PARA EL SIGUIENTE EJERCICIO

{% for rec in recomendaciones_siguiente %}- {{ rec }}
{% endfor %}

Las recomendaciones se incorporan a la planificación del siguiente ejercicio en el calendario anual del **E-405**.

## 11. CONCLUSIONES

**Valoración global del ejercicio**: {{ valoracion_global }}

{{ conclusion_texto }}

## 12. ANEXOS

- **Anexo A**: Logs técnicos completos del ejercicio.
- **Anexo B**: Capturas de pantalla relevantes.
- **Anexo C**: Hoja de asistencia firmada por los participantes.
- **Anexo D**: Documentación del escenario y de las inyecciones aplicadas.
- **Anexo E**: Comunicaciones generadas durante el ejercicio (mensajes internos/externos).

## TABLA DE FIRMAS

| Función | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elaborado | {{ firmas.elaborado.nombre }} | {{ firmas.elaborado.cargo }} | {{ firmas.elaborado.fecha }} | {{ firmas.elaborado.firma_marca }} |
| Revisado | {{ firmas.revisado.nombre }} | {{ firmas.revisado.cargo }} | {{ firmas.revisado.fecha }} | {{ firmas.revisado.firma_marca }} |
| Aprobado | {{ firmas.aprobado.nombre }} | {{ firmas.aprobado.cargo }} | {{ firmas.aprobado.fecha }} | {{ firmas.aprobado.firma_marca }} |
