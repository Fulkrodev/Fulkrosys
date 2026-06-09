# DOCUMENTO E-127 — POLÍTICA DE REGISTRO DE ACTIVIDAD: RETENCIÓN Y SINCRONIZACIÓN HORARIA

**Desarrolla la medida op.exp.8 (Registro de la actividad de los usuarios). Obligatoria en categoría MEDIA y ALTA: la retención mínima de 12 meses y la sincronización horaria son requisitos que el auditor ENAC verifica. En BÁSICA es recomendada.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-127"
titulo: "Política de Registro de Actividad: Retención y Sincronización Horaria"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE REGISTRO DE ACTIVIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-127 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y en particular de la medida del Anexo II:

- **op.exp.8 — Registro de la actividad de los usuarios.** Exige registrar la actividad relevante para la seguridad, conservar dichos registros durante un periodo suficiente (mínimo **12 meses** en categoría MEDIA y ALTA) y garantizar que las marcas de tiempo sean fiables mediante **sincronización horaria** de los sistemas.

Se alinea con las guías **CCN-STIC 808** (verificación del cumplimiento del ENS) y **CCN-STIC 809** (declaración y certificación), y complementa la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108) y el Procedimiento de Revisión de Registros (E-223).

---

## 1. OBJETO

Establecer los requisitos de {{ cliente.razon_social }} para el registro de la actividad de los sistemas y usuarios, su conservación durante al menos 12 meses, la protección de la integridad de los registros y la sincronización horaria que garantiza la validez probatoria de las marcas de tiempo.

## 2. ÁMBITO

Aplica a todos los sistemas de información incluidos en el alcance del ENS de {{ cliente.razon_social }}, incluidos los servicios cloud contratados. Para cada sistema se identificará el origen de los registros y el responsable de su custodia.

## 3. EVENTOS REGISTRADOS

Como mínimo se registrarán: accesos correctos y fallidos (autenticación), uso de privilegios y acciones administrativas, creación/modificación/borrado de cuentas y permisos, cambios de configuración relevantes para la seguridad, arranque y parada de los servicios de registro, y errores y eventos del sistema con impacto en seguridad. Cada registro incluirá, cuando proceda: fecha y hora (sincronizada), identidad del actor, evento, origen y resultado.

## 4. RETENCIÓN

| Categoría ENS | Retención mínima de los registros |
|---|---|
| BÁSICA | Recomendado ≥ 12 meses |
| MEDIA | **≥ 12 meses (obligatorio)** |
| ALTA | **≥ 12 meses (obligatorio), ampliable según valoración del riesgo** |

Los registros se conservarán protegidos durante todo el periodo de retención y no se eliminarán antes de su vencimiento. Cuando el cliente disponga de cloud conectado, la configuración de retención (p.ej. retención de CloudTrail/Azure Monitor/Workspace Audit) se aportará como evidencia de la medida op.exp.8.

## 5. PROTECCIÓN E INTEGRIDAD DE LOS REGISTROS

El acceso a los registros estará restringido al personal autorizado (Responsable de Seguridad y administradores designados). Se aplicarán controles para impedir su alteración o borrado no autorizado (almacenamiento de solo-anexado, control de acceso, copia en ubicación independiente). La eliminación al vencimiento de la retención se realizará de forma controlada y registrada.

## 6. SINCRONIZACIÓN HORARIA (NTP)

Todos los sistemas en alcance sincronizarán su reloj contra una **fuente de tiempo fiable** (servidor NTP interno o fuente oficial). La sincronización es condición para que las marcas de tiempo de los registros tengan valor probatorio ante una auditoría. Se documentará la fuente NTP utilizada y se aportará evidencia del estado de sincronización como parte de op.exp.8.

## 7. REVISIÓN Y MONITORIZACIÓN

Los registros se revisarán periódicamente conforme al **Procedimiento de Revisión de Registros (E-223)**. Las anomalías detectadas se tratarán como incidentes según {{ proyecto.codigo_documento_base }}-108.

## 8. ROLES Y RESPONSABILIDADES

El Responsable de Seguridad supervisa el cumplimiento de esta política; los administradores de sistemas garantizan la activación del registro, la retención configurada y la sincronización horaria; la Dirección dota de los recursos necesarios.

## 9. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual o ante cambios significativos en los sistemas en alcance.

---

**Documento {{ proyecto.codigo_documento_base }}-127 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
