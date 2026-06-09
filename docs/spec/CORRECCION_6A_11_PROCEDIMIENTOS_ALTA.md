# CORRECCIÓN 6A — 9 PROCEDIMIENTOS NUEVOS PRIORIDAD ALTA (Lote 1/3, numeración v2.1)

**Plan 100/100 FULKRO — Parche de auditoría**
**Fecha:** 10 de abril de 2026
**Nota:** Primer lote de 27 procedimientos nuevos para completar 35/35 del catálogo v2.1 §2.7.

---

# DOCUMENTO E-200 — PROCEDIMIENTO DE ALTA DE PERSONAL

**Es el procedimiento que el auditor pide ver primero con registros reales de los últimos 3-6 meses. Materializa mp.per.1 y mp.per.2.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-200"
titulo: "Procedimiento de Alta de Personal"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE ALTA DE PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-200 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los pasos operativos para la incorporación segura de una nueva persona a {{ cliente.razon_social }}, garantizando que antes de que acceda a cualquier sistema o información del alcance del SGSI se han completado todos los controles de seguridad requeridos.

## 2. ALCANCE

Aplica a toda incorporación: personal laboral, becarios, personal en prácticas, personal temporal y personal externo (proveedores, consultores) que vaya a acceder a sistemas o información del alcance.

## 3. FLUJO OPERATIVO

### Fase A — Pre-incorporación (antes del primer día)

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| A.1 | RRHH comunica al Responsable de la Seguridad los datos de la nueva incorporación: nombre, puesto, fecha de inicio, responsable jerárquico, tipo de relación (laboral/externo) | RRHH | ≥ 5 días hábiles antes del inicio |
| A.2 | El Responsable de la Seguridad determina el perfil de acceso necesario según el puesto (necesidad de saber, nivel de clasificación accesible, sistemas requeridos, privilegios) | Resp. Seguridad | 3 días hábiles |
| A.3 | RRHH prepara los documentos de incorporación: contrato laboral o acuerdo de prestación, compromiso de confidencialidad (NDA), acuse de recibo de la Política de Uso Aceptable ({{ proyecto.codigo_documento_base }}-103) | RRHH | Antes del inicio |
| A.4 | Si el puesto requiere acceso a información CONFIDENCIAL o superior: verificación de antecedentes proporcional (conforme a legislación laboral y RGPD) | RRHH + Resp. Seguridad | Antes del inicio |

### Fase B — Primer día

| Paso | Acción | Responsable |
|---|---|---|
| B.1 | Firma del contrato, NDA y acuse de la Política de Uso Aceptable | Nuevo empleado + RRHH |
| B.2 | **Sesión de acogida en seguridad** (mínimo 2 horas): presentación del SGSI, política de seguridad, normas de uso, procedimiento de notificación de incidentes, datos de contacto del Responsable de la Seguridad. Conforme al Plan de Formación (E-PF-001). | Resp. Seguridad o delegado |
| B.3 | Entrega de equipos corporativos con hardening aplicado conforme a E-IT-001 | Resp. Sistema |
| B.4 | Creación de cuentas y provisión de accesos conforme al procedimiento {{ proyecto.codigo_documento_base }}-231, con el perfil determinado en A.2 | Resp. Sistema |
| B.5 | Configuración de MFA conforme a {{ proyecto.codigo_documento_base }}-102 | Resp. Sistema + nuevo empleado |
| B.6 | Entrega de credenciales con cambio obligatorio en primer uso | Resp. Sistema |
| B.7 | Entrega de tarjeta/llave de acceso físico si procede, con registro en inventario | Resp. Sistema |

### Fase C — Primera semana

| Paso | Acción | Responsable |
|---|---|---|
| C.1 | Completar la formación de acogida específica del puesto (herramientas, procedimientos del área) | Responsable jerárquico |
| C.2 | Verificar que todos los accesos funcionan correctamente y son los necesarios (ni más ni menos) | Resp. Seguridad |
| C.3 | Registrar la incorporación en el sistema de gestión del SGSI como evidencia de cumplimiento de mp.per.1 y mp.per.2 | Resp. Seguridad |

## 4. REGISTROS GENERADOS

| Registro | Conservación |
|---|---|
| Contrato / acuerdo firmado | Vida laboral + 4 años |
| NDA firmado | Vigencia NDA + 5 años |
| Acuse de recibo Política Uso Aceptable | Vida laboral + 4 años |
| Registro de sesión de acogida (asistencia + firma) | 5 años |
| Registro de provisión de accesos (perfil, sistemas, fecha) | Vida laboral + 2 años |
| Registro de entrega de equipos (S/N, tipo, fecha) | Vida laboral + 2 años |

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Altas con sesión de acogida completada en primera semana | 100% |
| Altas con NDA firmado antes del primer acceso | 100% |
| Tiempo medio de provisión de accesos desde la incorporación | < 2 días hábiles |

