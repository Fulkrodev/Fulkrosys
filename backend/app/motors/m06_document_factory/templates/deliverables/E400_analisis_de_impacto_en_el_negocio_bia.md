# DOCUMENTO E-400 — ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)

**Es el análisis previo necesario para construir el Plan de Continuidad del Servicio.** Materializa la medida op.cont.1 del Anexo II del ENS y constituye la entrada fundamental para el Plan de Continuidad descrito en la Política E-104. Sigue las directrices de la norma UNE-EN ISO 22301:2019.

```jinja
---
codigo_documento: "E-400"
titulo: "Análisis de Impacto en el Negocio (BIA)"
version: "{{ bia.version | default('1.0') }}"
fecha: "{{ bia.fecha_emision }}"
clasificacion: "CONFIDENCIAL — Cliente"
elaborado_por: "{{ bia.elaborado_por }}"
aprobado_por: "Comité de Seguridad"
politica_madre: "POL-109"
---

# ANÁLISIS DE IMPACTO EN EL NEGOCIO (BIA)

## {{ cliente.razon_social }}

**Documento E-400 · Versión {{ bia.version | default('1.0') }} · {{ bia.fecha_emision }}**

---

## 1. INTRODUCCIÓN Y OBJETO

El presente Análisis de Impacto en el Negocio (en adelante, **"BIA"**, del inglés *Business Impact Analysis*) tiene por objeto identificar, valorar y documentar el impacto que tendría sobre {{ cliente.razon_social }} la interrupción de sus procesos de negocio críticos y de los servicios y sistemas que les dan soporte, con la finalidad de:

a) Identificar los procesos y servicios cuya interrupción supondría un impacto inasumible para la organización.

b) Determinar los recursos críticos necesarios para la prestación de dichos procesos y servicios.

c) Establecer los **objetivos de tiempo de recuperación (RTO)** y **objetivos de punto de recuperación (RPO)** aplicables a cada uno.

d) Identificar las dependencias internas y externas que condicionan la continuidad.

e) Proporcionar la base sobre la que construir el **Plan de Continuidad del Servicio** (PCS) descrito en la Política POL-109.

Este BIA da cumplimiento a la medida **op.cont.1 (Análisis de impacto)** del Anexo II del Real Decreto 311/2022 y se ha elaborado conforme a las directrices de la norma UNE-EN ISO 22301:2019 sobre Sistemas de Gestión de la Continuidad del Negocio.

---

## 2. ALCANCE

El presente análisis abarca la totalidad de los procesos, servicios, sistemas y recursos comprendidos en el alcance del SGSI definido en la Política POL-100 de {{ cliente.razon_social }}.

---

## 3. METODOLOGÍA

### 3.1 Fases del análisis

El BIA se ha desarrollado en las siguientes fases:

1. **Identificación de procesos críticos** mediante entrevistas con los responsables funcionales de cada área de la organización.

2. **Valoración del impacto** sobre cada proceso identificando criterios de impacto múltiples (operativo, económico, legal, reputacional).

3. **Identificación de recursos críticos** asociados a cada proceso (personal, infraestructura, aplicaciones, datos, proveedores).

4. **Determinación de los RTO y RPO** para cada proceso y recurso.

5. **Análisis de dependencias** internas y externas.

6. **Identificación de escenarios de disrupción** relevantes y de su impacto.

7. **Conclusiones y recomendaciones** para el Plan de Continuidad.

### 3.2 Escala de valoración del impacto

El impacto de la interrupción de cada proceso se valora en escala cualitativa, teniendo en cuenta su evolución temporal:

| Nivel | Descripción |
|---|---|
| **CRÍTICO** | Impacto irrecuperable o de muy difícil reparación. Pérdidas económicas superiores a 500.000 €. Sanciones regulatorias graves. Daño reputacional severo. |
| **ALTO** | Impacto significativo pero recuperable. Pérdidas económicas entre 100.000 y 500.000 €. Incumplimiento de obligaciones contractuales relevantes. |
| **MEDIO** | Impacto moderado. Pérdidas económicas entre 25.000 y 100.000 €. Retrasos operativos relevantes. |
| **BAJO** | Impacto menor. Pérdidas económicas inferiores a 25.000 €. Sin afectación a clientes externos. |

### 3.3 Definiciones operativas

a) **RTO (Recovery Time Objective):** tiempo máximo admisible que un proceso o servicio puede permanecer interrumpido antes de que el impacto resulte inasumible.

b) **RPO (Recovery Point Objective):** cantidad máxima admisible de datos que pueden perderse en una interrupción, expresada en términos de tiempo (cuántos minutos u horas de actividad reciente pueden perderse).

c) **MTPD (Maximum Tolerable Period of Disruption):** período máximo durante el cual la interrupción puede prolongarse antes de que la organización deje de ser viable.

d) **MBCO (Minimum Business Continuity Objective):** nivel mínimo de servicio que debe mantenerse durante una situación de disrupción para permitir la supervivencia de la organización.

---

## 4. INVENTARIO DE PROCESOS CRÍTICOS

Se han identificado los siguientes procesos críticos para la operación de {{ cliente.razon_social }}:

{% for proceso in bia.procesos %}
- **P-{{ '%03d' % loop.index }} · {{ proceso.nombre }}** — Área responsable: {{ proceso.area }} · Criticidad global: {{ proceso.criticidad }}
{% endfor %}

---

## 5. ANÁLISIS DETALLADO DE PROCESOS CRÍTICOS

{% for proceso in bia.procesos %}
### 5.{{ loop.index }} {{ proceso.nombre }}

**Identificador:** P-{{ '%03d' % loop.index }}
**Área responsable:** {{ proceso.area }}
**Responsable funcional:** {{ proceso.responsable }}

**Descripción del proceso:**

{{ proceso.descripcion }}

**Recursos críticos necesarios:**

{% for recurso in proceso.recursos %}
- **{{ recurso.tipo }}:** {{ recurso.descripcion }}
{% endfor %}

**Dependencias externas:**

{% for dep in proceso.dependencias_externas %}
- {{ dep }}
{% endfor %}

**Análisis temporal del impacto de interrupción** (operativo · económico · reputacional · legal):

- **1 hora:** {{ proceso.impacto.h1.operativo }} · {{ proceso.impacto.h1.economico }} · {{ proceso.impacto.h1.reputacional }} · {{ proceso.impacto.h1.legal }}
- **4 horas:** {{ proceso.impacto.h4.operativo }} · {{ proceso.impacto.h4.economico }} · {{ proceso.impacto.h4.reputacional }} · {{ proceso.impacto.h4.legal }}
- **8 horas:** {{ proceso.impacto.h8.operativo }} · {{ proceso.impacto.h8.economico }} · {{ proceso.impacto.h8.reputacional }} · {{ proceso.impacto.h8.legal }}
- **24 horas:** {{ proceso.impacto.h24.operativo }} · {{ proceso.impacto.h24.economico }} · {{ proceso.impacto.h24.reputacional }} · {{ proceso.impacto.h24.legal }}
- **72 horas:** {{ proceso.impacto.h72.operativo }} · {{ proceso.impacto.h72.economico }} · {{ proceso.impacto.h72.reputacional }} · {{ proceso.impacto.h72.legal }}
- **1 semana:** {{ proceso.impacto.s1.operativo }} · {{ proceso.impacto.s1.economico }} · {{ proceso.impacto.s1.reputacional }} · {{ proceso.impacto.s1.legal }}

**Objetivos de recuperación:**

- **RTO (Tiempo objetivo de recuperación):** {{ proceso.rto }}
- **RPO (Punto objetivo de recuperación):** {{ proceso.rpo }}
- **MTPD (Periodo máximo tolerable):** {{ proceso.mtpd }}
- **MBCO (Nivel mínimo de continuidad):** {{ proceso.mbco }}

{% endfor %}

---

## 6. RESUMEN CONSOLIDADO DE RTO Y RPO

{% for proceso in bia.procesos %}
- **{{ proceso.nombre }}** — RTO: {{ proceso.rto }} · RPO: {{ proceso.rpo }} · Criticidad: {{ proceso.criticidad }}
{% endfor %}

---

## 7. RECURSOS CRÍTICOS IDENTIFICADOS

### 7.1 Personal clave

{% for persona in bia.personal_clave %}
- **{{ persona.rol }}** — Procesos: {{ persona.procesos }} · Suplencia: {{ persona.suplencia | default('Sin suplencia identificada') }}
{% endfor %}

### 7.2 Infraestructura tecnológica crítica

{% for infra in bia.infraestructura_critica %}
- **{{ infra.nombre }}** — Procesos: {{ infra.procesos }} · RTO requerido: {{ infra.rto }}
{% endfor %}

### 7.3 Aplicaciones críticas

{% for app in bia.aplicaciones_criticas %}
- **{{ app.nombre }}** — Función: {{ app.funcion }} · RTO: {{ app.rto }} · RPO: {{ app.rpo }}
{% endfor %}

### 7.4 Proveedores críticos

{% for prov in bia.proveedores_criticos %}
- **{{ prov.nombre }}** — Servicio: {{ prov.servicio }} · Procesos: {{ prov.procesos }} · Plan B: {{ prov.plan_b | default('Sin plan B identificado') }}
{% endfor %}

---

## 8. ESCENARIOS DE DISRUPCIÓN ANALIZADOS

Se han considerado los siguientes escenarios de disrupción para evaluar la respuesta del Plan de Continuidad:

{% for esc in bia.escenarios %}
- **ESC-{{ '%03d' % loop.index }}:** {{ esc.descripcion }} — Probabilidad: {{ esc.probabilidad }} · Impacto: {{ esc.impacto }}
{% endfor %}

### 8.1 Escenarios prioritarios

Los siguientes escenarios han sido identificados como prioritarios para el desarrollo de planes de respuesta específicos:

{% for esc in bia.escenarios_prioritarios %}
**{{ loop.index }}. {{ esc.titulo }}**

- **Descripción:** {{ esc.descripcion }}
- **Procesos afectados:** {{ esc.procesos_afectados }}
- **Recursos comprometidos:** {{ esc.recursos_comprometidos }}
- **Estrategia de respuesta propuesta:** {{ esc.estrategia }}

{% endfor %}

---

## 9. ANÁLISIS DE DEPENDENCIAS

### 9.1 Dependencias internas

Las dependencias internas más críticas identificadas son:

{% for dep in bia.dependencias_internas %}
- {{ dep }}
{% endfor %}

### 9.2 Dependencias externas

Las dependencias externas más críticas identificadas son:

{% for dep in bia.dependencias_externas %}
- {{ dep }}
{% endfor %}

### 9.3 Puntos únicos de fallo (SPOF)

Se han identificado los siguientes puntos únicos de fallo que requieren atención prioritaria:

{% for spof in bia.spofs %}
- **{{ spof.nombre }}** — {{ spof.descripcion }}
  - *Mitigación propuesta:* {{ spof.mitigacion }}
{% endfor %}

---

## 10. CONCLUSIONES Y RECOMENDACIONES

### 10.1 Conclusiones del análisis

{{ bia.conclusiones }}

### 10.2 Recomendaciones para el Plan de Continuidad

{% for rec in bia.recomendaciones %}
{{ loop.index }}. {{ rec }}
{% endfor %}

### 10.3 Inversiones recomendadas

A partir del presente análisis, se identifican las siguientes inversiones prioritarias para reforzar la continuidad del servicio:

{% for inv in bia.inversiones_recomendadas %}
- **{{ inv.descripcion }}** — Justificación: {{ inv.justificacion }} · Coste estimado: {{ inv.coste }} · Prioridad: {{ inv.prioridad }}
{% endfor %}

---

## 11. APROBACIÓN Y REVISIÓN

### 11.1 Aprobación

El presente Análisis de Impacto en el Negocio ha sido elaborado por {{ bia.elaborado_por }} y se eleva al Comité de Seguridad para su aprobación formal y posterior remisión a {{ cliente.organo_aprobador_politicas }} para su conocimiento.

### 11.2 Revisión periódica

Conforme al apartado 4.2 de la Política POL-109, el presente BIA será objeto de revisión al menos con carácter **anual** y, con carácter extraordinario, cuando se produzcan cambios significativos en los servicios prestados, en la organización, en la infraestructura o en el contexto operativo de {{ cliente.razon_social }}.

**Próxima revisión prevista:** {{ bia.proxima_revision }}

---

## 12. ANEXOS

- **Anexo I:** Cuestionarios cumplimentados durante las entrevistas
- **Anexo II:** Listado completo de procesos analizados (incluidos los no críticos)
- **Anexo III:** Inventario detallado de recursos críticos
- **Anexo IV:** Matriz de dependencias completa
- **Anexo V:** Histórico de incidentes relevantes utilizados como referencia

---

**Elaborado por:** {{ bia.elaborado_por }}
**Aprobado por:** Comité de Seguridad de {{ cliente.razon_social }}
**Fecha de aprobación:** {{ bia.fecha_aprobacion }}

**Documento E-400 · {{ cliente.razon_social }} · Versión {{ bia.version | default('1.0') }}**

```
