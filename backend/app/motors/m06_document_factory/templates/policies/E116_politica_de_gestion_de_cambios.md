# DOCUMENTO E-116 — POLÍTICA DE GESTIÓN DE CAMBIOS

**Política madre del procedimiento E-203. Materializa op.exp.5 del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-116"
titulo: "Política de Gestión de Cambios"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE CAMBIOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-116 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que ningún cambio se introduzca en los sistemas productivos comprendidos en el alcance del SGSI sin haber sido previamente planificado, evaluado en términos de seguridad y estabilidad, autorizado por el órgano competente y verificado tras su implantación, en cumplimiento de la medida **op.exp.5 (Gestión de cambios)** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Todo cambio es formal.** Todo cambio en hardware, software, configuración, red o procedimientos operativos del sistema debe seguir un flujo formal documentado.

**2.2 Análisis de impacto previo.** Antes de su ejecución, cada cambio será evaluado en términos de impacto en la seguridad, la disponibilidad y la integridad del sistema.

**2.3 Reversibilidad.** Todo cambio debe tener un plan de marcha atrás (rollback) documentado y probado antes de su ejecución.

**2.4 Trazabilidad.** Todo cambio quedará registrado con identificador único, persona solicitante, autorizador, ejecutor, fecha y resultado.

**2.5 Comité de Cambios (CAB).** Los cambios de impacto ALTO o CRÍTICO serán evaluados y autorizados por el Comité de Cambios, conforme al procedimiento {{ proyecto.codigo_documento_base }}-203.

## 3. CLASIFICACIÓN

Los cambios se clasifican en: ESTÁNDAR (preautorizados, catálogo), NORMAL (requieren evaluación individual), EMERGENCIA (flujo abreviado con ratificación posterior).

## 4. PROCEDIMIENTO OPERATIVO

El detalle se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-203 (Gestión de Cambios Técnicos).

## 5. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-116 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
