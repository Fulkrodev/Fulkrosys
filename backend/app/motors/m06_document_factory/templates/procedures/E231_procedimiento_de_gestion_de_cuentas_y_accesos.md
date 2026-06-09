# DOCUMENTO E-231 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS

**Es el procedimiento operativo de la Política E-101.** Define quién pide, quién autoriza, quién provisiona, quién revisa y quién revoca cada acceso del sistema. El auditor pide ver el flujo completo en al menos 3 casos reales (alta, modificación, baja).

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-231"
titulo: "Procedimiento de Gestión de Cuentas y Accesos"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-101"
---

# PROCEDIMIENTO DE GESTIÓN DE CUENTAS Y ACCESOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-231 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para la solicitud, autorización, provisión, modificación, revisión periódica y revocación de cuentas de usuario y derechos de acceso a los sistemas de información de {{ cliente.razon_social }}, en desarrollo de la Política de Control de Acceso ({{ proyecto.codigo_documento_base }}-101).

## 2. ALCANCE

Aplica a toda cuenta de usuario, sea de personal interno, externo o de servicio, que permita el acceso a sistemas, redes, aplicaciones o información comprendidos en el alcance del SGSI.

## 3. TIPOS DE CUENTA

| Tipo | Descripción | Requisitos especiales |
|---|---|---|
| **Personal interno** | Empleado o personal estatutario | Vinculada a contrato laboral o de servicios |
| **Personal externo** | Contratista, consultor, becario | Vigencia limitada al periodo del contrato |
| **Privilegiada** | Administrador, root, sa, dba | MFA obligatorio. Revisión trimestral. |
| **De servicio** | Proceso automático, sistema-a-sistema | Sin acceso interactivo. Credenciales rotadas semestralmente. |
| **De emergencia** | Acceso break-glass | Custodia de credenciales en sobre sellado. Uso registrado y auditado. |

## 4. FLUJO DE GESTIÓN — ALTA

### 4.1 Solicitud

**Responsable:** Responsable jerárquico del solicitante (en personal externo, persona de contacto designada en el contrato).

**Acciones:**

1. Cumplimentar el **formulario de solicitud de acceso** (Anexo I), indicando:

- Datos de la persona solicitante.
- Fecha de incorporación o inicio de la prestación.
- Puesto, rol y funciones a desempeñar.
- Recursos a los que se solicita acceso (sistemas, aplicaciones, carpetas, etc.).
- Nivel de privilegio requerido en cada uno.
- Periodo previsto de vigencia (especialmente relevante en personal externo).
- Justificación del acceso.

2. Firmar electrónicamente la solicitud y remitirla al propietario de cada recurso solicitado.

### 4.2 Autorización

**Responsable:** Propietario del recurso (Responsable de la Información o Responsable del Servicio según el activo).

**Acciones:**

3. Verificar que la solicitud:

- Está firmada por el responsable jerárquico legitimado.
- Identifica claramente el rol y las funciones.
- Solicita un nivel de acceso proporcional a las funciones declaradas.
- Respeta el principio de necesidad de saber.
- Respeta las reglas de segregación de funciones del apartado 7 de la Política {{ proyecto.codigo_documento_base }}-101.

4. **Aprobar, denegar o modificar** la solicitud dentro de los siguientes plazos máximos desde la recepción:

| Tipo de acceso | Plazo máximo de decisión |
|---|---|
| Personal interno, acceso estándar | 3 días hábiles |
| Personal interno, acceso privilegiado | 5 días hábiles |
| Personal externo | 5 días hábiles |
| Cuenta de servicio | 5 días hábiles |

5. Documentar la decisión en el sistema de gestión de identidades, dejando trazabilidad del responsable y fecha.

### 4.3 Provisión técnica

**Responsable:** Responsable del Sistema o personal técnico bajo su supervisión.

**Acciones:**

6. Una vez autorizada la solicitud, provisionar técnicamente la cuenta y los accesos en un plazo máximo de **2 días hábiles** desde la autorización.

7. **Generar la credencial inicial** mediante un procedimiento que garantice:

- Aleatoriedad criptográfica.
- Cumplimiento de la política de contraseñas del apartado 5.3 de {{ proyecto.codigo_documento_base }}-101.
- Entrega segura al usuario por canal cifrado o con cambio obligatorio en el primer inicio de sesión.

8. **Configurar la autenticación multifactor** (MFA) cuando proceda según la política.

9. **Registrar la provisión** en el Inventario de Cuentas y Accesos del SGSI.

### 4.4 Notificación y aceptación

**Responsable:** Responsable del Sistema.

**Acciones:**

10. Notificar al usuario la disponibilidad de su cuenta, sus credenciales iniciales y las normas de uso aceptable ({{ proyecto.codigo_documento_base }}-103).

11. Requerir del usuario el **acuse de recibo** de las normas y, en su caso, la firma de los compromisos de confidencialidad correspondientes.

## 5. FLUJO DE GESTIÓN — MODIFICACIÓN

**Disparadores:** cambio de puesto, cambio de proyecto, asunción de nuevas funciones, finalización de un proyecto temporal.

**Responsable de iniciar:** Responsable jerárquico del usuario afectado.

**Acciones:**

12. Comunicar formalmente el cambio mediante el formulario del Anexo II.

13. El propietario del recurso evalúa los nuevos accesos necesarios y los privilegios que dejan de ser necesarios, autorizando la **modificación**.

