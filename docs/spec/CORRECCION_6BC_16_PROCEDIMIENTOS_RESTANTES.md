# CORRECCIÓN 6B+6C — 16 PROCEDIMIENTOS RESTANTES (numeración v2.1)

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026
**Nota:** Estos 16 procedimientos completan los 35/35 del catálogo v2.1 §2.7.

---

# E-208 — PROCEDIMIENTO DE RESTAURACIÓN

**Split del antiguo E-210 (Backup+Restore). Cubre la restauración operativa y las pruebas periódicas de restore. Materializa op.cont.3 y mp.info.9.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-208"
titulo: "Procedimiento de Restauración"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-106, {{ proyecto.codigo_documento_base }}-109"
---

# PROCEDIMIENTO DE RESTAURACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-208 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para la restauración de datos, configuraciones y sistemas a partir de las copias de seguridad, tanto en respuesta a un incidente como en el marco de las pruebas periódicas de verificación.

## 2. TIPOS DE RESTAURACIÓN

| Tipo | Disparador | Autorización |
|---|---|---|
| **Restauración de fichero individual** | Solicitud de usuario (pérdida accidental) | Resp. Sistema |
| **Restauración de base de datos** | Corrupción, error humano, incidente | Resp. Seguridad |
| **Restauración de sistema completo** | Incidente grave, ransomware, desastre | Coordinador ERI (si incidente) o Resp. Seguridad |
| **Prueba periódica de restauración** | Calendario de pruebas (E-209) | Resp. Seguridad |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Recepción de la solicitud con: datos a restaurar, punto en el tiempo deseado, justificación | Resp. Sistema |
| 2 | Autorización conforme a la tabla del apartado 2 | Autorizador |
| 3 | Identificación de la copia de seguridad adecuada en el inventario de copias | Resp. Sistema |
| 4 | Verificación del hash SHA-256 de la copia antes de iniciar la restauración | Resp. Sistema |
| 5 | Restauración en **entorno aislado** (nunca directamente en producción sin verificar) | Resp. Sistema |
| 6 | Verificación de integridad funcional: acceso a datos, consistencia, funcionamiento de aplicaciones | Resp. Sistema |
| 7 | Si la verificación es exitosa: migración al entorno productivo conforme al procedimiento de cambios ({{ proyecto.codigo_documento_base }}-203) | Resp. Sistema |
| 8 | Registro de la restauración: fecha, datos restaurados, punto en el tiempo, copia utilizada, resultado, persona ejecutora | Resp. Sistema |
| 9 | Notificación al solicitante | Resp. Sistema |

## 4. PRUEBAS PERIÓDICAS

Las pruebas de restauración se planifican y ejecutan conforme al procedimiento E-209 (Pruebas de Continuidad). Para cada prueba se mide el **tiempo real de restauración (RTR)** y se compara con el **RTO objetivo** del BIA.

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Pruebas de restauración exitosas | 100% |
| RTR ≤ RTO en todas las pruebas | 100% |
| Restauraciones operativas completadas sin pérdida de datos adicional | 100% |

---
```

---

# E-214 — PROCEDIMIENTO DE DESTRUCCIÓN SEGURA DE INFORMACIÓN

**Operativo de E-126. Materializa mp.si.5.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-214"
titulo: "Procedimiento de Destrucción Segura de Información"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-126"
---

# PROCEDIMIENTO DE DESTRUCCIÓN SEGURA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-214 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar los pasos operativos para la destrucción irreversible de información en soportes electrónicos, ópticos y en papel, conforme a los niveles de la Política E-126.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Solicitud de destrucción: soporte identificado, nivel de clasificación, motivo (fin de vida útil, fin de retención, cese de actividad) | Custodio del soporte |
| 2 | Verificación de que el periodo de conservación legal ha expirado (consultar {{ proyecto.codigo_documento_base }}-221) | Resp. Seguridad |
| 3 | Para datos personales: verificar que se ha completado el periodo de **bloqueo** del art. 32 LOPDGDD | DPO |
| 4 | Selección del método conforme a la tabla de E-126 §2 según nivel de clasificación y tipo de soporte | Resp. Sistema |
| 5 | Ejecución de la destrucción: borrado seguro (ATA Secure Erase, NIST SP 800-88), desmagnetización, trituración física o entrega a proveedor certificado | Resp. Sistema o proveedor |
| 6 | Si proveedor externo: obtener **certificado de destrucción** firmado con: soportes destruidos (S/N), método, fecha, persona responsable del proveedor | Resp. Sistema |
| 7 | Registro en el **Registro de Destrucción**: soporte, contenido, clasificación, método, fecha, ejecutor, referencia al certificado si externo | Resp. Seguridad |
| 8 | Actualización del inventario de soportes (baja) | Resp. Sistema |

## 3. INDICADORES

| Indicador | Objetivo |
|---|---|
| Destrucciones con registro completo | 100% |
| Destrucciones externas con certificado del proveedor | 100% |

---
```

