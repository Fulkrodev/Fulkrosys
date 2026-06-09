# E-600 · INVENTARIO DE PROVEEDORES ENS

{% set doc_codigo = documento.codigo if documento.codigo else 'E-600' %}
{% set doc_version = documento.version if documento.version else '1.0' %}
{% set doc_fecha = documento.fecha_emision if documento.fecha_emision else '—' %}
{% set rseg_nombre = cliente.responsable_seguridad.nombre if cliente.responsable_seguridad and cliente.responsable_seguridad.nombre else '—' %}
{% set rseg_cargo = cliente.responsable_seguridad.cargo if cliente.responsable_seguridad and cliente.responsable_seguridad.cargo else 'Responsable de Seguridad' %}
{% set rsis_nombre = cliente.responsable_sistemas.nombre if cliente.responsable_sistemas and cliente.responsable_sistemas.nombre else '—' %}
{% set rsis_cargo = cliente.responsable_sistemas.cargo if cliente.responsable_sistemas and cliente.responsable_sistemas.cargo else 'Responsable de Sistemas' %}
{% set dir_nombre = cliente.direccion.nombre if cliente.direccion and cliente.direccion.nombre else '—' %}
{% set dir_cargo = cliente.direccion.cargo if cliente.direccion and cliente.direccion.cargo else 'Dirección' %}

**Documento:** {{ doc_codigo }}
**Versión:** {{ doc_version }}
**Fecha de emisión:** {{ doc_fecha }}
**Entidad responsable:** {{ cliente.razon_social }}
**NIF:** {{ cliente.nif }}
**Responsable del documento:** {{ rseg_nombre }} ({{ rseg_cargo }})
**Clasificación:** Uso Interno

---

## 1. OBJETO Y MARCO NORMATIVO

El presente documento constituye el **inventario formal de proveedores** que prestan servicios a {{ cliente.razon_social }} con acceso, tratamiento, almacenamiento o procesamiento de información o sistemas comprendidos en el ámbito del **Esquema Nacional de Seguridad (ENS)** regulado por el Real Decreto 311/2022, de 3 de mayo.

Este inventario da cumplimiento a:

a) **ENS Art. 18 y Anexo II medida `op.ext.1` (Contratación y acuerdos de nivel de servicio)** — obliga a mantener relación documentada de los servicios externalizados y sus responsables.

b) **ENS Anexo II medida `op.ext.2` (Gestión diaria)** — exige supervisión documental periódica de los proveedores que prestan servicios al sistema en ámbito ENS.

c) **RGPD Art. 28** — cuando el proveedor actúa como encargado de tratamiento de datos personales, debe existir registro identificativo y contrato vigente.

d) **NIS2 Art. 21.2.d)** — cuando aplica, exige mantener inventario de la cadena de suministro TIC con criticidad evaluada.

Este documento es un **entregable rellenable y mantenido vivo**, derivado automáticamente de la tabla `providers` del sistema FULKRO y enriquecido con las evaluaciones recogidas en la tabla `provider_assessments`.

## 2. ALCANCE

Se incluyen en este inventario todos los terceros que cumplan al menos una de las siguientes condiciones:

a) Acceden a información clasificada bajo el ámbito ENS de la Entidad.

b) Operan, administran o mantienen sistemas que dan soporte a servicios incluidos en la declaración de aplicabilidad ENS.

c) Procesan datos personales por cuenta de la Entidad (encargados de tratamiento).

d) Forman parte de la cadena de suministro TIC con criticidad **MEDIA**, **ALTA** o **CRÍTICA**.

e) Prestan servicios cuya interrupción afectaría la continuidad de operaciones de la Entidad.

Se excluyen explícitamente los proveedores de bienes de consumo no críticos sin acceso a sistemas ni información ENS (suministro de oficina, catering ocasional, etc.).

## 3. METODOLOGÍA DE CLASIFICACIÓN

Cada proveedor incluido es clasificado conforme a un nivel de criticidad que determina la profundidad de la evaluación y la frecuencia de las revisiones supervisoras:

