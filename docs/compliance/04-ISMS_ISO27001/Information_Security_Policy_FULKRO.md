---
title: Política de Seguridad de la Información
codigo: FULKRO-ISMS-POL-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · referenciable Trust Center
marco_normativo:
  - ISO/IEC 27001:2022
  - Reglamento (UE) 2016/679 (RGPD)
  - Ley Orgánica 3/2018 (LOPDGDD)
  - Real Decreto 311/2022 (ENS)
  - Directiva (UE) 2022/2555 (NIS2)
---

# Política de Seguridad de la Información de FULKRO

## 1. Objeto y alcance

La presente Política constituye el documento rector del Sistema de Gestión de la Seguridad de la Información (SGSI) de FULKRO, conforme al marco metodológico establecido por la norma UNE-EN ISO/IEC 27001:2022.

El alcance de la Política comprende:

a) La plataforma tecnológica FULKRO en su totalidad: componentes de backend, frontend, infraestructura de datos, almacenamiento de objetos, sistema de firma criptográfica y los treinta motores funcionales (M01 a M30) más M31 (WhatsApp Business) y M32 (Capabilities).

b) Las operaciones de consultoría en materia de Esquema Nacional de Seguridad (Real Decreto 311/2022) prestadas a clientes en territorio español.

c) La totalidad de los datos personales, datos de negocio y datos operacionales tratados en el ejercicio de la actividad, en condición de responsable o de encargado del tratamiento conforme proceda.

d) Las relaciones contractuales con los cinco sub-procesadores activos identificados en el Listado de Sub-procesadores de FULKRO.

La Política es de aplicación obligatoria para Marcos Mata García en su condición de titular único de la actividad y administrador único de la plataforma, así como para todos los sub-procesadores conforme a los términos específicos de cada Acuerdo de Encargo de Tratamiento (DPA).

## 2. Términos y definiciones

A los efectos de la presente Política, se entenderá por:

**Confidencialidad, Integridad y Disponibilidad (CIA)**: propiedades fundamentales de la seguridad de la información, conforme a la definición proporcionada por la norma UNE-EN ISO/IEC 27000:2022.

**Activo de información**: cualquier elemento que tenga valor para la organización, incluyendo datos, software, hardware, servicios, personas, intangibles y reputación, conforme a la definición de la norma UNE-EN ISO/IEC 27000:2022.

**Riesgo**: efecto de la incertidumbre sobre los objetivos de seguridad, cuantificado como el producto de la probabilidad de ocurrencia por el impacto resultante (UNE-EN ISO/IEC 27005:2022).

**Amenaza**: causa potencial de un incidente no deseado que pueda ocasionar daño a un activo o conjunto de activos.

**Vulnerabilidad**: debilidad de un activo o de un control de seguridad que pueda ser explotada por una o más amenazas.

**Salvaguarda o control de seguridad**: medida adoptada para modificar el riesgo, conforme al catálogo del Anexo A de la norma UNE-EN ISO/IEC 27001:2022.

**Incidente de seguridad**: ocurrencia única o serie de ocurrencias de eventos de seguridad inesperados o no deseados que comprometen, con probabilidad significativa, las operaciones de la organización y amenazan la seguridad de la información.

**Evento de seguridad**: ocurrencia identificada del estado de un sistema, servicio o red que indica una posible violación de la política de seguridad de la información o el fallo de salvaguardas, o una situación previamente desconocida que pueda ser relevante para la seguridad.

## 3. Roles y responsabilidades

### 3.1 Marcos Mata García

Como titular único de la actividad y administrador único de la plataforma FULKRO, Marcos Mata García asume simultáneamente las siguientes funciones, con carácter interino y hasta la formalización del modelo organizativo definitivo previsto en el plan de delegación correspondiente:

a) Responsable de Seguridad de la Información (CISO interim).
b) Delegado de Protección de Datos (DPO interim) conforme al análisis de obligación documentado en el procedimiento FULKRO-LOPDGDD-DPO-001.
c) Administrador técnico único de la plataforma, con acceso privilegiado completo bajo el principio de mínimo privilegio aplicado al ámbito de su responsabilidad.

### 3.2 Sub-procesadores

Los sub-procesadores asumen las responsabilidades específicas establecidas en cada Acuerdo de Encargo de Tratamiento (DPA), conforme al artículo 28 del Reglamento (UE) 2016/679, y se sujetan a las obligaciones de seguridad, confidencialidad y notificación de incidentes derivadas de sus respectivos marcos contractuales.

### 3.3 Plan de delegación

Está prevista la separación funcional de los roles de Responsable de Seguridad de la Información y Delegado de Protección de Datos en el cuarto trimestre del año 2026, mediante la designación de un Delegado de Protección de Datos externo certificado, conforme se detalla en el documento FULKRO-LOPDGDD-DPO-001.

## 4. Principios rectores

