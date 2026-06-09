# DOCUMENTO E-205 — PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES

**Materializa la medida op.exp.4 del Anexo II del ENS** (Mantenimiento) y los controles A.8.8 (Gestión de vulnerabilidades técnicas) y A.8.32 (Gestión de cambios) de ISO/IEC 27001:2022. Es el procedimiento que el auditor pide demostrar con un escaneo real reciente y un parche desplegado en el último mes.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-205"
titulo: "Procedimiento de Gestión de Vulnerabilidades y Parches"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100, {{ proyecto.codigo_documento_base }}-107"
---

# PROCEDIMIENTO DE GESTIÓN DE VULNERABILIDADES Y PARCHES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-205 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el método mediante el cual {{ cliente.razon_social }} identifica, valora, prioriza y mitiga las vulnerabilidades técnicas que afectan a sus sistemas de información, así como gestiona la aplicación de los parches de seguridad publicados por los fabricantes y comunidades de software, en cumplimiento de la medida **op.exp.4 (Mantenimiento)** del Anexo II del Real Decreto 311/2022.

## 2. ALCANCE

Aplica a todos los sistemas, servicios, aplicaciones, dispositivos de red, sistemas operativos, bases de datos, librerías y componentes de software comprendidos en el alcance del SGSI, ya sean operados directamente por la Entidad o por terceros bajo su responsabilidad.

## 3. FUENTES DE INFORMACIÓN DE VULNERABILIDADES

El Responsable de la Seguridad mantendrá monitorizadas, al menos, las siguientes fuentes de información sobre vulnerabilidades:

a) **CCN-CERT** (avisos y vulnerabilidades): https://www.ccn-cert.cni.es/seguridad-al-dia.html

b) **INCIBE-CERT**: https://www.incibe.es/incibe-cert/avisos

c) **NVD (National Vulnerability Database)** del NIST: https://nvd.nist.gov

d) **CISA Known Exploited Vulnerabilities Catalog**: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

e) **Boletines de seguridad de los fabricantes** del software utilizado.

f) **Listas de seguridad** de las comunidades open source relevantes.

g) **Informes propios** del escáner de vulnerabilidades corporativo.

## 4. ESCANEO DE VULNERABILIDADES

### 4.1 Escaneo periódico

| Activo | Periodicidad mínima | Herramienta tipo |
|---|---|---|
| Servidores expuestos a Internet | Semanal | Escáner externo (OpenVAS, Nessus) |
| Servidores internos | Mensual | Escáner autenticado |
| Estaciones de trabajo | Mensual | Agente endpoint |
| Aplicaciones web | Trimestral | DAST |
| Código fuente propio | Por release | SAST + SCA |
| Contenedores e imágenes | Por build | Trivy o equivalente |
| Configuración cloud | Mensual | CSPM |

### 4.2 Escaneo extraordinario

Se realizarán escaneos extraordinarios cuando:

a) Se publique una vulnerabilidad crítica que afecte al inventario tecnológico de la Entidad.

b) Se incorpore al inventario un nuevo activo significativo.

c) Se produzca un cambio de configuración importante.

d) Se reciba una alerta del CCN-CERT o de cualquier otra fuente cualificada.

### 4.3 Pentesting

Con periodicidad **anual** se realizará un test de intrusión externo por una entidad independiente, conforme a las exigencias de las medidas mp.s.4 (Aceptación y puesta en servicio) y op.exp.4 del ENS para sistemas de categoría MEDIA o superior.

## 5. CLASIFICACIÓN Y PRIORIZACIÓN DE VULNERABILIDADES

### 5.1 Escala de criticidad

Las vulnerabilidades se clasifican atendiendo a su puntuación CVSS (Common Vulnerability Scoring System), conforme a la siguiente escala:

| Nivel | CVSS v3.x | Descripción |
|---|---|---|
| **CRÍTICA** | 9.0 - 10.0 | Vulnerabilidad explotable remotamente sin autenticación, con alto impacto |
| **ALTA** | 7.0 - 8.9 | Vulnerabilidad explotable con condiciones limitadas o impacto significativo |
| **MEDIA** | 4.0 - 6.9 | Vulnerabilidad con condiciones de explotación complejas o impacto moderado |
| **BAJA** | 0.1 - 3.9 | Vulnerabilidad con impacto menor o muy difícil de explotar |

### 5.2 Factores agravantes

La criticidad inicial se **eleva** automáticamente cuando concurre alguna de las siguientes circunstancias:

a) La vulnerabilidad está incluida en el catálogo CISA KEV (Known Exploited Vulnerabilities), indicando explotación activa en el mundo real.

b) Existe **exploit público** disponible.

c) El activo afectado tiene clasificación **ALTA** en cualquier dimensión del ENS.

d) El activo está expuesto a Internet o accesible desde redes no controladas.

e) El activo soporta servicios esenciales conforme al BIA del Plan de Continuidad.

### 5.3 Factores atenuantes

La criticidad inicial puede **reducirse** cuando:

a) El activo afectado está protegido por capas de defensa adicionales que dificultan la explotación.

