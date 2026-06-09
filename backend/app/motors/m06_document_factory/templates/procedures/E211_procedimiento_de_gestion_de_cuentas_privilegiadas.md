# DOCUMENTO E-211 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS

**Operativo de la Política PAM (E-117). Específico para cuentas admin, root, DBA, break-glass y de servicio con privilegios amplios.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-211"
titulo: "Procedimiento de Gestión de Cuentas Privilegiadas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-117"
---

# PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-211 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las reglas operativas específicas para la creación, uso, monitorización, rotación y revocación de cuentas con privilegios elevados.

## 2. INVENTARIO DE CUENTAS PRIVILEGIADAS

El Responsable del Sistema mantendrá un **inventario actualizado** de todas las cuentas privilegiadas, indicando: identificador, tipo (admin de dominio, root, DBA, admin cloud, cuenta de servicio, break-glass), persona o sistema asignado, privilegios concretos, fecha de última revisión, fecha de última rotación de credenciales.

## 3. CREACIÓN

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Solicitud formal con justificación de la necesidad del privilegio | Responsable jerárquico |
| 2 | Aprobación del Responsable de la Seguridad (obligatoria para toda cuenta privilegiada) | Resp. Seguridad |
| 3 | Creación de la cuenta separada (nomenclatura: `adm-{nombre}` o `svc-{sistema}`) | Resp. Sistema |
| 4 | Activación MFA obligatoria | Resp. Sistema |
| 5 | Almacenamiento de credenciales en vault corporativo | Resp. Sistema |
| 6 | Registro en el inventario de cuentas privilegiadas | Resp. Sistema |

## 4. REGLAS DE USO

a) La cuenta privilegiada se usará **exclusivamente** para las tareas que requieran ese nivel de privilegio. Para actividades ordinarias (correo, navegación, ofimática) se usará la cuenta nominativa estándar.

b) Las sesiones privilegiadas tendrán **duración limitada** y, cuando la tecnología lo permita, se implementará **Just-in-Time (JIT)**: el usuario solicita el privilegio → se le concede por un periodo definido (1-4 horas) → se revoca automáticamente.

c) Todas las sesiones privilegiadas se **registrarán con detalle** en el SIEM, incluyendo: usuario, sistema, hora inicio/fin, comandos ejecutados (cuando sea técnicamente viable).

d) Se realizarán **grabaciones de sesión** para los accesos privilegiados a sistemas críticos, conforme al nivel de la categoría ENS.

## 5. ROTACIÓN DE CREDENCIALES

| Tipo de cuenta | Frecuencia de rotación |
|---|---|
| Admin de dominio | Trimestral |
| Root / Administrator local | Trimestral |
| DBA | Semestral |
| Admin cloud | Trimestral |
| Cuenta de servicio privilegiada | Semestral |
| Break-glass | Tras cada uso + semestral preventiva |

## 6. CUENTAS BREAK-GLASS

a) Las credenciales se custodian en **sobre sellado en caja fuerte** con doble control de acceso.

b) El uso requiere: autorización del Resp. Seguridad (o del Comité de Crisis en incidente CRÍTICO), apertura con testigo, registro detallado de todas las acciones.

c) Tras el uso: cambio inmediato de credenciales, resellado del sobre, informe de uso al Comité de Seguridad.

## 7. REVISIÓN TRIMESTRAL

Cada trimestre el Resp. Seguridad verifica: vigencia de cada cuenta privilegiada, justificación actualizada, cumplimiento de MFA, última rotación, sesiones registradas.

## 8. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cuentas privilegiadas con MFA activo | 100% |
| Cuentas con credenciales rotadas en plazo | 100% |
| Cuentas privilegiadas sin uso > 60 días | 0 (deshabilitar) |
| Usos de break-glass sin registro completo | 0 |

---

**Documento {{ proyecto.codigo_documento_base }}-211 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