---

**Documento {{ proyecto.codigo_documento_base }}-200 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-201 — PROCEDIMIENTO DE BAJA DE PERSONAL

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-201"
titulo: "Procedimiento de Baja de Personal"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE BAJA DE PERSONAL DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-201 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que al cesar la relación de una persona con {{ cliente.razon_social }} se revocan todos los accesos, se recuperan todos los activos y se preserva la seguridad de la información, conforme a los plazos establecidos en la Política de Control de Accesos ({{ proyecto.codigo_documento_base }}-101).

## 2. TIPOS DE BAJA

| Tipo | Características | Plazos de revocación |
|---|---|---|
| **Ordinaria** | Fin de contrato, jubilación, dimisión voluntaria con preaviso | Conforme a tabla del apartado 3 |
| **Conflictiva** | Despido disciplinario, cese conflictivo, sospecha de deslealtad | **Inmediata y previa a la comunicación** |
| **Urgente** | Fallecimiento, incapacidad sobrevenida | 24 horas |

## 3. FLUJO OPERATIVO — BAJA ORDINARIA

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | RRHH notifica al Resp. Seguridad la fecha efectiva de baja | RRHH | ≥ 5 días hábiles antes |
| 2 | Resp. Seguridad genera la **lista de comprobación de baja** (Anexo I) con todos los accesos, equipos y credenciales de la persona | Resp. Seguridad | 2 días hábiles |
| 3 | Revocación de accesos lógicos en los plazos: privilegiados 1h, información ALTA 4h, MEDIA 24h, generales 72h desde la efectividad del cese | Resp. Sistema | Según plazos |
| 4 | Deshabilitación del correo electrónico corporativo con redirección al responsable jerárquico (máx. 30 días) | Resp. Sistema | Día del cese |
| 5 | Cierre de sesiones activas en todos los sistemas | Resp. Sistema | Día del cese |
| 6 | Recuperación de equipos: portátil, móvil, token MFA, tarjeta de acceso, llaves, soportes extraíbles | Resp. Sistema + RRHH | Día del cese |
| 7 | Recuperación o borrado de información corporativa en dispositivos personales si BYOD autorizado | Resp. Sistema | Día del cese |
| 8 | Recordatorio escrito de las obligaciones de confidencialidad subsistentes (NDA) | RRHH | Día del cese |
| 9 | Entrevista de salida (opcional, recomendada para puestos con acceso a información sensible) | RRHH + Resp. Seguridad | ≤ 5 días tras el cese |
| 10 | Verificación final de que todos los puntos de la lista de comprobación están cerrados | Resp. Seguridad | 72 horas tras el cese |
| 11 | Registro de la baja en el sistema de gestión del SGSI | Resp. Seguridad | 72 horas |

## 4. FLUJO — BAJA CONFLICTIVA

| Paso | Acción | Responsable |
|---|---|---|
| 1 | RRHH o Dirección notifica al Resp. Seguridad **antes** de comunicar el despido al afectado | RRHH/Dirección |
| 2 | **Revocación inmediata** de todos los accesos lógicos y físicos antes o simultáneamente a la comunicación | Resp. Sistema |
| 3 | Revisión forense de las acciones realizadas por la cuenta en los últimos 30 días | Resp. Seguridad |
| 4 | Monitorización reforzada durante 72 horas por si detecta accesos residuales | Resp. Sistema |
| 5 | Resto del flujo ordinario (pasos 6-11) | Según paso |

## 5. REGISTROS

| Registro | Conservación |
|---|---|
| Lista de comprobación de baja completada y firmada | 5 años |
| Acta de devolución de equipos | 5 años |
| Recordatorio NDA firmado por el exempleado (si acepta) | Vigencia NDA |

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Bajas con revocación de accesos en plazo | 100% |
| Bajas con todos los equipos recuperados | 100% |
| Lista de comprobación cerrada en 72h | ≥ 95% |

---

**Documento {{ proyecto.codigo_documento_base }}-201 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-202 — PROCEDIMIENTO DE CAMBIO DE ROL

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-202"
titulo: "Procedimiento de Cambio de Rol o Funciones"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-101, {{ proyecto.codigo_documento_base }}-124"
---

# PROCEDIMIENTO DE CAMBIO DE ROL O FUNCIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-202 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Garantizar que cuando una persona cambia de puesto, departamento o funciones dentro de {{ cliente.razon_social }}, sus accesos se ajustan al nuevo rol aplicando el principio de mínimo privilegio, revocando los accesos del puesto anterior que dejen de ser necesarios.

