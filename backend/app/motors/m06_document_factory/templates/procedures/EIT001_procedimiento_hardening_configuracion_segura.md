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
