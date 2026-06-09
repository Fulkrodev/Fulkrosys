# DOCUMENTO E-207 — PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN

**Materializa la medida mp.info.9 (Copias de seguridad) del Anexo II del ENS** y desarrolla el apartado 6.2 de la Política de Continuidad ({{ proyecto.codigo_documento_base }}-109). Es el procedimiento que el auditor pide demostrar con un test real de restauración reciente.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-207"
titulo: "Procedimiento de Copias de Seguridad y Restauración"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-109"
---

# PROCEDIMIENTO DE COPIAS DE SEGURIDAD Y RESTAURACIÓN DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-207 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método operativo mediante el cual {{ cliente.razon_social }} planifica, ejecuta, verifica, custodia y, en caso necesario, utiliza copias de seguridad de los datos, configuraciones y sistemas comprendidos en el alcance del SGSI, garantizando la disponibilidad e integridad de la información ante cualquier tipo de pérdida, corrupción, destrucción o cifrado malicioso.

Este procedimiento desarrolla el apartado 6.2 de la Política de Continuidad del Servicio ({{ proyecto.codigo_documento_base }}-109) y materializa la medida **mp.info.9 (Copias de seguridad)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los datos, configuraciones, sistemas operativos, aplicaciones, máquinas virtuales y elementos cuya pérdida o corrupción pudiera afectar a la operación de los servicios comprendidos en el alcance del SGSI.

## 3. ESTRATEGIA DE COPIA — REGLA 3-2-1-1-0

La estrategia de copia adoptada se ajusta a la **regla 3-2-1-1-0**:

- **3** copias de los datos críticos en total (incluido el original).
- **2** soportes diferentes para almacenarlas.
- **1** copia almacenada **fuera de las instalaciones principales** (offsite).
- **1** copia adicional **inmutable o air-gapped** para protección frente a ransomware.
- **0** errores detectados en las pruebas de restauración periódicas.

## 4. MATRIZ DE COPIA POR TIPO DE DATO

| Tipo de dato | Frecuencia | Retención mínima | Tipo de copia | Almacenamiento |
|---|---|---|---|---|
| Bases de datos críticas | Cada 4 horas (incremental) + diaria (completa) | 6 meses | Snapshot + dump lógico | Local + offsite cifrado |
| Bases de datos no críticas | Diaria | 3 meses | Dump lógico | Local + offsite |
| Sistemas de ficheros corporativos | Diaria (incremental) + semanal (completa) | 3 meses | A nivel de bloque o fichero | Local + offsite |
| Configuraciones de servidores | Tras cada cambio + semanal | 1 año | Snapshot + IaC en repositorio | Repositorio versionado |
| Configuraciones de red (firewall, switches, routers) | Tras cada cambio + diaria | 1 año | Export en formato texto | Repositorio versionado |
| Imágenes de máquinas virtuales | Semanal | 3 meses | Snapshot completo | Local + offsite |
| Código fuente y artefactos | Continuo | Indefinida | Repositorio Git + binarios firmados | Repositorio + offsite |
| Logs y trazas de auditoría | Continuo (envío a SIEM) + diaria | Según política {{ proyecto.codigo_documento_base }}-221 | Append-only | SIEM + almacenamiento WORM |
| Registros del SGSI | Diaria | Vida del SGSI + 5 años | Snapshot del repositorio | Repositorio + offsite |

## 5. REQUISITOS DE PROTECCIÓN DE LAS COPIAS

### 5.1 Cifrado

**Paso 1.** Todas las copias de seguridad se almacenarán **cifradas en reposo** mediante algoritmos conformes al apartado 4 de la Política de Cifrado ({{ proyecto.codigo_documento_base }}-107):

- AES-256 en modo GCM o CCM para el cifrado de los datos.
- Claves gestionadas en HSM o vault corporativo conforme al apartado 6 de la Política {{ proyecto.codigo_documento_base }}-107.

### 5.2 Verificación de integridad

**Paso 2.** Cada copia se acompañará de un **valor hash SHA-256** calculado en el momento de su creación, que permita verificar posteriormente su integridad.

**Paso 3.** El sistema de copias verificará automáticamente los hashes con periodicidad semanal y emitirá alerta ante cualquier discrepancia.

