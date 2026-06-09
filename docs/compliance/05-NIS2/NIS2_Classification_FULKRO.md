---
title: Análisis de Clasificación bajo la Directiva NIS2
codigo: FULKRO-NIS2-CLASS-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Anual + cambio de escala
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Público · referenciable Trust Center
marco_normativo:
  - Directiva (UE) 2022/2555 (NIS2)
  - Real Decreto-ley 7/2022 (transposición parcial)
---

# Análisis de Clasificación de FULKRO bajo la Directiva NIS2

## 1. Análisis de aplicabilidad conforme al artículo 3 de la Directiva NIS2

### 1.1 Sector de actividad

A los efectos del Anexo I de la Directiva (UE) 2022/2555, FULKRO desarrolla su actividad en el sector identificado como "Infraestructuras digitales" (sector 8 del Anexo I), en tanto desarrolla actividades de consultoría en tecnologías de la información y opera una plataforma SaaS de carácter interno.

### 1.2 Naturaleza de la actividad

FULKRO desarrolla las siguientes actividades:

a) Servicios de consultoría en materia de Esquema Nacional de Seguridad, conforme al Real Decreto 311/2022.

b) Plataforma tecnológica SaaS desplegada de manera interna (no comercializada a terceros como producto SaaS independiente).

### 1.3 Dimensión de la organización

A los efectos del análisis de aplicabilidad, se hacen constar los siguientes parámetros dimensionales:

a) Número de empleados: uno (Marcos Mata García, en condición de trabajador autónomo titular único).

b) Sub-procesadores externos contratados: cinco (Hetzner, Postmark, Anthropic, 360dialog, MinIO en régimen de autoalojamiento).

## 2. Umbrales de aplicabilidad

### 2.1 Umbrales contemplados en la Directiva NIS2

La Directiva NIS2 establece, con carácter general, umbrales mínimos de aplicabilidad referidos a la dimensión de la organización:

a) Empresas medianas: cincuenta empleados o más, o un volumen de negocio anual igual o superior a diez millones de euros.

b) Empresas pequeñas y micro-empresas que operen en sectores críticos por su naturaleza.

### 2.2 Verificación de umbrales para FULKRO

a) Empleados: uno (inferior a cincuenta).

b) Volumen de negocio: en fase de inicio de actividad, inferior a diez millones de euros anuales.

### 2.3 Conclusión del análisis

Del análisis de los umbrales establecidos por la Directiva NIS2 resulta que FULKRO **no constituye actualmente entidad esencial ni entidad importante** en el sentido estricto del artículo 3 de dicha Directiva, en atención a su condición de micro-organización.

## 3. Alineamiento voluntario con las medidas del artículo 21 NIS2

Sin perjuicio de la no concurrencia de los umbrales formales de obligatoriedad, FULKRO adopta de manera voluntaria las mejores prácticas de la Directiva NIS2, mediante la implantación de las siguientes medidas:

### 3.1 Publicación de fichero security.txt conforme a RFC 9116

Se publica un fichero conforme al estándar RFC 9116 en la ruta `/.well-known/security.txt` del dominio fulkro.es.

### 3.2 Procedimiento de divulgación coordinada de vulnerabilidades

Se implanta procedimiento de divulgación coordinada de vulnerabilidades conforme al estándar ISO/IEC 29147:2018, según se detalla en el documento FULKRO-NIS2-VULN-001.

### 3.3 Seguridad de la cadena de suministro

Se implanta procedimiento de revisión periódica de los Acuerdos de Encargo de Tratamiento con sub-procesadores, conforme se detalla en el documento FULKRO-NIS2-SUPPLY-001.

### 3.4 Procedimiento de notificación de incidentes 24h+72h+1 mes

Se mantiene operativo el procedimiento de notificación de incidentes con el cadenciado de alerta temprana en veinticuatro horas, notificación formal en setenta y dos horas e informe final en un mes, conforme se detalla en el documento FULKRO-NIS2-NOT-001.

## 4. Disparadores prospectivos de reclasificación

Procederá la revisión de la clasificación actual y la consiguiente eventual reclasificación de FULKRO como entidad esencial o entidad importante en los siguientes supuestos:

### 4.1 Crecimiento de la organización

a) Incremento de empleados por encima del umbral de cincuenta.

b) Incremento del volumen de negocio anual por encima del umbral de diez millones de euros.

### 4.2 Naturaleza del cliente

Aceptación de cliente perteneciente a sector crítico cuya operación dependa de manera significativa de los servicios prestados por FULKRO, supuesto que requerirá una evaluación caso por caso.

## 5. Plan operativo en caso de aplicación efectiva

En el caso de que de la revisión periódica o extraordinaria resulte la aplicabilidad efectiva de la Directiva NIS2 a FULKRO, se ejecutará el siguiente plan operativo:

a) Notificación de la condición de entidad esencial o entidad importante a la autoridad nacional competente (INCIBE-CERT, en el régimen vigente).

b) Registro en el padrón nacional de entidades NIS2 de España.

c) Realización de auditoría externa de conformidad con las medidas técnicas y organizativas exigidas.

d) Formalización de la designación de un Director de Seguridad de la Información (CISO) en régimen propio o externo.

## 6. Marco normativo de referencia

a) Directiva (UE) 2022/2555 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, relativa a las medidas destinadas a garantizar un elevado nivel común de ciberseguridad en toda la Unión.

b) Real Decreto-ley 7/2022, de 29 de marzo, sobre requisitos para garantizar la seguridad de las redes y sistemas de información de quinta generación.

c) Punto de contacto nacional: INCIBE-CERT, accesible en la dirección de correo electrónico incidencias@incibe-cert.es y en el número de teléfono 017.

## 7. Revisión

La presente análisis se revisará con periodicidad anual y, en todo caso, ante cualquier modificación sustancial de las circunstancias de aplicabilidad que pudiera resultar relevante a los efectos del régimen NIS2.

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
