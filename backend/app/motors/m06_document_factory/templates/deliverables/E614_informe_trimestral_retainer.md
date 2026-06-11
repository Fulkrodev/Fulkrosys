---
codigo_documento: "E-614"
titulo: "Informe Trimestral de Retainer"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · CLIENTE"
naturaleza: "Entregable periódico del servicio de retainer"
---

# INFORME TRIMESTRAL DE RETAINER

**Cliente: {{ cliente.razon_social }}**
**Documento E-614 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set ret = retainer if retainer else {} %}
{% set tier = ret.tier if ret and ret.tier else 'R_STD' %}
{% set tier_desc = ret.tier_descripcion if ret and ret.tier_descripcion else 'Retainer Estándar' %}
{% set per = ret.periodo_actual if ret and ret.periodo_actual else {} %}
{% set per_etiq = per.etiqueta if per and per.etiqueta else 'Trimestre actual' %}
{% set per_desde = per.desde if per and per.desde else '[fecha desde]' %}
{% set per_hasta = per.hasta if per and per.hasta else '[fecha hasta]' %}
{% set fecha_emision = proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha emisión]' %}
{% set cat_ens = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}
{% set rs_nombre = responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[RS]' %}
{% set rep_cliente = cliente.representante.nombre if cliente.representante else '[Representante]' %}
{% set tiene_kpis = ret.kpis_periodo and ret.kpis_periodo | length > 0 %}
{% set tiene_inc = ret.incidentes_periodo and ret.incidentes_periodo | length > 0 %}
{% set tiene_chg = ret.cambios_periodo and ret.cambios_periodo | length > 0 %}
{% set fecha_renov = ret.fecha_renovacion if ret and ret.fecha_renovacion else '' %}

## 1. IDENTIFICACIÓN DEL INFORME

| Campo | Valor |
|-------|-------|
| Cliente | **{{ cliente.razon_social }}** |
| NIF | {{ cliente.nif }} |
| Servicio | **{{ tier_desc }}** |
| Tier de retainer | {{ tier }} |
| Periodo reportado | **{{ per_etiq }}** |
| Desde | {{ per_desde }} |
| Hasta | {{ per_hasta }} |
| Fecha emisión informe | {{ fecha_emision }} |
| Categoría ENS del cliente | **{{ cat_ens }}** |

## 2. RESUMEN EJECUTIVO

Durante el periodo **{{ per_etiq }}** ({{ per_desde }} – {{ per_hasta }}), el servicio de retainer **{{ tier }}** se ha prestado conforme a las condiciones contractuales vigentes. La Entidad ha mantenido el nivel de seguridad declarado en la Declaración de Conformidad ENS (E-041) sin incidentes con impacto crítico.

A continuación se detallan los indicadores operativos del periodo, los incidentes gestionados y los cambios relevantes del sistema, junto con las recomendaciones para el próximo trimestre.

## 3. INDICADORES OPERATIVOS (KPIs)

{% if tiene_kpis %}
| Indicador | Valor del periodo | Objetivo | Estado |
|-----------|-------------------|----------|:------:|
{% for k in ret.kpis_periodo %}
| {{ k.nombre }} | **{{ k.valor }}** | {{ k.objetivo }} | {{ k.estado }} |
{% endfor %}
{% else %}
*Indicadores en proceso de medición. Se documentarán en el próximo informe trimestral.*
{% endif %}

## 4. INCIDENTES DE SEGURIDAD GESTIONADOS

{% if tiene_inc %}
Durante el periodo se han registrado y gestionado conforme al procedimiento E-204 los siguientes incidentes de seguridad. Todos los registrados se encuentran cerrados al cierre del periodo.

| ID | Fecha | Categoría | Severidad | Estado |
|----|-------|-----------|:---------:|:------:|
{% for inc in ret.incidentes_periodo %}
| {{ inc.id }} | {{ inc.fecha }} | {{ inc.categoria }} | {{ inc.severidad }} | {{ inc.estado }} |
{% endfor %}

Ningún incidente ha presentado severidad **ALTA** o **CRÍTICA** durante el periodo.
{% else %}
*No se han registrado incidentes de seguridad durante el periodo reportado.*
{% endif %}

## 5. CAMBIOS DEL SISTEMA

{% if tiene_chg %}
Durante el periodo se han documentado los siguientes cambios del sistema, gestionados conforme al procedimiento de gestión de cambios E-203.

| ID | Fecha | Descripción | Material |
|----|-------|-------------|:--------:|
{% for chg in ret.cambios_periodo %}
| {{ chg.id }} | {{ chg.fecha }} | {{ chg.descripcion }} | {{ 'SÍ' if chg.material else 'No' }} |
{% endfor %}

Los cambios marcados como **materiales** han sido documentados adicionalmente mediante el procedimiento E-042 (Comunicación de Cambio Material en el Sistema) y comunicados al CCN-CERT cuando ha procedido.
{% else %}
*No se han registrado cambios materiales del sistema durante el periodo.*
{% endif %}

## 6. ACCIONES PREVISTAS PARA EL PRÓXIMO PERIODO

a) **Mantenimiento ordinario** de las medidas del Anexo II del RD 311/2022 aplicables al sistema, conforme al Plan de Adecuación vigente (E-150).

b) **Revisión documental periódica** de las políticas y procedimientos del SGSI cuyo ciclo de revisión venza en el próximo trimestre.

c) **Programación o ejecución** de las pruebas de continuidad operativa previstas en el Plan de Continuidad del Negocio (E-401), si aplica al calendario anual.

d) **Programación de la auditoría interna anual** cuando el ciclo lo requiera.

e) **Continuidad del servicio de retainer** conforme a las condiciones contractuales vigentes.

## 7. CONSIDERACIONES Y RECOMENDACIONES

Se mantiene el nivel de servicio acorde al tier **{{ tier }}**. No se identifican desviaciones críticas respecto a los objetivos del periodo ni hallazgos que requieran intervención extraordinaria por parte del cliente.

Las recomendaciones de mejora continua identificadas durante el periodo se incorporarán al plan operativo del próximo trimestre como tareas de optimización, sin alterar el alcance contractual.

## 8. APROBACIÓN DEL INFORME

| Rol | Nombre | Firma |
|-----|--------|-------|
| Responsable de la Seguridad | {{ rs_nombre }} | _______________ |
| Representante del cliente | {{ rep_cliente }} | _______________ |
| Fecha de aprobación | {{ fecha_emision }} | — |

---

**Documento E-614 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: CONFIDENCIAL · CLIENTE**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ fecha_emision }}*