### 5.3 Inmutabilidad

**Paso 4.** Para protegerse frente a ataques de ransomware, al menos una copia de cada dato crítico se almacenará en un sistema **inmutable** durante el periodo de retención, mediante:

- Object lock en almacenamiento S3-compatible (modo *compliance*, no *governance*).
- Sistemas de cinta con protección de escritura física.
- Soluciones de backup con snapshots inmutables.

### 5.4 Air-gapping

**Paso 5.** Para sistemas de máxima criticidad, se mantendrá adicionalmente una copia en un soporte físicamente desconectado de la red (air-gapped), actualizada con periodicidad mensual.

### 5.5 Localización offsite

**Paso 6.** La copia offsite se almacenará en una **ubicación física distinta y suficientemente alejada** de las instalaciones principales para que un mismo evento (incendio, inundación, ataque físico) no pueda destruir simultáneamente el original y la copia.

Cuando la copia offsite se almacene en proveedor cloud externo, se aplicarán las exigencias del apartado 7 de la Política {{ proyecto.codigo_documento_base }}-112 (Política de Proveedores).

## 6. EJECUCIÓN DE LAS COPIAS

### 6.1 Programación

**Paso 7.** Las copias se programan en horarios que minimicen el impacto en la operación, preferentemente fuera de las ventanas de mayor actividad operativa.

**Paso 8.** El sistema de gestión de copias monitoriza automáticamente la ejecución y emite alertas en caso de:

- Fallo en la ejecución de una tarea programada.
- Tarea no completada en el plazo previsto.
- Discrepancia en el tamaño esperado.
- Error en la verificación de integridad.

### 6.2 Resolución de fallos

**Paso 9.** Ante cualquier alerta de fallo, el Responsable del Sistema procederá a:

- Diagnosticar la causa.
- Reintentar la ejecución de la copia fallida.
- Si el fallo persiste, escalar al Responsable de la Seguridad y registrar la incidencia.
- Documentar la solución aplicada.

**Paso 10.** Tres fallos consecutivos en el mismo conjunto de datos requieren la apertura de un análisis específico y se reportan en el informe mensual al Comité de Seguridad.

### 6.3 Registros de copias

**Paso 11.** Cada ejecución de copia genera un registro automático que incluye:

- Identificador único de la copia.
- Conjunto de datos copiado.
- Fecha y hora de inicio y fin.
- Tamaño de los datos copiados.
- Hash SHA-256 de la copia.
- Ubicación de almacenamiento.
- Resultado (exitoso, con avisos, fallido).
- Operador o sistema que ejecutó la copia.

## 7. PRUEBAS DE RESTAURACIÓN

### 7.1 Programa de pruebas

**Paso 12.** Las pruebas de restauración se realizarán con la siguiente periodicidad mínima, alineada con la categoría ENS del sistema:

| Tipo de prueba | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Restauración de fichero individual | Trimestral | Mensual | Mensual |
| Restauración de base de datos completa | Semestral | Trimestral | Mensual |
| Restauración de sistema completo (DR) | Anual | Semestral | Trimestral |
| Recuperación de copia inmutable / air-gapped | Anual | Anual | Semestral |

### 7.2 Ejecución de las pruebas

**Paso 13.** Cada prueba se planifica con un **escenario predeterminado** que documenta:

- Conjunto de datos a restaurar.
- Punto en el tiempo objetivo (RPO de prueba).
- Objetivo de tiempo (RTO de prueba).
- Entorno de destino (siempre entorno aislado, nunca productivo).
- Criterios de éxito.

**Paso 14.** Las pruebas se ejecutan en **entorno de laboratorio aislado**, sin interferir con los sistemas productivos.

**Paso 15.** Tras la restauración se verifica la **integridad funcional** del entorno restaurado mediante pruebas de:

- Acceso a los datos.
- Consistencia de las relaciones entre tablas.
- Integridad referencial.
- Funcionamiento de las aplicaciones que consumen los datos.

### 7.3 Documentación de resultados

**Paso 16.** Cada prueba genera un **Informe de Prueba de Restauración** que incluye:

