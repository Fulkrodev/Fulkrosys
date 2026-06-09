---
title: Seguridad de la Cadena de Suministro conforme a la Directiva NIS2
codigo: FULKRO-NIS2-SUPPLY-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Anual + cambio sub-procesadores
aprobado_por: Marcos Mata García
cargo_aprobador: Responsable de Seguridad de la Información (interim)
clasificacion: Interno · Auditor
marco_normativo:
  - Directiva (UE) 2022/2555 (NIS2) Artículo 21.2.d)
  - ISO/IEC 27001:2022 Anexo A.5.19 a A.5.23
---

# Seguridad de la Cadena de Suministro conforme a la Directiva NIS2

## 1. Inventario de sub-procesadores

El inventario detallado de los cinco sub-procesadores activos se encuentra consolidado en el documento FULKRO-SUB-LIST-001 (Lista de Sub-procesadores), al que se remite expresamente. Los sub-procesadores actuales son:

a) Hetzner Online GmbH (infraestructura como servicio).

b) Postmark, ActiveCampaign Inc. (correo transaccional).

c) Anthropic PBC (servicio de inteligencia artificial generativa).

d) 360dialog GmbH (mensajería WhatsApp Business).

e) MinIO en régimen de autoalojamiento (almacenamiento de objetos, sin condición de tercero proveedor).

## 2. Evaluación de seguridad por proveedor

Para cada uno de los sub-procesadores se realiza la siguiente evaluación de seguridad con periodicidad mínima anual:

### 2.1 Verificación de instrumentos contractuales

a) Existencia y vigencia del Acuerdo de Encargo de Tratamiento (DPA).

b) Existencia y vigencia, en su caso, de las Cláusulas Contractuales Tipo (SCC 2021) para los supuestos de transferencia internacional fuera del Espacio Económico Europeo.

c) Existencia y vigencia, en su caso, de mecanismos adicionales de transferencia (Trans-Atlantic Data Privacy Framework, entre otros).

### 2.2 Verificación de localización del tratamiento

Se verifica la residencia efectiva de los datos en territorio del Espacio Económico Europeo o, en caso contrario, el cumplimiento de los mecanismos de transferencia internacional aplicables.

### 2.3 Verificación de cifrado

a) Cifrado en tránsito mediante el protocolo TLS versión 1.3 o superior.

b) Cifrado en reposo mediante mecanismos reconocidos en el estado del arte.

### 2.4 Verificación de sub-encargados

Se verifica la transparencia del proveedor en relación con la utilización de sub-encargados (sub-sub-procesadores), conforme al artículo 28.2 del Reglamento (UE) 2016/679.

### 2.5 Monitorización continua

El sistema Self-Monitoring de FULKRO ejecuta diariamente el control identificado como `check_sub_processor_dpa_expirations`, que verifica de manera automática la vigencia de los Acuerdos de Encargo de Tratamiento y emite alertas con antelación suficiente a su vencimiento.

## 3. Lista de comprobación para incorporación de nuevos proveedores (vendor onboarding)

La incorporación de un nuevo sub-procesador se realiza conforme al siguiente procedimiento estructurado:

### 3.1 Cuestionario de seguridad

Cumplimentación por parte del proveedor candidato de un cuestionario de seguridad estructurado, integrado por treinta y cinco preguntas distribuidas en los siguientes dominios:

a) Gobierno de seguridad y certificaciones.

b) Gestión de identidades y accesos.

c) Cifrado y gestión de claves.

d) Seguridad de la red e infraestructura.

e) Gestión de incidentes y continuidad.

f) Cumplimiento normativo y transferencias internacionales.

g) Subcontratación y sub-encargados.

### 3.2 Formalización del Acuerdo de Encargo de Tratamiento

Suscripción del Acuerdo de Encargo de Tratamiento conforme al modelo de FULKRO o, en su caso, al modelo del proveedor adaptado a las exigencias del artículo 28.3 del Reglamento (UE) 2016/679.

### 3.3 Cláusulas Contractuales Tipo

Suscripción de las Cláusulas Contractuales Tipo aprobadas por la Comisión Europea en 2021, en los supuestos en los que concurra transferencia internacional fuera del Espacio Económico Europeo.

### 3.4 Integración en la evaluación de riesgos

Integración del nuevo sub-procesador en el documento FULKRO-ISMS-RISK-001 (Evaluación de Riesgos del SGSI), con identificación de los riesgos específicos asociados y de las salvaguardas aplicables.

### 3.5 Aceptación y entrada en producción

Aceptación formal por parte del Responsable de Seguridad de la Información y entrada en producción del sub-procesador, con actualización del documento FULKRO-SUB-LIST-001.

## 4. Procedimiento de desvinculación de proveedor (vendor offboarding)

La desvinculación de un sub-procesador se realiza conforme al siguiente procedimiento:

### 4.1 Verificación de eliminación de datos

Obtención por parte del sub-procesador de certificación documental relativa a la destrucción de los datos personales y operacionales transferidos durante la vigencia de la relación contractual, conforme a los términos del Acuerdo de Encargo de Tratamiento.

### 4.2 Revocación inmediata de credenciales

Revocación inmediata de todas las credenciales de acceso programático (claves de API) concedidas al sub-procesador.

### 4.3 Régimen de copias de seguridad

Verificación de los plazos de retención de copias de seguridad en posesión del sub-procesador, conforme a los términos específicos del Acuerdo de Encargo de Tratamiento.

### 4.4 Comunicación a interesados

Cuando proceda, comunicación a los interesados afectados de la modificación de la cadena de sub-procesadores, mediante los canales habilitados al efecto.

## 5. Monitorización continua

La monitorización continua de la cadena de suministro se realiza mediante:

### 5.1 Control automatizado

El sistema Self-Monitoring ejecuta diariamente el control `check_sub_processor_dpa_expirations`, que verifica la vigencia de los Acuerdos de Encargo de Tratamiento e identifica con antelación los próximos vencimientos.

### 5.2 Revisión anual

Cada sub-procesador es objeto de revisión anual, comprendiendo la verificación de los extremos detallados en la sección 2 del presente documento.

### 5.3 Activadores de revisión extraordinaria

Procederá la revisión extraordinaria de la situación de un sub-procesador en los siguientes supuestos:

a) Incidente de seguridad notificado o reconocido por el sub-procesador.

b) Operación de fusión o adquisición que afecte al sub-procesador.

c) Modificación sustancial de la política de utilización de sub-sub-procesadores por parte del sub-procesador.

d) Resolución judicial o administrativa que afecte al marco jurídico aplicable a la prestación del servicio.

## 6. Referencia normativa

a) Artículo 21.2.d) de la Directiva (UE) 2022/2555, relativo a la seguridad de la cadena de suministro.

b) Controles A.5.19 a A.5.23 del Anexo A de la norma UNE-EN ISO/IEC 27001:2022, relativos a la gestión de proveedores.

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