| Nivel | Criterios | Frecuencia revisión |
|-------|-----------|---------------------|
| **CRÍTICO** | Acceso a información categoría ALTA · su interrupción detiene servicios esenciales · trata datos personales categoría especial Art. 9 RGPD | Anual + ad-hoc en cambios |
| **ALTO** | Acceso a información categoría MEDIA · interrupción degrada significativamente el servicio · trata volúmenes elevados de datos personales | Anual |
| **MEDIO** | Acceso limitado · interrupción tolerable < 24h · datos personales no sensibles | Bienal |
| **BAJO** | Acceso ocasional o restringido · sin tratamiento datos personales | Trienal |

La asignación del nivel se realiza mediante el procedimiento **E-217** (Procedimiento de evaluación y seguimiento de proveedores) tras la cumplimentación del cuestionario **E-601**.

## 4. INVENTARIO POR NIVEL DE CRITICIDAD

{% for nivel in ['CRITICO', 'ALTO', 'MEDIO', 'BAJO'] %}

{% set proveedores_nivel = proveedores | selectattr('nivel_criticidad', 'equalto', nivel) | list %}

### 4.{{ loop.index }} Proveedores nivel {{ nivel }}

{% if proveedores_nivel | length == 0 %}
*No se han identificado proveedores con nivel de criticidad {{ nivel }} a la fecha de emisión.*

{% else %}

| # | Razón social | NIF | Servicio prestado | Inicio | Próxima revisión |
|---|--------------|-----|-------------------|--------|------------------|
{% for p in proveedores_nivel %}
| {{ loop.index }} | {{ p.razon_social }} | {{ p.nif }} | {{ p.servicio_descripcion }} | {{ p.fecha_inicio }} | {{ p.next_review_date }} |
{% endfor %}

{% for p in proveedores_nivel %}
{% set p_categoria = p.categoria_servicio if p.categoria_servicio else '—' %}
{% set p_contacto_nombre = p.contacto_operativo.nombre if p.contacto_operativo and p.contacto_operativo.nombre else '—' %}
{% set p_contacto_email = p.contacto_operativo.email if p.contacto_operativo and p.contacto_operativo.email else '—' %}
{% set p_last_assessment = p.last_assessment_date if p.last_assessment_date else 'Sin evaluar' %}
{% set p_last_decision = p.last_assessment_decision if p.last_assessment_decision else '—' %}
{% set p_vencimiento = p.fecha_vencimiento if p.fecha_vencimiento else 'Indefinido' %}
{% set p_observaciones = p.observaciones if p.observaciones else '—' %}

**{{ loop.index }}. {{ p.razon_social }}**

- **Servicio:** {{ p.servicio_descripcion }}
- **Categoría servicio:** {{ p_categoria }}
- **Contacto operativo:** {{ p_contacto_nombre }} ({{ p_contacto_email }})
- **Normativas aplicables:** {% if p.normativas_aplicables %}{{ p.normativas_aplicables | join(', ') }}{% else %}ENS{% endif %}
- **Encargado de tratamiento (RGPD):** {{ 'Sí' if p.es_encargado_rgpd else 'No' }}
- **Adenda ENS vigente:** {{ 'Sí — ref. ' ~ p.adenda_referencia if p.adenda_referencia else 'Pendiente formalizar' }}
- **Última evaluación:** {{ p_last_assessment }} ({{ p_last_decision }})
- **Vencimiento contrato:** {{ p_vencimiento }}
- **Observaciones:** {{ p_observaciones }}

{% endfor %}
{% endif %}

{% endfor %}

## 5. RESUMEN AGREGADO

{% set count_criticos = proveedores | selectattr('nivel_criticidad', 'equalto', 'CRITICO') | list | length %}
{% set count_altos = proveedores | selectattr('nivel_criticidad', 'equalto', 'ALTO') | list | length %}
{% set count_medios = proveedores | selectattr('nivel_criticidad', 'equalto', 'MEDIO') | list | length %}
{% set count_bajos = proveedores | selectattr('nivel_criticidad', 'equalto', 'BAJO') | list | length %}
{% set count_total = proveedores | length %}
{% set count_con_adenda = proveedores | selectattr('adenda_referencia') | list | length %}
{% set count_pendientes_eval = proveedores | rejectattr('last_assessment_date') | list | length %}
{% set count_encargados_rgpd = proveedores | selectattr('es_encargado_rgpd') | list | length %}

