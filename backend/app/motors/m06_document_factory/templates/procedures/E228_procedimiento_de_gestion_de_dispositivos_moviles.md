# DOCUMENTO E-228 — PROCEDIMIENTO DE GESTIÓN DE DISPOSITIVOS MÓVILES

**Es el procedimiento operativo que ejecuta la Política BYOD ({{ proyecto.codigo_documento_base }}-118) y la Política de Teletrabajo ({{ proyecto.codigo_documento_base }}-110) en lo relativo a smartphones y tabletas.** Define cómo se enrolan, configuran y supervisan los dispositivos móviles autorizados a acceder a información del alcance del SGSI.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-228"
titulo: "Procedimiento de Gestión de Dispositivos Móviles"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-118, {{ proyecto.codigo_documento_base }}-110"
medidas_ens: ["mp.eq.3", "op.acc.5", "mp.com.2"]
---

# PROCEDIMIENTO DE GESTIÓN DE DISPOSITIVOS MÓVILES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-228 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para enrolar, configurar, mantener y dar de baja los smartphones y tabletas (corporativos o personales en régimen BYOD) que acceden a información o servicios del alcance del SGSI de {{ cliente.razon_social }}.

Este procedimiento desarrolla la medida **mp.eq.3 (protección de equipos portátiles)** del Anexo II del Real Decreto 311/2022 conforme a la guía CCN-STIC 804 y a la guía CCN-STIC 880 sobre dispositivos móviles.

## 2. ALCANCE

Aplica a:

- Smartphones y tabletas iOS y Android utilizados para acceder a correo corporativo, intranet, aplicaciones de negocio, almacenamiento corporativo o cualquier sistema del alcance.
- Tanto dispositivos corporativos (Corporate-Owned, COBO/COPE) como personales (BYOD) autorizados.

Quedan excluidos los dispositivos que únicamente acceden a información PÚBLICA por canales no autenticados.

## 3. MODALIDADES Y CRITERIOS

| Modalidad | Propiedad | Gestión | Aplicaciones permitidas |
|---|---|---|---|
| **COBO** (Corporate Owned, Business Only) | {{ cliente.razon_social }} | MDM completo | Solo aplicaciones aprobadas |
| **COPE** (Corporate Owned, Personally Enabled) | {{ cliente.razon_social }} | MDM con perfil de trabajo separado | Aprobadas + uso personal limitado |
| **BYOD** (Bring Your Own Device) | Persona | MAM o perfil de trabajo (Android Enterprise / iOS managed apps) | Solo aplicaciones corporativas autorizadas |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** los dispositivos que accedan a información de la categoría son obligatoriamente COBO o COPE; el régimen BYOD queda restringido a información de clasificación INTERNA o inferior.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Responsable del Sistema** | Operar el MDM, enrolar dispositivos, atender incidencias. |
| **Responsable de la Seguridad** | Aprobar el catálogo de aplicaciones, supervisar postura, gestionar wipes remotos. |
| **Persona usuaria** | Cumplir la política, notificar pérdida o cambio de dispositivo. |
| **DPO** | Validar el régimen BYOD frente a la separación trabajo/personal. |
| **Soporte TI** | Atender el soporte funcional al usuario. |

## 5. ENROLAMIENTO DEL DISPOSITIVO

### Fase 1 — Solicitud

1. La persona solicita acceso desde el dispositivo cumplimentando el formulario **F-228 — Solicitud de Enrolamiento de Dispositivo Móvil** indicando:
   - Tipo (smartphone/tableta), modelo, sistema operativo y versión.
   - Modalidad solicitada (COBO/COPE/BYOD).
   - Aplicaciones requeridas.
   - Para BYOD, autorización por escrito conforme a {{ proyecto.codigo_documento_base }}-118.

### Fase 2 — Verificación de elegibilidad

2. El Responsable del Sistema verifica:
   - Modelo soportado por el MDM corporativo.
   - Versión del SO **dentro del soporte del fabricante** (no se admiten versiones EOL).
   - Capacidad para activar cifrado de dispositivo y biometría.
   - Pantalla de bloqueo activable con PIN/contraseña/biométrico.

### Fase 3 — Configuración base obligatoria

3. **Cifrado de dispositivo activado** (por defecto en iOS y Android modernos; verificar).
4. **Bloqueo automático** tras 1 minuto de inactividad.
5. **Código de bloqueo:** PIN ≥ 6 dígitos o contraseña alfanumérica de ≥ 8 caracteres. Biometría aceptable como conveniencia, no como sustituto.
6. **Borrado tras N intentos fallidos:** wipe del perfil corporativo (BYOD) o del dispositivo (COBO/COPE) tras 10 intentos.
7. **Geolocalización** activada para los servicios de "Buscar mi dispositivo" del fabricante.
8. **Almacenamiento externo** (microSD, USB-OTG): deshabilitado para modalidad COBO; restringido a aplicaciones autorizadas en COPE/BYOD.
9. **Conexiones inalámbricas:**
   - Bluetooth: solo emparejamiento con dispositivos identificables.
   - Wi-Fi: prohibida la conexión automática a redes abiertas; uso obligatorio de VPN si se accede a recursos corporativos desde Wi-Fi públicas.
