# DOCUMENTO E-112 — POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES

**Crítica para la cadena de suministro digital.** Materializa las medidas op.ext.1, op.ext.2, op.ext.3 y op.ext.4 (Servicios externos) del Anexo II del ENS, así como los controles A.5.19 a A.5.23 (Information security in supplier relationships) de ISO/IEC 27001:2022. Es la política que el auditor pide para verificar que el Anexo II del ENS se aplica también a los proveedores cloud y a los servicios externalizados, no solo al perímetro propio.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-112"
titulo: "Política de Seguridad en las Relaciones con Proveedores"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
aprobado_por: "{{ cliente.organo_aprobador_politicas }}"
---

# POLÍTICA DE SEGURIDAD EN LAS RELACIONES CON PROVEEDORES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-112 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

El presente documento establece los principios, criterios y obligaciones que regirán las relaciones de {{ cliente.razon_social }} con los proveedores y terceros que, en virtud de cualquier relación contractual, presten servicios a la Entidad, le suministren productos o accedan a sus sistemas, instalaciones, información o cualquier otro activo, con la finalidad de garantizar que la seguridad de la información se preserva en toda la cadena de suministro.

Esta Política da cumplimiento a las medidas **op.ext.1 (Contratación y acuerdos de nivel de servicio)**, **op.ext.2 (Gestión diaria)**, **op.ext.3 (Protección de la cadena de suministro)** y **op.ext.4 (Interconexión de sistemas)** del Anexo II del Real Decreto 311/2022, así como a los controles del dominio A.5 (relaciones con proveedores) de la norma UNE-EN ISO/IEC 27001:2022.

## 2. ÁMBITO DE APLICACIÓN

La presente Política se aplica a:

a) Todo proveedor de productos o servicios que tenga acceso a información, sistemas, redes o instalaciones de la Entidad comprendidos en el alcance del SGSI, ya sea de forma puntual o continuada.

b) Todo subcontratista, en cualquier nivel, que actúe en nombre o por cuenta de un proveedor de la Entidad.

c) Todo prestador de servicios cloud (IaaS, PaaS, SaaS) utilizado por la Entidad para tratar información comprendida en el alcance del SGSI.

d) Todo profesional independiente o consultor externo que preste servicios profesionales a la Entidad con acceso a información sensible.

## 3. CLASIFICACIÓN DE PROVEEDORES POR NIVEL DE CRITICIDAD

A los efectos de la aplicación graduada de las exigencias del presente documento, los proveedores se clasificarán en los siguientes niveles, atendiendo al riesgo derivado de la relación:

### 3.1 Nivel CRÍTICO

Son proveedores CRÍTICOS aquellos cuyos servicios cumplen al menos uno de los siguientes criterios:

a) Tratan información clasificada como nivel **ALTO** en cualquier dimensión del ENS.

b) Soportan servicios esenciales de la Entidad cuya interrupción podría producir un impacto significativo.

c) Acceden a información de carácter personal a gran escala o de categorías especiales conforme al artículo 9 del RGPD.

d) Tienen acceso administrativo o privilegiado a sistemas comprendidos en el alcance del SGSI.

e) Constituyen un punto único de fallo para alguna función crítica de la Entidad.

### 3.2 Nivel ALTO

Son proveedores de nivel ALTO aquellos cuyos servicios:

a) Tratan información clasificada como nivel **MEDIO** en cualquier dimensión del ENS.

b) Acceden de forma habitual a información de carácter personal.

c) Tienen acceso a sistemas relevantes pero sin privilegios administrativos.

### 3.3 Nivel MEDIO

Son proveedores de nivel MEDIO aquellos cuyos servicios:

a) Tratan exclusivamente información clasificada como nivel **BAJO**.

b) Acceden de forma puntual a información o sistemas de la Entidad.

c) Suministran productos o servicios que no implican acceso continuado a información sensible.

### 3.4 Nivel BAJO

Son proveedores de nivel BAJO aquellos cuyos servicios no implican acceso a información o sistemas de la Entidad y cuyo riesgo derivado para la seguridad de la información es despreciable.

