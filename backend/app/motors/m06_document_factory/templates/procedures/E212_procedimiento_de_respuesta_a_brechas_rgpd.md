# DOCUMENTO E-212 — PROCEDIMIENTO DE RESPUESTA A BRECHAS RGPD

**Operativo de la Política E-119. Detalla el flujo desde la detección hasta la notificación y comunicación.**

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-212"
titulo: "Procedimiento de Respuesta a Brechas de Datos Personales"
version: "{{ proyecto.version_actual }}"
clasificacion: "INTERNA"
politica_madre: "{{ proyecto.codigo_documento_base }}-119"
---

# PROCEDIMIENTO DE RESPUESTA A BRECHAS DE DATOS PERSONALES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-212 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Detallar las acciones operativas desde la detección de una brecha de seguridad que afecta a datos personales hasta su notificación a la AEPD y, cuando proceda, la comunicación a los interesados, en desarrollo de la Política E-119 y en coordinación con el procedimiento de gestión de incidentes E-204.

## 2. FLUJO OPERATIVO

### Fase 1 — Detección y escalado (T+0 a T+2 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 1 | Detección del incidente (vía E-204) que potencialmente afecta a datos personales | Cualquier persona / SIEM |
| 2 | El Resp. Seguridad activa al DPO inmediatamente | Resp. Seguridad |
| 3 | El DPO valora si el incidente constituye una brecha de datos personales conforme al art. 4.12 RGPD | DPO |

### Fase 2 — Valoración del riesgo (T+2 a T+12 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 4 | Determinar: tipo de brecha (confidencialidad/integridad/disponibilidad), categorías de datos afectados, nº de interesados, volumen de registros | DPO + Resp. Seguridad |
| 5 | Evaluar nivel de riesgo para los derechos y libertades con los 6 criterios de E-119 §3.2 | DPO |
| 6 | Documentar la valoración en el **Formulario de Valoración de Brecha** (Anexo I) | DPO |

### Fase 3 — Decisión de notificación (T+12 a T+24 horas)

| Paso | Acción | Responsable |
|---|---|---|
| 7 | Si riesgo = sin riesgo → registrar en el Registro de Brechas sin notificar | DPO |
| 8 | Si riesgo = bajo/medio/alto → **notificar a la AEPD** (seguir Fase 4) | DPO |
| 9 | Si riesgo = alto → adicionalmente **comunicar a los interesados** (seguir Fase 5) | DPO |

### Fase 4 — Notificación a la AEPD (≤ 72 horas desde conocimiento)

| Paso | Acción | Responsable |
|---|---|---|
| 10 | Acceder a la sede electrónica de la AEPD: https://sedeaepd.gob.es | DPO |
| 11 | Cumplimentar el **formulario de notificación de brechas** con: naturaleza, categorías y nº de interesados, datos contacto DPO, consecuencias probables, medidas adoptadas | DPO |
| 12 | Si la notificación no puede completarse en 72h: enviar notificación parcial con motivos del retraso y completar después | DPO |
| 13 | Conservar el acuse de recibo de la notificación | DPO |
| 14 | Mantener a la AEPD informada de la evolución si se solicita | DPO |

### Fase 5 — Comunicación a los interesados (sin dilación si riesgo alto)

| Paso | Acción | Responsable |
|---|---|---|
| 15 | Redactar la comunicación en lenguaje claro y sencillo conforme a E-119 §5 | DPO + Comunicación |
| 16 | Canal de comunicación: email directo cuando se disponga del email del interesado; publicación en web corporativa cuando no sea posible la comunicación individual | DPO |
| 17 | Documentar los envíos realizados y los acuses de recibo | DPO |

### Fase 6 — Registro y cierre

| Paso | Acción | Responsable |
|---|---|---|
| 18 | Registrar la brecha completa en el **Registro de Brechas de Datos Personales** | DPO |
| 19 | Integrar las lecciones aprendidas en el informe post-incidente de E-204 | Resp. Seguridad + DPO |
| 20 | Si la brecha revela deficiencias en los controles: abrir acción correctiva | Resp. Seguridad |

## 3. INDICADORES

| Indicador | Objetivo |
|---|---|
| Notificaciones a la AEPD dentro del plazo de 72h | 100% |
| Brechas registradas en el Registro | 100% |
| Comunicaciones a interesados realizadas sin dilación (riesgo alto) | 100% |

---

**Documento {{ proyecto.codigo_documento_base }}-212 — Versión {{ proyecto.version_actual }} — Clasificación: INTERNA**

```

---
