# DOCUMENTO E-233 — PROCEDIMIENTO DE SEGURIDAD EN REDES INALÁMBRICAS

**Es el procedimiento operativo que ejecuta la Política de Redes y Comunicaciones ({{ proyecto.codigo_documento_base }}-121) en lo relativo a redes WiFi.** Define cómo se diseñan, configuran, operan y supervisan las redes inalámbricas corporativas y de invitados de {{ cliente.razon_social }}.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-233"
titulo: "Procedimiento de Seguridad en Redes Inalámbricas"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-121"
medidas_ens: ["mp.com.4", "mp.com.2", "op.acc.5"]
---

# PROCEDIMIENTO DE SEGURIDAD EN REDES INALÁMBRICAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-233 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para el diseño, configuración, operación y supervisión de las redes inalámbricas (WiFi) de {{ cliente.razon_social }}, garantizando que la conectividad sin cable no constituye una vía de acceso indebida a la información ni a los servicios del alcance del SGSI.

Este procedimiento desarrolla las medidas **mp.com.4 (segregación de redes), mp.com.2 (protección de la confidencialidad) y op.acc.5 (mecanismo de autenticación)** del Anexo II del Real Decreto 311/2022, conforme a la guía **CCN-STIC 844 (seguridad en redes inalámbricas)**.

## 2. ALCANCE

Aplica a todas las redes inalámbricas operadas por {{ cliente.razon_social }}:

- WiFi corporativo para empleados.
- WiFi de invitados en sedes.
- WiFi para dispositivos IoT corporativos.
- Redes ad-hoc temporales (eventos, demostraciones).
- Puntos de acceso desplegados por proveedores en sedes corporativas.

## 3. SEGREGACIÓN DE SSIDs

Por defecto, en cada sede se publican como mínimo los siguientes SSIDs **separados lógica y físicamente**:

| SSID | Propósito | VLAN | Acceso a corporativo |
|---|---|---|---|
| **{{ cliente.nombre_corto }}-CORP** | Empleados con dispositivos corporativos | VLAN-corp | Acceso a recursos según roles |
| **{{ cliente.nombre_corto }}-BYOD** | Empleados con dispositivos personales (si BYOD aprobado) | VLAN-byod | Acceso restringido a aplicaciones SaaS vía SSO |
| **{{ cliente.nombre_corto }}-GUEST** | Invitados | VLAN-guest | Solo Internet, aislado del corporativo |
| **{{ cliente.nombre_corto }}-IOT** | Dispositivos IoT corporativos (impresoras, cámaras autorizadas, sensores) | VLAN-iot | Solo a servicios necesarios, microsegmentación |

Las VLANs se interconectan exclusivamente a través del cortafuegos corporativo con reglas explícitas y registradas.

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** los SSIDs corporativos no permiten acceso a información de la categoría sin VPN adicional, y los segmentos OT no son accesibles vía WiFi. Para sistemas críticos se prohibe el acceso WiFi por defecto y solo se autoriza por excepción {{ proyecto.codigo_documento_base }}-222.
{% endif %}

## 4. AUTENTICACIÓN Y CIFRADO

| SSID | Autenticación | Cifrado | Notas |
|---|---|---|---|
| **CORP** | WPA2-Enterprise / WPA3-Enterprise (EAP-TLS preferente, PEAP-MSCHAPv2 mínimo) con RADIUS contra IdP corporativo | AES-CCMP (WPA2) o GCMP-256 (WPA3) | Certificado del cliente cuando se utilice EAP-TLS |
| **BYOD** | WPA2/3-Enterprise con MFA en captive portal o EAP-TTLS | AES-CCMP / GCMP-256 | Acceso solo a aplicaciones autorizadas |
| **GUEST** | Captive portal con código diario o registro nominativo del visitante (DPO consent) | WPA2/3-Personal o cifrado opportunistic (OWE) cuando WPA esté inhabilitado | Aislamiento de clientes (client isolation) activado |
| **IOT** | WPA2-Personal con clave robusta y rotación periódica, o WPA2-Enterprise si el dispositivo lo soporta | AES-CCMP | MAC filtering complementario, sin acceso a la red corporativa |

**Está prohibido**:

- WEP, WPA original, WPA2-Personal con PSK débil.
- Redes corporativas abiertas sin autenticación.
- WPS (configuración pulsando botón).
- TKIP.

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Equipo de Redes / Operaciones** | Operar la WLAN, configurar APs y controladores, mantener documentación. |
| **Responsable del Sistema** | Aprobar cambios de configuración, supervisar disponibilidad. |
| **Responsable de la Seguridad** | Aprobar diseño y políticas, validar resultados de auditorías inalámbricas. |
| **DPO** | Validar el captive portal de invitados y la conservación de los logs de acceso. |

## 6. CONFIGURACIÓN DE EQUIPAMIENTO

Los puntos de acceso (AP) y controladores deben:

1. Provenir de proveedor con soporte vigente del fabricante y firmware en versión soportada.
2. Aplicar baseline de hardening conforme a CCN-STIC 844 y a la guía del fabricante.
3. Autenticación de gestión vía protocolos seguros (HTTPS, SSH); deshabilitados HTTP, Telnet y SNMPv1/v2c.
4. **Logging integral** enviado al SIEM ({{ proyecto.codigo_documento_base }}-223): autenticaciones (éxito/fallo), asociaciones, desautenticaciones, RFKill, intentos de rogue AP.
5. **Detección de rogue APs y rogue clients** activa, con alerta al SOC.
6. **WIPS** (Wireless Intrusion Prevention) cuando esté disponible en la plataforma.
7. **Sincronización horaria** vía NTP autorizado.
8. **Actualizaciones** dentro del ciclo del procedimiento {{ proyecto.codigo_documento_base }}-206 (parches), priorizando vulnerabilidades CRÍTICAS.

## 7. OPERACIÓN

### 7.1. Alta de usuarios

- Acceso al SSID corporativo por integración con AD/IdP. La revocación es inmediata al ejecutar la baja conforme a {{ proyecto.codigo_documento_base }}-201.
- BYOD requiere enrolamiento previo conforme a {{ proyecto.codigo_documento_base }}-228.
- Invitados: registro en recepción con DNI o equivalente, código válido por jornada, expiración automática.

### 7.2. Cambios de configuración

- Toda modificación de SSID, autenticación, cifrado o segmentación se canaliza por el procedimiento {{ proyecto.codigo_documento_base }}-203 (cambios) con aprobación del Responsable de Seguridad para cambios estructurales.

### 7.3. Auditorías inalámbricas

| Tipo | Frecuencia | Herramientas típicas |
|---|---|---|
| Detección de rogue APs | Continua (WIPS) | Plataforma WLAN nativa |
| Auditoría WiFi externa (war-driving controlado) | Anual | aircrack-ng suite, Wireshark, kismet |
| Pentest WiFi | Bienal en BÁSICA / MEDIA, anual en ALTA | hostapd-mana, wifite2 |
| Auditoría de configuración | Anual | Revisión manual + checklist CCN-STIC 844 |

Los resultados se reportan en el cuadro de mando de monitorización {{ proyecto.codigo_documento_base }}-229.

### 7.4. Cobertura y rendimiento

- Mapas de calor anuales para garantizar cobertura adecuada y minimizar emisión más allá de los perímetros físicos del cliente.
- Reducción de potencia en zonas perimetrales para limitar el alcance fuera de las instalaciones.

## 8. INCIDENTES ESPECÍFICOS

| Tipo | Acción |
|---|---|
| Rogue AP detectado | Bloqueo inmediato (de-auth si la regulación local lo permite), localización física, retirada |
| Cliente sospechoso (escaneo intensivo) | Bloqueo MAC, investigación |
| Compromiso del controlador WLAN | Aislamiento, restauración desde backup, rotación de credenciales y secretos |
| Pérdida del PSK del SSID IoT | Rotación inmediata + reconfiguración masiva |

Todos se gestionan conforme al procedimiento {{ proyecto.codigo_documento_base }}-204 (incidentes).

## 9. RGPD Y REDES DE INVITADOS

- El captive portal de invitados informa de qué datos se recogen (nombre, email, MAC) y para qué (cumplimiento de la Ley de Conservación de Datos / LOPDGDD si aplica al sector).
- Conservación máxima de los logs de invitados: **12 meses** salvo obligación legal específica que indique periodo distinto.
- Validación previa por el DPO del aviso de privacidad y del proceso de gestión de derechos.

## 10. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| INV-wifi | Inventario de SSIDs y APs | Permanente |
| L-233 | Logs WLAN en SIEM | conforme {{ proyecto.codigo_documento_base }}-223 |
| R-233.1 | Resultados de auditorías WiFi | 6 años |
| R-233.2 | Mapas de calor / estudios de cobertura | Vigente + 3 años |
| R-233.3 | Logs de captive portal de invitados | 12 meses |

## 11. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| % SSIDs corporativos con WPA2/3-Enterprise | conformes / total | 100 % |
| Rogue APs detectados (mes) | recuento | ≤ 1 |
| Auditorías WiFi planificadas vs ejecutadas | ejecutadas / planificadas | 100 % |
| Cobertura del SIEM en eventos WLAN | eventos en SIEM / eventos generados | ≥ 95 % |

## 12. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambie la guía CCN-STIC 844.
- Se sustituya la plataforma WLAN.
- Aparezcan vulnerabilidades estructurales en los protocolos WiFi (KRACK, FragAttacks, etc.).
- Se incorporen nuevas sedes o SSIDs adicionales.

Responsabilidad: **Equipo de Redes** + **Responsable del Sistema**, con aprobación del **Responsable de la Seguridad**.