---

# E-215 — PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES

**Operativo de E-122. Materializa mp.si.1 a mp.si.4.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-215"
titulo: "Procedimiento de Gestión de Soportes Extraíbles"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-122"
---

# PROCEDIMIENTO DE GESTIÓN DE SOPORTES EXTRAÍBLES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-215 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Regular el uso, inventario, cifrado, transporte y destrucción de soportes extraíbles (USB, discos externos, cintas, ópticos) que contengan información del alcance del SGSI.

## 2. AUTORIZACIÓN

El uso de soportes extraíbles para almacenar información CONFIDENCIAL o superior requiere **autorización previa del Responsable de la Seguridad**. La conexión de dispositivos USB no autorizados a equipos corporativos podrá ser bloqueada técnicamente mediante políticas de endpoint.

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Solicitud de uso de soporte extraíble con justificación | Usuario |
| 2 | Autorización y asignación de soporte corporativo cifrado del inventario | Resp. Seguridad |
| 3 | Registro del soporte en el inventario: tipo, S/N, custodio, clasificación máxima autorizada | Resp. Sistema |
| 4 | Etiquetado conforme al nivel de clasificación ({{ proyecto.codigo_documento_base }}-104) | Custodio |
| 5 | Uso: cifrado obligatorio si CONFIDENCIAL+ ({{ proyecto.codigo_documento_base }}-107), almacenamiento en lugar seguro cuando no esté en uso | Custodio |
| 6 | Transporte fuera de las instalaciones: conforme a {{ proyecto.codigo_documento_base }}-122 §6, registro de salida en {{ proyecto.codigo_documento_base }}-123 §9 | Custodio |
| 7 | Devolución al final de la necesidad: borrado seguro y vuelta al inventario, o destrucción si fin de vida | Custodio → Resp. Sistema |

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Soportes extraíbles inventariados | 100% |
| Soportes con información CONFIDENCIAL+ cifrados | 100% |

---
```

---

# E-216 — PROCEDIMIENTO DE GESTIÓN DE PROVEEDORES

**Operativo de la Política de Proveedores (E-112). Complementa E-217 (evaluación de riesgos) con la gestión operativa diaria.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-216"
titulo: "Procedimiento de Gestión Operativa de Proveedores"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-112"
---

# PROCEDIMIENTO DE GESTIÓN OPERATIVA DE PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-216 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para el registro, seguimiento, auditoría y baja de los proveedores que acceden a información o sistemas del alcance del SGSI, en desarrollo de la Política E-112 y como complemento del procedimiento de evaluación de riesgos E-217.

## 2. REGISTRO DE PROVEEDORES

Todo proveedor con acceso a información o sistemas del SGSI se registra en el **Registro de Proveedores** con: razón social, NIF, nivel de criticidad (CRÍTICO/ALTO/MEDIO/BAJO conforme a E-112 §3), servicios prestados, persona de contacto, fechas de contrato, certificaciones declaradas.

## 3. SEGUIMIENTO PERIÓDICO

| Nivel | Frecuencia reuniones seguridad | Auditoría documental | Auditoría in situ |
|---|---|---|---|
| CRÍTICO | Trimestral | Anual | Anual |
| ALTO | Semestral | Anual | Bienal |
| MEDIO | Anual | Bienal | Bajo demanda |
| BAJO | Bajo demanda | — | — |

## 4. GESTIÓN DE INCIDENTES DE PROVEEDOR

Los incidentes notificados por proveedores se gestionan conforme a E-204, considerando al proveedor como fuente. El Resp. Seguridad evalúa el impacto sobre la continuidad y activa planes de contingencia si procede.

## 5. BAJA DE PROVEEDOR

Conforme a la fase 5 del procedimiento E-217: plan de salida, devolución/destrucción de información, revocación de accesos, certificado de destrucción, recordatorio de confidencialidad subsistente.

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Proveedores CRÍTICO/ALTO con cuestionario vigente (<12 meses) | 100% |
| Proveedores con incidente no resuelto > 30 días | 0 |

---
```

---

# E-222 — PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES

**Operativo del apartado 9 de la Política de Seguridad (E-100). Regula cómo se autorizan, documentan y revisan las excepciones a la normativa del SGSI.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-222"
titulo: "Procedimiento de Gestión de Excepciones"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-222 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Regular el proceso formal por el que se autoriza el incumplimiento temporal o parcial de un requisito del SGSI cuando exista causa justificada, garantizando que el riesgo asumido está documentado, autorizado, compensado y acotado en el tiempo.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | **Solicitud** mediante formulario de excepción: requisito afectado, motivo, duración solicitada, riesgo asumido, medidas compensatorias propuestas | Solicitante | — |
| 2 | **Análisis de riesgo** de la excepción: probabilidad × impacto de la no aplicación del control | Resp. Seguridad | 5 días hábiles |
| 3 | **Autorización**: excepciones de riesgo bajo/medio → Resp. Seguridad. Excepciones de riesgo alto → Comité de Seguridad. | Autorizador | 10 días hábiles |
| 4 | **Registro** en el Registro de Excepciones con ID único, fecha de autorización, vigencia máxima (≤ 12 meses), condiciones | Resp. Seguridad | Inmediato |
| 5 | **Implantación de medidas compensatorias** documentadas | Solicitante | Según excepción |
| 6 | **Revisión periódica** de excepciones vigentes: ¿sigue siendo necesaria? ¿ha cambiado el riesgo? | Resp. Seguridad | Trimestral |
| 7 | **Cierre** cuando la excepción expira, el requisito se cumple, o se renueva con nueva autorización | Resp. Seguridad | Al vencimiento |