La gestión de la seguridad de la información en FULKRO se rige por los siguientes principios:

### 4.1 Confidencialidad

a) Cifrado en tránsito mediante el protocolo TLS versión 1.3, con configuración restringida a suites criptográficas seguras y prohibición expresa de versiones obsoletas.

b) Cifrado en reposo mediante Transparent Data Encryption (TDE) en PostgreSQL y cifrado AES-256 aplicado al almacenamiento de objetos en MinIO.

c) Aislamiento multi-tenant mediante Row Level Security (RLS) en PostgreSQL, con cobertura objetivo del cien por ciento sobre tablas con datos de cliente identificables.

### 4.2 Integridad

a) Firma criptográfica Ed25519 aplicada a todos los documentos generados con efectos jurídicos frente al cliente, conforme al sistema M5 de FULKRO.

b) Registros de auditoría continuos mediante PostgreSQL pgAudit y la tabla audit_logs, con cadenas de hash para garantizar la no alteración a posteriori.

c) Verificación de integridad de copias de seguridad mediante comprobación semestral obligatoria.

### 4.3 Disponibilidad

a) Tiempo Objetivo de Recuperación (RTO) establecido en cuatro horas.

b) Punto Objetivo de Recuperación (RPO) establecido en veinticuatro horas.

c) Esquema de copias de seguridad estratificado: diarias durante treinta días, archivo mensual durante doce meses y almacenamiento en frío durante siete años para cumplir con la obligación de retención del artículo 24.1 del Real Decreto 311/2022.

## 5. Compromiso de la dirección

La dirección de FULKRO, en la persona de su administrador único, asume los siguientes compromisos en relación con el Sistema de Gestión de la Seguridad de la Información:

a) Asignación de los recursos necesarios para la implantación, mantenimiento y mejora continua del SGSI.

b) Mejora continua a través de la revisión anual obligatoria de la presente Política y de la documentación derivada, así como de la incorporación sistemática de las lecciones aprendidas en cada incidente o auditoría conforme al patrón de cementación documental (LECCIÓN-OPS).

c) Comunicación y sensibilización en materia de seguridad mediante la publicación de un fichero security.txt conforme al estándar RFC 9116, la habilitación de un canal específico de contacto con el Delegado de Protección de Datos y la mantención de un Trust Center accesible al público.

d) Cumplimiento de los requisitos legales y contractuales aplicables, conforme al marco normativo identificado en la sección 6.

## 6. Marco normativo de referencia

La presente Política se fundamenta y se desarrolla en el siguiente marco normativo:

a) Norma UNE-EN ISO/IEC 27001:2022, "Tecnología de la información. Técnicas de seguridad. Sistemas de gestión de la seguridad de la información. Requisitos", y su Anexo A relativo a los noventa y tres controles de seguridad.

b) Reglamento (UE) 2016/679 del Parlamento Europeo y del Consejo, de 27 de abril de 2016, relativo a la protección de las personas físicas en lo que respecta al tratamiento de datos personales y a la libre circulación de estos datos (Reglamento General de Protección de Datos, RGPD).

c) Ley Orgánica 3/2018, de 5 de diciembre, de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD).

d) Real Decreto 311/2022, de 3 de mayo, por el que se regula el Esquema Nacional de Seguridad (ENS).

e) Directiva (UE) 2022/2555 del Parlamento Europeo y del Consejo, de 14 de diciembre de 2022, relativa a las medidas destinadas a garantizar un elevado nivel común de ciberseguridad en toda la Unión (NIS2).

f) Norma UNE-EN ISO/IEC 27002:2022, "Tecnología de la información. Técnicas de seguridad. Código de prácticas para los controles de seguridad de la información".

g) Metodología MAGERIT versión 3.0, "Metodología de Análisis y Gestión de Riesgos de los Sistemas de Información", publicada por el Centro Criptológico Nacional.

## 7. Aprobación y revisión

La presente Política fue aprobada por el órgano competente de FULKRO en fecha 12 de mayo de 2026.

Se establece una revisión obligatoria con periodicidad anual, fijándose la próxima revisión ordinaria para el mes de mayo de 2027.

Procederá adicionalmente la revisión extraordinaria de la presente Política en los siguientes supuestos:

a) Acaecimiento de un incidente de seguridad de clasificación HIGH conforme al Plan de Respuesta ante Incidentes.

b) Modificación sustancial de la arquitectura técnica de la plataforma FULKRO.

c) Incorporación o sustitución de sub-procesadores que afecte a procesos críticos.

d) Modificación del marco normativo aplicable que requiera actualización de las medidas de seguridad implantadas.

e) Resultados de auditoría interna o externa que evidencien necesidad de actualización.

## 8. Aprobación

**Firma**: Marcos Mata García
**Cargo**: Responsable de Seguridad de la Información (interim)
**Fecha**: 12 de mayo de 2026

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
