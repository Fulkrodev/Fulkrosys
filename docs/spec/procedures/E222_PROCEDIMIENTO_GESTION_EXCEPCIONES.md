# DOCUMENTO E-222 — PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES

**Es el procedimiento operativo que canaliza las desviaciones temporales respecto a la normativa interna del SGSI.** Asegura que toda excepción se solicita, evalúa, autoriza, registra, controla y caduca, evitando que las desviaciones se conviertan en debilidades permanentes.

```jinja
---
codigo_documento: "{{ proyecto.codigo_documento_base }}-222"
titulo: "Procedimiento de Gestión de Excepciones"
version: "{{ proyecto.version_actual }}"
fecha_aprobacion: "{{ proyecto.fecha_aprobacion_inicial }}"
fecha_proxima_revision: "{{ proyecto.proxima_revision }}"
clasificacion: "INTERNA"
propietario: "{{ responsables.responsable_seguridad.cargo }}"
politica_madre: "{{ proyecto.codigo_documento_base }}-100"
medidas_ens: ["org.4"]
---

# PROCEDIMIENTO DE GESTIÓN DE EXCEPCIONES DE {{ cliente.razon_social | upper }}

**Documento {{ proyecto.codigo_documento_base }}-222 — Versión {{ proyecto.version_actual }}**

---

## 1. OBJETO

Establecer el cauce formal para tramitar excepciones —desviaciones temporales y autorizadas— a las políticas, procedimientos y configuraciones de seguridad del SGSI de {{ cliente.razon_social }}, garantizando que cualquier desviación está justificada, valorada en términos de riesgo, autorizada por el órgano competente, sometida a controles compensatorios y limitada en el tiempo.

Este procedimiento desarrolla la medida **org.4 (proceso de autorización)** del Anexo II del Real Decreto 311/2022, conforme a las directrices de la guía CCN-STIC 802 sobre auditoría de la seguridad.

## 2. ALCANCE

Aplica a toda desviación respecto a:

- Políticas del SGSI ({{ proyecto.codigo_documento_base }}-100 a {{ proyecto.codigo_documento_base }}-126).
- Procedimientos del SGSI ({{ proyecto.codigo_documento_base }}-200 a {{ proyecto.codigo_documento_base }}-234).
- Configuraciones de baseline de hardening ({{ proyecto.codigo_documento_base }}-230).
- Reglas técnicas implantadas en herramientas de seguridad (firewall, EDR, MDM, IdP).
- Compromisos contractuales (cuando la desviación afecta a un tercero o a un cliente).

## 3. PRINCIPIOS GENERALES

1. **Toda excepción es temporal:** no se conceden excepciones indefinidas. La duración máxima inicial es de **6 meses**, prorrogable de forma motivada un máximo de dos veces hasta un total de **18 meses**. Pasado ese plazo, o se elimina la causa que motivó la excepción o se modifica la política/procedimiento.

2. **Toda excepción exige medidas compensatorias:** la persona solicitante propone controles que reduzcan el riesgo derivado de la desviación.

3. **Toda excepción se documenta y aprueba antes de su aplicación:** quedan prohibidas las excepciones de hecho o las regularizaciones a posteriori salvo en situaciones de emergencia operativa documentadas.

4. **Toda excepción es revocable** si el riesgo materializado supera el umbral asumido.

## 4. ROLES Y RESPONSABILIDADES

| Rol | Responsabilidades |
|---|---|
| **Solicitante** | Cumplimentar la solicitud, justificar la necesidad, proponer controles compensatorios. |
| **Responsable del Sistema** | Validar la viabilidad técnica de la excepción y de los controles compensatorios. |
| **Responsable de la Seguridad** | Evaluar el riesgo residual, recomendar aprobación o denegación, mantener el Registro de Excepciones. |
| **DPO** | Validar excepciones que afecten a tratamientos de datos personales. |
| **Aprobador** | Según la criticidad (apartado 5), aprueba o deniega formalmente la excepción. |
| **Auditor interno** | Revisar la base de excepciones en cada auditoría interna anual. |

## 5. NIVELES DE APROBACIÓN

| Nivel | Riesgo residual estimado | Aprobador competente | Plazo máximo de respuesta |
|---|---|---|---|
| **L1 — Bajo** | Sin impacto en datos personales ni en disponibilidad ≥ 4 h | Responsable del Sistema | 5 días hábiles |
| **L2 — Medio** | Impacto contenido, sin afectar a información CONFIDENCIAL+ ni a procesos críticos | Responsable de la Seguridad | 7 días hábiles |
| **L3 — Alto** | Afecta a información CONFIDENCIAL+ o a procesos del BIA con RTO ≤ 24 h | Comité de Seguridad | 15 días hábiles |
| **L4 — Crítico** | Afecta a categoría ALTA o a un compromiso contractual con cliente AAPP | Dirección General + Comité de Seguridad | 30 días hábiles |

{% if proyecto.categoria_ens == "ALTA" %}
**Categoría ALTA:** las excepciones L3 y L4 son adicionalmente notificadas al Responsable de la Información del cliente final cuando éste sea una entidad del sector público.
{% endif %}

## 6. FLUJO OPERATIVO

### Fase 1 — Solicitud (T+0)

1. El solicitante cumplimenta el formulario **F-222 — Solicitud de Excepción** con:
   - Identificación del solicitante y del área.
   - Política, procedimiento o configuración objeto de la excepción.
   - Justificación operativa detallada (problema que resuelve la excepción).
   - Alternativas evaluadas y motivo del rechazo.
   - Sistemas y datos afectados.
   - Duración solicitada (no superior a 6 meses).
   - Controles compensatorios propuestos.
   - Riesgo residual estimado.

2. La solicitud entra en el flujo del sistema de tickets corporativo con etiqueta `excepcion-sgsi` y se asigna automáticamente al Responsable del Sistema.

### Fase 2 — Análisis técnico (T+0 a T+3 días hábiles)

**Responsable:** Responsable del Sistema.

3. Verifica la viabilidad técnica de la solicitud y de los controles compensatorios.

4. Cuantifica el impacto en otros activos o procesos.

5. Si la excepción puede resolverse modificando la solución técnica sin necesidad de excepción, devuelve la solicitud con propuesta alternativa.

### Fase 3 — Análisis de riesgo (T+3 a T+7 días hábiles)

**Responsable:** Responsable de la Seguridad.

6. Reevalúa el riesgo residual conforme a la metodología MAGERIT v3 utilizada por la organización.

7. Determina el **nivel de aprobación** (apartado 5) y enruta al aprobador competente.

8. Si el riesgo residual supera los umbrales del Apetito de Riesgo definido en {{ proyecto.codigo_documento_base }}-AR-001, recomienda denegación.

### Fase 4 — Decisión y registro (según plazo del nivel)

**Responsable:** Aprobador competente.

9. Decide: APROBADA / APROBADA CON CONDICIONES / DENEGADA.

10. La decisión se firma electrónicamente y se incorpora al **Registro de Excepciones (R-222)**, con identificador único `EXC-AAAA-NNNN`.

11. El Responsable de la Seguridad notifica al solicitante en un máximo de 2 días hábiles desde la decisión.

### Fase 5 — Aplicación y supervisión continua

12. Si la excepción es APROBADA, el solicitante implementa los controles compensatorios y notifica al Responsable de la Seguridad la fecha real de inicio.

13. **Supervisión periódica** según nivel:

| Nivel | Frecuencia de revisión |
|---|---|
| L1 | Mensual (verificación de vigencia y compensatorios) |
| L2 | Mensual + verificación trimestral del riesgo |
| L3 | Quincenal + revisión de riesgo bimestral por Comité |
| L4 | Semanal durante el primer mes, después quincenal |

14. Las revisiones se documentan en el Registro de Excepciones (R-222) con sello de fecha y observaciones.

### Fase 6 — Cierre

15. **Por vencimiento:** 30 días antes de la fecha límite, el sistema notifica al solicitante para que:
    - Cierre la excepción habiendo regularizado la situación.
    - Solicite una **prórroga motivada** (que requiere de nuevo aprobación del nivel correspondiente).
    - Solicite una **modificación de política** si la excepción ha demostrado ser estructural.

16. **Por revocación:** si la supervisión detecta materialización de riesgo o incumplimiento de los controles compensatorios, el aprobador puede revocar la excepción inmediatamente. La revocación se notifica con plazo máximo de 48 horas para regularizar o escalar a incidente.

17. **Por regularización:** cuando se elimina la causa de la excepción, el solicitante notifica el cierre y el Responsable de la Seguridad lo refleja en R-222.

## 7. EXCEPCIONES DE EMERGENCIA

En caso de **emergencia operativa** (caída de servicio, incidente activo) que requiera saltarse temporalmente un control:

1. La persona con responsabilidad operativa puede aplicar la desviación inmediatamente comunicándolo simultáneamente al Responsable de la Seguridad por canal urgente.

2. En un plazo máximo de **24 horas**, debe presentar el formulario F-222 retroactivo con la documentación completa.

3. El Responsable de la Seguridad valora si la emergencia estaba justificada y, en caso contrario, abre **No Conformidad** conforme a {{ proyecto.codigo_documento_base }}-220.

4. Las excepciones de emergencia se etiquetan en R-222 como `tipo: emergencia` y son revisadas individualmente en cada Comité de Seguridad mensual.

## 8. INTEGRACIÓN CON OTROS PROCEDIMIENTOS

| Procedimiento | Relación |
|---|---|
| {{ proyecto.codigo_documento_base }}-220 (No Conformidades) | Una excepción no aprobada o vencida sin regularizar genera NC. |
| {{ proyecto.codigo_documento_base }}-218 (Auditoría Interna) | El auditor revisa el 100 % de excepciones L3/L4 y muestra del 20 % de L1/L2. |
| {{ proyecto.codigo_documento_base }}-AR-001 (Análisis de Riesgos) | Las excepciones aprobadas se incorporan al mapa de riesgos como riesgos asumidos temporalmente. |
| {{ proyecto.codigo_documento_base }}-219 (Revisión por la Dirección) | El cuadro de mando de excepciones se presenta anualmente. |

## 9. REGISTROS GENERADOS

| Código | Registro | Conservación |
|---|---|---|
| F-222 | Solicitud de Excepción | 6 años desde cierre |
| R-222 | Registro maestro de Excepciones | Permanente |
| L-222 | Log de revisiones periódicas | 3 años |

## 10. INDICADORES (KPI)

| Indicador | Fórmula | Objetivo |
|---|---|---|
| Excepciones vivas | recuento | < 30 (umbral revisado anualmente) |
| Excepciones vencidas sin cerrar | recuento | 0 |
| Tiempo medio de aprobación L1+L2 | media (días hábiles) | ≤ 5 |
| % excepciones revisadas en plazo | revisadas en plazo / requeridas | ≥ 95 % |
| Excepciones de emergencia justificadas | aprobadas / total emergencia | ≥ 90 % |

## 11. REVISIÓN

Este procedimiento se revisa **anualmente** o cuando:

- Cambien los umbrales de Apetito de Riesgo de la organización.
- Se modifique la guía CCN-STIC 802 en lo relativo a org.4.
- Se detecten patrones recurrentes que aconsejen modificar políticas en lugar de gestionar excepciones reiteradas.

Responsabilidad: **Responsable de la Seguridad**, con aprobación del **Comité de Seguridad**.