## 3. VIGENCIA

Ninguna excepción podrá tener vigencia superior a **12 meses**. Las prórrogas requieren nueva solicitud y nueva autorización, con actualización del análisis de riesgo.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Excepciones vigentes con documentación completa | 100% |
| Excepciones expiradas sin renovar ni cerrar | 0 |
| Excepciones con medidas compensatorias verificadas | 100% |

---
```

---

# E-223 — PROCEDIMIENTO DE REVISIÓN DE LOGS

**Materializa op.exp.8 (Registro de la actividad de los usuarios). El auditor pide ver evidencia de que alguien revisa los logs, no solo de que existen.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-223"
titulo: "Procedimiento de Revisión de Logs"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE REVISIÓN DE LOGS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-223 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer qué registros de actividad se revisan, con qué frecuencia, por quién, qué se busca y cómo se documentan las revisiones, en cumplimiento de la medida **op.exp.8 (Registro de la actividad de los usuarios)** del Anexo II del Real Decreto 311/2022.

## 2. FUENTES DE LOGS

| Fuente | Tipo de eventos registrados | Retención mínima |
|---|---|---|
| SIEM corporativo | Correlación de todos los orígenes | {% if proyecto.categoria_ens == "ALTA" %}3 años{% elif proyecto.categoria_ens == "MEDIA" %}2 años{% else %}1 año{% endif %} |
| Servidores (syslog, EventLog) | Inicio/cierre de sesión, cambios de configuración, errores | 1 año |
| Cortafuegos / IDS/IPS | Tráfico permitido/denegado, alertas | 1 año |
| Aplicaciones web | Accesos, errores, transacciones críticas | 1 año |
| Sistemas de autenticación (AD, LDAP, IdP) | Inicios de sesión, fallos, cambios de contraseña, bloqueos | 2 años |
| Sistemas de backup | Ejecuciones, fallos, restauraciones | 1 año |
| Acceso físico (tornos, lectores) | Entradas/salidas a zonas restringidas | 1 año |

## 3. FRECUENCIA DE REVISIÓN

| Tipo de revisión | Frecuencia | Responsable |
|---|---|---|
| **Revisión automatizada** (reglas SIEM, alertas) | Continua (24/7) | SIEM + Resp. Sistema |
| **Revisión manual de alertas** de seguridad | Diaria | Resp. Sistema |
| **Revisión de intentos de acceso fallido** | Semanal | Resp. Sistema |
| **Revisión de actividad de cuentas privilegiadas** | Semanal | Resp. Seguridad |
| **Revisión completa de logs de acceso** | Mensual | Resp. Seguridad |
| **Auditoría de la integridad de los logs** | Trimestral | Resp. Seguridad |

## 4. QUÉ BUSCAR

La revisión buscará, como mínimo:

a) Intentos repetidos de acceso fallido (fuerza bruta, password spraying).

b) Accesos fuera de horario habitual desde cuentas de usuario estándar.

c) Accesos desde ubicaciones o IPs anómalas.

d) Uso de cuentas privilegiadas fuera de ventanas de mantenimiento.

e) Modificaciones no autorizadas de configuraciones críticas.

f) Desactivación o manipulación de los propios logs (anti-tampering).

g) Tráfico de red anómalo (exfiltración, comunicación con IPs maliciosas).

h) Cuentas que no han iniciado sesión en > 90 días (posibles huérfanas).

## 5. DOCUMENTACIÓN DE LA REVISIÓN

Cada revisión manual genera un **registro de revisión** con: fecha, revisor, tipo de revisión, periodo cubierto, anomalías detectadas, acciones tomadas, referencia a incidentes abiertos si procede.

## 6. PROTECCIÓN DE LOS LOGS

a) Los logs se almacenarán en sistema centralizado (SIEM) con acceso restringido.

b) Los logs de seguridad serán **append-only**: ningún usuario, incluidos los administradores del sistema auditado, podrá modificar o eliminar logs ya escritos.

c) La integridad de los logs se verificará trimestralmente mediante hashes o firmas.

## 7. INDICADORES

| Indicador | Objetivo |
|---|---|
| Revisiones de logs ejecutadas conforme al calendario | 100% |
| Anomalías detectadas y gestionadas (vinculadas a E-204) | 100% |
| Intentos de manipulación de logs detectados | Registrados como incidente |

---
```

