# DOCUMENTO E-202 — PROCEDIMIENTO DE CAMBIO DE ROL

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-202"
titulo: "Procedimiento de Cambio de Rol o Funciones"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-101, {{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE CAMBIO DE ROL O FUNCIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-202 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que cuando una persona cambia de puesto, departamento o funciones dentro de {{ cliente.razon_social }}, sus accesos se ajustan al nuevo rol aplicando el principio de mínimo privilegio, revocando los accesos del puesto anterior que dejen de ser necesarios.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | RRHH notifica el cambio al Resp. Seguridad: persona, puesto anterior, puesto nuevo, fecha efectiva | RRHH | ≥ 5 días hábiles antes |
| 2 | Resp. Seguridad determina el nuevo perfil de acceso y lo compara con el actual | Resp. Seguridad | 3 días hábiles |
| 3 | **Revocación de accesos del puesto anterior** que no sean necesarios en el nuevo | Resp. Sistema | Fecha del cambio |
| 4 | **Provisión de accesos nuevos** requeridos por el nuevo puesto | Resp. Sistema | ≤ 3 días hábiles |
| 5 | Verificación de que no quedan privilegios residuales del puesto anterior (*privilege creep*) | Resp. Seguridad | 5 días hábiles |
| 6 | Formación específica de seguridad del nuevo puesto si procede | Resp. jerárquico | 10 días hábiles |
| 7 | Registro del cambio en el sistema de gestión de identidades | Resp. Sistema | Fecha del cambio |

## 3. REGLA ANTI-ACUMULACIÓN

Cuando la persona haya ocupado 3 o más puestos distintos en los últimos 3 años, el Resp. Seguridad realizará una **revisión completa** de todos sus accesos vigentes para detectar acumulación de privilegios residuales. Esta revisión se documenta como evidencia.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cambios con revisión de accesos completada en plazo | 100% |
| Privilegios residuales detectados en revisiones post-cambio | 0 |

---

**Documento {{ proyecto.codigo_documento_base }}-202 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