### 3.5 Asignación y revisión del nivel

La clasificación inicial corresponderá al Responsable del Servicio que solicita la contratación, en coordinación con el Responsable de la Seguridad. La clasificación se revisará al menos con carácter **anual** y siempre que se modifique sustancialmente el alcance de la relación.

## 4. EXIGENCIAS DE SEGURIDAD POR NIVEL

### 4.1 Exigencias comunes a todos los niveles

Con independencia del nivel de criticidad, todo proveedor deberá:

a) Suscribir las cláusulas de confidencialidad correspondientes.

b) Cumplir con la legislación vigente en materia de protección de datos personales y, cuando proceda, suscribir el contrato de encargo del tratamiento conforme al artículo 28 del RGPD.

c) Cumplir con la legislación vigente en materia de propiedad intelectual e industrial.

d) Notificar a la Entidad cualquier incidente de seguridad que afecte o pueda afectar a sus servicios o a la información de la Entidad.

### 4.2 Exigencias adicionales para proveedores de nivel MEDIO o superior

Adicionalmente, los proveedores de nivel MEDIO, ALTO o CRÍTICO deberán:

a) Disponer de un Sistema de Gestión de la Seguridad de la Información debidamente implantado, preferentemente certificado conforme a la norma UNE-EN ISO/IEC 27001 o equivalente.

b) Aceptar las obligaciones específicas que la Entidad les imponga contractualmente derivadas del presente documento y del SGSI.

c) Permitir auditorías de seguridad por parte de la Entidad o de terceros designados por esta, en los términos establecidos en el contrato.

d) Notificar a la Entidad cualquier incidente de seguridad relevante en un plazo máximo de **24 horas** desde su detección.

e) Disponer de un Plan de Continuidad del Servicio adecuado a los SLA contractualmente comprometidos.

### 4.3 Exigencias adicionales para proveedores de nivel ALTO o CRÍTICO

Adicionalmente, los proveedores de nivel ALTO o CRÍTICO deberán:

a) Estar adheridos al Esquema Nacional de Seguridad cuando presten servicios a entidades del sector público o cuando los servicios formen parte del alcance certificado de la Entidad cliente.

b) Disponer de certificación de conformidad con el ENS en categoría igual o superior a la del sistema al que sirven.

c) Disponer de cobertura aseguradora suficiente frente a los riesgos derivados de su actividad.

d) Notificar incidentes graves en un plazo máximo de **6 horas** y proporcionar informes de seguimiento periódicos.

e) Mantener trazabilidad completa de las acciones realizadas sobre los sistemas o información de la Entidad y poner los registros a disposición de esta cuando se solicite.

### 4.4 Exigencias adicionales para proveedores CRÍTICOS

Adicionalmente, los proveedores CRÍTICOS deberán:

a) Someterse a una evaluación inicial de seguridad antes del inicio de la prestación, conforme al procedimiento {{ proyecto.codigo_documento_base }}-217 (Procedimiento de Evaluación de Proveedores).

b) Someterse a auditorías periódicas de seguridad con la frecuencia establecida en el contrato y, en cualquier caso, al menos una vez al año.

c) Disponer de un equipo de respuesta a incidentes con disponibilidad 24x7.

d) Notificar incidentes críticos en un plazo máximo de **1 hora**.

e) Garantizar la trazabilidad y la disponibilidad de los datos al término de la relación contractual, mediante procedimientos de salida documentados.

## 5. PROCESO DE INCORPORACIÓN DE PROVEEDORES

### 5.1 Evaluación previa

Antes de iniciar la relación contractual con un nuevo proveedor que vaya a clasificarse como nivel MEDIO o superior, el Responsable del Servicio promoverá, en coordinación con el Responsable de la Seguridad, una **evaluación previa de seguridad** que incluirá, al menos:

a) Cuestionario de seguridad cumplimentado por el proveedor.

b) Verificación de las certificaciones declaradas por el proveedor.

c) Análisis de la solvencia técnica y financiera del proveedor en relación con los servicios a prestar.

d) Análisis de riesgos específico de la relación, conforme a la metodología MAGERIT v3.

