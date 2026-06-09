# DOCUMENTO E-703 — RESUMEN EJECUTIVO DE LA VERIFICACIÓN TÉCNICA

**Resumen de 2-3 páginas dirigido a la Dirección General del cliente.**
Traduce el detalle técnico del E-702 a términos de negocio: qué se ha
encontrado, qué implica, qué hay que decidir y cuándo.

```jinja
---
codigo_documento: "E-703"
titulo: "Resumen Ejecutivo de la Verificación Técnica"
version: "{{ run.version }}"
fecha: "{{ run.fecha_emision }}"
clasificacion: "INTERNA — Cliente"
elaborado_por: "Marcos Mata García — Consultor independiente en ENS"
---

# RESUMEN EJECUTIVO DE LA VERIFICACIÓN TÉCNICA

## {{ cliente.razon_social }}

**Documento E-703 · Versión {{ run.version }} · {{ run.fecha_emision }}**

---

## 1. PROPÓSITO DEL DOCUMENTO

Este documento resume, en términos de negocio, el resultado de la
verificación técnica del sistema declarado como alcance de certificación
al Esquema Nacional de Seguridad.

Está dirigido a la **Dirección de {{ cliente.razon_social }}** para permitir
la toma de decisiones sin entrar en detalle técnico. Todo el detalle técnico
está en el informe E-702 que acompaña a este documento.

## 2. QUÉ SE HA HECHO

Entre el {{ run.fecha_inicio }} y el {{ run.fecha_fin }} se ha ejecutado una
**verificación técnica ({{ run.categoria_ens }})** sobre el sistema objeto de
certificación. El proceso ha consistido en pasar pruebas automáticas y
correlacionar los resultados de varias herramientas para aislar únicamente
los hallazgos reales (lo que llamamos "Zero False Positives").

Concretamente se han analizado **{{ run.targets_count }} objetivos**
(servidores, servicios y aplicaciones) y se han generado **{{ run.total_findings }}
hallazgos potenciales**, de los cuales **{{ run.confirmed_findings }}** se han
confirmado como hallazgos reales susceptibles de remediación.

## 3. QUÉ SE HA ENCONTRADO

La puntuación global de seguridad del sistema es:

**{{ score.score }} / 100 — {{ score.level_upper }}**

Distribución por severidad:

| Severidad | # hallazgos | Qué implica |
|---|---|---|
| Crítica | **{{ score.critical }}** | Riesgo directo explotable ahora mismo. Corregir en 48 h. |
| Alta | **{{ score.high }}** | Riesgo importante. Corregir en 7 días. |
| Media | **{{ score.medium }}** | Riesgo moderado. Corregir en 30 días. |
| Baja | **{{ score.low }}** | Buenas prácticas. Corregir en 90 días. |

Cobertura sobre el Anexo II del ENS (73 medidas de seguridad):

| Estado | # medidas | % |
|---|---|---|
| Conformes | {{ heatmap_summary.compliant }} | {{ heatmap_summary.compliant_pct }}% |
| Parciales | {{ heatmap_summary.partial }} | {{ heatmap_summary.partial_pct }}% |
| No conformes | {{ heatmap_summary.non_compliant }} | {{ heatmap_summary.non_compliant_pct }}% |
| No verificadas | {{ heatmap_summary.not_verified }} | {{ heatmap_summary.not_verified_pct }}% |

## 4. QUÉ HA CAMBIADO RESPECTO AL RUN ANTERIOR

{% if delta.previous_run_date %}
El run anterior se ejecutó el **{{ delta.previous_run_date }}**. La evolución es:

| Concepto | # |
|---|---|
| Hallazgos nuevos | {{ delta.totals.new }} |
| Hallazgos resueltos | {{ delta.totals.resolved }} |
| Hallazgos persistentes | {{ delta.totals.persistent }} |
| Cambios de severidad | {{ delta.totals.severity_changes }} |

**Tendencia global:** {{ delta.overall_trend | upper }}.
{% else %}
_Este es el primer run de verificación técnica del proyecto. No hay un run
anterior con el que comparar._
{% endif %}

## 5. HALLAZGOS PRIORITARIOS QUE LA DIRECCIÓN DEBE CONOCER

{% if findings_priority %}
A continuación se resumen los hallazgos **críticos y altos** confirmados,
en lenguaje de negocio:

{% for f in findings_priority %}
### 5.{{ loop.index }}. {{ f.title }}

- **Severidad:** {{ f.severity | upper }}
- **Qué implica para el negocio:** {{ f.remediation.resumen_no_tecnico }}
- **Riesgo real si no se corrige:** {{ f.remediation.riesgo_real }}
- **Tiempo estimado de corrección:** {{ f.remediation.tiempo_estimado }}
- **Fecha límite (SLA):** {{ f.sla.deadline }}

{% endfor %}
{% else %}
_No se han detectado hallazgos críticos ni altos confirmados en esta verificación._
{% endif %}

## 6. DECISIONES QUE REQUIERE LA DIRECCIÓN

La Dirección de {{ cliente.razon_social }} debe tomar las siguientes
decisiones tras leer este informe:

1. **Aprobar los plazos de remediación propuestos** para los hallazgos
   críticos y altos, o definir plazos alternativos por motivos de negocio.
2. **Asignar presupuesto y personal** al Responsable de Seguridad para
   ejecutar la remediación en los plazos aprobados.
3. **Decidir si se aceptan formalmente los hallazgos de severidad media y
   baja** que se consideren no bloqueantes, registrándolos como riesgos
   residuales aceptados.
4. **Confirmar la fecha objetivo de la auditoría externa de certificación**
   teniendo en cuenta que, con el estado actual, la probabilidad de
   obtener un dictamen favorable es **{{ conclusion.probabilidad_certificacion }}**.

## 7. RECOMENDACIÓN DEL CONSULTOR

{% if score.score >= 75 %}
Se recomienda **mantener el calendario previsto de auditoría externa**.
Los hallazgos identificados son gestionables dentro del plazo antes de la
auditoría, siempre que se respeten los SLA indicados.
{% elif score.score >= 50 %}
Se recomienda **mantener el calendario** pero reforzar puntualmente al
equipo técnico del cliente en la primera semana tras este informe para
concentrar los trabajos en los hallazgos críticos y altos.
{% else %}
Se recomienda **replantear el calendario previsto de auditoría externa**.
La puntuación actual indica gaps que requieren más tiempo y/o recursos de
los previstos antes de comparecer ante ENAC con una probabilidad de éxito
razonable.
{% endif %}

---

**Elaborado por:** Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad
**Fecha:** {{ run.fecha_emision }}

**Documento E-703 · {{ cliente.razon_social }} · Versión {{ run.version }}**
```

---