- Identificación de la prueba y fecha.
- Conjunto de datos restaurado.
- Tiempo real de restauración (RTR) frente al objetivo.
- Resultados de las verificaciones de integridad.
- Incidencias detectadas y acciones correctivas.
- Conclusiones y recomendaciones.

**Paso 17.** Los informes se elevan al Comité de Seguridad y se incorporan al expediente del SGSI conforme al procedimiento {{ proyecto.codigo_documento_base }}-221.

### 7.4 Acción correctiva ante fallos

**Paso 18.** Si una prueba falla, se abre **acción correctiva inmediata** que incluya:

- Análisis de la causa raíz.
- Plan de corrección con plazo definido.
- Reverificación tras la corrección.
- Notificación al Comité de Seguridad.

## 8. RESTAURACIÓN OPERATIVA

### 8.1 Solicitud

**Paso 19.** Cualquier solicitud de restauración operativa se canaliza al Responsable del Sistema, indicando:

- Conjunto de datos a restaurar.
- Punto en el tiempo deseado.
- Justificación de la solicitud.
- Impacto previsto de no realizarla.

### 8.2 Autorización

**Paso 20.** La restauración será autorizada por:

- Restauraciones rutinarias (recuperación de fichero individual): Responsable del Sistema.
- Restauraciones de base de datos completa: Responsable de la Seguridad.
- Restauraciones tras incidente grave: Coordinador del ERI conforme al procedimiento {{ proyecto.codigo_documento_base }}-204.

### 8.3 Ejecución

**Paso 21.** La restauración se ejecuta conforme a la guía técnica correspondiente (instrucciones técnicas IT-210-XX), documentando todas las acciones.

**Paso 22.** Tras la restauración, se verifica la integridad y se notifica al solicitante.

### 8.4 Registro

**Paso 23.** Toda restauración operativa se registra en el sistema con identificador único, persona solicitante, autorizador, ejecutor, conjunto de datos restaurado y resultado.

## 9. INDICADORES

| Indicador | Objetivo |
|---|---|
| Tasa de éxito de copias programadas | ≥ 99% |
| Tasa de éxito de pruebas de restauración | 100% |
| RTO real / RTO objetivo | ≤ 1.0 |
| Antigüedad media de la última prueba de restauración por sistema | < periodicidad mínima |
| Conjuntos de datos sin copia offsite | 0 |
| Conjuntos de datos críticos sin copia inmutable | 0 |

## 10. ANEXOS

- **Anexo I:** Inventario de conjuntos de datos y matriz de copia
- **Anexo II:** Plantilla del Informe de Prueba de Restauración
- **Anexo III:** Calendario anual de pruebas de restauración
- **Anexo IV:** Instrucciones técnicas de restauración por sistema (IT-210-XX)

---

**Documento {{ proyecto.codigo_documento_base }}-207 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---

# DOCUMENTO E-IT-001 — PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA

**Materializa las medidas op.exp.2 (Configuración de seguridad) y op.exp.3 (Gestión de la configuración) del Anexo II del ENS** y los controles A.8.9 (Configuration management) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con configuraciones reales comparadas contra una baseline.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-IT-001"
titulo: "Procedimiento de Hardening y Configuración Segura"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
---

# PROCEDIMIENTO DE HARDENING Y CONFIGURACIÓN SEGURA DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-IT-001 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer los criterios técnicos y el método operativo mediante el cual {{ cliente.razon_social }} configura de forma segura los sistemas operativos, bases de datos, aplicaciones, dispositivos de red, servicios cloud y demás componentes tecnológicos comprendidos en el alcance del SGSI, en cumplimiento de las medidas **op.exp.2 (Configuración de seguridad)** y **op.exp.3 (Gestión de la configuración)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los componentes tecnológicos productivos comprendidos en el alcance del SGSI, así como a sus entornos de desarrollo y preproducción cuando estos puedan afectar a la seguridad del entorno productivo.

## 3. PRINCIPIOS

### 3.1 Mínima funcionalidad

Cada sistema se configura con los **servicios, puertos, cuentas, protocolos y funcionalidades estrictamente necesarios** para su función operativa. Todo lo demás debe deshabilitarse o eliminarse.

### 3.2 Configuración segura por defecto

