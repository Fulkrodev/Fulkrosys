# DOCUMENTO E-201 — PROCEDIMIENTO DE BAJA DE PERSONAL

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-201"
titulo: "Procedimiento de Baja de Personal"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE BAJA DE PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-201 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que al cesar la relación de una persona con {{ cliente.razon_social }} se revocan todos los accesos, se recuperan todos los activos y se preserva la seguridad de la información, conforme a los plazos establecidos en la Política de Control de Accesos ({{ proyecto.codigo_documento_base }}-101).

## 2. TIPOS DE BAJA

| Tipo | Características | Plazos de revocación |
|---|---|---|
| **Ordinaria** | Fin de contrato, jubilación, dimisión voluntaria con preaviso | Conforme a tabla del apartado 3 |
| **Conflictiva** | Despido disciplinario, cese conflictivo, sospecha de deslealtad | **Inmediata y previa a la comunicación** |
| **Urgente** | Fallecimiento, incapacidad sobrevenida | 24 horas |

## 3. FLUJO OPERATIVO — BAJA ORDINARIA

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | RRHH notifica al Resp. Seguridad la fecha efectiva de baja | RRHH | ≥ 5 días hábiles antes |
| 2 | Resp. Seguridad genera la **lista de comprobación de baja** (Anexo I) con todos los accesos, equipos y credenciales de la persona | Resp. Seguridad | 2 días hábiles |
| 3 | Revocación de accesos lógicos en los plazos: privilegiados 1h, información ALTA 4h, MEDIA 24h, generales 72h desde la efectividad del cese | Resp. Sistema | Según plazos |
| 4 | Deshabilitación del correo electrónico corporativo con redirección al responsable jerárquico (máx. 30 días) | Resp. Sistema | Día del cese |
| 5 | Cierre de sesiones activas en todos los sistemas | Resp. Sistema | Día del cese |
| 6 | Recuperación de equipos: portátil, móvil, token MFA, tarjeta de acceso, llaves, soportes extraíbles | Resp. Sistema + RRHH | Día del cese |
| 7 | Recuperación o borrado de información corporativa en dispositivos personales si BYOD autorizado | Resp. Sistema | Día del cese |
| 8 | Recordatorio escrito de las obligaciones de confidencialidad subsistentes (NDA) | RRHH | Día del cese |
| 9 | Entrevista de salida (opcional, recomendada para puestos con acceso a información sensible) | RRHH + Resp. Seguridad | ≤ 5 días tras el cese |
| 10 | Verificación final de que todos los puntos de la lista de comprobación están cerrados | Resp. Seguridad | 72 horas tras el cese |
| 11 | Registro de la baja en el sistema de gestión del SGSI | Resp. Seguridad | 72 horas |

## 4. FLUJO — BAJA CONFLICTIVA

| Paso | Acción | Responsable |
|---|---|---|
| 1 | RRHH o Dirección notifica al Resp. Seguridad **antes** de comunicar el despido al afectado | RRHH/Dirección |
| 2 | **Revocación inmediata** de todos los accesos lógicos y físicos antes o simultáneamente a la comunicación | Resp. Sistema |
| 3 | Revisión forense de las acciones realizadas por la cuenta en los últimos 30 días | Resp. Seguridad |
| 4 | Monitorización reforzada durante 72 horas por si detecta accesos residuales | Resp. Sistema |
| 5 | Resto del flujo ordinario (pasos 6-11) | Según paso |

## 5. REGISTROS

| Registro | Conservación |
|---|---|
| Lista de comprobación de baja completada y firmada | 5 años |
| Acta de devolución de equipos | 5 años |
| Recordatorio NDA firmado por el exempleado (si acepta) | Vigencia NDA |

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Bajas con revocación de accesos en plazo | 100% |
| Bajas con todos los equipos recuperados | 100% |
| Lista de comprobación cerrada en 72h | ≥ 95% |

---

**Documento {{ proyecto.codigo_documento_base }}-201 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
