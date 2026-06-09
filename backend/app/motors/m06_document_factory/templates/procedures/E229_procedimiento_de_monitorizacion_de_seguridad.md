# DOCUMENTO E-229 — PROCEDIMIENTO DE MONITORIZACIÓN DE SEGURIDAD

**Es el procedimiento operativo que materializa las medidas op.mon.1, op.mon.2 y op.mon.3 del Anexo II.** Mientras el procedimiento {{ proyecto.codigo_documento_base }}-223 cubre la revisión de logs, este documento define la monitorización integral: detección de intrusión, métricas de seguridad y vigilancia continuada del estado del sistema.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-229"
titulo: "Procedimiento de Monitorización de Seguridad"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
medidas_ens: ["op.mon.1", "op.mon.2", "op.mon.3"]
---

# PROCEDIMIENTO DE MONITORIZACIÓN DE SEGURIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-229 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para la monitorización integral de la seguridad de los activos del alcance del SGSI: detección de intrusión y comportamientos anómalos, métricas de seguridad y vigilancia continuada de la postura, asegurando capacidad de detectar, analizar y responder ante eventos adversos en plazos compatibles con la categoría ENS del sistema.

Este procedimiento desarrolla las medidas **op.mon.1 (detección de intrusión), op.mon.2 (sistema de métricas) y op.mon.3 (vigilancia)** del Anexo II del Real Decreto 311/2022 conforme a la guía CCN-STIC 804.

## 2. ALCANCE

Aplica a la monitorización de:

- Tráfico de red (perimetral, interno, segmentos OT si aplica).
- Endpoints (servidores, estaciones, dispositivos móviles).
- Aplicaciones críticas y sus APIs.
- Servicios cloud (IaaS/PaaS/SaaS).
- Identidades y accesos.
- Cumplimiento (postura de configuración, parches, certificaciones).
- Amenazas externas (CTI, OSINT relevante).

## 3. CAPACIDADES DE MONITORIZACIÓN

| Capacidad | Tecnología | Cobertura mínima |
|---|---|---|
| **Network Detection (NDR)** | IDS/IPS (Suricata / Snort) o NDR comercial | 100 % perímetro y enlaces inter-segmento |
| **Endpoint Detection (EDR/XDR)** | EDR corporativo en estaciones y servidores | ≥ 98 % endpoints |
| **SIEM** | Plataforma centralizada con correlación | Cobertura conforme a {{ proyecto.codigo_documento_base }}-223 |
| **Cloud Security Posture (CSPM)** | Prowler / ScoutSuite / Defender for Cloud | 100 % cuentas cloud |
| **Identity Threat Detection (ITDR)** | Señales del IdP + UEBA | Todos los usuarios privilegiados |
| **Vulnerability Management** | Scanner autenticado + agente | 100 % activos del inventario |
| **CTI** | Feeds (CCN-CERT, INCIBE, OSINT, comerciales) | Procesados diariamente |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** vigilancia 24x7 obligatoria mediante SOC interno o contratado, con capacidad de respuesta ante incidentes en menos de 15 minutos para alertas críticas.
{% endif %}

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **SOC L1** | Triaje 24x7 (interno o externalizado), escalado al L2. |
| **SOC L2 / Hunter** | Análisis profundo, threat hunting, ajuste de reglas. |
| **Responsable de la Seguridad** | Definir umbrales, gobernar reglas, presentar métricas a Dirección. |
| **CTI Analyst** (si existe) | Procesar feeds, identificar amenazas relevantes para el sector. |
| **Equipo de Operaciones** | Mantener disponibilidad de las plataformas de monitorización. |

## 5. FLUJO OPERATIVO

### 5.1. Detección de intrusión (op.mon.1)

1. **NDR perimetral** activo en cortafuegos y/o sondas dedicadas, con reglas Suricata/Snort actualizadas semanalmente desde repositorios oficiales (ETOpen, ET Pro, repositorios CCN cuando estén disponibles) y reglas custom para tráfico esperado de la organización.

2. **EDR/XDR en endpoint** con configuración:
   - Detecciones comportamentales activas (Defender for Endpoint, CrowdStrike, SentinelOne, Cortex XDR o equivalente CCN-aprobado).
   - Capacidad de respuesta automatizada (cuarentena, aislamiento de host).
   - Telemetría enviada al SIEM.

3. **Honeytokens y honeypots** desplegados en segmentos sensibles para detectar movimientos laterales (cuentas señuelo en AD, ficheros canary en file shares).

4. **Detecciones obligatorias** verificadas trimestralmente conforme al apartado 8 de {{ proyecto.codigo_documento_base }}-223.

### 5.2. Sistema de métricas (op.mon.2)

5. Cuadro de mando de seguridad publicado **mensualmente** al Comité de Seguridad y trimestralmente a Dirección con:

