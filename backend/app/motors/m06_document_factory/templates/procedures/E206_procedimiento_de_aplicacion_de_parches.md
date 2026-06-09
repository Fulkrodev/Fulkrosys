# DOCUMENTO E-206 — PROCEDIMIENTO DE APLICACIÓN DE PARCHES

**Split del antiguo procedimiento E-218 (Vulnerabilidades y Parches). Este cubre el ciclo de vida del parche; E-205 (ya existente, renumerado) cubre la detección de vulnerabilidades.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-206"
titulo: "Procedimiento de Aplicación de Parches"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-115"
---

# PROCEDIMIENTO DE APLICACIÓN DE PARCHES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para la aplicación controlada de parches de seguridad y actualizaciones en los sistemas del alcance del SGSI, desde la disponibilidad del parche hasta su verificación post-despliegue.

## 2. RELACIÓN CON E-205 (VULNERABILIDADES)

El procedimiento E-205 (Gestión de Vulnerabilidades) **detecta y prioriza** las vulnerabilidades. El presente procedimiento **gestiona la aplicación del parche** que las corrige. Ambos se ejecutan en cascada: E-205 identifica → E-206 aplica.

## 3. PLAZOS MÁXIMOS DE APLICACIÓN

| Criticidad (determinada por E-205) | Plazo máximo desde disponibilidad del parche |
|---|---|
| CRÍTICA con explotación activa (CISA KEV) | 24 horas |
| CRÍTICA | 7 días naturales |
| ALTA | 15 días naturales |
| MEDIA | 60 días naturales |
| BAJA | 180 días o siguiente ciclo de mantenimiento |

## 4. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Recepción de la asignación desde E-205 con vulnerabilidad, parche disponible y criticidad | Resp. Sistema |
| 2 | **Pruebas en preproducción**: aplicar el parche en entorno equivalente al productivo y verificar: no regresión funcional, compatibilidad, estabilidad | Resp. Sistema |
| 3 | Para parches CRÍTICOS con explotación activa: pruebas reducidas o en paralelo autorizadas por el Resp. Seguridad | Resp. Seguridad |
| 4 | **Solicitud de cambio** conforme al procedimiento E-203 (Gestión de Cambios). Para parches CRÍTICOS: flujo de cambio de emergencia | Resp. Sistema |
| 5 | **Despliegue** en la ventana de mantenimiento aprobada, documentando: fecha/hora exacta, sistemas parcheados, persona ejecutora, parche aplicado (referencia fabricante), resultado | Resp. Sistema |
| 6 | **Verificación post-despliegue**: comprobación de versión parcheada, re-escaneo de la vulnerabilidad, verificación del servicio | Resp. Sistema |
| 7 | **Cierre** en el sistema de gestión de vulnerabilidades: marcar como MITIGADA con fecha y verificador | Resp. Seguridad |

## 5. EXCEPCIONES

Cuando no sea posible aplicar un parche en plazo (incompatibilidad, sistema legacy, dependencia de terceros), se gestionará como excepción conforme a {{ proyecto.codigo_documento_base }}-222 (Gestión de Excepciones), documentando: vulnerabilidad, motivo, riesgo asumido, mitigaciones compensatorias, plazo máximo y plan de resolución.

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Parches CRÍTICOS aplicados en plazo | 100% |
| Parches ALTOS aplicados en plazo | ≥ 95% |
| Tasa de rollback por parche fallido | < 3% |
| Excepciones documentadas / excepciones totales | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