---

# E-224 — PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE

**Operativo de E-114 (SSDLC). Materializa mp.sw.2 (Aceptación y puesta en servicio).**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-224"
titulo: "Procedimiento de Despliegue de Software"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-114"
---

# PROCEDIMIENTO DE DESPLIEGUE DE SOFTWARE DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-224 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que ningún software (propio o de terceros) pasa a producción sin haber completado las verificaciones de seguridad exigidas por la Política E-114.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Desarrollo completado. Código en rama release. | Equipo desarrollo |
| 2 | **SAST** ejecutado: análisis estático del código (Semgrep, SonarQube). Hallazgos CRÍTICOS y ALTOS = bloqueantes. | DevSecOps / Resp. Sistema |
| 3 | **SCA** ejecutado: dependencias verificadas contra CVEs (Trivy, Safety). Dependencias con CVE CRÍTICA = bloqueantes. | DevSecOps |
| 4 | **Pruebas funcionales** en entorno de preproducción (E-225) superadas. | Equipo QA |
| 5 | **DAST** ejecutado contra entorno de preproducción (ZAP, Nikto). Hallazgos CRÍTICOS = bloqueantes. | Resp. Sistema |
| 6 | **Revisión de configuración del entorno de despliegue**: hardening conforme a E-IT-001, secretos en vault, TLS configurado. | Resp. Sistema |
| 7 | **Solicitud de cambio** conforme a {{ proyecto.codigo_documento_base }}-203 con evidencia de pasos 2-6. | Resp. Sistema |
| 8 | **Aprobación del Resp. Seguridad** para paso a producción. | Resp. Seguridad |
| 9 | **Despliegue** en ventana de mantenimiento aprobada, con rollback preparado. | Resp. Sistema |
| 10 | **Verificación post-despliegue**: servicio operativo, sin errores, sin regresión, monitorización activa 48h. | Resp. Sistema |

## 3. INDICADORES

| Indicador | Objetivo |
|---|---|
| Despliegues con SAST+SCA+DAST completados | 100% |
| Despliegues con hallazgos CRÍTICOS no resueltos | 0 |

---
```

---

# E-225 — PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-225"
titulo: "Procedimiento de Pruebas Pre-Producción"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-114"
---

# PROCEDIMIENTO DE PRUEBAS PRE-PRODUCCIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-225 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que toda modificación de software o infraestructura se prueba en un entorno equivalente a producción antes de su despliegue, detectando defectos funcionales y de seguridad antes de que impacten a los servicios reales.

## 2. ENTORNO DE PREPRODUCCIÓN

a) El entorno de preproducción será **equivalente al productivo** en configuración, versiones de software y datos de prueba representativos (datos anonimizados, nunca datos personales reales).

b) El acceso al entorno de preproducción se restringirá al personal técnico autorizado.

c) Las credenciales del entorno de preproducción serán distintas de las de producción.

## 3. CRITERIOS DE PASO A PRODUCCIÓN

| Criterio | Obligatorio |
|---|---|
| Pruebas funcionales superadas | Sí |
| SAST sin hallazgos CRÍTICOS/ALTOS | Sí |
| SCA sin CVEs CRÍTICAS en dependencias | Sí |
| DAST sin hallazgos CRÍTICOS | Sí (categoría MEDIA+) |
| Pruebas de rendimiento si aplica | Según impacto |
| Revisión de configuración de seguridad | Sí |
| Aprobación del Resp. Seguridad | Sí |

---
```

---

# E-226 — PROCEDIMIENTO DE TELETRABAJO

**Operativo de E-110. Detalla los pasos de autorización, conexión y supervisión.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-226"
titulo: "Procedimiento de Teletrabajo"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-110"
---

# PROCEDIMIENTO DE TELETRABAJO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-226 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar los pasos operativos para autorizar, configurar y supervisar el acceso remoto del personal en modalidad de teletrabajo, conforme a la Política E-110.

## 2. FLUJO DE AUTORIZACIÓN

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Solicitud del empleado o del responsable jerárquico, indicando: persona, puesto, frecuencia (permanente/parcial/puntual), dispositivo (corporativo/BYOD) | Solicitante |
| 2 | Autorización laboral conforme al RD-ley 28/2020 (acuerdo de teletrabajo) | RRHH |
| 3 | Autorización de seguridad: verificación de que el dispositivo cumple los requisitos de E-110 §4 | Resp. Seguridad |
| 4 | Configuración técnica: VPN, MFA, cifrado de disco, antimalware, bloqueo a 5 min | Resp. Sistema |
| 5 | Formación específica de seguridad en teletrabajo | Resp. Seguridad |
| 6 | Registro en el listado de teletrabajadores autorizados | Resp. Seguridad |

## 3. SUPERVISIÓN

a) Verificación mensual del estado de seguridad de los dispositivos remotos (parches, antimalware, cifrado).

b) Monitorización de los accesos VPN: horarios, duración, IPs de origen.

