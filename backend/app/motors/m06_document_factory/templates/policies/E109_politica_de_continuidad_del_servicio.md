# DOCUMENTO E-109 — POLÍTICA DE CONTINUIDAD DEL SERVICIO

**Materializa las medidas op.cont.1 a op.cont.4 del Anexo II del ENS** y los controles A.5.29, A.5.30 y A.8.14 de ISO 27001:2022. Es la política que el auditor ENAC pide siempre demostrada con un test real de restore.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-109"
titulo: "Política de Continuidad del Servicio"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE CONTINUIDAD DEL SERVICIO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-109 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y compromisos de {{ cliente.razon_social }} en materia de continuidad de los servicios y recuperación ante desastres, con la finalidad de garantizar que, ante una disrupción significativa, los servicios esenciales puedan mantenerse o restaurarse en niveles aceptables y dentro de los plazos comprometidos con las partes interesadas.

Esta Política da cumplimiento a las medidas **op.cont.1 (Análisis de impacto)**, **op.cont.2 (Plan de continuidad)**, **op.cont.3 (Pruebas periódicas)** y **op.cont.4 (Medios alternativos)** del Anexo II del Real Decreto 311/2022, así como, supletoriamente, a las directrices de la norma UNE-EN ISO 22301:2019 sobre Sistemas de Gestión de la Continuidad del Negocio.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a la totalidad de los servicios y sistemas comprendidos en el alcance del SGSI, conforme se define en el documento {{ proyecto.codigo_documento_base }}-100, y a todos los procesos, recursos humanos, infraestructuras, terceros y elementos de cualquier naturaleza que sean necesarios para la prestación de dichos servicios.

## 3. PRINCIPIOS DE CONTINUIDAD

### 3.1 Proporcionalidad

Las medidas de continuidad serán proporcionales a la criticidad de los servicios, valorada conforme a los criterios del Anexo I del ENS y al análisis de impacto en el negocio.

### 3.2 Anticipación

La Entidad actuará anticipándose a los escenarios de disrupción razonablemente previsibles, mediante la identificación temprana de amenazas, la evaluación de su impacto potencial y la planificación de las respuestas.

### 3.3 Recuperación priorizada

En caso de disrupción, la recuperación de los servicios se realizará atendiendo a su criticidad, comenzando por los servicios esenciales y continuando por los menos críticos hasta restablecer la operación normal.

### 3.4 Mejora continua

Los planes de continuidad serán objeto de revisión, prueba y mejora continua, integrándose en el ciclo PDCA del SGSI.

## 4. ANÁLISIS DE IMPACTO EN EL NEGOCIO [op.cont.1]

### 4.1 Realización del análisis

La Entidad realizará y mantendrá actualizado un **Análisis de Impacto en el Negocio** (en adelante, "BIA", del inglés *Business Impact Analysis*) que identifique:

a) Los procesos y servicios críticos para el cumplimiento de la misión de la Entidad.

b) Los recursos humanos, tecnológicos, físicos y de información necesarios para su prestación.

c) El impacto que produciría su interrupción a lo largo del tiempo, expresado en términos operativos, económicos, reputacionales, legales y sobre las partes interesadas.

d) Los **objetivos de tiempo de recuperación** (RTO – *Recovery Time Objective*) máximos admisibles para cada servicio crítico.

e) Los **objetivos de punto de recuperación** (RPO – *Recovery Point Objective*) máximos admisibles para los datos asociados a cada servicio crítico.

f) Las dependencias internas y externas (proveedores, terceros, infraestructuras compartidas).

### 4.2 Periodicidad

El BIA será revisado al menos con carácter **anual** y, con carácter extraordinario, cuando se produzcan cambios significativos en los servicios prestados, en la organización, en la infraestructura o en el contexto operativo de la Entidad.

### 4.3 Aprobación

El BIA será elaborado por el Responsable de la Seguridad en coordinación con los Responsables del Servicio y de la Información, y aprobado por el Comité de Seguridad.

## 5. PLAN DE CONTINUIDAD DEL SERVICIO [op.cont.2]

### 5.1 Elaboración

A partir de los resultados del BIA, la Entidad elaborará y mantendrá actualizado un **Plan de Continuidad del Servicio** (en adelante, "PCS"), que documentará:

a) La estrategia general de continuidad adoptada para cada servicio crítico.

b) Los procedimientos operativos para la activación, gestión y desactivación del Plan.

c) Los roles y responsabilidades del Equipo de Continuidad.

d) Los recursos alternativos previstos (instalaciones, equipos, conectividad, personal, proveedores).

e) Las comunicaciones internas y externas durante una situación de disrupción.

f) Los criterios y procedimientos para la vuelta a la normalidad.

### 5.2 Plan de Recuperación ante Desastres

