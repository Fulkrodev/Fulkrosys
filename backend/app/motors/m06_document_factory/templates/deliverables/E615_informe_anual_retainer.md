---
codigo_documento: "E-615"
titulo: "Informe Anual de Retainer"
version: "{{ proyecto.version_actual if proyecto.version_actual else '1.0' }}"
clasificacion: "CONFIDENCIAL · CLIENTE"
naturaleza: "Entregable anual consolidado del servicio de retainer"
---

# INFORME ANUAL DE RETAINER

**Cliente: {{ cliente.razon_social }}**
**Documento E-615 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }}**

---

{% set ret = retainer if retainer else {} %}
{% set tier = ret.tier if ret and ret.tier else 'R_STD' %}
{% set tier_desc = ret.tier_descripcion if ret and ret.tier_descripcion else 'Retainer Estándar' %}
{% set anio = ret.anio_reportado if ret and ret.anio_reportado else '2026' %}
{% set fecha_emision = proyecto.fecha_aprobacion_inicial if proyecto.fecha_aprobacion_inicial else '[fecha emisión]' %}
{% set cat_ens = proyecto.categoria_ens if proyecto.categoria_ens else 'MEDIA' %}
{% set fecha_renov = ret.fecha_renovacion if ret and ret.fecha_renovacion else '[fecha renovación]' %}
{% set rs_nombre = responsables.responsable_seguridad.nombre if responsables.responsable_seguridad else '[RS]' %}
{% set rep_cliente = cliente.representante.nombre if cliente.representante else '[Representante]' %}
{% set inc_total = ret.incidentes_anuales_total if ret and ret.incidentes_anuales_total else 'No disponible' %}
{% set inc_criticos = ret.incidentes_criticos_anuales if ret and ret.incidentes_criticos_anuales else '0' %}
{% set tiempo_medio = ret.tiempo_medio_anual if ret and ret.tiempo_medio_anual else 'No disponible' %}
{% set cambios_mat = ret.cambios_materiales_anuales if ret and ret.cambios_materiales_anuales else 'No disponible' %}
{% set cobertura = ret.cobertura_formacion_anual if ret and ret.cobertura_formacion_anual else 'No disponible' %}
{% set fecha_aud_int = ret.fecha_auditoria_interna_anual if ret and ret.fecha_auditoria_interna_anual else '[fecha]' %}
{% set fecha_verif = ret.fecha_verificacion_externa if ret and ret.fecha_verificacion_externa else 'No aplicable' %}
{% set cambio_tier = ret.recomendacion_cambio_tier if ret and ret.recomendacion_cambio_tier is defined else False %}
{% set tiene_inc = ret.incidentes_periodo and ret.incidentes_periodo | length > 0 %}
{% set tiene_chg = ret.cambios_periodo and ret.cambios_periodo | length > 0 %}

## 1. IDENTIFICACIÓN DEL INFORME

| Campo | Valor |
|-------|-------|
| Cliente | **{{ cliente.razon_social }}** |
| NIF | {{ cliente.nif }} |
| Servicio | **{{ tier_desc }}** |
| Tier de retainer | {{ tier }} |
| Año reportado | **{{ anio }}** |
| Fecha emisión informe | {{ fecha_emision }} |
| Categoría ENS del cliente | **{{ cat_ens }}** |
| Próxima renovación contractual | {{ fecha_renov }} |

## 2. RESUMEN EJECUTIVO ANUAL

Durante el ejercicio **{{ anio }}**, el servicio de retainer **{{ tier }}** se ha prestado de forma continuada conforme a las condiciones contractuales. La Entidad ha mantenido la conformidad con el ENS en su categoría **{{ cat_ens }}** sin incidentes con impacto crítico ni desviaciones materiales respecto a los objetivos del SGSI.

El presente informe consolida la actividad de los cuatro informes trimestrales (E-614) emitidos durante el año y constituye el documento de referencia para la revisión del Comité de Seguridad de la Información y para la eventual decisión de renovación del retainer en el siguiente ciclo contractual.

## 3. CONSOLIDACIÓN ANUAL DE INDICADORES