## 2. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | RRHH notifica el cambio al Resp. Seguridad: persona, puesto anterior, puesto nuevo, fecha efectiva | RRHH | ≥ 5 días hábiles antes |
| 2 | Resp. Seguridad determina el nuevo perfil de acceso y lo compara con el actual | Resp. Seguridad | 3 días hábiles |
| 3 | **Revocación de accesos del puesto anterior** que no sean necesarios en el nuevo | Resp. Sistema | Fecha del cambio |
| 4 | **Provisión de accesos nuevos** requeridos por el nuevo puesto | Resp. Sistema | ≤ 3 días hábiles |
| 5 | Verificación de que no quedan privilegios residuales del puesto anterior (*privilege creep*) | Resp. Seguridad | 5 días hábiles |
| 6 | Formación específica de seguridad del nuevo puesto si procede | Resp. jerárquico | 10 días hábiles |
| 7 | Registro del cambio en el sistema de gestión de identidades | Resp. Sistema | Fecha del cambio |

## 3. REGLA ANTI-ACUMULACIÓN

Cuando la persona haya ocupado 3 o más puestos distintos en los últimos 3 años, el Resp. Seguridad realizará una **revisión completa** de todos sus accesos vigentes para detectar acumulación de privilegios residuales. Esta revisión se documenta como evidencia.

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cambios con revisión de accesos completada en plazo | 100% |
| Privilegios residuales detectados en revisiones post-cambio | 0 |

---

**Documento {{ proyecto.codigo_documento_base }}-202 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-206 — PROCEDIMIENTO DE APLICACIÓN DE PARCHES

**Split del antiguo procedimiento E-218 (Vulnerabilidades y Parches). Este cubre el ciclo de vida del parche; E-205 (ya existente, renumerado) cubre la detección de vulnerabilidades.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-206"
titulo: "Procedimiento de Aplicación de Parches"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-115"
---

# PROCEDIMIENTO DE APLICACIÓN DE PARCHES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo operativo para la aplicación controlada de parches de seguridad y actualizaciones en los sistemas del alcance del SGSI, desde la disponibilidad del parche hasta su verificación post-despliegue.

## 2. RELACIÓN CON E-205 (VULNERABILIDADES)

El procedimiento E-205 (Gestión de Vulnerabilidades) **detecta y prioriza** las vulnerabilidades. El presente procedimiento **gestiona la aplicación del parche** que las corrige. Ambos se ejecutan en cascada: E-205 identifica → E-206 aplica.

## 3. PLAZOS MÁXIMOS DE APLICACIÓN

| Criticidad (determinada por E-205) | Plazo máximo desde disponibilidad del parche |
|---|---|
| CRÍTICA con explotación activa (CISA KEV) | 24 horas |
| CRÍTICA | 7 días naturales |
| ALTA | 15 días naturales |
| MEDIA | 60 días naturales |
| BAJA | 180 días o siguiente ciclo de mantenimiento |

## 4. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Recepción de la asignación desde E-205 con vulnerabilidad, parche disponible y criticidad | Resp. Sistema |
| 2 | **Pruebas en preproducción**: aplicar el parche en entorno equivalente al productivo y verificar: no regresión funcional, compatibilidad, estabilidad | Resp. Sistema |
| 3 | Para parches CRÍTICOS con explotación activa: pruebas reducidas o en paralelo autorizadas por el Resp. Seguridad | Resp. Seguridad |
| 4 | **Solicitud de cambio** conforme al procedimiento E-203 (Gestión de Cambios). Para parches CRÍTICOS: flujo de cambio de emergencia | Resp. Sistema |
| 5 | **Despliegue** en la ventana de mantenimiento aprobada, documentando: fecha/hora exacta, sistemas parcheados, persona ejecutora, parche aplicado (referencia fabricante), resultado | Resp. Sistema |
| 6 | **Verificación post-despliegue**: comprobación de versión parcheada, re-escaneo de la vulnerabilidad, verificación del servicio | Resp. Sistema |
| 7 | **Cierre** en el sistema de gestión de vulnerabilidades: marcar como MITIGADA con fecha y verificador | Resp. Seguridad |

## 5. EXCEPCIONES

Cuando no sea posible aplicar un parche en plazo (incompatibilidad, sistema legacy, dependencia de terceros), se gestionará como excepción conforme a {{ proyecto.codigo_documento_base }}-222 (Gestión de Excepciones), documentando: vulnerabilidad, motivo, riesgo asumido, mitigaciones compensatorias, plazo máximo y plan de resolución.

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Parches CRÍTICOS aplicados en plazo | 100% |
| Parches ALTOS aplicados en plazo | ≥ 95% |
| Tasa de rollback por parche fallido | < 3% |
| Excepciones documentadas / excepciones totales | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-206 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-209 — PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD

**Operativo de la Política de Continuidad (E-109). Complementa E-207 (Backup) y E-208 (Restauración) con pruebas completas del PCS.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-209"
titulo: "Procedimiento de Pruebas de Continuidad"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-109"
---

# PROCEDIMIENTO DE PRUEBAS DE CONTINUIDAD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-209 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer la planificación, ejecución y documentación de las pruebas periódicas del Plan de Continuidad del Servicio (PCS) y del Plan de Recuperación ante Desastres (DRP), conforme a la medida **op.cont.3 (Pruebas periódicas)** del Anexo II del Real Decreto 311/2022.

## 2. TIPOS DE PRUEBA

| Tipo | Descripción | Impacto en producción |
|---|---|---|
| **Revisión documental** | Revisión de los planes PCS/DRP para verificar vigencia y coherencia | Ninguno |
| **Walkthrough (ejercicio de mesa)** | Recorrido paso a paso con el Equipo de Continuidad sobre un escenario simulado | Ninguno |
| **Prueba parcial técnica** | Restauración de un componente o servicio concreto en entorno aislado | Ninguno |
| **Prueba completa (failover)** | Activación de los medios alternativos y restauración íntegra del servicio | Controlado, puede haber ventana de indisponibilidad |

## 3. PERIODICIDAD MÍNIMA

| Tipo de prueba | BÁSICA | MEDIA | ALTA |
|---|---|---|---|
| Revisión documental | Anual | Semestral | Semestral |
| Walkthrough | Anual | Anual | Semestral |
| Prueba parcial técnica | Bienal | Anual | Semestral |
| Prueba completa | Bienal | Bienal | Anual |

## 4. FLUJO OPERATIVO

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Elaborar el **Plan Anual de Pruebas de Continuidad** con escenarios, calendario, participantes y criterios de éxito | Resp. Seguridad |
| 2 | Aprobar el Plan por el Comité de Seguridad | Comité |
| 3 | Comunicar a los participantes con antelación suficiente (≥ 15 días para walkthroughs, ≥ 30 días para pruebas completas) | Resp. Seguridad |
| 4 | **Definir el escenario**: tipo de disrupción simulada, servicios afectados, RTO/RPO objetivo, criterios de éxito/fracaso | Resp. Seguridad |
| 5 | **Ejecutar la prueba** conforme al escenario, cronometrando los tiempos reales de cada fase | Equipo Continuidad |
| 6 | **Medir resultados**: tiempo real de recuperación (RTR) vs RTO objetivo, punto real de recuperación vs RPO, servicios restaurados vs previstos | Resp. Seguridad |
| 7 | Elaborar **Informe de Prueba de Continuidad** con: escenario, participantes, cronología, tiempos medidos, incidencias, desviaciones, lecciones aprendidas, acciones correctivas | Resp. Seguridad |
| 8 | Presentar el informe al Comité de Seguridad | Resp. Seguridad |
| 9 | Si la prueba falla o el RTR > RTO: abrir **acción correctiva** con análisis de causa raíz y plan de mejora | Resp. Seguridad |

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| Pruebas ejecutadas conforme al plan anual | 100% |
| RTR ≤ RTO en pruebas completas | 100% |
| Acciones correctivas cerradas en plazo | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-209 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-210 — PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS

**Operativo de la Política de Control de Accesos (E-101). Cubre la revisión periódica que el auditor pide demostrar con evidencia de los últimos 3-6 meses.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-210"
titulo: "Procedimiento de Revisión Periódica de Accesos"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-101"
---

# PROCEDIMIENTO DE REVISIÓN PERIÓDICA DE ACCESOS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Verificar periódicamente que los derechos de acceso vigentes de todas las personas usuarias siguen siendo necesarios, proporcionados y conformes al principio de mínimo privilegio, detectando y corrigiendo accesos residuales, cuentas huérfanas y acumulación de privilegios.

## 2. PERIODICIDAD