e) Verificación, en su caso, de la cadena de subcontratación que el proveedor pretende utilizar.

### 5.2 Aprobación

La incorporación de proveedores de nivel ALTO o CRÍTICO requerirá la aprobación expresa del Responsable de la Seguridad, previo informe del Comité de Seguridad cuando este lo estime necesario.

### 5.3 Cláusulas contractuales

Los contratos con proveedores de nivel MEDIO o superior incorporarán, como mínimo, las siguientes cláusulas:

a) **Cláusula de confidencialidad**, con vigencia que se prolongará tras la extinción del contrato durante el periodo legalmente exigible y, en defecto de norma, durante al menos cinco años.

b) **Cláusula de protección de datos personales** que recoja, cuando proceda, los elementos del artículo 28.3 del RGPD para el contrato de encargo del tratamiento.

c) **Cláusula de medidas de seguridad técnicas y organizativas** que el proveedor se compromete a aplicar.

d) **Cláusula de notificación de incidentes** con los plazos correspondientes al nivel del proveedor.

e) **Cláusula de derecho de auditoría** que permita a la Entidad o a terceros designados por ella verificar el cumplimiento de las obligaciones de seguridad.

f) **Cláusula de subcontratación**, que prohíba al proveedor subcontratar la totalidad o parte de los servicios sin autorización previa y por escrito de la Entidad, y que extienda al subcontratista las mismas obligaciones impuestas al contratista principal.

g) **Cláusula de localización del tratamiento de datos**, especificando los países en los que el proveedor podrá tratar la información de la Entidad y, cuando proceda, las garantías exigibles para las transferencias internacionales.

h) **Cláusula de devolución y destrucción** de la información al término del contrato, con plazos definidos.

i) **Cláusula de continuidad y reversibilidad**, especialmente para proveedores cloud, que garantice la portabilidad de los datos y servicios.

j) **Cláusula de penalización** por incumplimiento de las obligaciones de seguridad.

k) **Cláusula de responsabilidad**, incluyendo cobertura aseguradora exigible cuando proceda.

## 6. GESTIÓN DIARIA DE LA RELACIÓN

### 6.1 Seguimiento

El Responsable del Servicio realizará un seguimiento continuo del cumplimiento de las obligaciones contractuales por parte de los proveedores, en particular en lo relativo a los acuerdos de nivel de servicio (SLA) y a las obligaciones de seguridad.

Para los proveedores de nivel ALTO o CRÍTICO, se mantendrán **reuniones periódicas de seguimiento de seguridad**, con la frecuencia establecida en el contrato y, en cualquier caso, al menos con carácter trimestral para los CRÍTICOS y semestral para los de nivel ALTO.

### 6.2 Auditorías

La Entidad podrá auditar, directamente o a través de terceros independientes, el cumplimiento de las obligaciones de seguridad por parte de sus proveedores, conforme a lo establecido en el contrato. Las auditorías se realizarán con previo aviso razonable, salvo en caso de incidente grave que justifique la actuación inmediata.

Los resultados de las auditorías se documentarán y, en caso de detectarse no conformidades, se acordará un plan de acción con plazos definidos para su subsanación.

### 6.3 Gestión de incidentes derivados de proveedores

Los incidentes de seguridad notificados por proveedores se gestionarán conforme al procedimiento {{ proyecto.codigo_documento_base }}-204 (Procedimiento de Gestión de Incidentes), sin perjuicio de las acciones específicas que el contrato contemple frente al proveedor responsable.

## 7. SERVICIOS CLOUD

### 7.1 Especialidades

Los servicios cloud (IaaS, PaaS, SaaS) presentan particularidades relevantes para la seguridad que justifican tratamiento específico:

a) **Modelo de responsabilidad compartida**: la Entidad y el proveedor cloud comparten responsabilidades sobre la seguridad, con una distribución que varía según el modelo de servicio.

b) **Localización de los datos**: la información puede tratarse en infraestructuras situadas en distintas jurisdicciones, con implicaciones legales relevantes.