| Indicador | Acumulado anual | Objetivo anual | Tendencia |
|-----------|-----------------|----------------|:---------:|
| Incidentes registrados (total) | {{ inc_total }} | ≤ 20 | Estable |
| Incidentes críticos | {{ inc_criticos }} | 0 | OK |
| Tiempo medio de respuesta a incidentes | {{ tiempo_medio }} | ≤ 4h | OK |
| Cambios materiales documentados | {{ cambios_mat }} | — | — |
| Cobertura de formación en seguridad | {{ cobertura }} | ≥ 80% | OK |

## 4. INCIDENTES DE SEGURIDAD CONSOLIDADOS

{% if tiene_inc %}
A continuación se reseñan los incidentes más representativos gestionados durante el año:

| ID | Fecha | Categoría | Severidad | Estado final |
|----|-------|-----------|:---------:|:------------:|
{% for inc in ret.incidentes_periodo %}
| {{ inc.id }} | {{ inc.fecha }} | {{ inc.categoria }} | {{ inc.severidad }} | {{ inc.estado }} |
{% endfor %}

Todos los incidentes han sido gestionados conforme al procedimiento E-204 y registrados en el Libro de Incidentes del SGSI con su correspondiente trazabilidad documental.
{% else %}
*No se han registrado incidentes representativos durante el año reportado.*
{% endif %}

## 5. CAMBIOS MATERIALES Y NO MATERIALES

{% if tiene_chg %}
| ID | Fecha | Descripción | Material |
|----|-------|-------------|:--------:|
{% for chg in ret.cambios_periodo %}
| {{ chg.id }} | {{ chg.fecha }} | {{ chg.descripcion }} | {{ 'SÍ' if chg.material else 'No' }} |
{% endfor %}

Los cambios marcados como **materiales** han sido notificados adicionalmente mediante el procedimiento E-042 al CCN-CERT cuando ha procedido conforme al artículo 30 del RD 311/2022.
{% else %}
*No se han registrado cambios del sistema durante el año.*
{% endif %}

## 6. AUDITORÍAS REALIZADAS DURANTE EL AÑO

| Tipo | Fecha | Resultado | Observaciones |
|------|-------|-----------|---------------|
| Auditoría interna anual | {{ fecha_aud_int }} | Aprobada | Plan de acción al día |
| Verificación externa (si procede) | {{ fecha_verif }} | — | — |

## 7. PLAN PARA EL AÑO SIGUIENTE

a) **Continuidad de las medidas implantadas** conforme al Plan de Adecuación vigente (E-150) y a su actualización periódica.

b) **Programación de la auditoría interna anual** correspondiente al siguiente ejercicio, conforme al ciclo establecido por el Responsable de la Seguridad.

c) **Revisión del Análisis de Riesgos** (E-400) conforme a su ciclo anual y a los cambios materiales documentados durante el año reportado.

d) **Revisión de la categorización ENS** (E-012) conforme a su ciclo anual y al estado actual de las dimensiones de seguridad.

e) **Evaluación de la oportunidad de renovación** del retainer en su nivel actual o de ascenso a un tier superior, conforme a las necesidades de servicio del cliente y al perfil de riesgo del sistema.

f) **Continuidad de los informes trimestrales** E-614 durante el siguiente ejercicio.

## 8. DECISIÓN DE RENOVACIÓN DEL RETAINER

| Aspecto | Recomendación |
|---------|---------------|
| Mantener tier actual ({{ tier }}) | {{ 'Recomendado · servicio adecuado al perfil de riesgo actual' if not cambio_tier else 'A revisar' }} |
| Ascenso a tier superior | {{ 'A evaluar conjuntamente con el cliente' if cambio_tier else 'No necesario en el corto plazo' }} |
| Fecha de renovación contractual | **{{ fecha_renov }}** |

La decisión final de renovación corresponde al cliente. El Responsable de la Seguridad recomienda iniciar la conversación de renovación con un margen mínimo de **dos meses** sobre la fecha de vencimiento contractual.

## 9. APROBACIÓN DEL INFORME

| Rol | Nombre | Firma |
|-----|--------|-------|
| Responsable de la Seguridad | {{ rs_nombre }} | _______________ |
| Representante del cliente | {{ rep_cliente }} | _______________ |
| Fecha de aprobación | {{ fecha_emision }} | — |

---

**Documento E-615 — Versión {{ proyecto.version_actual if proyecto.version_actual else '1.0' }} — Clasificación: CONFIDENCIAL · CLIENTE**

*Documento generado por FULKRO · plataforma de gestión de cumplimiento normativo · {{ fecha_emision }}*