| Tipo de acceso | Frecuencia mínima de revisión |
|---|---|
| Cuentas privilegiadas (administradores, root, DBA) | Trimestral |
| Accesos a información clasificada nivel ALTO | Trimestral |
| Accesos a información clasificada nivel MEDIO | Semestral |
| Accesos generales de usuarios | Anual |
| Cuentas de servicio | Semestral |
| Cuentas de emergencia (break-glass) | Trimestral (verificar que no se han usado sin registrar) |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | Generar el **listado de accesos vigentes** desde el sistema de gestión de identidades, segregado por tipo | Resp. Sistema | Inicio del ciclo |
| 2 | Distribuir el listado a cada **propietario de recurso** (Resp. Información o Resp. Servicio según el activo) | Resp. Seguridad | 2 días hábiles |
| 3 | Cada propietario **revisa y valida**: ¿este usuario necesita este acceso? ¿el nivel de privilegio es el mínimo necesario? | Propietario del recurso | 15 días hábiles |
| 4 | Los accesos marcados como **innecesarios o excesivos** se revocan o ajustan | Resp. Sistema | 5 días hábiles |
| 5 | Las **cuentas inactivas > 90 días** se deshabilitan automáticamente, salvo justificación documentada | Resp. Sistema | Automático |
| 6 | Las **cuentas huérfanas** (sin persona asociada activa) se investigan y eliminan | Resp. Sistema + Resp. Seguridad | 5 días hábiles |
| 7 | Elaborar **Acta de Revisión de Accesos** con: fecha, alcance, nº accesos revisados, nº modificados, nº revocados, nº cuentas deshabilitadas | Resp. Seguridad | 5 días tras cierre |
| 8 | Elevar el Acta al Comité de Seguridad | Resp. Seguridad | Siguiente reunión ordinaria |

## 4. INDICADORES

| Indicador | Objetivo |
|---|---|
| Revisiones ejecutadas conforme al calendario | 100% |
| Cuentas inactivas > 90 días sin justificación | 0 |
| Cuentas huérfanas detectadas y eliminadas | 100% |
| Propietarios que responden en plazo (15 días) | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-210 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-211 — PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS

**Operativo de la Política PAM (E-117). Específico para cuentas admin, root, DBA, break-glass y de servicio con privilegios amplios.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-211"
titulo: "Procedimiento de Gestión de Cuentas Privilegiadas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-117"
---

# PROCEDIMIENTO DE GESTIÓN DE CUENTAS PRIVILEGIADAS DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-211 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las reglas operativas específicas para la creación, uso, monitorización, rotación y revocación de cuentas con privilegios elevados.

## 2. INVENTARIO DE CUENTAS PRIVILEGIADAS

El Responsable del Sistema mantendrá un **inventario actualizado** de todas las cuentas privilegiadas, indicando: identificador, tipo (admin de dominio, root, DBA, admin cloud, cuenta de servicio, break-glass), persona o sistema asignado, privilegios concretos, fecha de última revisión, fecha de última rotación de credenciales.

## 3. CREACIÓN

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Solicitud formal con justificación de la necesidad del privilegio | Responsable jerárquico |
| 2 | Aprobación del Responsable de la Seguridad (obligatoria para toda cuenta privilegiada) | Resp. Seguridad |
| 3 | Creación de la cuenta separada (nomenclatura: `adm-{nombre}` o `svc-{sistema}`) | Resp. Sistema |
| 4 | Activación MFA obligatoria | Resp. Sistema |
| 5 | Almacenamiento de credenciales en vault corporativo | Resp. Sistema |
| 6 | Registro en el inventario de cuentas privilegiadas | Resp. Sistema |

## 4. REGLAS DE USO

a) La cuenta privilegiada se usará **exclusivamente** para las tareas que requieran ese nivel de privilegio. Para actividades ordinarias (correo, navegación, ofimática) se usará la cuenta nominativa estándar.

b) Las sesiones privilegiadas tendrán **duración limitada** y, cuando la tecnología lo permita, se implementará **Just-in-Time (JIT)**: el usuario solicita el privilegio → se le concede por un periodo definido (1-4 horas) → se revoca automáticamente.

c) Todas las sesiones privilegiadas se **registrarán con detalle** en el SIEM, incluyendo: usuario, sistema, hora inicio/fin, comandos ejecutados (cuando sea técnicamente viable).

d) Se realizarán **grabaciones de sesión** para los accesos privilegiados a sistemas críticos, conforme al nivel de la categoría ENS.

## 5. ROTACIÓN DE CREDENCIALES

| Tipo de cuenta | Frecuencia de rotación |
|---|---|
| Admin de dominio | Trimestral |
| Root / Administrator local | Trimestral |
| DBA | Semestral |
| Admin cloud | Trimestral |
| Cuenta de servicio privilegiada | Semestral |
| Break-glass | Tras cada uso + semestral preventiva |

## 6. CUENTAS BREAK-GLASS

a) Las credenciales se custodian en **sobre sellado en caja fuerte** con doble control de acceso.

b) El uso requiere: autorización del Resp. Seguridad (o del Comité de Crisis en incidente CRÍTICO), apertura con testigo, registro detallado de todas las acciones.

c) Tras el uso: cambio inmediato de credenciales, resellado del sobre, informe de uso al Comité de Seguridad.

## 7. REVISIÓN TRIMESTRAL

Cada trimestre el Resp. Seguridad verifica: vigencia de cada cuenta privilegiada, justificación actualizada, cumplimiento de MFA, última rotación, sesiones registradas.