El PCS se complementará con un **Plan de Recuperación ante Desastres** (DRP, *Disaster Recovery Plan*), que detallará los procedimientos técnicos específicos para la restauración de los sistemas e infraestructuras tecnológicas tras una disrupción.

### 5.3 Aprobación

El PCS y el DRP serán aprobados por el Comité de Seguridad y elevados a {{ cliente.organo_aprobador_politicas }} para su conocimiento.

## 6. MEDIOS ALTERNATIVOS [op.cont.4]

### 6.1 Redundancia

Para los servicios cuya criticidad lo justifique, la Entidad mantendrá medios alternativos que permitan su prestación en caso de fallo del entorno principal. Estos medios podrán incluir:

a) **Redundancia de hardware**: servidores, sistemas de almacenamiento y elementos de red duplicados o en alta disponibilidad.

b) **Redundancia de comunicaciones**: enlaces de red alternativos con proveedores diferentes.

c) **Redundancia de instalaciones**: centros de proceso de datos alternativos, ubicados a distancia geográfica suficiente del principal.

d) **Redundancia de proveedores**: existencia de proveedores alternativos para servicios externalizados críticos.

e) **Copias de seguridad** (backups) almacenadas en ubicaciones independientes y protegidas, con políticas de retención y rotación adecuadas.

### 6.2 Política de copias de seguridad

Las copias de seguridad de la información y los sistemas se realizarán conforme a los siguientes criterios mínimos:

| Categoría ENS del sistema | Frecuencia mínima de respaldo | Retención mínima | Pruebas de restauración |
|---|---|---|---|
| BÁSICA | Semanal | 1 mes | Anual |
| MEDIA | Diaria | 3 meses | Semestral |
| ALTA | Diaria + incrementos | 6 meses | Trimestral |

Las copias se almacenarán cifradas, en ubicación física separada de los sistemas de origen, y serán objeto de pruebas periódicas de restauración para verificar su integridad y operatividad.

## 7. PRUEBAS PERIÓDICAS [op.cont.3]

### 7.1 Programa de pruebas

La Entidad mantendrá un programa anual de pruebas del PCS y del DRP que incluya, al menos, los siguientes tipos de ejercicio:

a) **Revisión documental**: revisión periódica de los planes y procedimientos para verificar su vigencia y consistencia.

b) **Walkthrough**: ejercicio teórico en mesa con los miembros del Equipo de Continuidad para revisar paso a paso la respuesta a un escenario simulado.

c) **Prueba parcial técnica**: ejercicio práctico de restauración de un componente o servicio concreto, sin afectar a la operación.

d) **Prueba completa**: ejercicio práctico de activación de los medios alternativos y restauración íntegra del servicio en el entorno alternativo.

### 7.2 Periodicidad mínima

| Tipo de prueba | Categoría BÁSICA | Categoría MEDIA | Categoría ALTA |
|---|---|---|---|
| Revisión documental | Anual | Semestral | Semestral |
| Walkthrough | Anual | Anual | Semestral |
| Prueba parcial técnica | Bienal | Anual | Semestral |
| Prueba completa | Bienal | Bienal | Anual |

### 7.3 Documentación de las pruebas

De cada prueba se elaborará un informe que recoja los objetivos, el escenario, los participantes, las acciones realizadas, los tiempos medidos, los problemas detectados y las acciones correctivas a emprender. Los informes serán elevados al Comité de Seguridad.

## 8. EQUIPO DE CONTINUIDAD

La Entidad constituye un **Equipo de Continuidad** cuya composición incluirá, al menos, al Responsable de la Seguridad, al Responsable del Sistema, al Responsable del Servicio y a una persona con capacidad de decisión sobre los recursos económicos necesarios.

En situaciones de **crisis** (incidentes de nivel CRÍTICO conforme al documento {{ proyecto.codigo_documento_base }}-108), el Equipo de Continuidad se integrará en el Comité de Crisis, asumiendo la coordinación operativa de la respuesta.

## 9. CONTINUIDAD DE PROVEEDORES CRÍTICOS

La Entidad identificará a los proveedores cuyos servicios resulten críticos para la prestación de sus propios servicios e incluirá en los contratos con estos proveedores:

a) Compromisos sobre continuidad del servicio y recuperación ante desastres.

b) Obligación de notificación inmediata de cualquier disrupción que pueda afectar a la Entidad.

c) Derecho de auditoría sobre las medidas de continuidad del proveedor.

d) Acuerdos de nivel de servicio (SLA) consistentes con los RTO y RPO de la Entidad.

## 10. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo, y en todo caso tras cualquier prueba completa del Plan que evidencie deficiencias significativas.

---

**Documento {{ proyecto.codigo_documento_base }}-109 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```