c) **Acceso del proveedor a los datos**: el proveedor puede tener acceso técnico a la información alojada, lo que exige medidas adicionales de protección.

d) **Dependencia y reversibilidad**: la migración entre proveedores puede ser técnicamente compleja y costosa.

### 7.2 Requisitos específicos

Los servicios cloud utilizados por la Entidad para tratar información comprendida en el alcance del SGSI deberán cumplir, además de los requisitos generales aplicables a su nivel de criticidad, los siguientes requisitos específicos:

a) **Conformidad con el ENS** en categoría igual o superior a la del sistema servido, cuando los servicios formen parte del alcance certificado de la Entidad. La conformidad debe acreditarse mediante el correspondiente certificado emitido por una entidad acreditada por ENAC o, alternativamente, mediante la aplicación del **Perfil de Cumplimiento Específico de Servicios Cloud (CCN-STIC 887)**.

b) **Localización de los datos** preferentemente en territorio del Espacio Económico Europeo, evitando transferencias internacionales innecesarias.

c) **Cifrado de los datos en reposo y en tránsito** conforme a los requisitos del documento {{ proyecto.codigo_documento_base }}-107.

d) **Control de las claves de cifrado** mediante mecanismos del tipo BYOK o HYOK siempre que sea técnicamente viable.

e) **Trazabilidad de los accesos del personal del proveedor** a las infraestructuras que alojan información de la Entidad.

f) **Plan de salida y reversibilidad** documentado, que garantice la portabilidad de los datos y servicios al término de la relación.

### 7.3 Aprobación de nuevos servicios cloud

La incorporación de cualquier nuevo servicio cloud requerirá la aprobación previa del Responsable de la Seguridad. Queda expresamente prohibida la utilización de servicios cloud no autorizados (*shadow IT*).

## 8. CADENA DE SUMINISTRO DE PRODUCTOS

### 8.1 Adquisición de productos de seguridad

La adquisición de productos de seguridad se realizará atendiendo, cuando proceda, a las disposiciones del **Catálogo de Productos y Servicios de Seguridad de las Tecnologías de la Información y la Comunicación (CPSTIC)** del Centro Criptológico Nacional, dando preferencia a los productos en él incluidos.

### 8.2 Origen de los productos

La Entidad valorará el origen de los productos tecnológicos críticos, atendiendo a criterios de soberanía digital, fiabilidad del fabricante y existencia de obligaciones legales aplicables al fabricante en su jurisdicción de origen que pudieran afectar a la seguridad de la información.

### 8.3 Mantenimiento del software

Solo se utilizará software con soporte vigente del fabricante y se aplicarán los parches de seguridad publicados conforme a los plazos establecidos en el procedimiento {{ proyecto.codigo_documento_base }}-205 (Procedimiento de Gestión de Vulnerabilidades).

## 9. EXTINCIÓN DE LA RELACIÓN

### 9.1 Procedimiento de salida

La extinción de la relación con un proveedor seguirá un procedimiento de salida documentado que incluirá, al menos:

a) Devolución o eliminación segura de la información de la Entidad en posesión del proveedor.

b) Revocación de todos los accesos del proveedor a sistemas, redes e instalaciones de la Entidad.

c) Devolución de todas las credenciales, tarjetas, dispositivos y demás recursos físicos.

d) Verificación documentada de que se han cumplido todas las obligaciones derivadas del contrato.

e) Recordatorio de las obligaciones que subsisten tras la extinción (confidencialidad, secreto profesional, etc.).

### 9.2 Continuidad del servicio

Cuando la extinción de la relación afecte a servicios críticos para la Entidad, se planificará con la antelación suficiente para garantizar la continuidad del servicio mediante migración a un proveedor alternativo o internalización del servicio.

## 10. APROBACIÓN, REVISIÓN Y VIGENCIA

El presente documento ha sido aprobado por {{ cliente.organo_aprobador_politicas }} el {{ proyecto.fecha_aprobacion_inicial }} y será objeto de revisión, al menos, con la misma periodicidad que la Política de Seguridad de la Información de la que es desarrollo.

---

**Documento {{ proyecto.codigo_documento_base }}-112 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