## 8. INDICADORES

| Indicador | Objetivo |
|---|---|
| Cuentas privilegiadas con MFA activo | 100% |
| Cuentas con credenciales rotadas en plazo | 100% |
| Cuentas privilegiadas sin uso > 60 días | 0 (deshabilitar) |
| Usos de break-glass sin registro completo | 0 |

---

**Documento {{ proyecto.codigo_documento_base }}-211 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-212 — PROCEDIMIENTO DE RESPUESTA A BRECHAS RGPD

**Operativo de la Política E-119. Detalla el flujo desde la detección hasta la notificación y comunicación.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-212"
titulo: "Procedimiento de Respuesta a Brechas de Datos Personales"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-119"
---

# PROCEDIMIENTO DE RESPUESTA A BRECHAS DE DATOS PERSONALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-212 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar las acciones operativas desde la detección de una brecha de seguridad que afecta a datos personales hasta su notificación a la AEPD y, cuando proceda, la comunicación a los interesados, en desarrollo de la Política E-119 y en coordinación con el procedimiento de gestión de incidentes E-204.

## 2. FLUJO OPERATIVO

### Fase 1 — Detección y escalado (T+0 a T+2 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Detección del incidente (vía E-204) que potencialmente afecta a datos personales | Cualquier persona / SIEM |
| 2 | El Resp. Seguridad activa al DPO inmediatamente | Resp. Seguridad |
| 3 | El DPO valora si el incidente constituye una brecha de datos personales conforme al art. 4.12 RGPD | DPO |

### Fase 2 — Valoración del riesgo (T+2 a T+12 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 4 | Determinar: tipo de brecha (confidencialidad/integridad/disponibilidad), categorías de datos afectados, nº de interesados, volumen de registros | DPO + Resp. Seguridad |
| 5 | Evaluar nivel de riesgo para los derechos y libertades con los 6 criterios de E-119 §3.2 | DPO |
| 6 | Documentar la valoración en el **Formulario de Valoración de Brecha** (Anexo I) | DPO |

### Fase 3 — Decisión de notificación (T+12 a T+24 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 7 | Si riesgo = sin riesgo → registrar en el Registro de Brechas sin notificar | DPO |
| 8 | Si riesgo = bajo/medio/alto → **notificar a la AEPD** (seguir Fase 4) | DPO |
| 9 | Si riesgo = alto → adicionalmente **comunicar a los interesados** (seguir Fase 5) | DPO |

### Fase 4 — Notificación a la AEPD (≤ 72 horas desde conocimiento)

| Paso | Acción | Responsable |
|---|---|---|
| 10 | Acceder a la sede electrónica de la AEPD: https://sedeaepd.gob.es | DPO |
| 11 | Cumplimentar el **formulario de notificación de brechas** con: naturaleza, categorías y nº de interesados, datos contacto DPO, consecuencias probables, medidas adoptadas | DPO |
| 12 | Si la notificación no puede completarse en 72h: enviar notificación parcial con motivos del retraso y completar después | DPO |
| 13 | Conservar el acuse de recibo de la notificación | DPO |
| 14 | Mantener a la AEPD informada de la evolución si se solicita | DPO |

### Fase 5 — Comunicación a los interesados (sin dilación si riesgo alto)

| Paso | Acción | Responsable |
|---|---|---|
| 15 | Redactar la comunicación en lenguaje claro y sencillo conforme a E-119 §5 | DPO + Comunicación |
| 16 | Canal de comunicación: email directo cuando se disponga del email del interesado; publicación en web corporativa cuando no sea posible la comunicación individual | DPO |
| 17 | Documentar los envíos realizados y los acuses de recibo | DPO |

### Fase 6 — Registro y cierre

| Paso | Acción | Responsable |
|---|---|---|
| 18 | Registrar la brecha completa en el **Registro de Brechas de Datos Personales** | DPO |
| 19 | Integrar las lecciones aprendidas en el informe post-incidente de E-204 | Resp. Seguridad + DPO |
| 20 | Si la brecha revela deficiencias en los controles: abrir acción correctiva | Resp. Seguridad |

## 3. INDICADORES

| Indicador | Objetivo |
|---|---|
| Notificaciones a la AEPD dentro del plazo de 72h | 100% |
| Brechas registradas en el Registro | 100% |
| Comunicaciones a interesados realizadas sin dilación (riesgo alto) | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-212 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-213 — PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD

**Procedimiento técnico complementario a E-212. Detalla el contenido exacto del formulario AEPD y los pasos en la sede electrónica.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-213"
titulo: "Procedimiento de Notificación de Brechas a la AEPD"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-119"
---