Las configuraciones por defecto del fabricante rara vez son seguras. Toda nueva instalación debe pasar por el proceso de hardening antes de su puesta en producción.

### 3.3 Reproducibilidad

Las configuraciones seguras se documentan mediante **plantillas reproducibles** (preferentemente Infrastructure as Code) que permitan desplegar nuevos sistemas con la misma configuración base de forma automatizada.

### 3.4 Verificación continua

La conformidad con la configuración segura no es un estado puntual sino una propiedad que debe verificarse de forma continua mediante herramientas automatizadas.

## 4. BASELINES DE REFERENCIA

### 4.1 Fuentes de las baselines

Como punto de partida para la elaboración de las baselines internas se utilizarán, en orden de preferencia:

a) Las **guías CCN-STIC de la serie 500** (Productos de Seguridad) y de la serie 600 (Aplicaciones), publicadas por el Centro Criptológico Nacional para los productos específicos cubiertos.

b) Los **CIS Benchmarks** del Center for Internet Security para sistemas operativos, bases de datos, aplicaciones y servicios cloud.

c) Los **STIGs (Security Technical Implementation Guides)** del DISA estadounidense.

d) Las recomendaciones específicas del **fabricante** del producto.

e) Las **plantillas Microsoft Security Baselines** para entornos Windows.

### 4.2 Adaptación a la realidad de la Entidad

**Paso 1.** El Responsable de la Seguridad, con el apoyo del Responsable del Sistema, adaptará las baselines de referencia a la realidad operativa de la Entidad, considerando:

- Compatibilidad con las aplicaciones y servicios productivos.
- Restricciones operativas específicas.
- Riesgo aceptable conforme al análisis del procedimiento {{ proyecto.codigo_documento_base }}-AR-001.

**Paso 2.** Toda divergencia respecto a la baseline de referencia se documentará como **excepción justificada** con el correspondiente análisis de riesgos.

### 4.3 Catálogo de baselines

**Paso 3.** El Responsable de la Seguridad mantendrá un **Catálogo de Baselines** del SGSI que incluya, como mínimo, las siguientes:

| Tipo de sistema | Baseline aplicable |
|---|---|
| Linux servidor (Ubuntu, RHEL, Debian) | CIS Benchmark + adaptaciones |
| Windows Server | CIS Benchmark + Microsoft Security Baseline |
| Estaciones de trabajo Windows | CIS Benchmark + Microsoft Security Baseline |
| Estaciones de trabajo macOS | CIS Benchmark |
| Bases de datos PostgreSQL / MySQL / SQL Server | CIS Benchmark |
| Servidores web (Nginx, Apache, IIS) | CIS Benchmark |
| Contenedores Docker / Kubernetes | CIS Benchmark + ENISA recommendations |
| AWS / Azure / GCP | CIS Benchmark cloud + Well-Architected Framework |
| Dispositivos de red (Cisco, Fortinet) | STIG + recomendaciones del fabricante |
| Productos del CPSTIC del CCN | Guías CCN-STIC específicas |

## 5. PROCESO DE HARDENING DE NUEVOS SISTEMAS

### 5.1 Análisis previo

**Paso 4.** Antes de la instalación de un nuevo sistema, el Responsable del Sistema identifica:

- Tipo de sistema y baseline aplicable.
- Función específica que va a desempeñar.
- Nivel de seguridad exigible conforme a la categoría ENS del servicio que sustenta.
- Excepciones previsibles a la baseline.

### 5.2 Instalación y hardening

**Paso 5.** La instalación se realiza utilizando, cuando sea posible, plantillas Infrastructure as Code (IaC) preconfiguradas con la baseline aplicable.

**Paso 6.** Tras la instalación se aplica el procedimiento de hardening específico documentado en la **Instrucción Técnica IT-219-XX** correspondiente al tipo de sistema, que incluye:

- Eliminación de servicios y software innecesarios.
- Configuración de cuentas: deshabilitar cuentas por defecto, renombrar la administradora local, fijar políticas de contraseñas.
- Configuración del firewall local: regla por defecto DENY, apertura solo de puertos estrictamente necesarios.
- Configuración del sistema de logging conforme al procedimiento {{ proyecto.codigo_documento_base }}-220.
- Configuración del sistema de actualizaciones automáticas conforme al procedimiento {{ proyecto.codigo_documento_base }}-205.
- Configuración del antimalware corporativo cuando proceda.
- Restricciones de protocolos y cifrados (TLS, SSH).
- Eliminación de banners informativos innecesarios.
- Configuración de auditoría.
- Configuración del sincronismo de tiempo con servidor NTP corporativo.

