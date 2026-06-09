---
title: Lista de Sub-procesadores de FULKRO
codigo: FULKRO-SUB-LIST-001
version: 1.0
fecha_aprobacion: 2026-05-12
proxima_revision: 2027-05-12
periodicidad_revision: Anual + cambio sub-procesadores
aprobado_por: Marcos Mata García
cargo_aprobador: Delegado de Protección de Datos (interim)
clasificacion: Público · Trust Center
marco_normativo:
  - Reglamento (UE) 2016/679 (RGPD) Artículos 28, 13, 14
---

# Lista de Sub-procesadores de FULKRO

## Política de transparencia

FULKRO publica la presente lista actualizada de sub-procesadores como manifestación de su compromiso de transparencia, en cumplimiento de los artículos 28 y 13/14 del Reglamento (UE) 2016/679.

**Última actualización**: 12 de mayo de 2026.

**Próxima revisión**: mayo de 2027, sin perjuicio de la revisión extraordinaria con ocasión de la incorporación o baja de sub-procesadores.

## Mecanismos del Reglamento (UE) 2016/679 aplicables

- **DPA**: Acuerdo de Encargo de Tratamiento (Data Processing Agreement), suscrito conforme al artículo 28.3 del Reglamento (UE) 2016/679.

- **SCC 2021**: Cláusulas Contractuales Tipo aprobadas por Decisión de Ejecución (UE) 2021/914 de la Comisión Europea, aplicables a las transferencias internacionales de datos personales fuera del Espacio Económico Europeo.

- **TADPF**: Trans-Atlantic Data Privacy Framework, marco de transferencia transatlántica de datos personales entre la Unión Europea y los Estados Unidos de América, complementario a las Cláusulas Contractuales Tipo.

## Sub-procesadores activos (5)

### 1. Hetzner Online GmbH

| Elemento | Detalle |
|----------|---------|
| Servicio | Infraestructura de alojamiento (production servers y bases de datos) |
| Localización de los datos | Falkenstein, Alemania (Espacio Económico Europeo) |
| Mecanismo del Reglamento UE 2016/679 | Acuerdo de Encargo de Tratamiento suscrito · sin necesidad de Cláusulas Contractuales Tipo (intra-EEE) |
| Sub-encargados (sub-sub-procesadores) | Ninguno declarado por el sub-procesador |
| Enlace al DPA | https://www.hetzner.com/legal/order-processing/ |
| Contacto de privacidad | privacy@hetzner.com |
| Revisión anual | Self-Monitoring `check_sub_processor_dpa_expirations` |

### 2. Postmark (ActiveCampaign Inc.)

| Elemento | Detalle |
|----------|---------|
| Servicio | Correo electrónico transaccional |
| Localización de los datos | Región de datos UE (Fráncfort), seleccionada expresamente |
| Mecanismo del Reglamento UE 2016/679 | Acuerdo de Encargo de Tratamiento suscrito · Cláusulas Contractuales Tipo 2021 |
| Sub-encargados (sub-sub-procesadores) | AWS Fráncfort (Acuerdo de Encargo de Tratamiento heredado) |
| Enlace al DPA | https://postmarkapp.com/eu-privacy |
| Contacto de privacidad | privacy@postmarkapp.com |
| Revisión anual | Self-Monitoring `check_sub_processor_dpa_expirations` |

### 3. Anthropic PBC

| Elemento | Detalle |
|----------|---------|
| Servicio | Servicio de inteligencia artificial generativa (modelos Claude) para análisis de texto y RAG |
| Localización de los datos | Estados Unidos de América (principal) · región UE Fráncfort disponible |
| Mecanismo del Reglamento UE 2016/679 | Acuerdo de Encargo de Tratamiento + Cláusulas Contractuales Tipo 2021 + Trans-Atlantic Data Privacy Framework |
| Sub-encargados (sub-sub-procesadores) | AWS US-East · Google Cloud Platform US-Central (Acuerdo de Encargo de Tratamiento heredado) |
| Medidas de seudonimización | Aplicación de seudonimización a los datos enviados al sub-procesador · ausencia de identificadores personales |
| Enlace al DPA | https://www.anthropic.com/legal/dpa |
| Contacto de privacidad | privacy@anthropic.com |
| Revisión anual | Self-Monitoring `check_sub_processor_dpa_expirations` |

### 4. 360dialog GmbH

| Elemento | Detalle |
|----------|---------|
| Servicio | Integración con WhatsApp Business API (Business Solution Provider) |
| Localización de los datos | Alemania (Espacio Económico Europeo) |
| Mecanismo del Reglamento UE 2016/679 | Acuerdo de Encargo de Tratamiento suscrito · sin necesidad de Cláusulas Contractuales Tipo (intra-EEE) |
| Sub-encargados (sub-sub-procesadores) | WhatsApp/Meta · 360dialog actúa como Business Solution Provider intermediario (Acuerdo de Encargo de Tratamiento heredado) |
| Enlace al DPA | https://www.360dialog.com/dpa |
| Contacto de privacidad | privacy@360dialog.com |
| Revisión anual | Self-Monitoring `check_sub_processor_dpa_expirations` |

### 5. MinIO (autoalojado sobre Hetzner)

| Elemento | Detalle |
|----------|---------|
| Servicio | Almacenamiento de objetos (documentos, evidencias, copias de seguridad) |
| Localización de los datos | Alemania (Espacio Económico Europeo) · sobre infraestructura Hetzner autoalojada |
| Mecanismo del Reglamento UE 2016/679 | No existe relación de tercero proveedor de servicios · FULKRO controla la totalidad de la infraestructura |
| Cifrado | AES-256 en reposo · URLs firmadas con vigencia temporal limitada |
| Acuerdo de Encargo de Tratamiento | No procede · ausencia de relación de tercero |

## Suscripción a notificaciones de cambios

Los clientes podrán suscribirse al sistema de notificaciones automáticas de cambios en la cadena de sub-procesadores, mediante la siguiente vía:

- **Endpoint**: `POST /api/v1/legal/compliance/sub-processors/subscribe`

Los supuestos que activan la notificación al cliente suscrito son los siguientes:

a) Incorporación de un nuevo sub-procesador.

b) Baja de un sub-procesador existente.

c) Modificación sustancial de la jurisdicción aplicable al sub-procesador (cambio de localización de los datos).

d) Modificación sustancial de las condiciones contractuales del Acuerdo de Encargo de Tratamiento.

---

FULKRO · Madrid, España · DPO: dpo@fulkro.es · Seguridad: security@fulkro.es
Documento versión 1.0 · Próxima revisión anual: mayo 2027
