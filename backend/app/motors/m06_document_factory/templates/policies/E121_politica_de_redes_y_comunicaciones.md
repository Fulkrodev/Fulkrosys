# DOCUMENTO E-121 — POLÍTICA DE REDES Y COMUNICACIONES

**Materializa mp.com.1 (Perímetro seguro), mp.com.2 (Protección de la confidencialidad), mp.com.3 (Protección de la integridad y autenticidad) y mp.com.4 (Segregación de redes) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-121"
titulo: "Política de Redes y Comunicaciones"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
clasificacion: "INTERNA"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE REDES Y COMUNICACIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-121 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los principios y requisitos de seguridad aplicables al diseño, operación y protección de las redes de comunicaciones de {{ cliente.razon_social }}, en cumplimiento de las medidas **mp.com.1** a **mp.com.4** del Anexo II del Real Decreto 311/2022.

## 2. PRINCIPIOS

**2.1 Perímetro seguro.** Todo punto de entrada y salida de la red corporativa estará controlado por un cortafuegos con política por defecto DENY y reglas explícitas documentadas.

**2.2 Segmentación de redes.** La red se segmentará conforme al principio de mínima exposición, separando al menos: red corporativa, red de servidores, red de gestión, red DMZ, red de invitados. Las redes de mayor criticidad estarán aisladas del acceso directo desde redes menos confiables.

**2.3 Cifrado de comunicaciones.** Conforme a la Política Criptográfica ({{ proyecto.codigo_documento_base }}-107), toda comunicación que transporte información sensible o que atraviese redes no controladas se cifrará con TLS 1.2 o superior (preferentemente TLS 1.3).

**2.4 Protección de integridad.** Los protocolos utilizados incorporarán mecanismos de verificación de integridad (HMAC, firmas digitales) para detectar manipulaciones en tránsito.

**2.5 Monitorización.** El tráfico de red se monitorizará mediante IDS/IPS y se registrará en el SIEM corporativo para la detección de anomalías y la respuesta a incidentes.

## 3. REGLAS DE CORTAFUEGOS

a) Regla por defecto: **DENY ALL** (denegar todo tráfico no expresamente autorizado).

b) Las reglas se documentarán individualmente con: origen, destino, puerto/protocolo, justificación y fecha de autorización.

c) Las reglas se revisarán **semestralmente** para eliminar las obsoletas.

d) Los cambios en reglas de cortafuegos siguen el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203).

## 4. REDES INALÁMBRICAS

a) Las redes Wi-Fi corporativas usarán cifrado **WPA3** (o WPA2-Enterprise como mínimo) con autenticación 802.1X.

b) La red de invitados estará completamente aislada de la red corporativa.

c) Se monitorizará la presencia de puntos de acceso no autorizados (rogue APs).

## 5. INTERCONEXIONES CON TERCEROS

Las interconexiones con redes de terceros requerirán autorización del Responsable de la Seguridad, documentación del flujo autorizado, cifrado del canal y monitorización específica.

## 6. APROBACIÓN Y VIGENCIA

Aprobada por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }}. Revisión anual.

---

**Documento {{ proyecto.codigo_documento_base }}-121 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
