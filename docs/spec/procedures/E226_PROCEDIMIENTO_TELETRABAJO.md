# DOCUMENTO E-226 — PROCEDIMIENTO DE TELETRABAJO

**Es el procedimiento operativo que ejecuta la Política de Teletrabajo y Movilidad ({{ proyecto.codigo_documento_base }}-110).** Define las condiciones técnicas y organizativas que deben cumplirse para que una persona pueda trabajar fuera de las instalaciones de {{ cliente.razon_social }} accediendo a sistemas e información del alcance del SGSI.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-226"
titulo: "Procedimiento de Teletrabajo"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-110"
medidas_ens: ["mp.eq.3", "op.acc.5", "op.acc.6", "mp.com.2"]
---

# PROCEDIMIENTO DE TELETRABAJO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-226 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para autorizar, configurar, supervisar y revocar el acceso remoto de las personas trabajadoras de {{ cliente.razon_social }} a los sistemas e información del alcance del SGSI desde ubicaciones distintas a las instalaciones corporativas.

Este procedimiento desarrolla las medidas **mp.eq.3 (protección de portátiles), op.acc.5 (mecanismo de autenticación) y op.acc.6 (acceso local)** del Anexo II del Real Decreto 311/2022, conforme a la guía CCN-STIC 804 y, en lo aplicable, la guía CCN-STIC 813 sobre teletrabajo.

## 2. ALCANCE

Aplica a:

- Empleados que prestan servicio en régimen total o parcial de teletrabajo.
- Trabajadores en desplazamiento ocasional fuera de instalaciones corporativas.
- Proveedores externos con acceso remoto autorizado.

Quedan **excluidos** los accesos puntuales tipo webmail desde dispositivos no corporativos, regulados por restricciones específicas de la plataforma.

## 3. AUTORIZACIÓN PARA TELETRABAJAR

### 3.1. Autorización formal

El régimen de teletrabajo debe estar autorizado:

1. **Acuerdo individual** firmado entre la persona trabajadora y {{ cliente.razon_social }}, conforme a la Ley 10/2021 de Trabajo a Distancia.
2. **Inclusión expresa** del acceso remoto en el contrato laboral o en anexo posterior.
3. **Compromiso de cumplimiento** de la Política {{ proyecto.codigo_documento_base }}-110 y de este procedimiento, firmado al inicio del régimen y renovado al menos anualmente.

### 3.2. Limitaciones por categoría

| Tipo de acceso | Categoría BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Acceso a información PÚBLICA / INTERNA | ✓ | ✓ | ✓ |
| Acceso a información CONFIDENCIAL | ✓ con restricciones | ✓ con restricciones | ✓ con auditoría reforzada |
| Acceso a información RESTRINGIDA | Requiere análisis caso a caso | ✗ por defecto | ✗ salvo emergencia con doble aprobación |
| Operaciones administrativas privilegiadas | ✓ con MFA | ✓ con MFA + bastion | ✓ con MFA + bastion + grabación |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** las operaciones de administración crítica (administración del directorio, KMS, SIEM, copias de seguridad) requieren acceso desde ubicación corporativa o desde sitio alternativo certificado en el Plan de Continuidad. El teletrabajo administrativo crítico está prohibido por defecto.
{% endif %}

## 4. EQUIPAMIENTO PERMITIDO

### 4.1. Equipos corporativos (modalidad por defecto)

Portátil corporativo entregado al usuario con:

- Imagen corporativa hardenizada conforme a {{ proyecto.codigo_documento_base }}-230.
- Cifrado de disco íntegro (BitLocker / FileVault / LUKS) — AES-256.
- EDR/antimalware corporativo activo y monitorizado.
- MDM corporativo con capacidad de borrado remoto.
- Inhabilitado el almacenamiento masivo USB salvo excepción {{ proyecto.codigo_documento_base }}-222.
- Cliente VPN corporativo preconfigurado.
- Política de bloqueo automático tras 5 minutos de inactividad.

### 4.2. Equipos personales (BYOD)

Solo permitidos si el régimen BYOD está aprobado conforme a {{ proyecto.codigo_documento_base }}-118 (Política BYOD), exigiendo:

- Container/perfil corporativo aislado del entorno personal (Intune Mobile Application Management, Workspace ONE, etc.).
- Cifrado del dispositivo activado.
- MDM corporativo aplicado al perfil corporativo (no al dispositivo completo).
- Acceso solo a aplicaciones corporativas autorizadas, sin VPN full-tunnel.
- Borrado remoto del perfil corporativo en caso de pérdida o cese.

### 4.3. Equipos prohibidos

- Equipos compartidos en cibercafés, hoteles, espacios públicos.
- Equipos de familiares o amigos.
- Equipos sin cifrado activo.
- Equipos con sistema operativo sin soporte de seguridad del fabricante.

## 5. AUTENTICACIÓN Y CONEXIÓN

### 5.1. VPN corporativa