c) Revocación inmediata si se detecta incumplimiento de las normas de E-110.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Teletrabajadores con dispositivo conforme a E-110 | 100% |
| Teletrabajadores con MFA activo | 100% |

---
```

---

# E-227 — PROCEDIMIENTO DE USO DE CLOUD

**Operativo de E-111. Flujo de solicitud, evaluación y onboarding de servicios cloud.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-227"
titulo: "Procedimiento de Uso de Servicios Cloud"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-111"
---

# PROCEDIMIENTO DE USO DE SERVICIOS CLOUD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-227 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar el flujo operativo para solicitar, evaluar, aprobar, configurar y supervisar el uso de servicios cloud en {{ cliente.razon_social }}.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | **Solicitud**: área funcional identifica necesidad de servicio cloud y solicita al Resp. Seguridad indicando: servicio, proveedor, tipo de información a tratar, finalidad | Solicitante |
| 2 | **Verificación de Shadow IT**: comprobar que el servicio no se está usando ya sin autorización | Resp. Seguridad |
| 3 | **Evaluación de seguridad** conforme a E-111 §3 y E-217: certificaciones, localización, cifrado, modelo responsabilidad compartida, plan de salida | Resp. Seguridad |
| 4 | **Aprobación o denegación** documentada | Resp. Seguridad |
| 5 | **Contratación** con inclusión de cláusulas de seguridad de E-112 §5.3 | Resp. Servicio + Resp. Seguridad |
| 6 | **Configuración segura** del servicio: MFA para admin, cifrado BYOK si posible, logs habilitados, acceso mínimo | Resp. Sistema |
| 7 | **Alta en el inventario** de servicios cloud | Resp. Sistema |
| 8 | **Supervisión periódica** conforme a E-216 | Resp. Seguridad |

## 3. INVENTARIO DE SERVICIOS CLOUD

Se mantendrá un inventario actualizado de todos los servicios cloud autorizados con: nombre, proveedor, modelo (IaaS/PaaS/SaaS), información tratada, nivel de clasificación máximo, certificaciones del proveedor, fecha de aprobación, responsable funcional.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Servicios cloud en uso con autorización documentada | 100% |
| Servicios cloud inventariados | 100% |

---
```

---

# E-228 — PROCEDIMIENTO DE RESPUESTA ANTE PÉRDIDA O ROBO DE DISPOSITIVOS

**Conforme a la numeración v2.1 (que asigna E-228 a este tema, no a custodia de evidencias).**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-228"
titulo: "Procedimiento de Respuesta ante Pérdida o Robo de Dispositivos"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-110"
---

# PROCEDIMIENTO DE RESPUESTA ANTE PÉRDIDA O ROBO DE DISPOSITIVOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-228 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones inmediatas que deben realizarse cuando un dispositivo corporativo (portátil, móvil, tableta, token) o un dispositivo personal autorizado (BYOD) que contenga información del alcance del SGSI se pierde, es sustraído o se sospecha que ha sido comprometido.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | La persona afectada **notifica inmediatamente** al Resp. Seguridad y al Resp. Sistema | Persona afectada | **Inmediato** (máx. 2 horas) |
| 2 | **Bloqueo remoto** del dispositivo mediante MDM o herramienta equivalente | Resp. Sistema | 1 hora desde la notificación |
| 3 | **Borrado remoto** de los datos corporativos si el dispositivo no se recupera en 24 horas o si la información es CONFIDENCIAL+ | Resp. Sistema + Resp. Seguridad | 24 horas |
| 4 | **Revocación** de todas las credenciales almacenadas en el dispositivo (contraseñas guardadas, tokens, certificados) | Resp. Sistema | 4 horas |
| 5 | **Valoración del impacto**: ¿el dispositivo contenía información CONFIDENCIAL o RESTRINGIDA? ¿datos personales? ¿estaba cifrado? | Resp. Seguridad | 4 horas |
| 6 | Si contenía datos personales y el cifrado no estaba activo → posible **brecha RGPD**: activar E-212 | Resp. Seguridad + DPO | Según E-212 |
| 7 | **Denuncia** ante las autoridades policiales si se sospecha robo | Persona afectada (con apoyo de la Entidad) | 24 horas |
| 8 | **Registro del incidente** en E-204 | Resp. Seguridad | 24 horas |
| 9 | **Sustitución** del dispositivo con nuevo equipo hardened | Resp. Sistema | Según disponibilidad |

## 3. MITIGACIÓN POR CIFRADO

Si el dispositivo tenía **cifrado de disco completo activo** (BitLocker, FileVault, LUKS), el riesgo de acceso a la información por el ladrón se considera **muy bajo**. No obstante, los pasos 2-4 se ejecutan igualmente como medida preventiva.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Dispositivos perdidos/robados con bloqueo remoto en < 1h | 100% |
| Dispositivos perdidos/robados con cifrado activo en el momento | 100% |

