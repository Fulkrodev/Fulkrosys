# DOCUMENTO E-200 — PROCEDIMIENTO DE ALTA DE PERSONAL

**Es el procedimiento que el auditor pide ver primero con registros reales de los últimos 3-6 meses. Materializa mp.per.1 y mp.per.2.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-200"
titulo: "Procedimiento de Alta de Personal"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE ALTA DE PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-200 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los pasos operativos para la incorporación segura de una nueva persona a {{ cliente.razon_social }}, garantizando que antes de que acceda a cualquier sistema o información del alcance del SGSI se han completado todos los controles de seguridad requeridos.

## 2. ALCANCE

Aplica a toda incorporación: personal laboral, becarios, personal en prácticas, personal temporal y personal externo (proveedores, consultores) que vaya a acceder a sistemas o información del alcance.

## 3. FLUJO OPERATIVO

### Fase A — Pre-incorporación (antes del primer día)

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| A.1 | RRHH comunica al Responsable de la Seguridad los datos de la nueva incorporación: nombre, puesto, fecha de inicio, responsable jerárquico, tipo de relación (laboral/externo) | RRHH | ≥ 5 días hábiles antes del inicio |
| A.2 | El Responsable de la Seguridad determina el perfil de acceso necesario según el puesto (necesidad de saber, nivel de clasificación accesible, sistemas requeridos, privilegios) | Resp. Seguridad | 3 días hábiles |
| A.3 | RRHH prepara los documentos de incorporación: contrato laboral o acuerdo de prestación, compromiso de confidencialidad (NDA), acuse de recibo de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103) | RRHH | Antes del inicio |
| A.4 | Si el puesto requiere acceso a información CONFIDENCIAL o superior: verificación de antecedentes proporcional (conforme a legislación laboral y RGPD) | RRHH + Resp. Seguridad | Antes del inicio |

### Fase B — Primer día

| Paso | Acción | Responsable |
|---|---|---|
| B.1 | Firma del contrato, NDA y acuse de la Política de Uso Aceptable | Nuevo empleado + RRHH |
| B.2 | **Sesión de acogida en seguridad** (mínimo 2 horas): presentación del SGSI, política de seguridad, normas de uso, procedimiento de notificación de incidentes, datos de contacto del Responsable de la Seguridad. Conforme al Plan de Formación (E-PF-001). | Resp. Seguridad o delegado |
| B.3 | Entrega de equipos corporativos con hardening aplicado conforme a E-IT-001 | Resp. Sistema |
| B.4 | Creación de cuentas y provisión de accesos conforme al procedimiento {{ proyecto.codigo_documento_base }}-231, con el perfil determinado en A.2 | Resp. Sistema |
| B.5 | Configuración de MFA conforme a {{ proyecto.codigo_documento_base }}-102 | Resp. Sistema + nuevo empleado |
| B.6 | Entrega de credenciales con cambio obligatorio en primer uso | Resp. Sistema |
| B.7 | Entrega de tarjeta/llave de acceso físico si procede, con registro en inventario | Resp. Sistema |

### Fase C — Primera semana

| Paso | Acción | Responsable |
|---|---|---|
| C.1 | Completar la formación de acogida específica del puesto (herramientas, procedimientos del área) | Responsable jerárquico |
| C.2 | Verificar que todos los accesos funcionan correctamente y son los necesarios (ni más ni menos) | Resp. Seguridad |
| C.3 | Registrar la incorporación en el sistema de gestión del SGSI como evidencia de cumplimiento de mp.per.1 y mp.per.2 | Resp. Seguridad |

## 4. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Contrato / acuerdo firmado | Vida laboral + 4 años |
| NDA firmado | Vigencia NDA + 5 años |
| Acuse de recibo Política Uso Aceptable | Vida laboral + 4 años |
| Registro de sesión de acogida (asistencia + firma) | 5 años |
| Registro de provisión de accesos (perfil, sistemas, fecha) | Vida laboral + 2 años |
| Registro de entrega de equipos (S/N, tipo, fecha) | Vida laboral + 2 años |

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Altas con sesión de acogida completada en primera semana | 100% |
| Altas con NDA firmado antes del primer acceso | 100% |
| Tiempo medio de provisión de accesos desde la incorporación | < 2 días hábiles |

---

**Documento {{ proyecto.codigo_documento_base }}-200 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
