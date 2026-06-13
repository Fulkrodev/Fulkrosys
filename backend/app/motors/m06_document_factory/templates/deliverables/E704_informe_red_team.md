# DOCUMENTO E-704 — INFORME DE VERIFICACIÓN RED TEAM EXTERNA (Categoría Alta)

**Informe técnico formal de la verificación Red Team externa** encargada
a un pentester OSCP independiente, integrado con el sistema interno de
FULKRO para alinear los findings con el Anexo II del ENS y las técnicas
MITRE ATT&CK. Obligatorio para sistemas de categoría Alta conforme al
Real Decreto 311/2022.

```jinja
---
codigo_documento: "E-704"
titulo: "Informe de Verificación Red Team Externa"
version: "{{ run.version }}"
fecha: "{{ run.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "Marcos Mata García — Consultor independiente en ENS"
revisado_por: "{{ responsables.responsable_seguridad.nombre }}"
---

# INFORME DE VERIFICACIÓN RED TEAM EXTERNA

## {{ cliente.razon_social }}

**Documento E-704 · Versión {{ run.version }} · {{ run.fecha_emision }}**

---

## 1. RESUMEN EJECUTIVO

Con motivo de la certificación en categoría **Alta** del Esquema Nacional
de Seguridad, y conforme al artículo 27 del Real Decreto 311/2022, se ha
encargado un ejercicio de **Red Team externo** sobre el sistema en alcance
de **{{ cliente.razon_social }}**, ejecutado por un profesional externo con
certificación vigente OSCP.

**Puntuación de seguridad resultante:** {{ score.score }} / 100 ({{ score.level }}).

**Hallazgos recibidos del pentester externo:** {{ handoff.total_findings_received }} ·
Integrados con hallazgos internos previos: {{ run.total_findings }} totales ·
{{ score.critical }} críticos · {{ score.high }} altos.

## 2. PROCESO DE CONTRATACIÓN

### 2.1 Pentester externo

| Concepto | Detalle |
|---|---|
| Nombre | {{ handoff.pentester.name }} |
| Certificación vigente | {{ handoff.pentester.certification }} (válida en la fecha del ejercicio) |
| Email de contacto | {{ handoff.pentester.email }} |
| Empresa | {{ handoff.pentester.company \| default('Profesional independiente') }} |

### 2.2 Cronograma

| Hito | Fecha |
|---|---|
| Preparación del engagement (paquete de documentación entregado) | {{ handoff.handoff_date }} |
| Kickoff de coordinación | {{ handoff.kickoff_scheduled_at }} |
| Inicio de la ventana de ejecución | {{ handoff.execution_start \| default(run.phase1_started_at) }} |
| Fin de la ventana de ejecución | {{ handoff.execution_end \| default(run.completed_at) }} |
| Entrega del informe externo | {{ handoff.report_received_at }} |
| Integración en sistema interno y emisión de E-704 | {{ run.fecha_emision }} |

## 3. ALCANCE AUTORIZADO

### 3.1 Objetivos en alcance

{% for target in run.scope.targets %}
- `{{ target }}`
{% endfor %}

### 3.2 Aplicaciones web en alcance

{% for app in run.scope.web_apps %}
- {{ app }}
{% endfor %}

### 3.3 Exclusiones expresas

{% for exc in run.scope.exclusions %}
- {{ exc }}
{% endfor %}

### 3.4 Reglas de compromiso (ROE)

- **Denegación de servicio:** no autorizada bajo ningún concepto.
- **Ingeniería social a personal del cliente:** no autorizada salvo fases
  específicas previamente acordadas con el RSEG.
- **Ventana horaria de ejecución:** {{ handoff.execution_window \| default('L-V 09:00-18:00 CET') }}.
- **Contacto de emergencia:** {{ responsables.responsable_seguridad.nombre }}
  ({{ responsables.responsable_seguridad.email }}).

### 3.5 Autorización formal

La autorización firmada por el representante legal del cliente obra en el
expediente del proyecto (enlace mágico de firma:
{{ handoff.authorization_signed_at }}).

## 4. METODOLOGÍA DEL PENTESTER

El ejercicio se ha ejecutado conforme a metodologías internacionales de
referencia: **OWASP WSTG v4.2**, **PTES (Penetration Testing Execution
Standard)** y **MITRE ATT&CK** para la fase de análisis post-explotación.

Fases ejecutadas por el pentester externo:

1. **Reconnaissance pasivo** — OSINT, DNS, Shodan, certificados.
2. **Enumeración activa** — nmap, dirb, nuclei, testssl.
3. **Identificación de vulnerabilidades** — análisis manual + automatizado.
4. **Explotación controlada** — prueba de concepto sin afectar operación.
5. **Análisis post-explotación** — en los casos que procedió, evaluación
   del movimiento lateral y persistencia.
6. **Informe final** — en formato estructurado y PDF, entregado al consultor para integración.

## 5. INTEGRACIÓN CON EL SISTEMA INTERNO

El informe recibido del pentester externo se ha integrado en el sistema
interno de verificación técnica mediante el motor de ingesta de findings
externos. La integración realiza:

- Parseo y normalización al schema `VerificationFinding`.
- Mapeo automático a medidas del **Anexo II del ENS** (método
  `rule` + `LLM cross-check`).
- Mapeo a técnicas **MITRE ATT&CK**.
- Verificación de confianza Zero False Positives (ZFP): los findings
  externos entran con confianza base 0,85 y pueden bajar a 0,72 si
  contradicen la telemetría interna (controles M3 ya verificados).
- Persistencia con trazabilidad completa: fichero PDF original
  archivado con hash SHA-256.

## 6. CONSOLIDADO DE HALLAZGOS

### 6.1 Distribución por severidad (tras ZFP)

| Severidad | # findings externos | # findings internos previos | Total tras deduplicación |
|---|---|---|---|
| Crítica | {{ score.by_source.external.critical \| default(0) }} | {{ score.by_source.internal.critical \| default(0) }} | {{ score.critical }} |
| Alta | {{ score.by_source.external.high \| default(0) }} | {{ score.by_source.internal.high \| default(0) }} | {{ score.high }} |
| Media | {{ score.by_source.external.medium \| default(0) }} | {{ score.by_source.internal.medium \| default(0) }} | {{ score.medium }} |
| Baja | {{ score.by_source.external.low \| default(0) }} | {{ score.by_source.internal.low \| default(0) }} | {{ score.low }} |

### 6.2 Mapeo al Anexo II del ENS

El heatmap de cobertura ({{ heatmap_summary.total }} medidas del Anexo II)
queda como sigue tras integrar los findings externos:

| Estado | Medidas | % |
|---|---|---|
| Conformes | {{ heatmap_summary.compliant }} | {{ heatmap_summary.compliant_pct }}% |
| Parciales | {{ heatmap_summary.partial }} | {{ heatmap_summary.partial_pct }}% |
| No conformes | {{ heatmap_summary.non_compliant }} | {{ heatmap_summary.non_compliant_pct }}% |
| No verificadas | {{ heatmap_summary.not_verified }} | {{ heatmap_summary.not_verified_pct }}% |

### 6.3 Cadena de ataque identificada por el Red Team

{% if run.attack_chain %}
{% for step in run.attack_chain %}
{{ loop.index }}. **{{ step.phase }}** — {{ step.description }} ({{ step.technique }})
{% endfor %}
{% else %}
_El informe externo no documenta una cadena de ataque explotable end-to-end._
{% endif %}

## 7. HALLAZGOS DEL RED TEAM (DETALLE)

{% if findings_external %}
Los siguientes hallazgos provienen del pentester externo y han sido
integrados al sistema interno con su trazabilidad preservada
(`tool_sources` contiene `external_structured` o `external_pdf`):

{% for f in findings_external %}
### 7.{{ loop.index }}. {{ f.title }}

| Campo | Detalle |
|---|---|
| Severidad | **{{ f.severity_upper }}** |
| Confianza ZFP | {{ f.confidence_score }} ({{ f.classification }}) |
| Fuente | {{ f.tool_sources_str }} |
| Host | `{{ f.host_port_disp }}` |

**Descripción:** {{ f.description }}

**Mapeo ENS:** {{ f.ens_measures_str }}

{% if f.mitre_str %}
**MITRE ATT&CK:** {{ f.mitre_str }}
{% endif %}

**Remediación propuesta:** {{ f.remediation.resumen_no_tecnico }}

**SLA:** {{ f.sla.deadline }} ({{ f.sla.hours_total }} h)

---
{% endfor %}
{% else %}
_No se han integrado hallazgos externos. Verificar el flujo de ingesta._
{% endif %}

## 8. CONCLUSIÓN Y DICTAMEN

La verificación Red Team externa ha cumplido los requisitos formales
exigibles en categoría Alta del ENS: pentester con certificación vigente
(OSCP), alcance formalmente autorizado por el representante legal del
cliente, metodología alineada con PTES/OWASP, y trazabilidad completa de
la cadena de evidencia.

**Estado técnico del sistema tras la integración:**
- Puntuación global: **{{ score.score }} / 100** ({{ score.level }}).
- Tendencia frente al run anterior: **{{ delta.overall_trend }}**.
- Hallazgos críticos abiertos: {{ score.critical }}.

{% if score.critical > 0 or score.high > 3 %}
⚠️ Se detecta presencia de hallazgos críticos o un volumen significativo
de hallazgos altos. Se recomienda priorizar la remediación y ejecutar un
re-test dirigido antes de comparecer a la auditoría externa ENAC.
{% else %}
El estado del sistema tras la verificación externa es compatible con la
comparecencia a la auditoría externa ENAC, siempre que se respeten los
plazos SLA de remediación de los hallazgos identificados.
{% endif %}

---

**Elaborado por:** Marcos Mata García, Consultor independiente en Esquema Nacional de Seguridad
**Revisado por:** {{ responsables.responsable_seguridad.nombre }} — {{ responsables.responsable_seguridad.cargo }}
**Fecha:** {{ run.fecha_emision }}

**Documento E-704 · {{ cliente.razon_social }} · Versión {{ run.version }}**
```

---