10. **Cámara y micrófono:** restringidos por aplicación; prohibido el uso en zonas señalizadas.

### Fase 4 — Despliegue del catálogo de aplicaciones

11. Solo aplicaciones del catálogo corporativo (Managed Google Play / Apple Business Manager / Intune Company Portal). Catálogo mantenido por el Responsable de Seguridad con frecuencia mínima de revisión semestral.

12. Aplicaciones críticas (correo, almacenamiento, comunicación) configuradas con:
    - SSO con el IdP corporativo y MFA.
    - Container o managed-app que restringe copy/paste fuera del perímetro corporativo.
    - Imposibilidad de hacer backup de datos corporativos a cuentas personales.

### Fase 5 — Notificación al usuario

13. Entrega de la **guía de uso seguro** del dispositivo y firma del compromiso de cumplimiento.

## 6. OPERACIÓN Y SUPERVISIÓN

### 6.1. Postura de cumplimiento (compliance)

El MDM evalúa continuamente la postura del dispositivo:

- Versión SO dentro del soporte del fabricante.
- No detección de **jailbreak / root**.
- Cifrado activo.
- Bloqueo activo conforme a la política.
- Aplicaciones permitidas vigentes.
- Última sincronización < 30 días.

Los dispositivos **non-compliant** pierden el acceso a recursos corporativos hasta su regularización (Conditional Access en el IdP).

### 6.2. Aplicación de parches

- Notificación automática al usuario cuando hay actualizaciones de SO.
- Plazo máximo para aplicar parches del SO:
  - Críticos de seguridad: **7 días naturales**.
  - Resto: 30 días naturales.
- Tras el plazo, el dispositivo entra en estado non-compliant.

### 6.3. Revisión periódica

- Mensual: muestreo de dispositivos para verificar postura.
- Trimestral: revisión completa del inventario y reconciliación con HHRR.
- Anual: actualización del catálogo de aplicaciones y de la guía de uso.

## 7. INCIDENTES Y RESPUESTA

### 7.1. Pérdida o sustracción

1. La persona usuaria comunica inmediatamente al buzón de seguridad y al Responsable del Sistema.
2. Activación inmediata de:
   - **Wipe remoto** del dispositivo (COBO/COPE) o del perfil corporativo (BYOD).
   - **Revocación de tokens** de sesión y certificados.
   - **Cambio de contraseña** del usuario y reemisión de MFA.
3. Apertura de incidente conforme a {{ proyecto.codigo_documento_base }}-204 con clasificación mínima ALTO si el dispositivo contenía información CONFIDENCIAL+.
4. Si había datos personales, evaluación de la activación de notificación de brecha conforme a {{ proyecto.codigo_documento_base }}-213.

### 7.2. Compromiso por malware

1. Aislamiento del dispositivo desde el MDM (revocación de accesos).
2. Análisis remoto si la solución MDM lo permite.
3. Reinstalación desde imagen limpia obligatoria si el malware no se elimina con confianza.

### 7.3. Cese de la persona / cambio de rol

- Wipe del perfil corporativo en máximo 24 horas tras la baja conforme a {{ proyecto.codigo_documento_base }}-201.
- Para BYOD, eliminación exclusiva del perfil corporativo sin afectar a datos personales del usuario.
- Devolución física del dispositivo si era COBO/COPE conforme a {{ proyecto.codigo_documento_base }}-201.

## 8. RGPD Y BYOD

Para dispositivos BYOD:

- Información transparente al usuario de las funciones de gestión y supervisión que se aplican (qué ve {{ cliente.razon_social }} y qué no).
- Imposibilidad de acceder al contenido personal (mensajes, ubicación fuera de horario, fotos personales).
- Derecho del usuario a finalizar el régimen BYOD recuperando exclusivamente su perfil personal.
- Acuerdo de uso que incluye estos puntos validado por el DPO.

## 9. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-228 | Solicitud de Enrolamiento | Vigente + 3 años |
| F-228.B | Acuerdo BYOD firmado | Vigente + 6 años |
| INV-mobile | Inventario de Dispositivos Móviles | Permanente |
| L-228 | Logs MDM (en SIEM) | conforme {{ proyecto.codigo_documento_base }}-223 |
| R-228 | Actas de revisión periódica | 3 años |

## 10. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % dispositivos compliant | compliant / enrolados | ≥ 95 % |
| Tiempo medio de wipe tras notificación | media | ≤ 1 h |
| % dispositivos con SO en soporte del fabricante | en soporte / total | 100 % |
| Incidentes con dispositivos móviles | recuento trimestral | ≤ 3 |

## 11. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambie la guía CCN-STIC 880 o las medidas mp.eq.3.
- Se cambie de plataforma MDM/MAM.
- Se incorporen nuevas familias de dispositivos.
- Cambien los criterios AEPD sobre supervisión de dispositivos personales.

Responsabilidad: **Responsable del Sistema** + **Responsable de Seguridad**, con visto bueno del **DPO** para los aspectos BYOD/RGPD.
