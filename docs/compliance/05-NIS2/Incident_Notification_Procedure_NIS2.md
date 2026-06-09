---
title: Procedimiento de Notificación de Incidentes conforme a la Directiva NIS2
codigo: FULKRO-NIS2-NOT-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor
marco_normativo:
  - Directiva (UE) 2022/2555 (NIS2) Artículo 23
  - Real Decreto-ley 7/2022 (transposición parcial)
---

# Procedimiento de Notificación de Incidentes conforme a la Directiva NIS2

## 1. Flujo de notificación 24h + 72h + 1 mes

FULKRO implanta el cadenciado de notificación de incidentes previsto en el artículo 23 de la Directiva (UE) 2022/2555, articulado en tres hitos sucesivos:

a) **Alerta temprana**: dentro del plazo de veinticuatro horas desde la detección del incidente.

b) **Notificación formal del incidente**: dentro del plazo de setenta y dos horas desde la detección.

c) **Informe final**: dentro del plazo de un mes desde la detección.

El presente procedimiento se aplica con carácter voluntario en tanto FULKRO no haya sido formalmente clasificada como entidad esencial o entidad importante conforme al documento FULKRO-NIS2-CLASS-001.

## 2. Alerta temprana (veinticuatro horas)

### 2.1 Activador

El cómputo del plazo de veinticuatro horas se inicia desde el momento de detección del incidente significativo, conforme a los criterios de severidad establecidos en el Plan de Respuesta ante Incidentes (FULKRO-ISMS-IR-BCP-001).

### 2.2 Destinatario

La alerta temprana se dirigirá a INCIBE-CERT, a través de la dirección de correo electrónico **incidencias@incibe-cert.es** y, en su caso, mediante el número de teléfono **017**.

### 2.3 Información mínima

La alerta temprana incluirá, como mínimo, la siguiente información:

a) Identificación de FULKRO como entidad notificante.

b) Tipología preliminar del incidente.

c) Estimación inicial del impacto.

d) Medidas inmediatas de contención adoptadas o en curso de adopción.

### 2.4 Canal de comunicación

La comunicación se efectuará por correo electrónico al canal indicado en la sección 2.2, complementada en su caso por comunicación telefónica para incidentes con elevada urgencia.

## 3. Notificación formal del incidente (setenta y dos horas)

### 3.1 Activador

El cómputo del plazo de setenta y dos horas se inicia desde el momento de detección del incidente significativo.

### 3.2 Contenido del informe

El informe formal incluirá, como mínimo, los siguientes elementos:

a) Clasificación de severidad del incidente (HIGH, MEDIUM o LOW), conforme al Plan de Respuesta ante Incidentes.

b) Identificación de los sistemas afectados y de las categorías de datos comprometidas.

c) Descripción de las medidas de contención aplicadas hasta el momento del informe.

d) Estimación del número de personas afectadas (interesados) y de su localización.

e) Análisis de la existencia de impacto transfronterizo, con indicación, en su caso, de los Estados miembros afectados.

### 3.3 Plantilla

La elaboración del informe formal se basará en la plantilla MJML implementada en el motor M18 para notificación de brechas, adaptada a los requisitos específicos del marco NIS2.

## 4. Informe final (un mes)

### 4.1 Activador

El cómputo del plazo de un mes se inicia desde el momento de detección del incidente significativo.

### 4.2 Contenido del informe final

El informe final comprenderá, como mínimo, los siguientes elementos:

a) Análisis detallado de la causa raíz del incidente.

b) Identificación de las lecciones aprendidas, formalizadas conforme al patrón de cementación documental LECCIÓN-OPS.

c) Descripción de las medidas preventivas adoptadas con efectos prospectivos.

d) Actualización de los controles y políticas afectados.

e) Resumen de la coordinación realizada con los sub-procesadores afectados, en su caso.

## 5. Coordinación con sub-procesadores

### 5.1 Notificación bilateral

En el caso de incidentes que afecten a la cadena de sub-procesadores, FULKRO realizará la notificación bilateral inmediata al sub-procesador afectado, conforme a los términos del correspondiente Acuerdo de Encargo de Tratamiento.

### 5.2 Identificación de responsabilidad compartida

En los supuestos de responsabilidad compartida, se identificará formalmente la distribución de obligaciones de notificación entre FULKRO y el sub-procesador afectado, sin perjuicio de las obligaciones autónomas que pudieran corresponder a cada uno.

### 5.3 Comunicación coordinada a interesados

Cuando proceda la notificación a los interesados afectados, conforme al artículo 34 del Reglamento (UE) 2016/679, FULKRO coordinará la comunicación con el sub-procesador afectado a fin de garantizar la coherencia y completitud de la información proporcionada.

## 6. Referencia normativa

a) Artículo 23 de la Directiva (UE) 2022/2555, relativo a las obligaciones de notificación de incidentes.

b) Real Decreto-ley 7/2022, de 29 de marzo, sobre requisitos para garantizar la seguridad de las redes y sistemas de información de quinta generación, en cuanto al procedimiento nacional de notificación aplicable.

c) Artículo 31 de la Directiva (UE) 2022/2555, relativo a la cooperación con los equipos de respuesta a incidentes de seguridad informática (CSIRTs) y con la Agencia de la Unión Europea para la Ciberseguridad (ENISA).

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
