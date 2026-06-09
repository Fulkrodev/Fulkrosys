# DOCUMENTO E-223 — PROCEDIMIENTO DE REVISIÓN DE LOGS

**Es el procedimiento operativo que ejecuta la Política de Gestión de Incidentes ({{ proyecto.codigo_documento_base }}-108) y materializa las medidas op.exp.8 y op.mon.1.** Define qué se loguea, dónde se centraliza, cómo se revisa, qué se considera anomalía y cuándo se escala a incidente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-223"
titulo: "Procedimiento de Revisión de Logs"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
medidas_ens: ["op.exp.8", "op.exp.10", "op.mon.1", "op.mon.2"]
---

# PROCEDIMIENTO DE REVISIÓN DE LOGS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-223 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para la generación, centralización, protección, retención y revisión sistemática de los registros de actividad (logs) de los sistemas y servicios del alcance del SGSI, con el objetivo de detectar accesos no autorizados, errores de configuración, abusos de privilegio y patrones anómalos que pudieran indicar un incidente de seguridad.

Este procedimiento desarrolla las medidas **op.exp.8 (registro de la actividad), op.exp.10 (protección del registro de actividad), op.mon.1 (detección de intrusión) y op.mon.2 (sistema de métricas)** del Anexo II del Real Decreto 311/2022, conforme a la guía CCN-STIC 804.

## 2. ALCANCE

Aplica a los logs generados por:

- Sistemas operativos (Windows, Linux) — eventos de seguridad y de sistema.
- Servidores de directorio (AD, LDAP) — autenticación, autorización, cambios.
- Cortafuegos perimetrales y de host.
- IDS/IPS, EDR/XDR.
- Servidores web, proxies y balanceadores.
- Bases de datos (auditoría DML/DDL).
- Aplicaciones de negocio críticas.
- Servicios cloud (CloudTrail, Activity Log, Audit Log).
- Sistemas de gestión de claves (KMS, HSM).
- Plataformas de telefonía, MDM y herramientas de control de acceso físico.

## 3. CATEGORÍAS DE EVENTOS A REGISTRAR

Los siguientes eventos deben registrarse en todos los sistemas del alcance:

| Categoría | Eventos mínimos |
|---|---|
| **Autenticación** | Inicio/cierre de sesión, intentos fallidos, bloqueos de cuenta, cambio de contraseña, uso de MFA |
| **Autorización** | Cambio de privilegios, asignación/revocación de roles, accesos denegados a recursos protegidos |
| **Gestión de cuentas** | Alta/baja/modificación de usuarios y grupos |
| **Acceso a datos sensibles** | Lectura/modificación de información CONFIDENCIAL+ y datos personales de categoría especial |
| **Cambios de configuración** | Modificación de baselines, reglas de firewall, GPO, políticas de aplicación |
| **Operaciones administrativas** | Ejecución de comandos privilegiados (sudo, runas, PowerShell elevado) |
| **Eventos del sistema** | Arranque/parada, errores críticos del kernel, fallos de hardware |
| **Eventos de seguridad** | Detecciones de antivirus/EDR, alertas IDS/IPS, intentos de exfiltración |
| **Eventos de aplicación** | Operaciones críticas de negocio (transferencias, autorizaciones de pago, modificación de expedientes) |

Cada evento incluye, como mínimo: timestamp UTC con precisión ≥ ms, identidad del actor (usuario y sistema), origen (IP, host), recurso afectado, acción ejecutada y resultado (éxito/fallo).

## 4. CENTRALIZACIÓN Y RETENCIÓN

### 4.1. Plataforma SIEM corporativo

Todos los logs se canalizan al **SIEM corporativo** mediante:

- Agente local en sistemas operativos (Wazuh, Sysmon + Winlogbeat, journald + Filebeat).
- Syslog seguro (TLS) para dispositivos de red.
- Conectores nativos para servicios cloud.
- API push para aplicaciones que lo soporten.

Los logs se firman digitalmente o se almacenan en repositorio WORM para garantizar integridad (op.exp.10).

