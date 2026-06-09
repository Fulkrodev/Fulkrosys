# DOCUMENTO E-808 — AUTOEVALUACIÓN ANUAL DE LA DECLARACIÓN DE APLICABILIDAD

**Artefacto del ciclo de revisión anual del Análisis de Riesgos / Declaración de Aplicabilidad (mantenimiento, Fase 8). Soporta la autoevaluación de seguimiento conforme a la CCN-STIC 808 y la revisión periódica que exige el RD 311/2022 (art. 31, mantenimiento de la conformidad).**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-808"
titulo: "Autoevaluación Anual de la Declaración de Aplicabilidad"
version: "{{ proyecto.version_actual }}"
fecha_revision: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# AUTOEVALUACIÓN ANUAL DE LA DECLARACIÓN DE APLICABILIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-808 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta autoevaluación se realiza en cumplimiento del **Real Decreto 311/2022** (ENS) — en particular el mantenimiento periódico de la conformidad — y se apoya en la metodología de la guía **CCN-STIC 808** (verificación del cumplimiento del ENS). Revisa la vigencia de la **Declaración de Aplicabilidad** sobre las 73 medidas del Anexo II y del **Análisis de Riesgos** asociado.

---

## 1. OBJETO Y ALCANCE

Documentar la revisión anual de la Declaración de Aplicabilidad de {{ cliente.razon_social }}: confirmar que la aplicabilidad de las medidas, su estado de implantación y los riesgos asociados siguen vigentes, e identificar los cambios respecto a la versión anterior que requieren reaprobación de la Dirección.

## 2. RESULTADO DE LA REVISIÓN (resumen)

| Indicador | Valor |
|---|---|
| Versión revisada | v{{ revision.version_to }} (anterior: v{{ revision.version_from }}) |
| Medidas aplicables | {{ revision.total_aplicables }} |
| Implantadas | {{ revision.implantadas }} |
| Parciales | {{ revision.parcial }} |
| No implantadas | {{ revision.no_implantadas }} |
| No valoradas | {{ revision.no_valoradas }} |
| Grado de implantación | {{ revision.completion_pct }}% |

## 3. CAMBIOS RESPECTO A LA VERSIÓN ANTERIOR

Se documentan los deltas detectados en el estado de implantación de las medidas y en la valoración del riesgo desde la última revisión aprobada. Cada cambio relevante se justifica y, si procede, se traslada al Plan de Adecuación vigente.

## 4. CONCLUSIÓN Y REAPROBACIÓN

La presente revisión deja la Declaración de Aplicabilidad **pendiente de reaprobación por la Dirección** ({{ cliente.organo_aprobador_politicas }}), que asume la responsabilidad sobre la vigencia del sistema conforme al ENS. Hasta su firma, la DdA permanece en estado de revisión (no congelada).

---

**Documento {{ proyecto.codigo_documento_base }}-808 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
