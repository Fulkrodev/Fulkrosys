# DOCUMENTO E-702 — INFORME DE VERIFICACIÓN TÉCNICA

**Informe técnico detallado para el Responsable de Seguridad (RSEG) del cliente.** Documenta la verificación técnica (categoría Básica o Media) realizada sobre el sistema objeto de certificación ENS, con todos los hallazgos, su clasificación de confianza (ZFP), el mapeo a medidas del Anexo II y la remediación propuesta.

```jinja
---
codigo_documento: "E-702"
titulo: "Informe de Verificación Técnica"
version: "{{ run.version }}"
fecha: "{{ run.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "Marcos Mata García — Consultor independiente en ENS"
revisado_por: "{{ responsables.responsable_seguridad.nombre }}"
---

# INFORME DE VERIFICACIÓN TÉCNICA

## {{ cliente.razon_social }}

**Documento E-702 · Versión {{ run.version }} · {{ run.fecha_emision }}**

---

## 1. RESUMEN EJECUTIVO

Entre el {{ run.fecha_inicio }} y el {{ run.fecha_fin }} se ha ejecutado la
verificación técnica del sistema declarado como alcance de certificación de
**{{ cliente.razon_social }}** en categoría **{{ run.categoria_ens }}**.

**Puntuación de seguridad del sistema:** {{ score.score }} / 100 ({{ score.level }}).

**Estado:** {{ run.total_findings }} hallazgos totales · {{ run.confirmed_findings }}
confirmados y considerados en este informe · {{ score.critical }} críticos ·
{{ score.high }} altos · {{ score.medium }} medios · {{ score.low }} bajos.

**Tendencia frente al run anterior ({{ delta.previous_run_date | default('—') }}):**
{{ delta.overall_trend }} · {{ delta.totals.new }} nuevos · {{ delta.totals.resolved }} resueltos ·
{{ delta.totals.persistent }} persistentes.

## 2. METODOLOGÍA

La verificación se ha ejecutado conforme al procedimiento de
verificación técnica estándar del consultor, alineado con la guía
CCN-STIC 808 y con OWASP WSTG v4.2 en la parte de aplicaciones web.
El proceso se estructura en tres fases:

| Fase | Descripción | Tools utilizadas |
|---|---|---|
| 1 · Descubrimiento | Enumeración de servicios y superficie de ataque | {{ run.tools_discovery }} |
| 2 · Verificación | Ejecución de pruebas automáticas con Zero False Positives (ZFP) | {{ run.tools_verification }} |
| 3 · Análisis | Correlación, clasificación y mapeo a Anexo II ENS | (análisis) |

Todo el output crudo de las herramientas queda almacenado con hash SHA-256
para preservar la cadena de custodia, conforme al procedimiento E-228.

### 2.1 Ventana de ejecución

| Concepto | Detalle |
|---|---|
| Categoría ENS | {{ run.categoria_ens }} |
| Modo de verificación | {{ run.mode }} |
| Autorización | {{ run.authorized_by }} (firma {{ run.authorization_signed_at }}) |
| Inicio fase 1 | {{ run.phase1_started_at }} |
| Fin fase 3 | {{ run.completed_at }} |
| Duración total | {{ run.duration }} |

## 3. ALCANCE DE LA VERIFICACIÓN

### 3.1 Objetivos incluidos

{% for target in run.scope.targets %}
- `{{ target }}`
{% endfor %}

### 3.2 Aplicaciones web verificadas

{% if run.scope.web_apps %}
{% for app in run.scope.web_apps %}
- {{ app }}
{% endfor %}
{% else %}
_No se han incluido aplicaciones web en el alcance de esta verificación._
{% endif %}

### 3.3 Exclusiones

{% if run.scope.exclusions %}
{% for exc in run.scope.exclusions %}
- {{ exc }}
{% endfor %}
{% else %}
_Sin exclusiones expresas._
{% endif %}

## 4. PUNTUACIÓN Y COBERTURA

### 4.1 Puntuación de seguridad

La puntuación se calcula conforme a la fórmula estándar del consultor
(100 − 15 × crítico − 8 × alto − 3 × medio − 1 × bajo), considerando solo
hallazgos con clasificación ZFP `confirmed` o `probable` y estado `open`.

| Concepto | Valor |
|---|---|
| Puntuación global | **{{ score.score }} / 100** |
| Nivel cualitativo | {{ score.level }} |
| Penalización total | {{ score.total_penalty }} puntos |

### 4.2 Heatmap de cobertura (Anexo II ENS)

| Estado | Medidas |
|---|---|
| Conformes (verde) | {{ heatmap_summary.compliant }} |
| Parciales (amarillo) | {{ heatmap_summary.partial }} |
| No conformes (rojo) | {{ heatmap_summary.non_compliant }} |
| No verificadas (gris) | {{ heatmap_summary.not_verified }} |
| **Total** | **{{ heatmap_summary.total }}** |

### 4.3 Detalle por medida del Anexo II

| Medida | Estado | # findings | Peor severidad |
|---|---|---|---|
{% for cell in heatmap %}
| {{ cell.measure }} | {{ cell.status }} | {{ cell.findings_count }} | {{ cell.worst_severity | default('—') }} |
{% endfor %}

## 5. HALLAZGOS CONFIRMADOS

{% if findings_confirmed %}
A continuación se detallan los **{{ findings_confirmed_count }}** hallazgos con
clasificación ZFP `confirmed` (confianza ≥ 0,90) o `probable`
(confianza ≥ 0,70). Cada hallazgo incluye su mapeo a medidas del Anexo II,
técnicas MITRE ATT&CK asociadas y la guía de remediación propuesta.

{% for f in findings_confirmed %}
### 5.{{ loop.index }}. {{ f.title }}

| Campo | Detalle |
|---|---|
| Severidad | **{{ f.severity_upper }}** |
| Confianza ZFP | {{ f.confidence_score }} ({{ f.classification }}) |
| CVE | {{ f.cve_id_disp }} |
| CVSS v3.1 | {{ f.cvss_score_disp }} |
| CWE | {{ f.cwe_id_disp }} |
| Host | `{{ f.host_port_disp }}` |
| Servicio | {{ f.service_disp }} |
| URL | {{ f.affected_url_disp }} |
| Fuentes | {{ f.tool_sources_str }} |

**Descripción:** {{ f.description }}

**Mapeo ENS Anexo II:** {{ f.ens_measures_str }}

{% if f.mitre_str %}
**MITRE ATT&CK:** {{ f.mitre_str }}
{% endif %}

**Estado actual:** {{ f.status }}

**Guía de remediación:**

_Resumen para dirección:_ {{ f.remediation.resumen_no_tecnico }}

_Riesgo real:_ {{ f.remediation.riesgo_real }}

_Tiempo estimado:_ {{ f.remediation.tiempo_estimado }} · Requiere reinicio: {{ f.remediation.requiere_reinicio }} · Requiere ventana de mantenimiento: {{ f.remediation.requiere_ventana_mantenimiento }}

_Pasos:_

{% for paso in f.remediation.pasos %}
{{ paso.paso }}. **{{ paso.titulo }}**
   - Comando: `{{ paso.comando }}`
   - Explicación: {{ paso.explicacion }}
   - Verificación: `{{ paso.verificacion }}`
{% endfor %}

**SLA de remediación:** deadline {{ f.sla.deadline }} ({{ f.sla.hours_total }} h desde detección).

---
{% endfor %}
{% else %}
_No se han identificado hallazgos con clasificación `confirmed` o `probable` en esta verificación._
{% endif %}

## 6. DELTA FRENTE AL RUN ANTERIOR

### 6.1 Hallazgos nuevos

{% if delta.new %}
| # | Título | Severidad |
|---|---|---|
{% for n in delta.new %}
| {{ loop.index }} | {{ n.title }} | {{ n.severity }} |
{% endfor %}
{% else %}
_No hay hallazgos nuevos respecto al run anterior._
{% endif %}

### 6.2 Hallazgos resueltos

{% if delta.resolved %}
| # | Título | Severidad |
|---|---|---|
{% for r in delta.resolved %}
| {{ loop.index }} | {{ r.title }} | {{ r.severity }} |
{% endfor %}
{% else %}
_No hay hallazgos resueltos respecto al run anterior._
{% endif %}

### 6.3 Cambios de severidad en hallazgos persistentes

{% if delta.severity_changes %}
| Título | Antes | Ahora |
|---|---|---|
{% for c in delta.severity_changes %}
| {{ c.title }} | {{ c.from_sev }} | {{ c.to_sev }} |
{% endfor %}
{% else %}
_Sin cambios de severidad._
{% endif %}

## 7. CONCLUSIÓN

A la fecha de emisión del presente informe, el sistema de **{{ cliente.razon_social }}**
presenta una puntuación de **{{ score.score }} / 100**. La tendencia respecto al
run anterior se califica como **{{ delta.overall_trend }}**.

{% if score.critical > 0 %}
⚠️ **ATENCIÓN:** existen {{ score.critical }} hallazgos críticos abiertos. Su
remediación es prioritaria antes de cualquier auditoría externa.
{% endif %}

Se recomienda al RSEG trabajar con los responsables técnicos del cliente
para aplicar las guías de remediación incluidas en la sección 5, respetando
los plazos SLA indicados. Un nuevo run de verificación debe ejecutarse
cuando al menos el 80 % de los hallazgos críticos y altos estén corregidos,
para confirmar su cierre y actualizar el heatmap.

---

**Elaborado por:** Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad
**Revisado por:** {{ responsables.responsable_seguridad.nombre }} — {{ responsables.responsable_seguridad.cargo }}
**Fecha:** {{ run.fecha_emision }}

**Documento E-702 · {{ cliente.razon_social }} · Versión {{ run.version }}**
```

---
