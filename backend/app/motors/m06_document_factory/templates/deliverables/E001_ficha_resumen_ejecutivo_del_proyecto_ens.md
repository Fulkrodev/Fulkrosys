# DOCUMENTO E-001 — FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS

**Es el documento de una página que la dirección del cliente lee.** Resume el estado del proyecto en términos de negocio, sin tecnicismos. Se entrega al inicio del proyecto y se actualiza en cada hito.

```jinja
---
codigo_documento: "E-001"
titulo: "Ficha Resumen Ejecutivo del Proyecto ENS"
version: "{{ ficha.version }}"
fecha: "{{ ficha.fecha_emision }}"
clasificacion: "INTERNA — Cliente"
---

# FICHA RESUMEN EJECUTIVO DEL PROYECTO ENS

## {{ cliente.razon_social }}

**Documento E-001 · Versión {{ ficha.version }} · {{ ficha.fecha_emision }}**

---

### DATOS GENERALES DEL PROYECTO

| Concepto | Detalle |
|---|---|
| Cliente | {{ cliente.razon_social }} |
| NIF | {{ cliente.nif }} |
| Sector de actividad | {{ cliente.sector }} |
| Categoría ENS objetivo | **{{ proyecto.categoria_ens }}** |
| Alcance del proyecto | {{ proyecto.alcance.descripcion_corta }} |
| Fecha de inicio | {{ proyecto.fecha_inicio }} |
| Duración total estimada | {{ proyecto.duracion_meses }} meses |
| Fecha objetivo de certificación | {{ proyecto.fecha_objetivo_certificacion }} |
| Entidad certificadora elegida | {{ proyecto.entidad_certificadora | default('Pendiente de selección') }} |
| Inversión total contratada | {{ proyecto.inversion_contratada }} € + IVA |
| Inversión estimada en auditoría externa | {{ proyecto.inversion_auditoria_externa }} € + IVA |

---

### ESTADO ACTUAL DEL PROYECTO

| Indicador | Estado |
|---|---|
| Fase actual | **{{ ficha.fase_actual }}** ({{ ficha.numero_fase }}/{{ ficha.fases_totales }}) |
| Avance global del proyecto | **{{ ficha.avance_porcentaje }}%** |
| Estado de salud (semáforo) | {% if ficha.semaforo == "verde" %}🟢 **EN PLAZO**{% elif ficha.semaforo == "amarillo" %}🟡 **CON DESVIACIÓN MENOR**{% else %}🔴 **CON RIESGO**{% endif %} |
| Próximo hito | {{ ficha.proximo_hito }} |
| Fecha objetivo del próximo hito | {{ ficha.fecha_proximo_hito }} |
| Días hasta el próximo hito | {{ ficha.dias_proximo_hito }} días |

---

### LOGROS DEL PERIODO

{% for logro in ficha.logros_periodo %}
✅ {{ logro }}
{% endfor %}

---

### RIESGOS ABIERTOS

{% if ficha.riesgos %}
| # | Descripción | Impacto | Probabilidad | Acción mitigadora |
|---|---|---|---|---|
{% for riesgo in ficha.riesgos %}
| {{ loop.index }} | {{ riesgo.descripcion }} | {{ riesgo.impacto }} | {{ riesgo.probabilidad }} | {{ riesgo.accion }} |
{% endfor %}
{% else %}
_No hay riesgos significativos abiertos en este momento._
{% endif %}

---

### DECISIONES PENDIENTES DEL CLIENTE

{% if ficha.decisiones_pendientes %}
La siguiente lista recoge las decisiones que requieren aprobación o acción por parte de {{ cliente.razon_social }} para no bloquear el avance del proyecto:

{% for decision in ficha.decisiones_pendientes %}
**{{ loop.index }}. {{ decision.titulo }}**
- **Descripción:** {{ decision.descripcion }}
- **Decisor:** {{ decision.decisor }}
- **Fecha límite:** {{ decision.fecha_limite }}
- **Impacto si no se decide:** {{ decision.impacto_demora }}

{% endfor %}
{% else %}
_No hay decisiones pendientes del cliente en este momento._
{% endif %}

---

### CONSUMO DE INVERSIÓN

| Concepto | Importe |
|---|---|
| Honorarios del consultor contratados | {{ proyecto.inversion_contratada }} € |
| Honorarios del consultor consumidos a {{ ficha.fecha_emision }} | {{ ficha.honorarios_consumidos }} € ({{ ficha.porcentaje_consumido }}%) |
| Horas del consultor contratadas | {{ proyecto.horas_contratadas }} h |
| Horas del consultor consumidas | {{ ficha.horas_consumidas }} h ({{ ficha.porcentaje_horas_consumidas }}%) |
| Desviación respecto al plan | {% if ficha.desviacion_horas > 0 %}+{% endif %}{{ ficha.desviacion_horas }} h |

{% if ficha.desviacion_horas > 0 %}
⚠️ **Nota:** se observa una desviación positiva de horas. Esta desviación está justificada por: {{ ficha.justificacion_desviacion }}.
{% endif %}

---

### COMENTARIO DEL CONSULTOR

> {{ ficha.comentario_consultor }}

---

**Próxima actualización prevista:** {{ ficha.proxima_actualizacion }}

**Para cualquier consulta:** Marcos Mata García · marcosmata@fulkro.es

---

**Documento E-001 · {{ cliente.razon_social }} · Versión {{ ficha.version }} · {{ ficha.fecha_emision }}**

```

---