### 4.2. Plazos de retención

| Tipo de log | Retención mínima | Retención máxima |
|---|---|---|
| Eventos de seguridad y autenticación | 12 meses online + 24 meses archivo frío | 5 años |
| Eventos administrativos privilegiados | 24 meses online | 6 años |
| Eventos de acceso a datos personales | 6 años (criterio AEPD) | 6 años + bloqueo |
| Eventos de aplicación / auditoría de negocio | Según marco regulatorio aplicable (mínimo 5 años) | — |
| Eventos de sistema operativo | 6 meses online + 12 meses archivo frío | 3 años |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** retención mínima online de 24 meses para eventos de seguridad y autenticación, con sellado de tiempo cualificado de los lotes mensuales de logs.
{% endif %}

## 5. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Operador SOC / Analista L1** | Triaje 24x7 de alertas SIEM, escalado de incidentes confirmados. |
| **Analista L2 / Hunter** | Revisión proactiva semanal y mensual, threat hunting, mejora de reglas. |
| **Responsable de la Seguridad** | Aprobar reglas de detección, validar excepciones, responder de la calidad del proceso. |
| **Administrador del SIEM** | Operar la plataforma, mantener disponibilidad, gestionar conectores y retención. |
| **DPO** | Validar la retención de logs con datos personales y los accesos a los mismos. |

## 6. FLUJO OPERATIVO

### 6.1. Revisión continua (24x7)

1. Las alertas SIEM se revisan **en tiempo real** por el SOC interno o externalizado.
2. Cada alerta se clasifica en uno de los estados:
   - **Falso positivo:** se cierra con etiqueta y se evalúa ajustar la regla.
   - **Verdadero positivo benigno:** se documenta como evento conocido (cambio programado, prueba autorizada).
   - **Verdadero positivo a investigar:** se asciende a Analista L2.
   - **Incidente confirmado:** se abre ticket de incidente conforme a {{ proyecto.codigo_documento_base }}-204.

3. Tiempos máximos de reacción:

| Severidad de la alerta | MTTA (max) | MTTI (max) |
|---|---|---|
| CRÍTICA | 15 minutos | 1 hora |
| ALTA | 1 hora | 4 horas |
| MEDIA | 4 horas | 24 horas |
| BAJA | 24 horas | 5 días |

(MTTA = Mean Time to Acknowledge; MTTI = Mean Time to Investigate)

### 6.2. Revisión diaria

**Responsable:** Analista L1 (operador de turno).

4. Cuadre diario:
   - Verificación de que todas las fuentes están enviando logs (alertas de fuentes silentes).
   - Conteo de eventos por categoría comparado con la media móvil de 7 días (alertas de desviación ≥ 30 %).
   - Revisión de cuentas administrativas con actividad fuera del horario habitual.

5. Generación del **informe diario** con métricas básicas, anexado al ticket de turno.

### 6.3. Revisión semanal

**Responsable:** Analista L2.

6. Threat hunting con consultas predefinidas:
   - Patrones de movimiento lateral (PsExec, WMI remoto inusual).
   - Acceso a recursos sensibles fuera de patrón (volumen, horario, geolocalización).
   - Uso de cuentas de servicio con perfil de uso interactivo.
   - Intentos de fuerza bruta segmentados por origen.
   - Modificaciones inesperadas en GPOs o en políticas de seguridad.

7. Revisión de **excepciones vivas** del procedimiento {{ proyecto.codigo_documento_base }}-222 con potencial impacto en logs.

8. Cierre del informe semanal y propuesta de ajuste de reglas si procede.

### 6.4. Revisión mensual

**Responsable:** Responsable de la Seguridad.

9. **Reunión mensual de SIEM** con KPIs de detección:
   - Cobertura de fuentes (% de sistemas en el SIEM frente a inventario).
   - Reglas activas y reglas que no han disparado en 90 días (candidatas a revisar).
   - Falsos positivos por regla.
   - Incidentes detectados desde el SIEM frente a incidentes reportados por usuarios.

