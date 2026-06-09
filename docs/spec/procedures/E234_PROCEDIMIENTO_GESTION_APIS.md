# DOCUMENTO E-234 — PROCEDIMIENTO DE GESTIÓN DE APIs

**Es el procedimiento operativo que materializa las medidas mp.s.2 (protección de servicios web) y op.acc.5 (autenticación) en lo relativo a interfaces programáticas (APIs).** Define el ciclo de vida de las APIs de {{ cliente.razon_social }}, su gobierno, los controles obligatorios de seguridad y la integración con OWASP API Security.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-234"
titulo: "Procedimiento de Gestión de APIs"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_sistema.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-114, {{ proyecto.codigo_documento_base }}-121"
medidas_ens: ["mp.s.2", "mp.sw.1", "op.acc.5", "mp.com.2"]
---

# PROCEDIMIENTO DE GESTIÓN DE APIs DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-234 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para gobernar el ciclo de vida de las APIs (REST, GraphQL, gRPC, webhooks) que {{ cliente.razon_social }} expone o consume, garantizando confidencialidad, integridad, disponibilidad y trazabilidad conforme al Esquema Nacional de Seguridad y a las guías OWASP API Security Top 10 (versión vigente).

Este procedimiento desarrolla las medidas **mp.s.2 (protección de servicios web), mp.sw.1 (desarrollo seguro), op.acc.5 (mecanismo de autenticación) y mp.com.2 (protección de la confidencialidad)** del Anexo II del Real Decreto 311/2022 conforme a la guía CCN-STIC 804.

## 2. ALCANCE

Aplica a:

- APIs internas (servicios entre equipos del cliente).
- APIs B2B (compartidas con socios / clientes / proveedores).
- APIs públicas (consumibles por terceros sin acuerdo previo).
- Webhooks salientes y entrantes.
- Integraciones con SaaS de terceros vía API.

## 3. PRINCIPIOS

1. **API-first:** toda API se diseña con contrato (OpenAPI 3.x para REST, schema GraphQL, .proto para gRPC) antes de su implementación.
2. **Zero-trust:** ninguna API confía en la red de origen; toda llamada se autentica y autoriza.
3. **Mínimo privilegio:** los tokens y claves dan acceso solo a los recursos estrictamente necesarios.
4. **Defensa en profundidad:** combinación de WAF/API Gateway + autenticación + autorización + validación de entrada + rate limiting + monitorización.
5. **Trazabilidad completa:** cada llamada deja log con identidad, recurso, acción, resultado y timestamp.

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Equipo de Desarrollo** | Diseñar y construir la API conforme al estándar corporativo. |
| **API Product Owner** | Gobierno funcional, evolución, deprecación. |
| **Equipo de Plataforma** | Operar API Gateway, WAF, IdP de máquinas. |
| **Responsable de la Seguridad** | Aprobar diseños sensibles, supervisar postura, gestionar incidentes API. |
| **DPO** | Validar APIs que tratan datos personales. |
| **Equipo de QA** | Pruebas funcionales y de seguridad de la API antes de cada release. |

## 5. CICLO DE VIDA DE UNA API

### Fase 1 — Diseño y aprobación

1. Definición del contrato (OpenAPI / GraphQL schema / .proto) con:
   - Recursos y operaciones.
   - Modelos de datos y esquemas de validación.
   - Códigos de respuesta estándar.
   - Versión semántica del contrato.

2. Análisis de seguridad por diseño:
   - Clasificación de la información expuesta.
   - Identificación de operaciones sensibles (escritura, descarga masiva).
   - Aplicabilidad de RGPD (datos personales, transferencias internacionales).
   - Modelo de amenazas con base en OWASP API Top 10:
     - **API1:2023** Broken Object Level Authorization (BOLA).
     - **API2:2023** Broken Authentication.
     - **API3:2023** Broken Object Property Level Authorization.
     - **API4:2023** Unrestricted Resource Consumption.
     - **API5:2023** Broken Function Level Authorization.
     - **API6:2023** Unrestricted Access to Sensitive Business Flows.
     - **API7:2023** Server-Side Request Forgery (SSRF).
     - **API8:2023** Security Misconfiguration.
     - **API9:2023** Improper Inventory Management.
     - **API10:2023** Unsafe Consumption of APIs.

3. Aprobación por el Responsable de Seguridad (B2B y públicas) o por el Responsable del Sistema (internas).

### Fase 2 — Construcción

4. Implementación con frameworks corporativos aprobados que ofrezcan controles por defecto (validación, serialización segura, rate limiting).

5. **Autenticación** según el caso:

| Caso de uso | Mecanismo |
|---|---|
| Usuario en navegador | OAuth 2.0 + OIDC con IdP corporativo (Authorization Code + PKCE) |
| Servicio interno | mTLS o tokens OAuth 2.0 client_credentials de corta duración |
| Partner B2B | mTLS y/o OAuth 2.0 client_credentials con rotación trimestral |
| Pública con cuotas | API key + OAuth 2.0; API key nunca por sí sola para datos sensibles |
| Webhook entrante | Firma HMAC SHA-256 con clave compartida + TLS |

6. **Autorización** mediante claims/scopes verificados en cada endpoint, con tests automatizados de BOLA/BFLA en pipeline.

7. **Validación de entrada** estricta basada en el contrato (no se confía en parámetros de cliente). Sanitización de salida cuando aplique.

8. **Rate limiting** por consumidor (token, API key o IP en caso de pública sin token).

9. **Cifrado en tránsito obligatorio** (TLS 1.2+ con cipher suites conforme a CCN-STIC 807).

### Fase 3 — Pruebas