---
```

---

# E-229 — PROCEDIMIENTO DE VISITAS EXTERNAS

**Materializa mp.if.2 (Identificación de personas) del Anexo II.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-229"
titulo: "Procedimiento de Control de Visitas Externas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-123"
---

# PROCEDIMIENTO DE CONTROL DE VISITAS EXTERNAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-229 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Regular el acceso de personas externas (visitantes, proveedores puntuales, candidatos, auditores) a las instalaciones de {{ cliente.razon_social }}.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | El anfitrión notifica la visita con antelación mínima de 24h: nombre visitante, empresa, motivo, fecha/hora, zonas a visitar | Anfitrión (personal interno) |
| 2 | Recepción verifica la identidad del visitante (DNI/pasaporte) y registra: nombre, empresa, DNI, anfitrión, hora entrada | Recepción |
| 3 | Se entrega tarjeta de visitante visible. En zonas restringidas: acompañamiento obligatorio durante toda la visita | Recepción + anfitrión |
| 4 | El visitante firma el compromiso de confidencialidad si va a acceder a información CONFIDENCIAL+ | Visitante |
| 5 | Al finalizar: devolución de tarjeta, registro de hora de salida | Recepción |
| 6 | Si el visitante requiere acceso a sistemas (auditor externo, técnico de proveedor): alta temporal conforme a E-200 con vigencia limitada al día/semana de la visita | Resp. Sistema |

## 3. RESTRICCIONES

a) Los visitantes no accederán a zonas restringidas o críticas sin acompañamiento.

b) Queda prohibido que los visitantes conecten dispositivos propios a la red corporativa salvo autorización del Resp. Seguridad.

c) Los visitantes no fotografiarán ni grabarán en zonas restringidas salvo autorización expresa.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Visitas registradas en el libro de visitas | 100% |
| Visitas a zonas restringidas con acompañamiento | 100% |

---
```

---

# E-230 — PROCEDIMIENTO DE CATEGORIZACIÓN DE SISTEMAS

**Operativo del Motor 1 (Categorization Engine). Materializa el Anexo I del RD 311/2022 y la guía CCN-STIC 803.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-230"
titulo: "Procedimiento de Categorización de Sistemas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE CATEGORIZACIÓN DE SISTEMAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-230 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método para determinar la categoría de seguridad de los sistemas de información de {{ cliente.razon_social }} conforme al Anexo I del Real Decreto 311/2022 y a la guía CCN-STIC 803.

## 2. DIMENSIONES DE SEGURIDAD

Para cada información tratada y cada servicio prestado, se valora el impacto de un incidente en 5 dimensiones:

| Sigla | Dimensión | Pregunta clave |
|---|---|---|
| **D** | Disponibilidad | ¿Qué impacto tendría la indisponibilidad? |
| **I** | Integridad | ¿Qué impacto tendría la alteración no autorizada? |
| **C** | Confidencialidad | ¿Qué impacto tendría la divulgación no autorizada? |
| **A** | Autenticidad | ¿Qué impacto tendría la suplantación de identidad? |
| **T** | Trazabilidad | ¿Qué impacto tendría la imposibilidad de rastrear quién hizo qué? |

## 3. NIVELES DE IMPACTO

| Nivel | Criterio |
|---|---|
| **BAJO** | Perjuicio limitado a la organización, sin afectación significativa a terceros |
| **MEDIO** | Perjuicio grave a la organización o limitado a terceros |
| **ALTO** | Perjuicio muy grave a la organización o grave a terceros |

## 4. REGLA DEL MÁXIMO

La categoría del sistema es la **más alta** de cualquier dimensión de cualquier información o servicio dentro del alcance:

- Todas BAJO → **BÁSICA**
- La más alta es MEDIO → **MEDIA**
- La más alta es ALTO → **ALTA**

## 5. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Identificar las informaciones tratadas y los servicios prestados dentro del alcance | Resp. Información + Resp. Servicio |
| 2 | Para cada información/servicio, valorar el impacto en cada dimensión (D, I, C, A, T) en escala BAJO/MEDIO/ALTO/N/A | Resp. Información (para C, I, A, T) + Resp. Servicio (para D) |
| 3 | Documentar la justificación de cada valoración en la **Ficha de Categorización** (Anexo I) | Resp. Seguridad |
| 4 | Aplicar la regla del máximo para obtener la categoría del sistema | Resp. Seguridad |
| 5 | Someter la categorización a aprobación del Comité de Seguridad | Resp. Seguridad |
| 6 | Documentar en acta firmada por {{ cliente.organo_aprobador_politicas }} | Secretario del Comité |

## 6. REVISIÓN

La categorización se revisará al menos **anualmente** y siempre que se produzcan cambios significativos en el alcance, los servicios o las informaciones tratadas.

## 7. INDICADORES

| Indicador | Objetivo |
|---|---|
| Sistemas del alcance con categorización vigente (<12 meses) | 100% |
| Categorizaciones aprobadas por el Comité | 100% |