| Familia | Indicadores |
|---|---|
| **Detección y respuesta** | MTTA, MTTI, MTTR, alertas críticas/mes, % cerradas en SLA |
| **Vulnerabilidades** | n.º vulnerabilidades CRÍTICAS abiertas, edad media, % parcheadas en SLA |
| **Identidad** | % cuentas con MFA, cuentas inactivas, accesos privilegiados sin renovación |
| **Cumplimiento** | Cobertura EDR, hallazgos CSPM críticos, configuraciones drift |
| **Concienciación** | Click-rate phishing, % personal formado |
| **Continuidad** | Pruebas BCP planificadas vs ejecutadas, RTO/RPO real vs objetivo |
| **Cadena de suministro** | Proveedores con evaluación al día, incidentes notificados por proveedores |

6. Cada KPI tiene **objetivo, umbral de alerta y propietario**. Los desvíos se discuten en el Comité con plan de acción asociado.

### 5.3. Vigilancia (op.mon.3)

7. **Vigilancia tecnológica** mediante consumo activo de fuentes:
   - CCN-CERT (informes y alertas).
   - INCIBE (avisos para ciudadanos y empresas).
   - CISA, ENISA y CERT-EU.
   - Bug bounty / disclosure de proveedores tecnológicos en el stack.
   - Listas de IoCs y TTPs (MISP corporativo o equivalente).

8. **Threat intelligence aplicado:**
   - Comparación diaria de IoCs con telemetría interna.
   - Adaptación de reglas SIEM y EDR a los TTPs actualmente activos.
   - Comunicaciones internas cuando aparece una amenaza relevante para el sector.

9. **Vigilancia de marca y exfiltración:**
   - Monitorización de menciones a {{ cliente.razon_social }} en foros, paste sites y dark-web (servicio interno o contratado).
   - Detección de credenciales corporativas filtradas mediante feeds (HIBP business / DeHashed / similares).

10. **Vigilancia de superficie expuesta** (External Attack Surface Management):
    - Inventario continuo de activos públicos (dominios, IPs, certificados, subdominios).
    - Detección de cambios no autorizados (shadow IT, dominios caducados).
    - Reporte mensual al Responsable de Seguridad.

## 6. AUTOMATIZACIÓN Y RESPUESTA (SOAR)

Cuando exista plataforma SOAR:

- Playbooks automatizados para los **5 incidentes más frecuentes** (phishing, malware en endpoint, intento de fuerza bruta, anomalía de privilegio, compromiso de credencial).
- Respuestas automatizadas con criterios conservadores (aislar endpoint, deshabilitar usuario, abrir ticket) y siempre con auditoría.
- Acciones destructivas (purga de email, restablecimiento masivo) requieren validación humana.

## 7. INTEGRACIÓN CON OTROS PROCEDIMIENTOS

| Procedimiento | Relación |
|---|---|
| {{ proyecto.codigo_documento_base }}-204 (Incidentes) | Las alertas confirmadas se canalizan como incidentes. |
| {{ proyecto.codigo_documento_base }}-205 (Vulnerabilidades) | Los hallazgos del scanner alimentan el inventario. |
| {{ proyecto.codigo_documento_base }}-223 (Logs) | Comparten plataforma SIEM y reglas. |
| {{ proyecto.codigo_documento_base }}-218 (Auditoría interna) | Los KPIs son input al programa anual. |
| {{ proyecto.codigo_documento_base }}-219 (Revisión por la Dirección) | El cuadro de mando se incluye en la revisión anual. |

## 8. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| R-229.1 | Cuadro de mando mensual | 3 años |
| R-229.2 | Informe trimestral a Dirección | 3 años |
| R-229.3 | Boletín CTI semanal/quincenal | 12 meses |
| R-229.4 | Acta de revisión de reglas (trimestral) | 6 años |

## 9. INDICADORES MAESTROS

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura EDR | endpoints con EDR / total | ≥ 98 % |
| Cobertura SIEM | fuentes en SIEM / fuentes inventariadas | ≥ 95 % |
| MTTD medio (mes) | media | ≤ 1 h críticos |
| MTTR medio (mes) | media | ≤ 4 h críticos |
| Cumplimiento de SLA por severidad | en SLA / total | ≥ 95 % |
| % reglas validadas trimestralmente | validadas / total | 100 % |

## 10. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien las medidas op.mon.1/2/3 en CCN-STIC 804.
- Se incorpore o sustituya alguna plataforma de monitorización principal.
- Se modifique el modelo de SOC (interno / mixto / externalizado).
- Aparezcan nuevas amenazas estructurales en el sector que exijan ampliar capacidades.

Responsabilidad: **Responsable de la Seguridad**, con aprobación del **Comité de Seguridad** y elevación a **Dirección** cuando suponga inversión adicional.