10. Validación de la **retención y la integridad** de los logs (muestra del 1 % verificada con hash o firma).

11. Envío del cuadro de mando al **Comité de Seguridad** (op.mon.2).

### 6.5. Revisión trimestral

**Responsable:** Responsable de la Seguridad y Administrador del SIEM.

12. Auditoría de **accesos al propio SIEM** y a los repositorios de logs (op.exp.10).

13. Pruebas controladas de detección (purple-teaming): inyección de patrones conocidos para validar que las reglas se disparan.

14. Revisión y actualización del catálogo de reglas, incluyendo:
    - Adopción de nuevas reglas Sigma públicas relevantes.
    - Tuning de reglas con alto ruido.
    - Baja de reglas obsoletas o cubiertas por otras.

## 7. PROTECCIÓN DEL REGISTRO DE ACTIVIDAD (op.exp.10)

- **Acceso al SIEM** solo para personal designado, con MFA obligatorio y registro de cada acceso.
- **Separación de roles:** los administradores de los sistemas que generan logs no pueden modificar ni borrar logs en el SIEM.
- **Sellado de tiempo y firma electrónica** de los lotes mensuales (mínimo) o hash en cadena para garantizar integridad temporal.
- **Backup independiente** del SIEM con cifrado y custodia separada.
- **Sincronización horaria** de todos los sistemas mediante NTP autorizado, con alerta si la deriva supera 1 segundo.

## 8. CASOS DE USO DE DETECCIÓN OBLIGATORIOS

Las siguientes detecciones deben estar implementadas y verificadas mediante prueba trimestral:

1. Inicio de sesión exitoso fuera del horario habitual del usuario.
2. Login exitoso desde geolocalización imposible (impossible travel).
3. Cuenta administrativa creada fuera del proceso autorizado.
4. Acceso masivo a datos personales (lectura > N registros en X minutos).
5. Cambio de privilegios en cuenta no nominativa.
6. Desactivación o modificación del agente EDR/SIEM.
7. Ejecución de comandos sospechosos (mimikatz, psexec, powershell encoded).
8. Conexión saliente a IP/dominio en lista de IOCs.
9. Modificación de logs o configuración de auditoría.
10. Patrón de exfiltración (volumen saliente atípico hacia destino externo).

## 9. INTEGRACIÓN CON RGPD

Los logs son tratamientos de datos personales (incluyen identidades de usuarios). Por ello:

- Inscritos en el **RAT** con base legal "interés legítimo en seguridad y prevención de fraude".
- **Acceso restringido** y registrado.
- **Plazo de conservación máximo** definido en apartado 4.
- En caso de **derecho de acceso, rectificación o supresión** de un sujeto sobre sus logs, se valora con el DPO la prevalencia del interés legítimo.

## 10. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| R-223.1 | Informes diarios SIEM | 6 meses |
| R-223.2 | Informes semanales de threat hunting | 24 meses |
| R-223.3 | Cuadro de mando mensual | 3 años |
| R-223.4 | Acta de revisión trimestral del SIEM | 6 años |
| L-223 | Log de accesos al SIEM | 24 meses |

## 11. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura de fuentes | sistemas con logs en SIEM / sistemas en inventario | ≥ 95 % |
| MTTA medio (alertas críticas) | media | ≤ 15 min |
| MTTI medio (alertas críticas) | media | ≤ 1 h |
| Tasa de falsos positivos | falsos positivos / total alertas | ≤ 25 % |
| Disponibilidad del SIEM | uptime mensual | ≥ 99,5 % |
| Reglas validadas trimestralmente | reglas validadas / total | 100 % |

## 12. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Se incorporen nuevas plataformas SIEM o XDR.
- Cambien las medidas op.exp.8/10 o op.mon.1/2 en CCN-STIC 804.
- Se detecten incidentes en los que el log no permitió la trazabilidad esperada.
- Cambie el modelo de operación SOC (internalización / externalización).

Responsabilidad: **Responsable de la Seguridad**, con visto bueno del **Comité de Seguridad**.