14. El Responsable del Sistema ejecuta los cambios en el plazo de **3 días hábiles**.

15. Se aplican los principios de **mínimo privilegio** y **necesidad de saber** en la nueva configuración, eliminando privilegios residuales del puesto anterior.

## 6. FLUJO DE GESTIÓN — REVISIÓN PERIÓDICA

**Responsable de la coordinación:** Responsable de la Seguridad.

**Periodicidad:** según el apartado 6.4 de la Política {{ proyecto.codigo_documento_base }}-101:

| Tipo de acceso | Frecuencia mínima |
|---|---|
| Privilegiados (admin) | Trimestral |
| Información clasificada nivel ALTO | Trimestral |
| Información clasificada nivel MEDIO | Semestral |
| Generales | Anual |

**Acciones:**

16. El Responsable de la Seguridad genera el **listado de accesos vigentes** desde el sistema de gestión de identidades.

17. Se distribuye a los propietarios de los recursos para **validación**.

18. Cada propietario revisa, **dispone de 15 días hábiles** para confirmar la vigencia de cada acceso y, en su caso, solicitar la revocación o modificación de los que ya no sean necesarios.

19. Las modificaciones se ejecutan según el flujo del apartado 5.

20. Se elabora un **acta de revisión** que se eleva al Comité de Seguridad.

## 7. FLUJO DE GESTIÓN — REVOCACIÓN

### 7.1 Por cese ordinario

**Disparador:** baja del personal o finalización del contrato.

**Responsable de notificar:** Responsable jerárquico o departamento de Recursos Humanos.

**Acciones:**

21. Notificar el cese al Responsable de la Seguridad con **al menos 5 días hábiles de antelación** cuando sea posible.

22. El Responsable del Sistema procede a la revocación en los plazos máximos del apartado 6.5 de la Política {{ proyecto.codigo_documento_base }}-101:

| Tipo de acceso | Plazo máximo desde el cese |
|---|---|
| Privilegiados | 1 hora |
| Información ALTA | 4 horas |
| Información MEDIA | 24 horas |
| Generales | 72 horas |

23. Se ejecuta la **lista de comprobación de baja** del Anexo III, que incluye:

- Deshabilitación de la cuenta principal.
- Revocación de accesos a aplicaciones específicas.
- Cierre de sesiones activas.
- Bloqueo del correo electrónico (con redirección durante el periodo establecido).
- Recuperación de equipos y soportes corporativos.
- Recuperación de credenciales físicas (tarjetas, llaves, tokens).
- Comunicación a interlocutores externos cuando proceda.

24. La cuenta se mantiene **deshabilitada pero conservada** durante un periodo mínimo de 6 meses para preservar registros y evidencias, y posteriormente se elimina conforme al periodo de conservación establecido.

### 7.2 Por cese conflictivo o despido disciplinario

**Acciones especiales:**

25. La revocación es **inmediata y previa o simultánea** a la comunicación formal del cese a la persona afectada.

26. Se aplican medidas adicionales de monitorización forense durante las 72 horas siguientes al cese.

27. Se realiza una **revisión específica** de las acciones realizadas por la cuenta en los 30 días previos al cese.

## 8. CUENTAS DE SERVICIO

**Acciones específicas:**

28. Las cuentas de servicio se documentan en el **Inventario de Cuentas de Servicio**, identificando:

- Sistema o aplicación que la utiliza.
- Función que desempeña.
- Privilegios asignados.
- Responsable funcional.
- Mecanismo de gestión de credenciales.

29. Las **credenciales de cuentas de servicio** se almacenan en una **solución de gestión de secretos** (vault) con acceso restringido y auditado.

30. Se rotan al menos **cada 6 meses** y siempre que cese el personal con conocimiento de las mismas.

## 9. CUENTAS DE EMERGENCIA (BREAK-GLASS)

**Características:**

31. Existirán cuentas de emergencia para garantizar el acceso a sistemas críticos en situaciones excepcionales (fallo del sistema de identidades, indisponibilidad del personal habitual, etc.).

32. Las credenciales se custodiarán en **sobre sellado físico** o en bóveda con doble control, con acceso restringido a {{ responsables.responsable_seguridad.nombre }} y a su suplente designado.

33. Cualquier uso requerirá:

- Autorización previa del Responsable de la Seguridad o, en su defecto, del Comité de Crisis.
- Apertura formal del sobre con testigo.
- Registro detallado de las acciones realizadas.
- Cambio inmediato de la credencial tras el uso.
- Resellado y almacenamiento de la nueva credencial.

## 10. INDICADORES

| Indicador | Objetivo |
|---|---|
| Tiempo medio de provisión | < 2 días hábiles |
| Cumplimiento plazos de revocación tras cese | 100% |
| Cuentas privilegiadas con MFA activo | 100% |
| Cuentas huérfanas (sin revisión > 12 meses) | 0 |
| Cuentas inactivas > 90 días | < 5% del total |

## 11. ANEXOS

- **Anexo I:** Formulario de solicitud de acceso
- **Anexo II:** Formulario de modificación de acceso
- **Anexo III:** Lista de comprobación de baja
- **Anexo IV:** Plantilla de revisión periódica
- **Anexo V:** Registro de uso de cuentas break-glass

---

**Documento {{ proyecto.codigo_documento_base }}-231 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