| Indicador | Valor |
|-----------|-------|
| Proveedores CRÍTICOS | {{ count_criticos }} |
| Proveedores ALTOS | {{ count_altos }} |
| Proveedores MEDIOS | {{ count_medios }} |
| Proveedores BAJOS | {{ count_bajos }} |
| **TOTAL en inventario** | **{{ count_total }}** |
| Con adenda ENS firmada | {{ count_con_adenda }} |
| Pendientes evaluación inicial | {{ count_pendientes_eval }} |
| Encargados de tratamiento (RGPD Art. 28) | {{ count_encargados_rgpd }} |

## 6. DEPENDENCIAS CRÍTICAS Y RIESGOS DE CONCENTRACIÓN

{% if dependencias_criticas %}
Se han identificado las siguientes dependencias críticas que requieren atención especial por concentración o irremplazabilidad:

{% for dep in dependencias_criticas %}
{% set dep_plan = dep.plan_contingencia if dep.plan_contingencia else 'Pendiente definir' %}
- **{{ dep.proveedor }}** — {{ dep.descripcion_riesgo }}
  - Plan de contingencia: {{ dep_plan }}
{% endfor %}
{% else %}
No se han identificado dependencias críticas con riesgo de concentración a la fecha de emisión. La Entidad mantiene la diligencia de revisar este apartado en cada actualización del inventario.
{% endif %}

## 7. CALENDARIO DE REVISIONES PROGRAMADAS

{% set proveedores_con_review = proveedores | selectattr('next_review_date') | list %}
{% set proveedores_con_review_sorted = proveedores_con_review | sort(attribute='next_review_date') %}
{% if proveedores_con_review %}

| Proveedor | Tipo revisión | Fecha programada | Responsable |
|-----------|---------------|------------------|-------------|
{% for p in proveedores_con_review_sorted %}
{% set p_review_type = p.next_review_type if p.next_review_type else 'Periódica' %}
{% set p_review_owner = p.next_review_owner if p.next_review_owner else rseg_nombre %}
| {{ p.razon_social }} | {{ p_review_type }} | {{ p.next_review_date }} | {{ p_review_owner }} |
{% endfor %}

{% else %}
*No hay revisiones programadas con fecha definida a la emisión del presente inventario. Se acometerán en función del calendario operativo del procedimiento E-217.*
{% endif %}

## 8. PROVEEDORES DESVINCULADOS EN EL PERIODO

{% if proveedores_desvinculados %}

| Proveedor | Fecha baja | Motivo | Procedimiento exit completado |
|-----------|-----------|--------|-------------------------------|
{% for d in proveedores_desvinculados %}
| {{ d.razon_social }} | {{ d.fecha_baja }} | {{ d.motivo }} | {{ 'Sí' if d.exit_completo else 'Parcial — ' ~ d.exit_pendiente }} |
{% endfor %}

{% else %}
*No se han producido bajas de proveedores en el periodo cubierto por este inventario.*
{% endif %}

## 9. APROBACIÓN Y FIRMAS

El presente Inventario de Proveedores ha sido revisado y aprobado conforme a la Política de Seguridad en las Relaciones con Proveedores (E-112) y al Procedimiento de Gestión Operativa de Proveedores (E-216) vigentes en la Entidad.

| Rol | Nombre | Cargo | Fecha | Firma |
|-----|--------|-------|-------|-------|
| Elaborado por | {{ rseg_nombre }} | {{ rseg_cargo }} | {{ doc_fecha }} | |
| Revisado por | {{ rsis_nombre }} | {{ rsis_cargo }} | | |
| Aprobado por | {{ dir_nombre }} | {{ dir_cargo }} | | |

---

*Documento generado por FULKRO · plataforma de gestión ENS · {{ doc_fecha }}*
*Trazabilidad: este inventario se deriva en tiempo real de las tablas `providers` + `provider_assessments` del sistema FULKRO. La versión firmada en papel constituye el snapshot oficial en la fecha indicada.*