### 5.3 Validación

**Paso 7.** Tras el hardening se ejecuta una **validación automática** mediante herramienta de cumplimiento (CIS-CAT, OpenSCAP, Lynis, Wazuh u otras), que verifica el grado de cumplimiento con la baseline.

**Paso 8.** El umbral mínimo aceptable de cumplimiento es del **85%** para sistemas de categoría BÁSICA y del **90%** para categorías MEDIA y ALTA.

**Paso 9.** Las divergencias se analizan caso por caso:

- Si pueden corregirse, se corrigen y se reverifica.
- Si no pueden corregirse, se documentan como excepciones justificadas.

### 5.4 Aceptación y puesta en producción

**Paso 10.** Una vez validado el hardening, el sistema se pone en producción siguiendo el procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203).

**Paso 11.** Se incorpora al **Inventario de Activos** y al **Inventario de Configuraciones** del SGSI.

## 6. GESTIÓN CONTINUA DE LA CONFIGURACIÓN

### 6.1 Monitorización del cumplimiento

**Paso 12.** El cumplimiento de cada sistema con su baseline se monitoriza de forma **continua o periódica** mediante:

- Agentes de cumplimiento instalados en los sistemas.
- Escaneos programados desde una herramienta centralizada.
- Integración con el SIEM corporativo cuando sea posible.

**Paso 13.** Las desviaciones detectadas generan alertas que son tratadas por el Responsable del Sistema en los siguientes plazos:

| Severidad de la desviación | Plazo máximo de corrección |
|---|---|
| Crítica | 24 horas |
| Alta | 7 días |
| Media | 30 días |
| Baja | 90 días |

### 6.2 Cambios autorizados

**Paso 14.** Cualquier modificación intencional de la configuración debe gestionarse a través del procedimiento de gestión de cambios ({{ proyecto.codigo_documento_base }}-203), actualizándose la documentación del sistema y, cuando proceda, la propia baseline.

### 6.3 Cambios no autorizados (drift)

**Paso 15.** Cuando se detecta una modificación no autorizada de la configuración (drift), el Responsable de la Seguridad:

- Analiza el cambio y determina su origen.
- Decide si se trata de un incidente que requiera activar el procedimiento {{ proyecto.codigo_documento_base }}-204.
- Restaura la configuración correcta.
- Refuerza los controles para evitar la repetición.

## 7. REVISIÓN PERIÓDICA DE LAS BASELINES

**Paso 16.** Las baselines se revisan al menos **anualmente** por el Responsable de la Seguridad, atendiendo a:

- Actualizaciones de las baselines de referencia (CIS, STIG, CCN-STIC).
- Nuevas vulnerabilidades publicadas.
- Lecciones aprendidas de incidentes.
- Nuevas necesidades operativas.
- Cambios en el inventario tecnológico.

**Paso 17.** Las modificaciones aprobadas se aplican a los sistemas existentes según el calendario que apruebe el Comité de Seguridad, priorizando los sistemas de mayor categoría.

## 8. INDICADORES

| Indicador | Objetivo |
|---|---|
| Sistemas con baseline aplicada | 100% |
| Cumplimiento medio con la baseline (todos los sistemas) | ≥ 90% |
| Desviaciones críticas abiertas | 0 |
| Antigüedad media de la última verificación | < 30 días |
| Excepciones documentadas y autorizadas | 100% |
| Drift no autorizado detectado y resuelto en plazo | 100% |

## 9. ANEXOS

- **Anexo I:** Catálogo de Baselines del SGSI
- **Anexo II:** Plantilla de Excepción a la Baseline
- **Anexo III:** Formulario de Validación de Hardening
- **Anexo IV:** Listado de Instrucciones Técnicas IT-219-XX

---

**Documento {{ proyecto.codigo_documento_base }}-IT-001 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