- Cliente VPN aprobado (Cisco AnyConnect / FortiClient / OpenVPN corporativo / Tailscale empresarial).
- **MFA obligatorio:** algo que sé (PIN/contraseña) + algo que tengo (token TOTP o llave FIDO2).
- Establecimiento de túnel solo desde el equipo corporativo registrado en MDM.
- Verificación previa del estado del equipo (postura: parches al día, EDR activo, disco cifrado).
- Sesión limitada a la duración del trabajo; cierre forzado tras 12 horas inactivas.

### 5.2. Acceso a aplicaciones SaaS sin VPN

Cuando la aplicación es SaaS y el control se delega al IdP corporativo (Single Sign-On):

- Conexión solo a través del **IdP corporativo** (Azure AD / Okta / Keycloak / similar).
- MFA obligatorio en el IdP.
- Política de **Conditional Access** que verifica:
  - Equipo en MDM corporativo (compliance).
  - Origen geográfico permitido.
  - Riesgo del usuario aceptable según señales del IdP.

### 5.3. Acceso administrativo privilegiado

Para administración remota (acceso a servidores, consolas cloud, BD productivas):

- Conexión obligatoria mediante **bastion host** (Teleport / Boundary / Privileged Access Management).
- Cuenta diferente de la cuenta de usuario diario.
- MFA reforzado (FIDO2 idealmente).
- **Grabación íntegra de la sesión** y revisión por muestreo conforme a {{ proyecto.codigo_documento_base }}-211.

## 6. ENTORNO FÍSICO DEL PUESTO REMOTO

La persona teletrabajadora debe:

1. Disponer de un espacio reservado en su domicilio o ubicación habitual de teletrabajo, libre de visualización por terceros.
2. Mantener el dispositivo bajo control físico durante la jornada.
3. Bloquear pantalla al ausentarse, por breve que sea la ausencia.
4. No imprimir documentos clasificados CONFIDENCIAL+ en impresoras no corporativas.
5. No realizar reuniones en las que se traten datos sensibles desde lugares públicos sin auriculares.
6. Comunicar al Responsable de Seguridad cualquier cambio prolongado de ubicación al extranjero (puede afectar a transferencias internacionales RGPD y a regímenes fiscales).

## 7. SUPERVISIÓN Y REVISIÓN

### 7.1. Supervisión continua

- El SIEM ({{ proyecto.codigo_documento_base }}-223) recibe los logs de VPN, IdP y bastion. Se generan alertas por:
  - Conexión desde ubicación atípica.
  - Volumen anómalo de descargas.
  - Acceso fuera del horario habitual no justificado.
  - Errores recurrentes de MFA.

### 7.2. Revisión periódica

- **Trimestral:** revisión de cuentas con teletrabajo activo y verificación de su vigencia.
- **Semestral:** muestreo de sesiones grabadas de acceso privilegiado.
- **Anual:** renovación del compromiso de cumplimiento.

## 8. INCIDENTES ESPECÍFICOS DEL TELETRABAJO

| Tipo | Acción inmediata |
|---|---|
| Pérdida o sustracción del portátil | Comunicación inmediata, ejecución de borrado remoto vía MDM, revocación de credenciales y certificados, apertura de incidente nivel ALTO ({{ proyecto.codigo_documento_base }}-204) |
| Compromiso de credenciales | Cambio forzado, revocación de tokens MFA y reemisión, revisión de actividad reciente |
| Acceso desde ubicación no autorizada | Bloqueo del usuario, contacto con la persona, evaluación |
| Detección de malware en equipo remoto | Aislamiento vía EDR, análisis forense remoto, reinstalación si procede |

## 9. REVOCACIÓN DEL TELETRABAJO

El régimen de teletrabajo se revoca:

- **Por baja del trabajador:** revocación inmediata conforme al procedimiento {{ proyecto.codigo_documento_base }}-201.
- **Por cambio de rol:** reevaluación de los accesos remotos.
- **Por incidente grave de seguridad atribuible al usuario:** suspensión inmediata.
- **Por fin del acuerdo individual de teletrabajo.**

## 10. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-226.1 | Compromiso de teletrabajo firmado | Vigente + 6 años |
| F-226.2 | Inventario de equipo entregado al teletrabajador | Vigente + 3 años |
| L-226 | Logs VPN / IdP / bastion (en SIEM) | conforme {{ proyecto.codigo_documento_base }}-223 |
| R-226 | Actas de revisión trimestral / semestral | 3 años |

## 11. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % usuarios con compromiso vigente | con compromiso al día / teletrabajadores | 100 % |
| % equipos con MDM compliance | compliant / total | ≥ 98 % |
| Incidentes de seguridad atribuibles a teletrabajo | recuento trimestral | ≤ 2 |
| Tiempo medio de borrado remoto tras pérdida | media horas | ≤ 1 h |

## 12. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las medidas mp.eq.3 / op.acc.5 / op.acc.6 en CCN-STIC 804.
- Se modifique la Ley 10/2021 de Trabajo a Distancia o su desarrollo reglamentario.
- Se incorporen nuevas plataformas de IdP, VPN o MDM.
- Se detecten incidentes recurrentes en el régimen remoto.

Responsabilidad: **Responsable de la Seguridad** + **Responsable de RRHH**, con aprobación del **Comité de Seguridad**.