b) La vulnerabilidad requiere acceso físico al activo, no factible para atacantes externos.

c) Existen mitigaciones temporales eficaces ya aplicadas (workarounds documentados por el fabricante).

## 6. PLAZOS DE APLICACIÓN DE PARCHES

| Criticidad efectiva | Plazo máximo de aplicación |
|---|---|
| **CRÍTICA con explotación activa** | 24 horas |
| **CRÍTICA** | 7 días naturales |
| **ALTA** | 15 días naturales |
| **MEDIA** | 60 días naturales |
| **BAJA** | 180 días naturales o siguiente ciclo de mantenimiento |

Estos plazos son **máximos** y se cuentan desde la publicación oficial del parche por el fabricante o desde la disponibilidad de una mitigación.

## 7. CICLO DE GESTIÓN DEL PARCHE

### 7.1 Identificación

**Responsable:** Responsable de la Seguridad.

**Acciones:**

1. Revisión diaria de las fuentes de información de vulnerabilidades.

2. Cruce con el Inventario de Activos para identificar las vulnerabilidades que afectan al entorno propio.

3. Registro en el **Sistema de Gestión de Vulnerabilidades** del SGSI.

### 7.2 Análisis y priorización

**Acciones:**

4. Cálculo de la criticidad efectiva conforme al apartado 5.

5. Determinación del plazo máximo de aplicación conforme al apartado 6.

6. Asignación al Responsable del Sistema con instrucciones específicas.

### 7.3 Pruebas

**Responsable:** Responsable del Sistema.

**Acciones:**

7. Antes del despliegue en producción, los parches se prueban en un **entorno de preproducción** equivalente al productivo en la medida de lo posible, verificando:

- Aplicación correcta del parche.
- No regresión funcional.
- Compatibilidad con las personalizaciones existentes.

8. Cuando la criticidad CRÍTICA con explotación activa exija aplicación inmediata, las pruebas pueden reducirse o realizarse en paralelo, asumiendo el riesgo bajo decisión expresa del Responsable de la Seguridad.

### 7.4 Despliegue

9. El despliegue se realiza conforme al **procedimiento de gestión de cambios** ({{ proyecto.codigo_documento_base }}-203), con la autorización correspondiente al riesgo del cambio.

10. Para parches CRÍTICOS, la autorización puede ser **abreviada** mediante el procedimiento de cambio de emergencia.

11. El despliegue se documenta indicando:

- Fecha y hora exacta.
- Sistemas afectados.
- Persona que ejecuta el despliegue.
- Parche aplicado (referencia del fabricante).
- Resultado.

### 7.5 Verificación

12. Tras el despliegue, se verifica que el parche se ha aplicado correctamente, mediante:

- Comprobación manual o automatizada del número de versión.
- Re-escaneo de la vulnerabilidad para confirmar su mitigación.
- Verificación del funcionamiento del servicio afectado.

13. La verificación se documenta en el Sistema de Gestión de Vulnerabilidades.

### 7.6 Cierre

14. La vulnerabilidad se marca como **MITIGADA** o **CERRADA** en el sistema, registrando la fecha y la persona que verifica el cierre.

## 8. EXCEPCIONES

15. Cuando no sea técnicamente posible o económicamente proporcionado aplicar un parche en plazo, se gestionará como **excepción** conforme al apartado 9 de la Política {{ proyecto.codigo_documento_base }}-100, documentando:

- Vulnerabilidad afectada.
- Motivo de la excepción.
- Riesgo asumido.
- Mitigaciones compensatorias adoptadas.
- Plazo máximo de la excepción.
- Plan para su resolución definitiva.

16. Las excepciones requieren autorización del Responsable de la Seguridad y, para vulnerabilidades CRÍTICAS o ALTAS, del Comité de Seguridad.

## 9. SISTEMAS LEGACY SIN SOPORTE

17. Los sistemas que dejan de recibir soporte del fabricante (end-of-life) serán identificados con anticipación y se planificará su sustitución o migración.

18. Cuando no sea posible su sustitución inmediata, se aplicarán **medidas compensatorias reforzadas**:

- Aislamiento de red.
- Monitorización intensificada.
- Restricción máxima de accesos.
- Plan documentado de salida con plazos.

## 10. INDICADORES

| Indicador | Objetivo |
|---|---|
| Vulnerabilidades CRÍTICAS abiertas > plazo | 0 |
| Vulnerabilidades ALTAS abiertas > plazo | < 5 |
| Tiempo medio de aplicación parches CRÍTICOS | < 7 días |
| Cobertura del escaneo (activos escaneados / inventariados) | ≥ 95% |
| Excepciones vigentes documentadas | 100% |

## 11. ANEXOS

- **Anexo I:** Plantilla del Informe Mensual de Vulnerabilidades
- **Anexo II:** Formulario de Excepción de Parcheo
- **Anexo III:** Lista de fuentes de información monitorizadas
- **Anexo IV:** Calendario de escaneos programados

---

**Documento {{ proyecto.codigo_documento_base }}-205 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```