---
```

---

# E-232 — PROCEDIMIENTO DE GESTIÓN CRIPTOGRÁFICA

**Operativo de E-107 y E-120. Detalla la operación del inventario de claves, la rotación y la respuesta a compromisos.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-232"
titulo: "Procedimiento de Gestión Criptográfica"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-107, {{ proyecto.codigo_documento_base }}-120"
---

# PROCEDIMIENTO DE GESTIÓN CRIPTOGRÁFICA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-232 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar la operación del inventario de claves, los procedimientos de generación, rotación, archivo y destrucción, y la respuesta ante compromiso o sospecha de compromiso de material criptográfico.

## 2. INVENTARIO DE CLAVES

Conforme a E-120 §2, el inventario registra: ID clave, tipo, algoritmo, longitud, propósito, sistema, fecha generación, fecha expiración, custodio, estado.

Se revisa **trimestralmente** por el Resp. Seguridad.

## 3. ROTACIÓN PROGRAMADA

Conforme a la tabla de E-120 §5:

| Tipo de clave | Plazo | Procedimiento |
|---|---|---|
| Claves de sesión TLS | Por sesión | Automático por protocolo |
| Claves operativas (cifrado reposo) | 24 meses | Generar nueva clave → re-cifrar datos → destruir clave anterior (o archivar si los datos cifrados deben ser accesibles) |
| Claves de servidor TLS | 12 meses | Renovar certificado → desplegar → verificar |
| Certificados de personal | Conforme al periodo del certificado | Renovar con el Prestador de Servicios de Confianza |
| Claves maestras (KEK) | 36 meses | Doble control: generar nueva KEK → re-envolver claves operativas → destruir KEK anterior |

## 4. RESPUESTA A COMPROMISO

| Paso | Acción | Plazo |
|---|---|---|
| 1 | Notificar al Resp. Seguridad | Inmediato |
| 2 | **Revocar** la clave comprometida | < 1 hora |
| 3 | **Generar** clave de sustitución | < 4 horas |
| 4 | **Evaluar** la integridad de la información protegida por la clave comprometida | 24 horas |
| 5 | Gestionar como incidente conforme a E-204 | Según E-204 |
| 6 | Si la clave comprometida protegía datos personales → evaluar si es brecha RGPD (E-212) | Según E-212 |
| 7 | Documentar en el inventario: fecha revocación, motivo, clave sustituta | Resp. Seguridad |

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Claves rotadas en plazo | 100% |
| Claves expiradas sin rotación | 0 |
| Compromisos de clave gestionados en < 4h | 100% |

---
```

---

# E-233 — PROCEDIMIENTO DE NOTIFICACIÓN A LUCIA

**Para clientes del sector público o que presten servicios esenciales. Aplazable para el ICP actual (PYMEs privadas) pero necesario tenerlo preparado.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-233"
titulo: "Procedimiento de Notificación de Incidentes al CCN-CERT vía LUCIA"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-108"
---

# PROCEDIMIENTO DE NOTIFICACIÓN DE INCIDENTES AL CCN-CERT VÍA LUCIA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-233 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar el flujo de notificación de incidentes de seguridad al CCN-CERT a través de la herramienta LUCIA, conforme a la Instrucción Técnica de Seguridad de Notificación de Incidentes (BOE-A-2018-5370).

{% if not cliente.es_sector_publico %}
**Nota:** {{ cliente.razon_social }} no es una entidad del sector público. La notificación al CCN-CERT vía LUCIA tiene carácter **voluntario** salvo que el incidente afecte a servicios prestados a la Administración Pública, en cuyo caso será obligatoria conforme al contrato vigente con el organismo público correspondiente.
{% endif %}

## 2. PLAZOS DE NOTIFICACIÓN

| Nivel del incidente | Plazo de notificación inicial |
|---|---|
| CRÍTICO | 1 hora |
| MUY ALTO | 6 horas |
| ALTO | 24 horas |
| MEDIO | 72 horas (voluntario para privados) |
| BAJO | No requiere notificación |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | El incidente se clasifica conforme a E-204 | Resp. Seguridad |
| 2 | Si el nivel requiere notificación: acceder a LUCIA con el **certificado digital** de la entidad | Resp. Seguridad |
| 3 | Cumplimentar la notificación inicial en LUCIA: tipo, impacto, sistemas afectados, acciones tomadas | Resp. Seguridad |
| 4 | Mantener actualizada la ficha del incidente en LUCIA durante su gestión | Resp. Seguridad |
| 5 | Al cierre del incidente: enviar la notificación de cierre en LUCIA con informe final | Resp. Seguridad |

## 4. INTERLOCUCIÓN

La interlocución con el CCN-CERT corresponde exclusivamente al Responsable de la Seguridad o a la persona en quien delegue formalmente.

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Notificaciones al CCN-CERT realizadas en plazo (cuando proceda) | 100% |

