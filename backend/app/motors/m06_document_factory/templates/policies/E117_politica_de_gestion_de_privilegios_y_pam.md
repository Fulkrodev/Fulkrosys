# DOCUMENTO E-117 — POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y PAM

**Materializa op.acc.3 (Segregación de funciones) y op.acc.4 (Gestión de derechos de acceso) con foco en cuentas privilegiadas. Obligatoria desde categoría MEDIA.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-117"
titulo: "Política de Gestión de Privilegios y Acceso Privilegiado (PAM)"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE GESTIÓN DE PRIVILEGIOS Y ACCESO PRIVILEGIADO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-117 — Versión {{ proyecto.version_actual }}**

---

## MARCO NORMATIVO

Esta política se desarrolla en cumplimiento del **Real Decreto 311/2022**, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS), y en particular de las siguientes medidas recogidas en su Anexo II:

- **op.acc.3** — Segregación de funciones y tareas.
- **op.acc.4** — Proceso de gestión de derechos de acceso.
- **op.acc.5** — Mecanismo de autenticación (MFA reforzado para accesos privilegiados).

Complementa la Política Maestra de Seguridad de la Información ({{ proyecto.codigo_documento_base }}-100) y concreta los principios allí establecidos en el ámbito del acceso privilegiado. Se alinea con la guía CCN-STIC 801 (Roles) para la separación de cuentas administrativas y con CCN-STIC 884 Anexo B (Privileged Identity Management) para entornos cloud Azure.

---

## 1. OBJETO

Establecer las reglas específicas para la gestión de cuentas con privilegios elevados (administradores, operadores, root, DBA, cuentas de servicio con acceso amplio) en los sistemas comprendidos en el alcance del SGSI, garantizando que el acceso privilegiado se concede con el mínimo alcance necesario, por el tiempo mínimo necesario y con trazabilidad completa.

## 2. PRINCIPIOS

**2.1 Privilegio mínimo estricto.** Los privilegios elevados se concederán únicamente para las tareas concretas que los requieran, nunca con carácter permanente o genérico.

**2.2 Justificación y aprobación.** Toda concesión de privilegios elevados requiere solicitud formal con justificación, aprobación del Responsable de la Seguridad y registro en el sistema de gestión de identidades.

**2.3 Separación de cuentas.** Las personas con funciones administrativas dispondrán de una cuenta nominativa estándar para su trabajo diario y una cuenta administrativa separada exclusivamente para tareas que requieran privilegios elevados. Queda prohibido el uso de la cuenta administrativa para actividades ordinarias.

**2.4 Sesiones acotadas.** Las sesiones privilegiadas tendrán duración limitada. Los privilegios Just-in-Time (JIT) se emplearán cuando la tecnología lo permita: el usuario solicita el privilegio, se le concede por un periodo definido, y se revoca automáticamente al expirar.

**2.5 Monitorización reforzada.** Todas las acciones realizadas con cuentas privilegiadas se registrarán en el SIEM con nivel de detalle superior al del usuario estándar, y se revisarán conforme al procedimiento de revisión de logs ({{ proyecto.codigo_documento_base }}-223).

**2.6 MFA obligatorio.** La autenticación multifactor es obligatoria para todo acceso privilegiado, sin excepción.

## 3. TIPOS DE CUENTAS PRIVILEGIADAS

| Tipo | Descripción | Requisitos específicos |
|---|---|---|
| Administrador de dominio | Control total sobre el directorio activo | MFA + sesión grabada + revisión mensual |
| Administrador de servidor | Root/Administrator en servidores | MFA + cuenta separada |
| DBA | Administrador de bases de datos | MFA + acceso restringido a producción |
| Administrador de red | Control sobre firewall, switches, routers | MFA + doble aprobación para cambios en producción |
| Administrador cloud | Consola de administración AWS/Azure/GCP | MFA + IP origen restringida |
| Cuenta de servicio privilegiada | Sistema a sistema con privilegios amplios | Credenciales en vault, rotación automática |
| Break-glass | Emergencia: acceso total al sistema | Sobre sellado, doble custodia, uso con testigo |

## 4. REVISIÓN PERIÓDICA

Las cuentas privilegiadas se revisarán **trimestralmente** para verificar que los privilegios concedidos siguen siendo necesarios y proporcionados. Las cuentas inactivas durante más de 60 días se deshabilitarán automáticamente.

## 5. PROCEDIMIENTO OPERATIVO

El detalle se desarrolla en el procedimiento {{ proyecto.codigo_documento_base }}-211 (Gestión de Cuentas Privilegiadas).

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-117 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