# PROCEDIMIENTO DE NOTIFICACIÓN DE BRECHAS A LA AEPD DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-213 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar el contenido, formato, canal y plazos de la notificación de brechas de datos personales a la Agencia Española de Protección de Datos, en cumplimiento del artículo 33 del RGPD.

## 2. CANAL

La notificación se realizará **exclusivamente** a través de la sede electrónica de la AEPD: https://sedeaepd.gob.es, usando el formulario específico de notificación de brechas.

Se requiere certificado digital (persona jurídica o representante) o Cl@ve para acceder a la sede.

## 3. CONTENIDO OBLIGATORIO (art. 33.3 RGPD)

El formulario exige:

a) **Naturaleza de la violación:** descripción del tipo de brecha (confidencialidad/integridad/disponibilidad), vectores de ataque si conocidos.

b) **Categorías de datos afectados:** identificativos, contacto, financieros, salud, categorías especiales, etc.

c) **Número aproximado de interesados afectados** y de registros de datos afectados.

d) **Datos del DPO** o punto de contacto: nombre, email, teléfono.

e) **Consecuencias probables** de la brecha para los interesados.

f) **Medidas adoptadas o propuestas** para poner remedio a la brecha y, en su caso, para mitigar sus efectos.

## 4. PLAZOS

| Situación | Plazo |
|---|---|
| Notificación completa | ≤ 72 horas desde el conocimiento |
| Notificación parcial (información incompleta) | ≤ 72 horas con indicación de los motivos del retraso |
| Complemento de la notificación parcial | Sin dilación, tan pronto como se disponga de la información |
| Notificación de seguimiento (si la AEPD lo requiere) | En el plazo que indique la AEPD |

## 5. RESPONSABLE

La interlocución con la AEPD corresponde al DPO ({{ responsables.delegado_proteccion_datos.nombre }}), con apoyo del Responsable de la Seguridad para la información técnica.

## 6. CONSERVACIÓN

El acuse de recibo de la notificación, el formulario enviado y toda la correspondencia con la AEPD se conservarán durante **6 años** en el Registro de Brechas.

---

**Documento {{ proyecto.codigo_documento_base }}-213 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-219 — PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN

**Materializa el requisito ISO 27001:2022 cláusula 9.3 y el artículo 12 del RD 311/2022 sobre revisión periódica de la Política. Es la sesión anual donde el órgano de gobierno superior revisa el SGSI.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-219"
titulo: "Procedimiento de Revisión por la Dirección"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE REVISIÓN POR LA DIRECCIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el flujo mediante el cual {{ cliente.organo_aprobador_politicas }} revisa, al menos anualmente, el estado del SGSI, valora su adecuación, eficacia y alineación con los objetivos de la Entidad, y adopta las decisiones de mejora que procedan.

## 2. PERIODICIDAD

La revisión por la dirección se realizará con carácter ordinario **al menos una vez al año**, y con carácter extraordinario cuando lo requieran circunstancias excepcionales (incidente grave, cambio normativo mayor, reestructuración organizativa).

## 3. ENTRADAS (INPUT)

El Responsable de la Seguridad preparará y presentará a la dirección:

a) Estado de las acciones derivadas de revisiones anteriores.

b) Cambios en cuestiones internas y externas relevantes para el SGSI (contexto, normativa, amenazas, organización).

c) Resultados de las auditorías internas y externas.

d) Resumen de incidentes de seguridad del periodo y su gestión.

e) Estado del análisis de riesgos y del plan de tratamiento.

f) Estado de cumplimiento de las medidas del Anexo II (informe de la Declaración de Aplicabilidad).

g) Indicadores de rendimiento del SGSI (KPIs definidos en los procedimientos).

h) Resultados de las pruebas de continuidad.

i) Resultado de los simulacros de phishing y métricas de formación.

j) Oportunidades de mejora identificadas.

k) Estado del presupuesto de seguridad.

## 4. SALIDAS (OUTPUT)

La dirección adoptará decisiones documentadas sobre:

a) Oportunidades de mejora y acciones a emprender.

b) Necesidades de cambio en la Política de Seguridad o en la normativa interna.

c) Necesidades de recursos (humanos, técnicos, económicos).

d) Aceptación o no de los riesgos residuales actualizados.

e) Actualización de los objetivos de seguridad si procede.

## 5. REGISTRO

Las decisiones se documentarán en **acta de revisión por la dirección** firmada por el presidente de la sesión, que se conservará conforme al procedimiento de gestión documental ({{ proyecto.codigo_documento_base }}-221).

## 6. INDICADORES

| Indicador | Objetivo |
|---|---|
| Revisiones por la dirección realizadas en el año | ≥ 1 |
| Acciones derivadas cerradas en plazo | ≥ 90% |

---

**Documento {{ proyecto.codigo_documento_base }}-219 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-220 — PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES

**Complementa E-218 (Auditoría Interna). Define cómo se gestionan las NC detectadas en auditorías, revisiones e inspecciones.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-220"
titulo: "Procedimiento de Gestión de No Conformidades y Acciones Correctivas"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE GESTIÓN DE NO CONFORMIDADES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-220 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método para el registro, análisis, tratamiento, seguimiento y cierre de las no conformidades detectadas en el SGSI, ya provengan de auditorías internas, auditorías externas, revisiones por la dirección, incidentes de seguridad o cualquier otra fuente.

## 2. CLASIFICACIÓN

| Tipo | Definición | Plazo máximo de corrección |
|---|---|---|
| **NC Mayor** | Incumplimiento sistemático, ausencia total de control crítico, fallo sistémico | 90 días |
| **NC Menor** | Incumplimiento puntual, fallo aislado no crítico | 180 días |
| **Observación** | Cumplimiento formal con potencial mejora | Análisis en 90 días, acción voluntaria |
| **Oportunidad de mejora** | Recomendación sin incumplimiento | Análisis por el Comité |

## 3. FLUJO OPERATIVO

| Paso | Acción | Responsable | Plazo |
|---|---|---|---|
| 1 | Registro de la NC en el **Registro de No Conformidades** con: fuente, descripción, evidencia, clasificación, área afectada | Quien la detecta | Inmediato |
| 2 | Asignación al **responsable del área afectada** | Resp. Seguridad | 5 días hábiles |
| 3 | **Análisis de causa raíz** (5 Whys, Ishikawa u otra técnica apropiada) | Responsable del área | 15 días hábiles |
| 4 | Elaboración del **Plan de Acción Correctiva (PAC)**: acciones a emprender, responsable de cada acción, plazo, indicador de cierre, acciones preventivas para evitar recurrencia | Responsable del área | 15 días tras análisis |
| 5 | **Aprobación del PAC** | Resp. Seguridad | 5 días hábiles |
| 6 | **Ejecución** de las acciones correctivas | Responsable del área | Según PAC |
| 7 | **Verificación de eficacia**: comprobar que la NC no recurrirá. Puede incluir: revisión documental, nueva inspección, nueva auditoría parcial | Resp. Seguridad (o auditor) | 30 días tras ejecución |
| 8 | **Cierre formal** de la NC en el registro | Resp. Seguridad | Tras verificación |

## 4. ESCALADO

Las NC Mayores no cerradas en plazo se escalan al Comité de Seguridad. Las NC Mayores recurrentes (misma causa raíz detectada en dos ciclos consecutivos) se escalan a {{ cliente.organo_aprobador_politicas }}.

## 5. INDICADORES

| Indicador | Objetivo |
|---|---|
| NC Mayores cerradas en 90 días | 100% |
| NC Menores cerradas en 180 días | ≥ 90% |
| NC recurrentes (misma causa raíz en 2 ciclos) | 0 |
| PAC aprobados en plazo | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-220 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

## RESUMEN DEL BLOQUE 6A

### 9 procedimientos nuevos PRIORIDAD ALTA entregados

| ID v2.1 | Título | Medidas/requisitos cubiertos |
|---|---|---|
| **E-200** | Alta de personal | mp.per.1, mp.per.2 |
| **E-201** | Baja de personal | mp.per.1, revocación accesos |
| **E-202** | Cambio de rol | op.acc.4, anti-privilege creep |
| **E-206** | Aplicación de parches | op.exp.4 (parte parches) |
| **E-209** | Pruebas de continuidad | op.cont.3 |
| **E-210** | Revisión periódica de accesos | op.acc.4, cuentas huérfanas |
| **E-211** | Gestión de cuentas privilegiadas | op.acc.3, op.acc.4, PAM |
| **E-212** | Respuesta a brechas RGPD | RGPD art. 33-34 |
| **E-213** | Notificación de brechas a la AEPD | RGPD art. 33, sede electrónica |
| **E-219** | Revisión por la dirección | ISO 27001 cláusula 9.3 |
| **E-220** | Gestión de no conformidades | ISO 27001 cláusula 10.1-10.2 |

*(Son 11, no 9 — he metido 2 extra porque eran cortos y dependían de los anteriores.)*

### Estado de los 35 procedimientos

| Estado | Cantidad |
|---|---|
| ✅ Existentes (renumerados de F2) | 8 |
| ✅ **Nuevos en este bloque 6A** | **11** |
| 🔲 Pendientes (bloque 6B + 6C) | 16 |

**Progreso: 19/35 procedimientos completos (54%).**

### Siguiente: Bloques 6B y 6C — los 16 procedimientos restantes

Si me dices "seguimos" arranco con el segundo lote.
