# DOCUMENTO E-235 — PROCEDIMIENTO DE SELLADO DE TIEMPO

**Es el procedimiento operativo que materializa la medida _mp.info.4 (Sellos de tiempo)_ del Anexo II del Real Decreto 311/2022.** Esta medida es un **refuerzo exigible únicamente a la categoría ALTA**: define cómo {{ cliente.razon_social }} garantiza la datación fiable e irrefutable de las evidencias y registros críticos mediante sellos de tiempo cualificados emitidos por una autoridad de sellado de confianza (TSA).

> **AVISO DE APLICABILIDAD.** Para categorías BÁSICA y MEDIA esta medida **no aplica** (mp.info.4 solo se exige en ALTA). El presente procedimiento se incorpora al cuerpo documental como **procedimiento documentado**; la contratación efectiva de la TSA cualificada y la integración técnica RFC 3161 se ejecutan en el arranque del **primer proyecto de categoría ALTA**. Hasta entonces, la cronología e integridad de los registros se sostienen sobre el mecanismo interno descrito en la sección 4.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-235"
titulo: "Procedimiento de Sellado de Tiempo"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-107"
medidas_ens: ["mp.info.4"]
aplica_categorias: ["ALTA"]
---

# PROCEDIMIENTO DE SELLADO DE TIEMPO DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-235 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer las acciones operativas para dotar de **datación fiable, verificable e irrefutable** a las evidencias, registros de actividad y documentos críticos de {{ cliente.razon_social }}, de modo que pueda demostrarse de forma fehaciente que un determinado dato existía en un instante concreto y no ha sido alterado posteriormente.

Este procedimiento desarrolla la medida **mp.info.4 (Sellos de tiempo)** del Anexo II del Real Decreto 311/2022, alineada con la guía **CCN-STIC 807 (criptología en el ENS)** y con el **Reglamento (UE) 910/2014 (eIDAS)** en lo relativo a sellos electrónicos de tiempo cualificados.

## 2. ALCANCE

Aplica **exclusivamente a sistemas de categoría ALTA** (la medida mp.info.4 no es exigible en BÁSICA ni MEDIA). Dentro de ese alcance cubre:

- Registros de auditoría y trazas con valor probatorio (op.exp.8).
- Evidencias de cumplimiento aportadas a la auditoría de certificación ENAC.
- Documentos firmados electrónicamente cuyo momento de firma deba acreditarse frente a terceros.
- Asientos del registro de actividad que sustenten la respuesta ante incidentes (op.exp.7) o requerimientos legales.

## 3. MARCO NORMATIVO

- **RD 311/2022, Anexo II — mp.info.4 (Sellos de tiempo)**: refuerzo R1 en categoría ALTA. Criterio de conformidad: *sello de tiempo cualificado emitido por una autoridad de sellado de confianza*.
- **CCN-STIC 807**: empleo de mecanismos criptográficos acreditados en el ENS.
- **Reglamento (UE) 910/2014 (eIDAS), art. 41–42**: sellos cualificados de tiempo electrónico y sus efectos jurídicos.
- **RFC 3161 / RFC 5816**: protocolo Time-Stamp Protocol (TSP) y formato del token de sello (`.tsr`).

## 4. MECANISMO INTERNO DE INTEGRIDAD CRONOLÓGICA (base actual)

Con independencia del sellado cualificado externo, la plataforma sostiene de forma permanente la **integridad y el orden cronológico** de los registros mediante dos mecanismos propios:

1. **Cadena de hash del registro de auditoría (`audit_log`)** — cada asiento encadena un `SHA-256` con el hash del asiento anterior (trigger inmutable en base de datos). Cualquier alteración o reordenación retroactiva rompe la cadena y es detectable. Esto aporta **integridad + secuencia**, no datación cualificada por tercero de confianza.
2. **Firmas Ed25519 de eventos críticos (motor de firma)** — los eventos firmados incorporan su instante UTC (`signed_at`) y un `event_hash`, verificables con la clave pública.

> **Brecha de cualificación (honestidad documental).** Estos mecanismos son **internos**: prueban integridad y cronología relativa, pero **no constituyen un sello de tiempo _cualificado_** en el sentido de eIDAS (que requiere una TSA acreditada e independiente). La sección 5 cubre esa brecha para los proyectos ALTA.

## 5. SELLADO DE TIEMPO CUALIFICADO (TSA eIDAS)

Para los sistemas de categoría ALTA se contrata un **prestador cualificado de servicios de confianza (TSP)** que emita sellos de tiempo conforme a eIDAS y RFC 3161:

1. **Selección de la TSA** — prestador incluido en la _Trusted List_ española/europea (p. ej. FNMT-RCM, Uanataca, u otro TSP cualificado), a confirmar en el arranque del primer proyecto de categoría ALTA.
2. **Solicitud del sello** — para cada evidencia crítica se calcula su huella `SHA-256` y se envía una _TimeStampRequest_ (RFC 3161) al endpoint TSP; **nunca se envía el contenido**, solo la huella.
3. **Custodia del token** — el _TimeStampToken_ (`.tsr`) devuelto se almacena junto al documento/evidencia en el gestor documental (IDMS), enlazado a su `content_hash`.
4. **Verificación** — la validez del sello (firma de la TSA + correspondencia de huella) se comprueba en cualquier momento contra el certificado de la TSA.

## 6. PROCEDIMIENTO OPERATIVO

| Paso | Acción | Responsable | Evidencia |
|------|--------|-------------|-----------|
| 1 | Identificar el conjunto de evidencias/registros sujetos a sellado | {{ responsables.responsable_seguridad.cargo }} | Inventario de activos de información |
| 2 | Calcular la huella `SHA-256` de cada elemento | Plataforma (automático) | `content_hash` en IDMS |
| 3 | Solicitar el sello cualificado a la TSA (RFC 3161) | Plataforma / TSP | `.tsr` recibido |
| 4 | Custodiar el token enlazado a la evidencia | Plataforma (IDMS) | Registro de sellos de tiempo |
| 5 | Verificar periódicamente la validez de los sellos | {{ responsables.responsable_seguridad.cargo }} | Informe de verificación |

## 7. ROLES Y RESPONSABILIDADES

- **{{ responsables.responsable_seguridad.cargo }}**: aprueba el alcance, supervisa la contratación de la TSA y la verificación periódica.
- **Equipo de Fulkro**: implementa y opera la integración técnica RFC 3161 y la custodia de tokens.

## 8. REGISTRO Y CONSERVACIÓN DE EVIDENCIAS

Los tokens de sello (`.tsr`) se conservan durante el mismo periodo que la evidencia sellada, con un mínimo alineado a la política de retención de registros ({{ proyecto.codigo_documento_base }}-127, op.exp.8). La pérdida de un token no invalida la evidencia, pero sí su valor probatorio cualificado.

## 9. REVISIÓN

Este procedimiento se revisa con periodicidad **anual** o ante cambios en el prestador TSA, en la normativa eIDAS aplicable o en la categoría del sistema. La próxima revisión está prevista para {{ proyecto.proxima_revision }}.
```