10. Test suite obligatorio en pipeline CI:
    - Pruebas funcionales con cobertura ≥ 80 % de endpoints.
    - **Pruebas de seguridad automatizadas:** ZAP API scan, Schemathesis (fuzzing basado en contrato), 42Crunch / Stoplight si están disponibles.
    - **Pruebas de autorización:** matriz de roles vs endpoints validada como contract test.
    - SCA y SAST conforme a {{ proyecto.codigo_documento_base }}-114.

11. Pre-producción conforme a {{ proyecto.codigo_documento_base }}-225 con pruebas de carga representativas (P95 latencia, error-rate ≤ 0,1 %).

### Fase 4 — Publicación y despliegue

12. Despliegue conforme a {{ proyecto.codigo_documento_base }}-224 con publicación en el **API Gateway corporativo** (Kong / Apigee / AWS API Gateway / Azure APIM).

13. El API Gateway aplica:
    - Terminación TLS y revalidación contra el backend.
    - Rate limiting global y por consumidor.
    - Validación del contrato (schema enforcement) cuando esté soportado.
    - Logging y forwarding al SIEM ({{ proyecto.codigo_documento_base }}-223).
    - WAF en modo prevención para APIs públicas.
    - Inyección de cabeceras de seguridad (HSTS, X-Content-Type-Options, etc.).

14. Publicación en el **catálogo corporativo de APIs** (developer portal interno) con: contrato, ejemplos, política de uso, contacto del propietario.

### Fase 5 — Operación

15. **Monitorización continua:**
    - Latencia, throughput, error rate.
    - Patrones anómalos (volumen atípico, errores de autorización masivos, descargas en bloque).
    - Detección de claves o tokens filtrados (revisión periódica con feeds tipo HIBP).

16. **Gestión de credenciales de consumidor:**
    - Tokens OAuth de larga duración prohibidos; usar refresh tokens cuando aplique.
    - API keys con rotación cada 6 meses por defecto, inmediata ante sospecha.
    - Credenciales nunca compartidas entre entornos.

17. **Revisión trimestral del catálogo:** detección de APIs sin propietario, sin tráfico, sin documentación o con vulnerabilidades.

### Fase 6 — Versionado y deprecación

18. Versionado semántico (`/v1`, `/v2`...) con compatibilidad hacia atrás durante el periodo de deprecación.

19. **Plazo mínimo de deprecación:** 6 meses para APIs internas, 12 meses para B2B y públicas, comunicado con anticipación al developer portal.

20. Tras la deprecación, la versión antigua se retira y queda registrada en el catálogo histórico.

### Fase 7 — Baja

21. Comunicación al consumidor con plazo razonable.
22. Revocación de credenciales asociadas.
23. Registro de la baja y, si afectaba a tratamientos de datos personales, validación con DPO.

## 6. APIs CONSUMIDAS DE TERCEROS

24. Inventario de las APIs consumidas con propietario interno.
25. Validación previa de credenciales y rotación periódica.
26. Validación de respuesta (no se confía ciegamente en datos del proveedor).
27. **Manejo de fallos** del proveedor (circuit breaker, fallback) para evitar cascadas.
28. Inclusión de la dependencia en el inventario de proveedores ({{ proyecto.codigo_documento_base }}-216) cuando aplique.

## 7. CASOS PARTICULARES

### 7.1. APIs públicas con datos personales

- Consentimiento o base legal documentados.
- Minimización de los datos devueltos.
- Pseudonimización cuando sea técnicamente viable.
- Auditoría reforzada de accesos.

### 7.2. APIs de IA

- Política específica de input/output filtering.
- Limitación de longitud para prevenir DoS de coste.
- Bloqueo de temáticas prohibidas alineado con el AI Act.

### 7.3. Webhooks

- Firma HMAC obligatoria.
- Verificación de firma en destino antes de procesar.
- Reintentos con backoff exponencial y dead-letter queue.

## 8. INTEGRACIÓN CON OTROS PROCEDIMIENTOS

| Procedimiento | Relación |
|---|---|
| {{ proyecto.codigo_documento_base }}-204 (Incidentes) | Compromiso de credenciales API → incidente. |
| {{ proyecto.codigo_documento_base }}-205 (Vulnerabilidades) | Hallazgos de pentest API se canalizan al inventario. |
| {{ proyecto.codigo_documento_base }}-216 (Proveedores) | APIs consumidas son tratadas como dependencias de proveedor. |
| {{ proyecto.codigo_documento_base }}-218 (Auditoría interna) | El catálogo de APIs y su postura se audita anualmente. |

## 9. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| INV-api | Catálogo de APIs (expuestas y consumidas) | Permanente |
| F-234 | Solicitud de Publicación de API | 6 años |
| R-234.1 | Informes ZAP / Schemathesis por release | 24 meses |
| R-234.2 | Actas trimestrales del API Governance Board | 3 años |
| L-234 | Logs de API Gateway en SIEM | conforme {{ proyecto.codigo_documento_base }}-223 |

## 10. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Cobertura del catálogo | APIs en catálogo / APIs detectadas | ≥ 95 % |
| % APIs con escaneo en pipeline | con escaneo / total | 100 % |
| Hallazgos OWASP API críticos abiertos | recuento | 0 |
| Tiempo medio de revocación de credencial comprometida | media horas | ≤ 1 h |
| % APIs con MFA / mTLS | con autenticación robusta / total | 100 % B2B y privilegiadas |

## 11. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Se publique nueva versión de OWASP API Security Top 10.
- Cambien las medidas mp.s.2 / mp.sw.1 / op.acc.5 en CCN-STIC 804.
- Se sustituya el API Gateway corporativo.
- Se incorporen nuevas categorías de API (IA generativa, M2M industrial).

Responsabilidad: **Responsable del Sistema** + **API Product Owner**, con aprobación del **Responsable de la Seguridad**.