---
```

---

# E-234 — PROCEDIMIENTO DE PROCESO DE AUTORIZACIÓN (org.4)

**Materializa directamente la medida org.4 del Anexo II. Define el flujo formal por el que se autorizan cambios significativos en el sistema.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-234"
titulo: "Procedimiento de Proceso de Autorización"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE PROCESO DE AUTORIZACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-234 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el proceso formal por el que se autorizan las actuaciones significativas que afectan al sistema de información del alcance del SGSI, conforme a la medida **org.4 (Proceso de autorización)** del Anexo II del Real Decreto 311/2022.

## 2. ACTUACIONES QUE REQUIEREN AUTORIZACIÓN FORMAL

La medida org.4 del ENS exige autorización formal previa para:

a) **Instalación de nuevos equipos** en la red o en los locales de la Entidad.

b) **Conexión de sistemas a redes** distintas de las habituales.

c) **Paso a producción** de nuevas aplicaciones o versiones (cubierto también por E-224).

d) **Contratación de servicios externos** que afecten al sistema (cubierto también por E-216/E-217/E-227).

e) **Uso de dispositivos personales** para acceso a información corporativa (cubierto por E-118).

f) **Uso de soportes extraíbles** para información CONFIDENCIAL+ (cubierto por E-215).

g) **Cualquier actuación** que el Responsable de la Seguridad determine que puede afectar a la seguridad del sistema.

## 3. FLUJO DE AUTORIZACIÓN

| Paso | Acción | Responsable |
|---|---|---|
| 1 | **Solicitud** por escrito (formulario o correo electrónico al Resp. Seguridad) indicando: actuación propuesta, justificación, impacto previsto, fecha deseada | Solicitante |
| 2 | **Evaluación de impacto** en la seguridad del sistema | Resp. Seguridad |
| 3 | **Decisión**: autorizar / autorizar con condiciones / denegar. Documentada con motivación. | Resp. Seguridad (impacto BAJO/MEDIO) o Comité de Seguridad (impacto ALTO/CRÍTICO) |
| 4 | **Registro** de la autorización en el Registro de Autorizaciones | Resp. Seguridad |
| 5 | **Ejecución** de la actuación conforme a las condiciones impuestas | Solicitante |
| 6 | **Verificación** posterior de que la actuación se ha ejecutado conforme a la autorización | Resp. Seguridad |

## 4. REGISTRO DE AUTORIZACIONES

Se mantendrá un registro de todas las autorizaciones concedidas, con: ID, fecha, solicitante, actuación, decisión, condiciones, fecha de ejecución, persona que verificó.

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Actuaciones del alcance org.4 con autorización previa documentada | 100% |
| Actuaciones no autorizadas detectadas | 0 |

---
```

---

## HITO: 35/35 PROCEDIMIENTOS COMPLETADOS ✅

### Estado completo del catálogo de procedimientos v2.1 §2.7

| Bloque | Procedimientos | Estado |
|---|---|---|
| F2.1+F2.2 originales (renumerados) | E-203, E-204, E-205, E-207, E-217, E-218, E-221, E-231 | ✅ 8 renumerados |
| Corrección 6A (nuevos ALTA) | E-200, E-201, E-202, E-206, E-209, E-210, E-211, E-212, E-213, E-219, E-220 | ✅ 11 nuevos |
| **Corrección 6B+6C (nuevos restantes)** | **E-208, E-214, E-215, E-216, E-222, E-223, E-224, E-225, E-226, E-227, E-228, E-229, E-230, E-232, E-233, E-234** | **✅ 16 nuevos** |
| **TOTAL** | **35/35** | **100%** |

### Documentos adicionales (fuera de la serie E-2XX)

| ID | Título | Estado |
|---|---|---|
| E-AR-001 | Análisis y Gestión de Riesgos MAGERIT v3 | ✅ Renumerado desde antiguo E-200 |
| E-PF-001 | Plan de Formación y Concienciación | ✅ Renumerado desde antiguo E-207 |
| E-IT-001 | Instrucción Técnica de Hardening | ✅ Renumerado desde antiguo E-219 |
| E-204-A | Anexo Forense (Custodia de Evidencias) | ✅ Renumerado desde antiguo E-228 |

---

## ESTADO GLOBAL DE LAS CORRECCIONES

| Corrección | Estado |
|---|---|
| ✅ **C-1** Renumeración | Tabla + script completados |
| ⏳ **C-2** Motor 8 ampliado | Pendiente |
| ⏳ **C-3** Cláusula Recursos C-001 | Pendiente |
| ⏳ **C-4** Effort Estimator | Pendiente |
| ✅ **C-5** 27/27 Políticas | **COMPLETADAS** |
| ✅ **C-6** 35/35 Procedimientos | **COMPLETADAS** |
| ⏳ **C-7** 8 Plantillas comerciales | Pendiente |
| ⏳ **C-8** 4 Agentes 17-20 | Pendiente |

**Quedan 4 correcciones pendientes:** Motor 8 ampliado, cláusula C-001, Effort Estimator y plantillas+agentes. ¿Seguimos?
